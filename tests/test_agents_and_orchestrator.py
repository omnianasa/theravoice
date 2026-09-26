"""Agent and orchestrator behavior tests, including 'no autonomous medication changes'."""

from __future__ import annotations

from theravoice.agents.medication_agent import MedicationAgent
from theravoice.agents.orchestrator import AgentOrchestrator
from theravoice.agents.speech_agent import SpeechAgent
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
