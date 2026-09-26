"""Tests for the top-level agents/manifest.yaml loader and orchestrator wiring."""

from __future__ import annotations

import yaml

from theravoice.agents.manifest import load_agent_manifest, reload_agent_manifest
from theravoice.agents.orchestrator import AgentOrchestrator
from theravoice.detection.anomaly_detector import MetricAnomalyResult


def test_default_manifest_loads_and_enables_all_known_agents():
    manifest = load_agent_manifest()
    expected_agents = {
        "speech_agent",
        "text_agent",
        "context_agent",
        "medication_agent",
        "therapy_agent",
        "summary_agent",
    }
    assert expected_agents.issubset(manifest.keys())
    assert all(manifest[name] is True for name in expected_agents)


def test_missing_manifest_file_fails_open(tmp_path):
    manifest = reload_agent_manifest(path=tmp_path / "does-not-exist.yaml")
    assert manifest == {}


def test_malformed_manifest_fails_open(tmp_path):
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text("not: a: valid: manifest: [", encoding="utf-8")
    manifest = reload_agent_manifest(path=bad_path)
    assert manifest == {}


def test_orchestrator_skips_disabled_agent(tmp_path):
    reload_agent_manifest()  # reset cache so other tests aren't affected

    disabled_manifest = {
        "speech_agent": False,
        "text_agent": True,
        "context_agent": True,
        "medication_agent": True,
        "therapy_agent": True,
        "summary_agent": True,
    }
    orchestrator = AgentOrchestrator(agent_manifest=disabled_manifest)

    significant_pause = MetricAnomalyResult(
        metric_name="pause_ratio",
        current_value=1.0,
        baseline_mean=0.0,
        baseline_std=0.2,
        z_score=5.0,
        status="significant",
        confidence=0.9,
    )
    response = orchestrator.run(patient_id="p1", anomaly_results=[significant_pause])

    # SpeechAgent is disabled, so the speech-only deviation must not surface
    # as an event even though the anomaly result itself is significant.
    assert response.events == []


def test_orchestrator_runs_all_agents_when_manifest_empty():
    orchestrator = AgentOrchestrator(agent_manifest={})
    significant_pause = MetricAnomalyResult(
        metric_name="pause_ratio",
        current_value=1.0,
        baseline_mean=0.0,
        baseline_std=0.2,
        z_score=5.0,
        status="significant",
        confidence=0.9,
    )
    response = orchestrator.run(patient_id="p1", anomaly_results=[significant_pause])
    assert len(response.events) == 1
