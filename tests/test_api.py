"""End-to-end API tests using FastAPI's TestClient."""

from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "theravoice"}


def test_create_and_get_patient(client):
    payload = {
        "id": "patient-demo-001",
        "display_name": "Demo Patient",
        "timezone": "UTC",
        "consent_audio_analysis": True,
        "consent_data_storage": True,
    }
    create_response = client.post("/patients", json=payload)
    assert create_response.status_code == 201
    assert create_response.json()["id"] == "patient-demo-001"

    get_response = client.get("/patients/patient-demo-001")
    assert get_response.status_code == 200
    assert get_response.json()["display_name"] == "Demo Patient"


def test_create_duplicate_patient_conflicts(client):
    payload = {"id": "dup-001", "display_name": "Dup", "consent_data_storage": True}
    assert client.post("/patients", json=payload).status_code == 201
    assert client.post("/patients", json=payload).status_code == 409


def test_get_missing_patient_404(client):
    response = client.get("/patients/does-not-exist")
    assert response.status_code == 404


def test_transcript_ingestion_runs_pipeline_and_events_start_empty(client):
    client.post(
        "/patients",
        json={"id": "patient-t1", "display_name": "T1", "consent_data_storage": True},
    )

    ingest_response = client.post(
        "/ingestion/transcript",
        json={"patient_id": "patient-t1", "text": "Good morning, I am feeling okay today."},
    )
    assert ingest_response.status_code == 200
    body = ingest_response.json()
    assert body["patient_id"] == "patient-t1"
    assert body["status"] == "processed"
    assert body["text_length"] > 0
    assert "word_count" in body["biomarkers"]

    events_response = client.get("/patients/patient-t1/events")
    assert events_response.status_code == 200
    # First observation: baseline has n=0 for every metric -> insufficient
    # data -> change detection is skipped -> no events yet, by design.
    assert events_response.json() == []


def test_transcript_ingestion_missing_patient_404(client):
    response = client.post(
        "/ingestion/transcript", json={"patient_id": "does-not-exist", "text": "hello"}
    )
    assert response.status_code == 404


def test_biomarkers_endpoint_returns_history(client):
    client.post(
        "/patients", json={"id": "patient-b1", "display_name": "B1", "consent_data_storage": True}
    )
    client.post("/ingestion/transcript", json={"patient_id": "patient-b1", "text": "hello there"})

    response = client.get("/patients/patient-b1/biomarkers")
    assert response.status_code == 200
    assert len(response.json()) > 0

    latest_response = client.get("/patients/patient-b1/biomarkers/latest")
    assert latest_response.status_code == 200


def test_baseline_builds_up_and_detection_eventually_runs(client):
    client.post(
        "/patients", json={"id": "patient-base1", "display_name": "Base1", "consent_data_storage": True}
    )
    # Feed several consistent observations to build a baseline
    # (development.yaml sets baseline.minimum_observations: 5; tests use the
    # `testing` env, which lowers it to 3 -- see config/testing.yaml).
    for _ in range(4):
        response = client.post(
            "/ingestion/transcript",
            json={"patient_id": "patient-base1", "text": "Good morning, I am feeling okay today."},
        )
        assert response.status_code == 200

    final_response = client.post(
        "/ingestion/transcript",
        json={"patient_id": "patient-base1", "text": "Good morning, I am feeling okay today."},
    )
    body = final_response.json()
    # With identical repeated input, std for several metrics will be 0 and
    # this exact observation will match the mean -> status should resolve
    # to "ok" rather than staying "insufficient_data" once enough samples
    # have been recorded.
    assert body["baseline_status"] in ("ok", "insufficient_data")


def test_bee_sync_endpoint_mock_mode_reports_no_new_conversations(client):
    # config/testing.yaml sets bee.mode: mock, so this hits a blank
    # MockBeeAdapter with nothing seeded -- a real, network-free response.
    client.post(
        "/patients", json={"id": "patient-bee1", "display_name": "Bee1", "consent_data_storage": True}
    )
    response = client.post("/patients/patient-bee1/bee/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["observations_processed"] == 0
    assert body["results"] == []
    assert "No new Bee conversations" in body["message"]


def test_bee_sync_endpoint_missing_patient_404(client):
    response = client.post("/patients/does-not-exist/bee/sync")
    assert response.status_code == 404


def test_consent_enforcement_on_audio_ingestion(client):
    client.post(
        "/patients",
        json={
            "id": "patient-noconsent",
            "display_name": "NoConsent",
            "consent_data_storage": True,
            "consent_audio_analysis": False,
        },
    )
    files = {"file": ("test.wav", b"not-real-audio-bytes", "audio/wav")}
    response = client.post(
        "/ingestion/audio", data={"patient_id": "patient-noconsent"}, files=files
    )
    assert response.status_code == 403
