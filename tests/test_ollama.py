import json
import pytest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from bashmage.ollama import OllamaClient, OllamaError, _RESPONSE_SCHEMA


def _mock_urlopen(command: str):
    body = json.dumps({"response": json.dumps({"command": command})}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = False
    return mock_cm


def test_generate_returns_stripped_response():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen("  docker ps  ")):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.generate("list docker containers") == "docker ps"


def test_generate_sends_request_to_api_generate_endpoint():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen("echo hi")) as mock_open:
        client = OllamaClient("http://myhost:9999", "mymodel")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://myhost:9999/api/generate"


def test_generate_sends_model_prompt_format_in_payload():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen("echo hi")) as mock_open:
        client = OllamaClient("http://localhost:11434", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    payload = json.loads(req.data)
    assert payload["model"] == "llama3.2"
    assert payload["prompt"] == "say hi"
    assert payload["stream"] is False
    assert payload["format"] == _RESPONSE_SCHEMA


def test_generate_raises_ollama_error_on_connection_failure():
    with patch("bashmage.ollama.urllib.request.urlopen", side_effect=URLError("Connection refused")):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        with pytest.raises(OllamaError, match="Cannot reach Ollama"):
            client.generate("anything")


def test_generate_raises_ollama_error_on_missing_response_key():
    body = json.dumps({"unexpected": "shape"}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = False
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=mock_cm):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        with pytest.raises(OllamaError, match="Unexpected response"):
            client.generate("anything")


def test_generate_raises_ollama_error_when_structured_response_missing_command_key():
    body = json.dumps({"response": json.dumps({"other": "field"})}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = False
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=mock_cm):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        with pytest.raises(OllamaError, match="Unexpected response"):
            client.generate("anything")


def test_generate_strips_trailing_slash_from_base_url():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen("echo hi")) as mock_open:
        client = OllamaClient("http://localhost:11434/", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://localhost:11434/api/generate"


def _mock_ps_urlopen(models: list[str]):
    body = json.dumps({"models": [{"name": m} for m in models]}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = False
    return mock_cm


def test_is_model_loaded_returns_true_when_model_present():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_ps_urlopen(["llama3.2:latest"])):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.is_model_loaded() is True


def test_is_model_loaded_returns_false_when_model_absent():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_ps_urlopen(["mistral:latest"])):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.is_model_loaded() is False


def test_is_model_loaded_returns_false_when_no_models_running():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_ps_urlopen([])):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.is_model_loaded() is False


def test_is_model_loaded_matches_base_name_ignoring_tag():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_ps_urlopen(["llama3.2:latest"])):
        client = OllamaClient("http://localhost:11434", "llama3.2:latest")
        assert client.is_model_loaded() is True


def test_is_model_loaded_returns_false_on_connection_failure():
    with patch("bashmage.ollama.urllib.request.urlopen", side_effect=URLError("Connection refused")):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.is_model_loaded() is False


def test_is_model_loaded_calls_api_ps_endpoint():
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_ps_urlopen([])) as mock_open:
        client = OllamaClient("http://localhost:11434", "llama3.2")
        client.is_model_loaded()
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://localhost:11434/api/ps"
