import argparse
import json
import os
import pickle
import re
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    db,
    utility,
)
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

# custom BM25 encoder needed; to output format: Dict[int, float] compatible with Milvus sparse vector field
from .sparse import BM25SparseEncoder

# load env vars from .env file
load_dotenv()

# Environment variable keys
ENV_MILVUS_URI = "MILVUS_URI"
ENV_MILVUS_TOKEN = "MILVUS_TOKEN"
ENV_MILVUS_DB = "MILVUS_DB"  # okay to not set as env var; it has a default if blank

# Runtime defaults
DATA_ROOT = Path("data")
DEFAULT_COLLECTION = "sg_budget_evidence"
DEFAULT_MODEL = "BAAI/bge-base-en-v1.5"  # recommended model for local embedding with balanced quality / speed
DEFAULT_CHUNK_SIZE = 400
DEFAULT_CHUNK_OVERLAP = 80
DEFAULT_EMBED_BATCH_SIZE = 32  # to control how many chunks to embed per model call to avoid spiking RAM/CPU

# Operational constants
ARTIFACTS_DIR = Path("artifacts")
BM25_MODEL_FILENAME = "bm25_model.pkl"
DELETE_BATCH_SIZE = 50  # Controlled delete for incremental runs and smoothen vector db traffic
DENSE_INDEX_PARAMS = {"index_type": "HNSW", "metric_type": "IP", "params": {"M": 8, "efConstruction": 200}}
SPARSE_INDEX_PARAMS = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}


