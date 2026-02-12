import io
import os
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from src.agents.core.config import AgentConfig
from src.agents.core.manager import Manager
from src.agents.planner.service import PlannerAI
from src.agents.runtime import main as runtime_main
from src.agents.specialists.service import GuardrailsViolationError, MCPReadinessError, Specialists
from src.agents.core.types import ReflectionResult, RetrievalHit, UserQuery


def setUpModule():
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


class ConfigTests(unittest.TestCase):
    def test_langchain_tracing_env_true_enables_tracing(self):
        original = os.environ.get("LANGCHAIN_TRACING_V2")
        try:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            config = AgentConfig.from_env()
            self.assertTrue(config.langsmith_tracing)
        finally:
            if original is None:
                os.environ.pop("LANGCHAIN_TRACING_V2", None)
            else:
                os.environ["LANGCHAIN_TRACING_V2"] = original

    def test_invalid_threshold_raises_validation_error(self):
        original = os.environ.get("AGENT_CONFIDENCE_STRONG")
        try:
            os.environ["AGENT_CONFIDENCE_STRONG"] = "1.5"
            with self.assertRaises(ValidationError):
                AgentConfig.from_env()
        finally:
            if original is None:
                os.environ.pop("AGENT_CONFIDENCE_STRONG", None)
            else:
                os.environ["AGENT_CONFIDENCE_STRONG"] = original

    def test_planner_env_overrides(self):
        original_model = os.environ.get("AGENT_PLANNER_MODEL")
        original_temp = os.environ.get("AGENT_PLANNER_TEMPERATURE")
        try:
            os.environ["AGENT_PLANNER_MODEL"] = "gpt-4o-mini"
            os.environ["AGENT_PLANNER_TEMPERATURE"] = "0.2"
            config = AgentConfig.from_env()
            self.assertEqual(config.planner_model, "gpt-4o-mini")
            self.assertEqual(config.planner_temperature, 0.2)
        finally:
            if original_model is None:
                os.environ.pop("AGENT_PLANNER_MODEL", None)
            else:
                os.environ["AGENT_PLANNER_MODEL"] = original_model
            if original_temp is None:
                os.environ.pop("AGENT_PLANNER_TEMPERATURE", None)
            else:
                os.environ["AGENT_PLANNER_TEMPERATURE"] = original_temp

    def test_synthesis_and_reflection_temperature_env_overrides(self):
        original_syn_temp = os.environ.get("AGENT_SYNTHESIS_TEMPERATURE")
        original_ref_temp = os.environ.get("AGENT_REFLECTION_TEMPERATURE")
        try:
            os.environ["AGENT_SYNTHESIS_TEMPERATURE"] = "0.3"
            os.environ["AGENT_REFLECTION_TEMPERATURE"] = "0.0"
            config = AgentConfig.from_env()
            self.assertEqual(config.synthesis_temperature, 0.3)
            self.assertEqual(config.reflection_temperature, 0.0)
        finally:
            if original_syn_temp is None:
                os.environ.pop("AGENT_SYNTHESIS_TEMPERATURE", None)
            else:
                os.environ["AGENT_SYNTHESIS_TEMPERATURE"] = original_syn_temp
            if original_ref_temp is None:
                os.environ.pop("AGENT_REFLECTION_TEMPERATURE", None)
            else:
                os.environ["AGENT_REFLECTION_TEMPERATURE"] = original_ref_temp


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.config = AgentConfig()
        self.planner = PlannerAI(self.config)

    def test_default_plan_sequence_and_revision(self):
        with patch.object(
            self.planner,
            "_generate_planner_output",
            return_value={"revised_query": "FY2025 support for SMEs", "coherence": "coherent", "coherence_reason": None},
        ) as mock_revision:
            plan = self.planner.build_plan(UserQuery(query="What are FY2025 support measures?"))
        self.assertEqual([step.name for step in plan.steps], ["retrieve", "rerank", "synthesize", "reflect"])
        self.assertEqual(plan.original_query, "What are FY2025 support measures?")
        self.assertEqual(plan.revised_query, "FY2025 support for SMEs")
        self.assertNotIn("sub_queries", plan.steps[0].params)
        self.assertEqual(mock_revision.call_count, 1)

    def test_context_uses_llm_output_and_calls_every_cycle(self):
        with patch.object(
            self.planner,
            "_generate_planner_output",
            return_value={"revised_query": "Revised query from planner", "coherence": "coherent", "coherence_reason": None},
        ) as mock_revision:
            plan = self.planner.build_plan(
                UserQuery(
                    query="Original user question",
                    context={
                        "original_query": "Original user question",
                        "revised_query": "Stale revised query",
                    },
                )
            )
        self.assertEqual(plan.original_query, "Original user question")
        self.assertEqual(plan.revised_query, "Revised query from planner")
        self.assertEqual(mock_revision.call_count, 1)

    def test_requested_years_are_added_to_retrieve_params(self):
        with patch.object(
            self.planner,
            "_generate_planner_output",
            return_value={"revised_query": "recent productivity support", "coherence": "coherent", "coherence_reason": None},
        ):
            plan = self.planner.build_plan(
                UserQuery(query="What are FY2024 measures?", context={"requested_years": [2024, 2025]})
            )
        retrieve_params = plan.steps[0].params
        self.assertEqual(retrieve_params["year_mode"], "explicit")
        self.assertEqual(retrieve_params["requested_years"], [2024, 2025])

    def test_no_requested_years_defaults_to_no_filter(self):
        with patch.object(
            self.planner,
            "_generate_planner_output",
            return_value={"revised_query": "productivity support", "coherence": "coherent", "coherence_reason": None},
        ):
            plan = self.planner.build_plan(UserQuery(query="What are productivity measures?"))
        retrieve_params = plan.steps[0].params
        self.assertEqual(retrieve_params["year_mode"], "none")
        self.assertEqual(retrieve_params["requested_years"], [])

    def test_fail_fast_on_empty_revised_query(self):
        with patch.object(
            self.planner,
            "_generate_planner_output",
            return_value={"revised_query": "   ", "coherence": "coherent", "coherence_reason": None},
        ):
            with self.assertRaises(RuntimeError):
                self.planner.build_plan(UserQuery(query="test"))

    def test_planner_uses_prompt_builder_for_revision(self):
        class FakeModel:
            def __init__(self):
                self.last_prompt = None

            def invoke(self, prompt):
                self.last_prompt = prompt
                return SimpleNamespace(content='{"revised_query":"revised by builder"}')

        fake_model = FakeModel()
        with patch(
            "src.agents.planner.service.planner_prompts.build_planner_prompt",
            return_value="PLANNER_PROMPT",
        ) as mock_builder:
            self.planner._get_planner_model = lambda: fake_model
            output = self.planner._generate_planner_output(
                original_query="original",
                context={},
            )
        self.assertEqual(output["revised_query"], "revised by builder")
        self.assertEqual(output["coherence"], "coherent")
        self.assertEqual(fake_model.last_prompt, "PLANNER_PROMPT")
        self.assertEqual(mock_builder.call_count, 1)

    def test_planner_sets_incoherent_fields(self):
        with patch.object(
            self.planner,
            "_generate_planner_output",
            return_value={
                "revised_query": "???",
                "coherence": "incoherent",
                "coherence_reason": "query_not_interpretable",
            },
        ):
            plan = self.planner.build_plan(UserQuery(query="???"))
        self.assertEqual(plan.coherence, "incoherent")
        self.assertEqual(plan.coherence_reason, "query_not_interpretable")




