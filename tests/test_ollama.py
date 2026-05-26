import json
import pytest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from bashmage.ollama import OllamaClient, OllamaError


def _mock_urlopen(response_body: bytes):
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = False
    return mock_cm


def test_generate_returns_stripped_response():
    body = json.dumps({"response": "  docker ps  "}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.generate("list docker containers") == "docker ps"


def test_generate_sends_request_to_api_generate_endpoint():
    body = json.dumps({"response": "echo hi"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)) as mock_open:
        client = OllamaClient("http://myhost:9999", "mymodel")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://myhost:9999/api/generate"


def test_generate_sends_model_and_prompt_in_payload():
    body = json.dumps({"response": "echo hi"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)) as mock_open:
        client = OllamaClient("http://localhost:11434", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    payload = json.loads(req.data)
    assert payload["model"] == "llama3.2"
    assert payload["prompt"] == "say hi"
    assert payload["stream"] is False


def test_generate_raises_ollama_error_on_connection_failure():
    with patch("bashmage.ollama.urllib.request.urlopen", side_effect=URLError("Connection refused")):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        with pytest.raises(OllamaError, match="Cannot reach Ollama"):
            client.generate("anything")


def test_generate_raises_ollama_error_on_missing_response_key():
    body = json.dumps({"unexpected": "shape"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        with pytest.raises(OllamaError, match="Unexpected response"):
            client.generate("anything")


def test_generate_strips_trailing_slash_from_base_url():
    body = json.dumps({"response": "echo hi"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)) as mock_open:
        client = OllamaClient("http://localhost:11434/", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://localhost:11434/api/generate"
