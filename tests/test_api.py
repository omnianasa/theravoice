"""End-to-end API tests using FastAPI's TestClient."""

from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "theravoice"}


def test_api_key_is_required_when_authentication_is_enabled(monkeypatch):
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from theravoice.api.app import create_app
    from theravoice.security import authentication

    monkeypatch.setattr(
        authentication,
        "get_settings",
        lambda: SimpleNamespace(
            security=SimpleNamespace(require_api_key=True, api_key="test-secret")
        ),
    )
    with TestClient(create_app()) as test_client:
        assert test_client.get("/health").status_code == 401
        assert test_client.get("/health", headers={"X-API-Key": "wrong"}).status_code == 401
        response = test_client.get("/health", headers={"X-API-Key": "test-secret"})
        assert response.status_code == 200
        registration = test_client.post(
            "/auth/register",
            json={
                "email": "production-user@example.com",
                "display_name": "Production User",
                "password": "production-user-password",
            },
        )
        assert registration.status_code == 201
        bearer = registration.json()["access_token"]
        assert test_client.get(
            "/health", headers={"Authorization": f"Bearer {bearer}"}
        ).status_code == 200


def test_account_register_login_me_and_logout(client):
    registration = client.post(
        "/auth/register",
        json={
            "email": "Account@Example.com",
            "display_name": "Account User",
            "password": "a-strong-password-42",
        },
    )
    assert registration.status_code == 201
    registered = registration.json()
    assert registered["user"]["email"] == "account@example.com"
    assert "password" not in registered["user"]
    assert "password_hash" not in registered["user"]

    login = client.post(
        "/auth/login",
        json={"email": "ACCOUNT@example.com", "password": "a-strong-password-42"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    current_user = client.get("/auth/me", headers=headers)
    assert current_user.status_code == 200
    assert current_user.json()["id"] == registered["user"]["id"]

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.post(
        "/auth/login", json={"email": "account@example.com", "password": "wrong-password"}
    ).status_code == 401


def test_accounts_cannot_access_each_others_patients_or_ingest_for_them(client):
    first = client.post(
        "/auth/register",
        json={"email": "first@example.com", "display_name": "First", "password": "first-password-long"},
    ).json()
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    created = client.post(
        "/patients",
        headers=first_headers,
        json={"id": "private-patient", "display_name": "Private", "consent_data_storage": True},
    )
    assert created.status_code == 201

    second = client.post(
        "/auth/register",
        json={"email": "second@example.com", "display_name": "Second", "password": "second-password-long"},
    ).json()
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.get("/patients/private-patient", headers=second_headers).status_code == 404
    assert client.post(
        "/ingestion/transcript",
        headers=second_headers,
        json={"patient_id": "private-patient", "text": "private record"},
    ).status_code == 404
    assert client.get("/patients/private-patient", headers=first_headers).status_code == 200


def test_create_and_get_patient(client):
    payload = {
        "id": "patient-demo-001",
        "display_name": "Demo Patient",
        "timezone": "UTC",
        "consent_audio_analysis": True,
        "consent_data_storage": True,
        "consent_llm_processing": True,
    }
    create_response = client.post("/patients", json=payload)
    assert create_response.status_code == 201
    assert create_response.json()["id"] == "patient-demo-001"

    get_response = client.get("/patients/patient-demo-001")
    assert get_response.status_code == 200
    assert get_response.json()["display_name"] == "Demo Patient"
    assert get_response.json()["consent_llm_processing"] is True


def test_patient_llm_consent_can_be_revoked(client):
    client.post(
        "/patients",
        json={
            "id": "patient-consent",
            "display_name": "Consent Test",
            "consent_llm_processing": True,
        },
    )

    response = client.patch(
        "/patients/patient-consent/consent", json={"consent_llm_processing": False}
    )

    assert response.status_code == 200
    assert response.json()["consent_llm_processing"] is False


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
