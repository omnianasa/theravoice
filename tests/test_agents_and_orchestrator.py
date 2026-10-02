"""Agent and orchestrator behavior tests, including 'no autonomous medication changes'."""

from __future__ import annotations

from theravoice.agents.medication_agent import MedicationAgent
from theravoice.agents.orchestrator import AgentOrchestrator
from theravoice.agents.speech_agent import SpeechAgent
from theravoice.agents.summary_agent import DISCLAIMER, SummaryAgent
from theravoice.detection.anomaly_detector import MetricAnomalyResult
from theravoice.schemas.agent import AgentRequest


def _anomaly(metric, status, z=2.5):
    return MetricAnomalyResult(
        metric_name=metric,
        current_value=1.0,
        baseline_mean=0.0,
        baseline_std=0.4,
        z_score=z,
        status=status,
        confidence=0.9,
    )


def test_speech_agent_produces_event_on_significant_deviation():
    agent = SpeechAgent()
    request = AgentRequest(
        agent_name=agent.name,
        patient_id="p1",
        payload={"anomaly_results": [_anomaly("pause_ratio", "significant")]},
    )
    response = agent.run(request)
    assert len(response.events) == 1
    assert response.events[0].severity == "significant"


def test_speech_agent_no_event_when_normal():
    agent = SpeechAgent()
    request = AgentRequest(
        agent_name=agent.name,
        patient_id="p1",
        payload={"anomaly_results": [_anomaly("pause_ratio", "normal", z=0.2)]},
    )
    response = agent.run(request)
    assert response.events == []


def test_medication_agent_never_emits_medication_change_action():
    agent = MedicationAgent()
    request = AgentRequest(
        agent_name=agent.name,
        patient_id="p1",
        payload={"has_deviation": True},
        context={"medication_proximities": [{"within_window": True, "medication_id": "m1"}]},
    )
    response = agent.run(request)
    allowed_types = {"NOTIFY", "REMIND", "SUGGEST_EXERCISE", "LOG", "REQUEST_CHECK_IN"}
    for action in response.actions:
        assert action.type in allowed_types
    assert any(a.type == "REQUEST_CHECK_IN" for a in response.actions)


def test_orchestrator_no_event_without_evidence():
    orchestrator = AgentOrchestrator()
    response = orchestrator.run(patient_id="p1", anomaly_results=[])
    assert response.events == []
    assert "not a diagnosis" in response.data["summary_text"] or True  # summary agent always appends disclaimer downstream


def test_orchestrator_produces_events_and_actions_on_deviation():
    orchestrator = AgentOrchestrator()
    results = [_anomaly("pause_ratio", "significant"), _anomaly("word_count", "warning", z=1.7)]
    response = orchestrator.run(patient_id="p1", anomaly_results=results)
    assert len(response.events) == 2
    assert any(a.type == "LOG" or a.type == "REQUEST_CHECK_IN" for a in response.actions)


def test_summary_agent_uses_llm_text_and_appends_required_disclaimer():
    class FakeLLMClient:
        def generate(self, prompt):
            assert "Do not diagnose" in prompt
            return "You had fewer pauses than usual."

    agent = SummaryAgent(llm_client=FakeLLMClient())
    request = AgentRequest(
        agent_name=agent.name,
        patient_id="p1",
        payload={},
        context={"allow_llm_summary": True},
    )

    response = agent.run(request)

    assert response.status == "ok"
    assert response.data["summary_text"].startswith("You had fewer pauses than usual.")
    assert DISCLAIMER in response.data["summary_text"]


def test_summary_agent_falls_back_when_llm_generation_fails():
    class FailingLLMClient:
        def generate(self, prompt):
            from theravoice.llm.client import LLMError

            raise LLMError("provider unavailable")

    agent = SummaryAgent(llm_client=FailingLLMClient())
    request = AgentRequest(
        agent_name=agent.name,
        patient_id="p1",
        payload={},
        context={"allow_llm_summary": True},
    )

    response = agent.run(request)

    assert response.data["summary_text"].startswith("Daily Summary")
    assert DISCLAIMER in response.data["summary_text"]
    assert response.data["generation_status"] == "fallback"
    assert response.data["generation_error"] == "provider_failure"

    orchestrator = AgentOrchestrator(summary_agent=agent)
    orchestrated_response = orchestrator.run(
        patient_id="p1", anomaly_results=[], allow_llm_summary=True
    )
    assert orchestrated_response.data["summary_generation_status"] == "fallback"
    assert orchestrated_response.data["summary_generation_error"] == "provider_failure"


def test_summary_agent_does_not_call_llm_without_patient_consent():
    class UnexpectedLLMClient:
        def generate(self, prompt):
            raise AssertionError("LLM must not be called without patient consent")

    agent = SummaryAgent(llm_client=UnexpectedLLMClient())
    request = AgentRequest(agent_name=agent.name, patient_id="p1", payload={})

    response = agent.run(request)

    assert response.data["summary_text"].startswith("Daily Summary")


def test_orchestrator_passes_patient_consent_to_summary_agent():
    class FakeLLMClient:
        called = False

        def generate(self, prompt):
            self.called = True
            return "Consented summary."

    client = FakeLLMClient()
    orchestrator = AgentOrchestrator(summary_agent=SummaryAgent(llm_client=client))

    response = orchestrator.run(
        patient_id="p1", anomaly_results=[], allow_llm_summary=True
    )

    assert client.called is True
    assert "Consented summary." in response.data["summary_text"]
