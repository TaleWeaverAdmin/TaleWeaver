import json
import urllib.error
import urllib.request


def list_models(base_url):
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("models", [])
    except Exception:
        return []


def chat_json(base_url, model, messages, temperature=0.8, options=None):
    request_options = {"temperature": temperature}
    if isinstance(options, dict):
        request_options.update(options)
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": request_options,
        "messages": messages,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))
    content = data.get("message", {}).get("content") or "{}"
    return parse_json_object(content)


def parse_json_object(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
