from cnlc_agent.framework import EnvironmentModelCredential
from cnlc_agent.app import build_app
from fastapi.testclient import TestClient


def test_environment_credential_exposes_configured_model_without_storing_secret(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "demo-chat-model")
    monkeypatch.setenv("MODEL_API_KEY", "test-secret")
    monkeypatch.setenv("MODEL_BASE_URL", "https://model.example/v1")

    credential = EnvironmentModelCredential(id="test-env-model", name="Environment model")

    assert credential.model_dump() == {
        "id": "test-env-model",
        "name": "Environment model",
        "type": "cnlc_env_model",
    }
    cards = credential.list_models()
    assert [card.name for card in cards] == ["demo-chat-model"]
    assert cards[0].label == "demo-chat-model"


def test_environment_chat_model_reads_api_settings_at_runtime(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "demo-chat-model")
    monkeypatch.setenv("MODEL_API_KEY", "test-secret")
    monkeypatch.setenv("MODEL_BASE_URL", "https://model.example/v1")

    credential = EnvironmentModelCredential(id="test-env-model", name="Environment model")
    model_cls = credential.get_chat_model_class()
    model = model_cls(credential=credential, model="demo-chat-model")

    assert model.client.api_key == "test-secret"
    assert str(model.client.base_url) == "https://model.example/v1/"


def test_configured_environment_credential_is_available_without_exposing_key(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "demo-chat-model")
    monkeypatch.setenv("MODEL_API_KEY", "test-secret")
    monkeypatch.setenv("MODEL_BASE_URL", "https://model.example/v1")
    monkeypatch.setenv("CNLC_DEFAULT_USER_ID", "local-demo")

    with TestClient(build_app(tmp_path), headers={"X-User-ID": "local-demo"}) as client:
        credentials = client.get("/credential/").json()["credentials"]
        env_credential = next(item for item in credentials if item["data"]["type"] == "cnlc_env_model")
        models = client.get("/model/", params={"provider": "cnlc_env_model"}).json()["models"]

    assert env_credential["data"]["name"] == "CNLC .env 模型 · demo-chat-model"
    assert "api_key" not in env_credential["data"]
    assert [model["name"] for model in models] == ["demo-chat-model"]