def list_pdf_files(data_root: Path) -> List[Path]:
    """List pdf files with validation"""
    if not data_root.exists():
        raise RuntimeError(f"Data root does not exist: {data_root}")
    if not data_root.is_dir():
        raise RuntimeError(f"Data root is not a directory: {data_root}")
    # return sorted pdfs for defensive idempotent runs (listings) before chunking
    return sorted(p for p in data_root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def infer_doc_type(pdf_path: Path, data_root: Path) -> str:
    """Infer doc types with validation.
    Per design, should only exist one from ('budget_statements', 'round_up_speech', 'annex')
    """
    rel = pdf_path.relative_to(data_root)  # define relative path to data folder
    if len(rel.parts) < 2:  # .parts is a tuple of the individual components (directories and file name) of the path.
        raise RuntimeError(
            f"Cannot infer doc_type for '{pdf_path}'. Expected path like data/<doc_type>/.../<file>.pdf."
        )
    return rel.parts[0]  # return first element of [<doc_type>, ...]


def infer_financial_year_from_filename(pdf_path: Path) -> int:
    match = re.search(r"fy(\d{4})", pdf_path.stem.lower())  # search for 4 digits after 'fy' by design after manually rename pdf files
    if not match:
        raise RuntimeError(f"Cannot infer financial_year from filename '{pdf_path.name}'. Expected token fyYYYY.")
    return int(match.group(1))


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract pdf text with defensive validation"""
    reader = PdfReader(str(pdf_path))  # Opens PDF with PyPDF, expects str path input
    pages = [(page.extract_text() or "") for page in reader.pages] # Loops over every page during extraction, avoid crash if blank page ""
    text = "\n".join(pages)  # join pages with newlines
    text = re.sub(r"\n{3,}", "\n\n", text) # Collapses excessive whitespace newlines
    text = text.strip() # trim leading/trailing whitespace
    if not text:  # Fail fast if unexpected input
        raise RuntimeError(f"No extractable text found in PDF: {pdf_path}")
    return text


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[Tuple[str, int, int]]:
    """Overlapping chunk to prepare for embedding.
    Per chunk: (text, chunk_start, chunk_end)
    Return list of chunks [(chunk), (chunk), ...]
    """
    words = text.split()
    chunks: List[Tuple[str, int, int]] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append((" ".join(words[start:end]), start, end))
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def build_chunk_records(data_root: Path, pdf_paths: List[Path], chunk_size: int, overlap: int) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []  # records: list of dict
    for pdf_path in pdf_paths:
        doc_type = infer_doc_type(pdf_path, data_root)
        financial_year = infer_financial_year_from_filename(pdf_path)
        rel_path = pdf_path.relative_to(data_root).as_posix()  # <doc_type>/.../<filename>.pdf; e.g. round_up_speech/fy2018_budget_debate_round_up_speech.pd
        text = extract_pdf_text(pdf_path)
        chunks = chunk_text(text, chunk_size, overlap)
        if not chunks:
            raise RuntimeError(f"No chunks generated for PDF: {pdf_path}")

        # Replace \, / with _ for safer field ids
        doc_slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", rel_path)  # doc_slug e.g. round_up_speech_fy2018_budget_debate_round_up_speech.pd
        for idx, (chunk, start, end) in enumerate(chunks):
            records.append(
                {
                    "chunk_id": f"{doc_slug}-c{idx}",  # keep for tracability; <doc_type>/.../<filename>.pdf-c<idx>
                    "doc_id": doc_slug,  # keep for tracability
                    "source_path": rel_path,  # keep for tracability
                    "doc_type": doc_type,  # # keep to optimize retrieval
                    "financial_year": financial_year,  # keep to optimize retrieval
                    "chunk_start": start,
                    "chunk_end": end,
                    "text": chunk,
                }
            )
    return records


def embed_texts_local(model_name: str, texts: List[str], batch_size: int) -> List[List[float]]:
    """
    When running SentenceTransformer(), Hugging Face downloads models to:
        ~/.cache/huggingface/
    For this reason, may be better to use venv instead of docker for repo reproducibility
    for infra to be lightweight.

    Otherwise, need to re-download model everytime if docker launch without persisting the model to volume.
    """
    model = SentenceTransformer(model_name, device="cpu")  
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return [vector.astype("float32").tolist() for vector in vectors]


def ensure_collection(name: str, embedding_dim: int) -> Collection:
    """If collection exist, perform validation tests.
    If collection don't exist, create new collections"""
    # If collection exist
    if utility.has_collection(name):
        collection = Collection(name)
        dense_field = next((field for field in collection.schema.fields if field.name == "dense_vector"), None)

        # validation tests
        if dense_field is None:
            raise RuntimeError(f"Existing collection '{name}' is missing dense_vector field.")
        existing_dim = dense_field.params.get("dim")
        if existing_dim and int(existing_dim) != embedding_dim:
            raise RuntimeError(
                f"Collection '{name}' dense_vector dim={existing_dim} does not match model dim={embedding_dim}."
            )
        return collection

    # Create new collections if collection not exist
    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="source_path", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="financial_year", dtype=DataType.INT64),
        FieldSchema(name="chunk_start", dtype=DataType.INT64),
        FieldSchema(name="chunk_end", dtype=DataType.INT64),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim),
        FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
    ]
    schema = CollectionSchema(fields, description="SG budget evidence store")
    collection = Collection(name, schema)
    collection.create_index(
        field_name="dense_vector",
        index_params=DENSE_INDEX_PARAMS,
    )
    collection.create_index(
        field_name="sparse_vector",
        index_params=SPARSE_INDEX_PARAMS,
    )
    return collection