class StyleLoopSpecialists:
    def retrieve(self, query, top_k, retrieve_context=None):
        return [
            RetrievalHit(chunk_id="a", source_path="s1", text="alpha", score=0.8),
            RetrievalHit(chunk_id="b", source_path="s2", text="beta", score=0.7),
        ]

    def rerank(self, query, hits, top_n):
        return list(hits[:top_n])

    def synthesize(self, original_query, revised_query, hits):
        return "Unstructured answer"

    def reflect(self, original_query, revised_query, answer, hits):
        return ReflectionResult(reason="ok", confidence=0.9, comments="Looks good")


class LowCoverageSpecialists:
    def retrieve(self, query, top_k, retrieve_context=None):
        return [RetrievalHit(chunk_id="a", source_path="s1", text="alpha", score=0.8)]

    def rerank(self, query, hits, top_n):
        return list(hits[:top_n])

    def synthesize(self, original_query, revised_query, hits):
        return "Answer: limited"

    def reflect(self, original_query, revised_query, answer, hits):
        return ReflectionResult(reason="low_coverage", confidence=0.2, comments="Need broader coverage")


class MediumConfidenceSpecialists(LowCoverageSpecialists):
    def reflect(self, original_query, revised_query, answer, hits):
        return ReflectionResult(reason="low_coverage", confidence=0.75, comments="Some details uncertain")


