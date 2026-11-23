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
    with patch(
        "bashmage.ollama.urllib.request.urlopen",
        return_value=_mock_urlopen("  docker ps  "),
    ):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.generate("list docker containers") == "docker ps"


def test_generate_sends_request_to_api_generate_endpoint():
    with patch(
        "bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen("echo hi")
    ) as mock_open:
        client = OllamaClient("http://myhost:9999", "mymodel")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://myhost:9999/api/generate"


def test_generate_sends_model_prompt_format_in_payload():
    with patch(
        "bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen("echo hi")
    ) as mock_open:
        client = OllamaClient("http://localhost:11434", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    payload = json.loads(req.data)
    assert payload["model"] == "llama3.2"
    assert payload["prompt"] == "say hi"
    assert payload["stream"] is False
    assert payload["format"] == _RESPONSE_SCHEMA


from urllib.error import URLError


def test_generate_raises_ollama_error_on_connection_failure():
    with patch(
        "bashmage.ollama.urllib.request.urlopen",
        side_effect=URLError("Connection refused"),
    ):
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
    with patch(
        "bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen("echo hi")
    ) as mock_open:
        client = OllamaClient("http://localhost:11434/", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://localhost:11434/api/generate"
