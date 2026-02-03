import math
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


def _tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokenization for BM25-style scoring."""
    return _TOKEN_PATTERN.findall(text.lower())


@dataclass
class BM25SparseEncoder:
    """Minimal BM25 encoder that returns sparse vectors for Milvus.

    Why this exists:
    - We need sparse vectors for hybrid retrieval.

    Reference: README.math.md
    """
    k1: float = 1.5
    b: float = 0.75
    vocab: Dict[str, int] = field(default_factory=dict)
    idf: List[float] = field(default_factory=list)
    avgdl: float = 0.0

    def fit(self, texts: Iterable[str]) -> None:
        """Learn vocabulary + IDF from the corpus."""
        # Build document frequency and average document length for BM25.
        doc_freq: Dict[str, int] = {}
        doc_lens: List[int] = []
        total_docs = 0

        for text in texts:
            total_docs += 1
            # Tokenize the document and count unique terms for DF.
            tokens = _tokenize(text)
            doc_lens.append(len(tokens))
            for token in set(tokens):
                doc_freq[token] = doc_freq.get(token, 0) + 1

        if total_docs == 0:
            return

        # Average document length is used in BM25 length normalization.
        self.avgdl = sum(doc_lens) / total_docs
        # Assign each term a stable index for sparse vector keys.
        self.vocab = {token: idx for idx, token in enumerate(doc_freq.keys())}
        self.idf = [0.0] * len(self.vocab)
        for token, df in doc_freq.items():
            idx = self.vocab[token]
            # Standard BM25 IDF term (see README.math.md).
            self.idf[idx] = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))

    def encode_documents(self, texts: Iterable[str]) -> List[Dict[int, float]]:
        """Encode documents with BM25 weights."""
        return [self._encode(text, use_bm25=True) for text in texts]

    def encode_queries(self, texts: Iterable[str]) -> List[Dict[int, float]]:
        """Encode queries with IDF-weighted term frequency (no length normalization)."""
        return [self._encode(text, use_bm25=False) for text in texts]

    def _encode(self, text: str, use_bm25: bool) -> Dict[int, float]:
        # Sparse dict maps vocab index -> weight, matching Milvus sparse format.
        tokens = _tokenize(text)
        if not tokens:
            return {}

        # Term frequency by vocab index.
        tf: Dict[int, int] = {}
        for token in tokens:
            idx = self.vocab.get(token)
            if idx is None:
                continue
            tf[idx] = tf.get(idx, 0) + 1

        if not tf:
            return {}

        weights: Dict[int, float] = {}
        dl = len(tokens)
        for idx, freq in tf.items():
            idf = self.idf[idx]
            if use_bm25:
                # BM25 core: idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl/avgdl))
                denom = freq + self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl else 0))
                score = idf * (freq * (self.k1 + 1)) / (denom if denom else 1)
            else:
                # Query weighting: idf * tf (see README.math.md for mapping)
                score = idf * freq
            if score:
                weights[idx] = float(score)
        return weights


# Example:
# encoder = BM25SparseEncoder()
# encoder.fit(["risk factors include supply chain issues", "liquidity risks are disclosed"])
# doc_vectors = encoder.encode_documents(["supply chain risks"])
# query_vector = encoder.encode_queries(["supply chain risks"])[0]