class LowConfidencePartialSpecialists(LowCoverageSpecialists):
    def reflect(self, original_query, revised_query, answer, hits):
        return ReflectionResult(reason="low_coverage", confidence=0.55, comments="Coverage is partial")


class ManagerTests(unittest.TestCase):
    def test_manager_runs_single_execute_then_success(self):
        config = AgentConfig()
        manager = Manager(config)
        planner = PlannerAI(config)
        specialists = StyleLoopSpecialists()

        with patch.object(
            planner,
            "_generate_planner_output",
            return_value={"revised_query": "query-v1", "coherence": "coherent", "coherence_reason": None},
        ):
            result = manager.run(UserQuery(query="test query"), planner, specialists)
        self.assertEqual(result.state_history[-1], "success")
        self.assertEqual(result.state_history.count("execute_plan"), 1)
        self.assertEqual(result.final_reason, "confidence_high")

    def test_manager_very_low_confidence_returns_success_without_answer_append(self):
        config = AgentConfig()
        manager = Manager(config)
        planner = PlannerAI(config)
        specialists = LowCoverageSpecialists()

        with patch.object(
            planner,
            "_generate_planner_output",
            return_value={"revised_query": "query-v1", "coherence": "coherent", "coherence_reason": None},
        ):
            result = manager.run(UserQuery(query="test query"), planner, specialists)

        self.assertNotIn("replan", result.state_history)
        self.assertEqual(result.state_history[-1], "success")
        self.assertEqual(result.final_reason, "confidence_too_low_clarify")
        self.assertEqual(result.answer, "Answer: limited")

    def test_manager_medium_confidence_returns_caveated_success(self):
        config = AgentConfig()
        manager = Manager(config)
        planner = PlannerAI(config)
        specialists = MediumConfidenceSpecialists()

        with patch.object(
            planner,
            "_generate_planner_output",
            return_value={"revised_query": "query-v1", "coherence": "coherent", "coherence_reason": None},
        ):
            result = manager.run(UserQuery(query="test query"), planner, specialists)

        self.assertEqual(result.state_history[-1], "success")
        self.assertEqual(result.final_reason, "confidence_medium_caveated")
        self.assertEqual(result.answer, "Answer: limited")

    def test_manager_low_confidence_partial_returns_success_with_limits(self):
        config = AgentConfig()
        manager = Manager(config)
        planner = PlannerAI(config)
        specialists = LowConfidencePartialSpecialists()

        with patch.object(
            planner,
            "_generate_planner_output",
            return_value={"revised_query": "query-v1", "coherence": "coherent", "coherence_reason": None},
        ):
            result = manager.run(UserQuery(query="test query"), planner, specialists)

        self.assertEqual(result.state_history[-1], "success")
        self.assertEqual(result.final_reason, "confidence_low_partial")
        self.assertEqual(result.answer, "Answer: limited")

    def test_manager_guardrail_block_returns_safe_reply(self):
        config = AgentConfig()
        manager = Manager(config)
        planner = PlannerAI(config)

        class GuardrailSpecialists(LowCoverageSpecialists):
            def retrieve(self, query, top_k, retrieve_context=None):
                raise GuardrailsViolationError(stage="input", reason="pii_detected:email", safe_reply="safe blocked")

        with patch.object(
            planner,
            "_generate_planner_output",
            return_value={"revised_query": "query-v1", "coherence": "coherent", "coherence_reason": None},
        ):
            result = manager.run(UserQuery(query="test query"), planner, GuardrailSpecialists())
        self.assertEqual(result.state_history[-1], "fail")
        self.assertIn("safe", result.answer.lower())
        self.assertEqual(result.guardrail_event["stage"], "input")

    def test_manager_rejects_incoherent_query_without_specialist_calls(self):
        config = AgentConfig()
        manager = Manager(config)
        planner = PlannerAI(config)

        class NoCallSpecialists:
            def retrieve(self, *args, **kwargs):
                raise AssertionError("retrieve should not be called for incoherent query")

            def rerank(self, *args, **kwargs):
                raise AssertionError("rerank should not be called for incoherent query")

            def synthesize(self, *args, **kwargs):
                raise AssertionError("synthesize should not be called for incoherent query")

            def reflect(self, *args, **kwargs):
                raise AssertionError("reflect should not be called for incoherent query")

        with patch.object(
            planner,
            "_generate_planner_output",
            return_value={
                "revised_query": "???",
                "coherence": "incoherent",
                "coherence_reason": "query_not_interpretable",
            },
        ):
            result = manager.run(UserQuery(query="???"), planner, NoCallSpecialists())

        self.assertEqual(result.state_history, ["fail"])
        self.assertEqual(result.final_reason, "incoherent_query")
        self.assertEqual(result.coherence["label"], "incoherent")
        self.assertIn("couldn’t interpret the query clearly", result.answer.lower())