def connect_milvus() -> None:
    milvus_uri = os.getenv(ENV_MILVUS_URI)
    milvus_token = os.getenv(ENV_MILVUS_TOKEN)
    milvus_db = os.getenv(ENV_MILVUS_DB)
    if not milvus_uri:
        raise RuntimeError(f"Missing required environment variable: {ENV_MILVUS_URI}")
    if not milvus_token:
        raise RuntimeError(f"Missing required environment variable: {ENV_MILVUS_TOKEN}")
    connections.connect(uri=milvus_uri, token=milvus_token)
    if milvus_db:
        db.using_database(milvus_db)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load local SG budget PDFs into Milvus with dense+sparse vectors")
    parser.add_argument("--data-root", default=str(DATA_ROOT), help="Root directory for recursive PDF ingestion")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Milvus collection name")
    parser.add_argument("--embedding-model", default=DEFAULT_MODEL, help="SentenceTransformer model name")
    parser.add_argument("--embedding-batch-size", type=int, default=DEFAULT_EMBED_BATCH_SIZE)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size in words")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP, help="Chunk overlap in words")
    parser.add_argument(
        "--reset-docs",
        action="store_true",
        help="Delete existing chunks for discovered doc_ids before ingesting",
    )
    parser.add_argument(
        "--recreate-collection",
        action="store_true",
        help="Drop and recreate the collection before ingest (strong idempotency)",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root)
    pdf_paths = list_pdf_files(data_root)
    if not pdf_paths:
        raise RuntimeError(f"No PDF files found under: {data_root}")
    print(f"Found {len(pdf_paths)} PDF files under '{data_root}'")

    chunk_records = build_chunk_records(data_root, pdf_paths, args.chunk_size, args.chunk_overlap)
    if not chunk_records:
        raise RuntimeError("No chunk records were created.")
    print(f"Built {len(chunk_records)} chunk records")

    texts = [record["text"] for record in chunk_records]

    bm25 = BM25SparseEncoder()
    bm25.fit(texts)
    sparse_vectors = bm25.encode_documents(texts)

    ARTIFACTS_DIR.mkdir(exist_ok=True)
    with open(ARTIFACTS_DIR / BM25_MODEL_FILENAME, "wb") as handle:
        pickle.dump(bm25, handle)

    dense_vectors = embed_texts_local(args.embedding_model, texts, args.embedding_batch_size)
    if not dense_vectors:
        raise RuntimeError("Dense embedding generation returned no vectors.")
    embedding_dim = len(dense_vectors[0])
    print(f"Generated dense vectors with dim={embedding_dim}")

    if len(dense_vectors) != len(chunk_records) or len(sparse_vectors) != len(chunk_records):
        raise RuntimeError(
            "Vector count mismatch: "
            f"chunks={len(chunk_records)} dense={len(dense_vectors)} sparse={len(sparse_vectors)}"
        )

    connect_milvus()
    if args.recreate_collection and utility.has_collection(args.collection):
        """If apply --recreate_collection (overrides --reset_docs).
        Hard idempotency (Just drop entire collection then recreate)."""
        print(f"Dropping existing collection '{args.collection}' for full rebuild")
        utility.drop_collection(args.collection)
    collection = ensure_collection(args.collection, embedding_dim)

    if args.reset_docs and not args.recreate_collection:
        """If apply --reset_docs and not --recreate_collection.
        Soft idempotency (incremental runs by delete then upsert docs).

        ie. controlled delete by batches by doc_id (or doc_slug) and smoothen vector db traffic.
        """
        collection.load()  # load to memory
        doc_ids = sorted({record["doc_id"] for record in chunk_records})  # sort doc_ids for defensive deterministic runs before delete
        for i in range(0, len(doc_ids), DELETE_BATCH_SIZE):
            batch = doc_ids[i : i + DELETE_BATCH_SIZE]
            collection.delete(f"doc_id in {json.dumps(batch)}")

    columns = [
        "chunk_id",
        "doc_id",
        "source_path",
        "doc_type",
        "financial_year",
        "chunk_start",
        "chunk_end",
        "text",
    ]
    payload = [[record[column] for record in chunk_records] for column in columns]  # records: list of dict from build_chunk_records()
    payload.extend([dense_vectors, sparse_vectors])  # append the list of vectors to payload list

    # Recent managed milvus (zilliz cloud) should support upsert operations
    collection.upsert(payload)

    collection.flush()  # flush() forces all buffered insert / upsert / delete operations to be persisted as segments on storage.
    collection.load()  # refresh memory
    print(f"Inserted {len(chunk_records)} chunks into '{args.collection}'")


if __name__ == "__main__":
    main()
