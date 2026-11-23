import json
import urllib.request
import urllib.error


SYSTEM_PROMPT = """\
You are a bash command generator.
Given a description of what the user wants to do, generate the appropriate bash command.
Rules:
- Be mindful of what the user needs and be effective, using common tools and idioms
- For values the user needs to supply (filenames, ports, hosts, etc.), use {placeholder} syntax, e.g. {host}, {port}, {file}
- Multi-line commands are acceptable; use backslash continuation or shell operators
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
    },
    "required": ["command"],
}


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._url = f"{self._base_url}/api/generate"
        self._model = model

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "format": _RESPONSE_SCHEMA,
                "think": False,
            }
        ).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read())
                structured = json.loads(body["response"])
                return structured["command"].strip()
        except urllib.error.URLError as e:
            raise OllamaError(f"Cannot reach Ollama at {self._url}: {e.reason}") from e
        except (KeyError, json.JSONDecodeError) as e:
            raise OllamaError(f"Unexpected response from Ollama: {e}") from e