class SpecialistsTests(unittest.TestCase):
    def test_specialists_rerank_and_retrieve_mapping(self):
        config = AgentConfig(guardrails_enabled=False, mcp_strict=False)

        class FakeVector:
            def astype(self, _):
                return self

            def tolist(self):
                return [0.1, 0.2]

        class FakeEmbedder:
            def encode(self, texts, normalize_embeddings=True):
                return [FakeVector()]

        class FakeBM25:
            def encode_queries(self, texts):
                return [{1: 0.7}]

        class FakeResult:
            def __init__(self, chunk_id: str, score: float):
                self.entity = {
                    "chunk_id": chunk_id,
                    "source_path": f"{chunk_id}.pdf",
                    "text": f"text {chunk_id}",
                    "doc_type": "d",
                    "financial_year": 2025,
                }
                self.score = score

        with (
            patch.object(Specialists, "validate_ready", return_value=None),
            patch("src.agents.specialists.retrieval.search_collection_dense", return_value=[[FakeResult("x", 0.88)]]),
            patch("src.agents.specialists.retrieval.search_collection_sparse", return_value=[[FakeResult("x", 0.55)]]),
        ):
            specialists = Specialists(config)
            specialists._get_embedder = lambda: FakeEmbedder()
            specialists._get_collection = lambda: object()
            specialists._get_bm25_encoder = lambda: FakeBM25()
            hits = specialists.retrieve("budget support", 3, retrieve_context={"year_mode": "recent", "recent_year_window": 2})

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].metadata["tool"], "retrieve")
        self.assertEqual(hits[0].metadata["retrieval_sources"], ["dense", "sparse"])
        self.assertIn("merged_score", hits[0].metadata)

    def test_specialists_retrieve_explicit_year_expr(self):
        config = AgentConfig(guardrails_enabled=False)

        class FakeVector:
            def astype(self, _):
                return self

            def tolist(self):
                return [0.1, 0.2]

        class FakeEmbedder:
            def encode(self, texts, normalize_embeddings=True):
                return [FakeVector()]

        class FakeBM25:
            def encode_queries(self, texts):
                return [{1: 0.7}]

        captured = {"year_expr": None}

        def fake_dense_search(collection, query_vector, top_k, year_expr):
            captured["year_expr"] = year_expr
            return [[]]

        with (
            patch.object(Specialists, "validate_ready", return_value=None),
            patch("src.agents.specialists.retrieval.search_collection_dense", side_effect=fake_dense_search),
            patch("src.agents.specialists.retrieval.search_collection_sparse", return_value=[[]]),
        ):
            specialists = Specialists(config)
            specialists._get_embedder = lambda: FakeEmbedder()
            specialists._get_collection = lambda: object()
            specialists._get_bm25_encoder = lambda: FakeBM25()
            specialists.retrieve("query", 3, retrieve_context={"year_mode": "explicit", "requested_years": [2024, 2025]})

        self.assertEqual(captured["year_expr"], "financial_year in [2024, 2025]")

    def test_specialists_rerank_uses_cross_encoder_scores(self):
        config = AgentConfig(guardrails_enabled=False, mcp_strict=False, rerank_candidate_limit=10)
        hits = [
            RetrievalHit(chunk_id="a", source_path="a.pdf", text="alpha text", score=0.2),
            RetrievalHit(chunk_id="b", source_path="b.pdf", text="beta text", score=0.9),
        ]

        class FakeCrossEncoder:
            def predict(self, pairs):
                return [0.95, 0.10]

        with patch.object(Specialists, "validate_ready", return_value=None):
            specialists = Specialists(config)
            specialists._get_cross_encoder = lambda: FakeCrossEncoder()
            reranked = specialists.rerank("query", hits, 1)

        self.assertEqual(reranked[0].chunk_id, "a")

    def test_specialists_rerank_fails_when_cross_encoder_missing(self):
        config = AgentConfig(guardrails_enabled=False, mcp_strict=False, rerank_candidate_limit=10)
        hits = [
            RetrievalHit(chunk_id="a", source_path="a.pdf", text="alpha budget support", score=0.2),
            RetrievalHit(chunk_id="b", source_path="b.pdf", text="beta", score=0.9),
        ]

        with patch.object(Specialists, "validate_ready", return_value=None):
            specialists = Specialists(config)
            specialists._get_cross_encoder = lambda: None
            with self.assertRaises(RuntimeError):
                specialists.rerank("budget support", hits, 1)

    def test_specialists_synthesize_and_reflect(self):
        config = AgentConfig(guardrails_enabled=False)

        class FakeModel:
            def invoke(self, prompt):
                prompt_text = str(prompt)
                if "Return JSON only with keys" in prompt_text:
                    return SimpleNamespace(content='{"reason":"ok","confidence":0.91,"comments":"good"}')
                return SimpleNamespace(content="Answer: ok\\nEvidence:\\n- (s) text")

        hits = [RetrievalHit(chunk_id="x", source_path="s", text="text", score=0.5)]
        with patch.object(Specialists, "validate_ready", return_value=None):
            specialists = Specialists(config)
            specialists._get_synthesis_model = lambda: FakeModel()
            specialists._get_reflection_model = lambda: FakeModel()
            answer = specialists.synthesize("orig", "revised", hits)
            reflection = specialists.reflect("original query", "revised query", answer, hits)

        self.assertIn("Answer:", answer)
        self.assertEqual(reflection.reason, "ok")

    def test_specialists_use_prompt_builders(self):
        config = AgentConfig(guardrails_enabled=False)

        class FakeModel:
            def __init__(self):
                self.prompts = []

            def invoke(self, prompt):
                self.prompts.append(prompt)
                if prompt == "REF_PROMPT":
                    return SimpleNamespace(content='{"reason":"ok","confidence":0.8,"comments":"fine"}')
                return SimpleNamespace(content="Answer: builder\\nEvidence:\\n- (s) text")

        hits = [RetrievalHit(chunk_id="x", source_path="s", text="text", score=0.5)]
        with (
            patch.object(Specialists, "validate_ready", return_value=None),
            patch("src.agents.specialists.synthesis.synthesis_prompts.build_synthesis_prompt", return_value="SYN_PROMPT") as syn_builder,
            patch("src.agents.specialists.reflection.reflection_prompts.build_reflection_prompt", return_value="REF_PROMPT") as ref_builder,
        ):
            specialists = Specialists(config)
            fake_model = FakeModel()
            specialists._get_synthesis_model = lambda: fake_model
            specialists._get_reflection_model = lambda: fake_model
            answer = specialists.synthesize("orig", "revised", hits)
            reflection = specialists.reflect("original query", "revised query", answer, hits)

        self.assertIn("Answer:", answer)
        self.assertEqual(reflection.reason, "ok")
        self.assertEqual(syn_builder.call_count, 1)
        self.assertEqual(ref_builder.call_count, 1)
        self.assertEqual(ref_builder.call_args.kwargs["original_query"], "original query")
        self.assertEqual(ref_builder.call_args.kwargs["revised_query"], "revised query")

    def test_specialists_fail_fast_when_disabled(self):
        with self.assertRaises(MCPReadinessError):
            Specialists(AgentConfig(mcp_enabled=False))

    def test_specialists_bm25_artifact_missing_raises(self):
        config = AgentConfig(guardrails_enabled=False)
        with patch.object(Specialists, "validate_ready", return_value=None):
            specialists = Specialists(config)
            with patch("src.agents.specialists.service.Path.exists", return_value=False):
                with self.assertRaises(RuntimeError):
                    specialists._get_bm25_encoder()

    def test_specialists_guardrails_block_on_input(self):
        config = AgentConfig(guardrails_enabled=True)
        with patch.object(Specialists, "validate_ready", return_value=None):
            specialists = Specialists(config)
            with patch.object(
                specialists._guardrails,
                "guard_input",
                side_effect=GuardrailsViolationError(stage="input", reason="pii_detected", safe_reply="safe reply"),
            ):
                with self.assertRaises(GuardrailsViolationError):
                    specialists.retrieve("email me at foo@example.com", 3)


class RuntimeTests(unittest.TestCase):
    def test_runtime_cli_fails_cleanly_when_mcp_not_ready(self):
        with patch("src.agents.runtime.Specialists", side_effect=MCPReadinessError("missing env vars")):
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = runtime_main(["--query", "What is the FY2025 budget focus?"])
        output = buf.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("startup_error=MCP readiness failed", output)


if __name__ == "__main__":
    unittest.main()
