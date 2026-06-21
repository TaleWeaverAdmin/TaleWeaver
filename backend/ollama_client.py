import json
import re
import urllib.error
import urllib.request


class OllamaJSONError(RuntimeError):
    def __init__(self, message, content="", parse_error=None):
        super().__init__(message)
        self.content = content
        self.parse_error = parse_error


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
    think = request_options.pop("think", None)
    keep_alive = request_options.pop("keep_alive", None)
    timeout = float(request_options.pop("request_timeout", 180) or 180)
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": request_options,
        "messages": with_plain_json_instruction(messages),
    }
    if think is not None:
        payload["think"] = bool(think)
    if keep_alive:
        payload["keep_alive"] = str(keep_alive)
    data = post_chat(base_url, payload, timeout)
    content = data.get("message", {}).get("content") or "{}"
    try:
        return parse_json_object(content)
    except json.JSONDecodeError as exc:
        repaired = repair_json_with_ollama(base_url, model, content, timeout)
        if repaired:
            try:
                return parse_json_object(repaired)
            except json.JSONDecodeError:
                pass
        excerpt = compact_error_body(content)
        raise OllamaJSONError(
            f"Ollama returned invalid JSON: {exc}. Response excerpt: {excerpt}",
            content,
            exc,
        ) from exc


def post_chat(base_url, payload, timeout):
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def with_plain_json_instruction(messages):
    strict_message = {
        "role": "system",
        "content": (
            "Return one valid JSON object only. JSON string values must be plain text. "
            "Do not use markdown, HTML, CSS, XML tags, color spans, inline styles, or formatting annotations."
        ),
    }
    return [strict_message, *list(messages or [])]


def parse_json_object(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_json_text_locally(text)
        if repaired != text:
            return json.loads(repaired)
        raise


def repair_json_text_locally(content):
    text = extract_jsonish_text(content)
    text = text.replace("\ufeff", "").strip()
    text = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r'([}\]"0-9])\s+("[A-Za-z0-9_ -]+"\s*:)', r"\1, \2", text)
    text = re.sub(r'\b(true|false|null)\s+("[A-Za-z0-9_ -]+"\s*:)', r"\1, \2", text)
    return text


def extract_jsonish_text(content):
    text = str(content or "")
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def repair_json_with_ollama(base_url, model, content, timeout):
    if not content:
        return ""
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You repair malformed JSON for a visual novel app. "
                    "Return only one compact valid JSON object. "
                    "Preserve the original fields and content; only fix JSON syntax. "
                    "Use plain text only, without markdown, HTML, CSS, or comments."
                ),
            },
            {
                "role": "user",
                "content": f"Repair this invalid JSON into valid JSON:\n\n{content}",
            },
        ],
    }
    try:
        data = post_chat(base_url, payload, min(float(timeout or 180), 240))
        return data.get("message", {}).get("content") or ""
    except Exception:
        return ""


def compact_error_body(content, limit=700):
    text = str(content or "").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
