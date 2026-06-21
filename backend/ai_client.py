import json
import re
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlparse, urlunparse

from . import db, ollama_client


OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"


class EmptyModelResponseError(RuntimeError):
    def __init__(self, message, content=""):
        super().__init__(message)
        self.content = content


class InvalidJsonResponseError(RuntimeError):
    def __init__(self, message, content=""):
        super().__init__(message)
        self.content = content


def list_ollama_models(settings=None):
    settings = settings or db.get_settings()
    return ollama_client.list_models(settings.get("ollama_url"))


def provider_id(settings=None):
    settings = settings or db.get_settings()
    provider = str(settings.get("ai_provider") or "ollama").strip().lower()
    if provider in {"openai", "openai-compatible"}:
        return provider
    return "ollama"


def provider_model(settings=None):
    settings = settings or db.get_settings()
    provider = provider_id(settings)
    if provider == "openai":
        return str(settings.get("openai_model") or "gpt-4.1-mini").strip()
    if provider == "openai-compatible":
        return str(settings.get("openai_compatible_model") or settings.get("openai_model") or "").strip()
    return str(settings.get("ollama_model") or "mistral-nemo").strip()


def provider_base_url(settings=None):
    settings = settings or db.get_settings()
    provider = provider_id(settings)
    if provider == "openai":
        return str(settings.get("openai_base_url") or OPENAI_DEFAULT_BASE_URL).strip()
    if provider == "openai-compatible":
        return str(settings.get("openai_compatible_base_url") or "").strip()
    return str(settings.get("ollama_url") or "http://127.0.0.1:11434").strip()


def request_info(settings=None, messages=None, **extra):
    settings = settings or db.get_settings()
    info = {
        "provider": provider_id(settings),
        "model": provider_model(settings),
        "base_url": provider_base_url(settings),
    }
    if messages is not None:
        info["messages"] = messages
    info.update(extra)
    return info


def chat_json(base_url, model, messages, temperature=0.8, options=None, settings=None):
    settings = settings or db.get_settings()
    provider = provider_id(settings)
    if provider == "ollama":
        return ollama_client.chat_json(
            settings.get("ollama_url") or base_url,
            settings.get("ollama_model") or model,
            messages,
            temperature,
            options,
        )
    return chat_openai_compatible_json(settings, provider, messages, temperature, options)


def settings_for_ai_role(settings, role):
    settings = dict(settings or db.get_settings())
    prefix = "story_ai" if role == "story" else "scene_ai" if role == "scene" else ""
    if not prefix:
        return settings

    provider = str(settings.get(f"{prefix}_provider") or settings.get("ai_provider") or "ollama").strip().lower()
    if provider not in {"ollama", "openai", "openai-compatible"}:
        provider = "openai-compatible"
    settings["ai_provider"] = provider

    mappings = {
        "openai_compatible_base_url": f"{prefix}_openai_compatible_base_url",
        "openai_compatible_model": f"{prefix}_openai_compatible_model",
        "openai_compatible_api_key": f"{prefix}_openai_compatible_api_key",
        "openai_compatible_verify_ssl": f"{prefix}_openai_compatible_verify_ssl",
        "openai_compatible_llama_mode": f"{prefix}_openai_compatible_llama_mode",
        "llama_preset": f"{prefix}_llama_preset",
        "llama_temperature": f"{prefix}_llama_temperature",
        "llama_top_p": f"{prefix}_llama_top_p",
        "llama_top_k": f"{prefix}_llama_top_k",
        "llama_min_p": f"{prefix}_llama_min_p",
        "llama_context_window": f"{prefix}_llama_context_window",
        "llama_max_tokens": f"{prefix}_llama_max_tokens",
        "llama_retry_max_tokens": f"{prefix}_llama_retry_max_tokens",
        "llama_max_attempts": f"{prefix}_llama_max_attempts",
        "llama_repeat_penalty": f"{prefix}_llama_repeat_penalty",
        "llama_repeat_last_n": f"{prefix}_llama_repeat_last_n",
        "llama_enable_thinking": f"{prefix}_llama_enable_thinking",
        "llama_cache_prompt": f"{prefix}_llama_cache_prompt",
        "llama_timings_per_token": f"{prefix}_llama_timings_per_token",
        "llama_timeout": f"{prefix}_llama_timeout",
    }
    for target, source in mappings.items():
        value = settings.get(source)
        if value not in {None, ""}:
            settings[target] = value
    return settings


def chat_openai_compatible_json(settings, provider, messages, temperature=0.8, options=None):
    model = provider_model(settings)
    if not model:
        raise ValueError(f"Modelo nao configurado para provider {provider}.")
    base_url = provider_base_url(settings)
    if not base_url:
        raise ValueError(f"Base URL nao configurada para provider {provider}.")
    api_key = provider_api_key(settings, provider)
    if not api_key and provider == "openai-compatible" and llama_mode_enabled(settings):
        api_key = "no-key"
    if not api_key:
        raise ValueError(f"API key nao configurada para provider {provider}.")
    verify_ssl = provider_verify_ssl(settings, provider)

    request_options = openai_compatible_request_options(settings, provider, options)
    timeout = float(request_options.pop("request_timeout", default_openai_compatible_timeout(settings, provider)) or 240)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature if temperature is not None else default_openai_compatible_temperature(settings, provider)),
    }
    max_tokens = request_options.pop("num_predict", None)
    if max_tokens not in {None, ""}:
        payload["max_tokens"] = int(max_tokens)
    top_p = request_options.pop("top_p", None)
    if top_p not in {None, "", 0}:
        payload["top_p"] = float(top_p)
    if provider == "openai-compatible" and llama_mode_enabled(settings):
        add_llama_cpp_payload_options(payload, request_options)

    payload = add_json_strictness(payload)
    data = post_chat_completion(provider, base_url, api_key, payload, timeout, verify_ssl, use_json_mode=True)
    content = extract_chat_completion_content(data, provider)
    try:
        return parse_json_content(content)
    except json.JSONDecodeError as exc:
        return repair_and_parse_json(provider, base_url, api_key, payload, content, timeout, verify_ssl, exc)


def add_json_strictness(payload):
    messages = list(payload.get("messages") or [])
    strict_content = (
        "JSON syntax requirements: return a single compact JSON object only. "
        "Do not use markdown, HTML, CSS, XML tags, color spans, inline styles, or formatting annotations. "
        "Use plain text only inside JSON string values. "
        "Escape every double quote inside string values, or use apostrophes inside prose. "
        "Do not put raw line breaks inside string values. Check every comma between fields and array items."
    )
    if messages and messages[0].get("role") == "system":
        messages[0] = {
            **messages[0],
            "content": f"{strict_content}\n\n{messages[0].get('content') or ''}".strip(),
        }
    else:
        messages = [{"role": "system", "content": strict_content}, *messages]
    return {**payload, "messages": normalize_chat_messages(messages)}


def normalize_chat_messages(messages):
    normalized = []
    for message in messages or []:
        role = str((message or {}).get("role") or "user").strip().lower()
        if role not in {"system", "user", "assistant"}:
            role = "user"
        content = normalize_message_content((message or {}).get("content"))
        if not content and role != "assistant":
            continue
        if normalized and normalized[-1]["role"] == role:
            normalized[-1]["content"] = f"{normalized[-1].get('content') or ''}\n\n{content}".strip()
        else:
            normalized.append({"role": role, "content": content})
    return normalized


def normalize_message_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


def parse_json_content(content):
    try:
        return ollama_client.parse_json_object(content)
    except json.JSONDecodeError:
        repaired = repair_json_text_locally(content)
        if repaired != content:
            return ollama_client.parse_json_object(repaired)
        raise


def repair_json_text_locally(content):
    text = extract_jsonish_text(content)
    text = text.replace("\ufeff", "").strip()
    text = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()
    text = escape_control_characters_in_json_strings(text)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r'([}\]"0-9])\s+("[A-Za-z0-9_ -]+"\s*:)', r"\1, \2", text)
    text = re.sub(r'\b(true|false|null)\s+("[A-Za-z0-9_ -]+"\s*:)', r"\1, \2", text)
    return text


def extract_jsonish_text(content):
    text = str(content or "")
    start = text.find("{")
    if start >= 0:
        balanced = extract_balanced_json_object(text, start)
        if balanced:
            return balanced
        end = text.rfind("}")
        if end > start:
            return text[start : end + 1]
    return text


def extract_balanced_json_object(text, start=0):
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "\"":
                in_string = False
            continue
        if char == "\"":
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def escape_control_characters_in_json_strings(text):
    output = []
    in_string = False
    escaped = False
    for char in str(text or ""):
        if in_string:
            if escaped:
                output.append(char)
                escaped = False
                continue
            if char == "\\":
                output.append(char)
                escaped = True
                continue
            if char == "\"":
                output.append(char)
                in_string = False
                continue
            if char == "\n":
                output.append("\\n")
            elif char == "\r":
                output.append("\\n")
            elif char == "\t":
                output.append("\\t")
            elif ord(char) < 32:
                output.append(" ")
            else:
                output.append(char)
            continue
        output.append(char)
        if char == "\"":
            in_string = True
    return "".join(output)


def repair_and_parse_json(provider, base_url, api_key, original_payload, content, timeout, verify_ssl, parse_error):
    repair_options = repair_payload_options(original_payload)
    repair_payload = {
        "model": original_payload.get("model"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You repair malformed JSON for a visual novel app. Return only one compact valid JSON object. "
                    "Do not include markdown, HTML, CSS, comments, explanations, or text outside JSON. Preserve the original "
                    "fields and content; only fix JSON syntax. Escape internal double quotes inside strings."
                ),
            },
            {
                "role": "user",
                "content": f"Repair this invalid JSON into valid JSON:\n\n{content}",
            },
        ],
        "temperature": 0,
        **repair_options,
    }
    if original_payload.get("chat_template_kwargs"):
        repair_payload["chat_template_kwargs"] = dict(original_payload.get("chat_template_kwargs") or {})
    try:
        data = post_chat_completion(provider, base_url, api_key, repair_payload, timeout, verify_ssl, use_json_mode=True)
        repaired = extract_chat_completion_content(data, provider)
        return parse_json_content(repaired)
    except Exception:
        pass

    try:
        retry_payload = retry_json_generation_payload(original_payload, parse_error)
        data = post_chat_completion(provider, base_url, api_key, retry_payload, timeout, verify_ssl, use_json_mode=True)
        regenerated = extract_chat_completion_content(data, provider)
        return parse_json_content(regenerated)
    except Exception as exc:
        excerpt = compact_error_body(content)
        raise InvalidJsonResponseError(
            f"{provider} returned invalid JSON: {parse_error}. Response excerpt: {excerpt}",
            content,
        ) from exc


def repair_payload_options(original_payload):
    result = {}
    for key in [
        "top_p",
        "top_k",
        "min_p",
        "repeat_penalty",
        "repeat_last_n",
        "cache_prompt",
        "timings_per_token",
        "chat_template_kwargs",
    ]:
        if key in original_payload:
            result[key] = original_payload[key]
    max_tokens = original_payload.get("max_tokens")
    if max_tokens:
        result["max_tokens"] = min(2400, max(1200, int(max_tokens)))
    return result


def retry_json_generation_payload(original_payload, parse_error):
    messages = list(original_payload.get("messages") or [])
    retry_content = (
        f"The previous response was invalid JSON: {parse_error}. Regenerate the requested result from scratch. "
        "Return only one compact valid JSON object. Do not include markdown, HTML, CSS, or inline formatting. Escape internal double quotes inside "
        "string values. Use apostrophes inside prose instead of unescaped double quotes. Check all commas."
    )
    messages = append_user_instruction(messages, retry_content)
    payload = {
        **original_payload,
        "temperature": 0,
        "messages": normalize_chat_messages(messages),
    }
    if payload.get("max_tokens"):
        current = int(payload.get("max_tokens"))
        payload["max_tokens"] = min(4096, max(1600, current * 2))
    return payload


def append_user_instruction(messages, instruction):
    messages = list(messages or [])
    if messages and messages[-1].get("role") == "user":
        messages[-1] = {
            **messages[-1],
            "content": f"{messages[-1].get('content') or ''}\n\n{instruction}".strip(),
        }
    else:
        messages.append({"role": "user", "content": instruction})
    return messages


def extract_chat_completion_content(data, provider):
    choices = data.get("choices") if isinstance(data, dict) else None
    choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    content = normalize_chat_content(message.get("content"))
    if content.strip():
        return content
    summary = empty_response_summary(data, choice, message)
    raise EmptyModelResponseError(
        f"{provider} returned empty message content. Response summary: {compact_error_body(summary)}",
        summary,
    )


def normalize_chat_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item.get("text"))
        return "\n".join(parts)
    return ""


def empty_response_summary(data, choice, message):
    summary = {
        "finish_reason": choice.get("finish_reason"),
        "message_keys": sorted(message.keys()),
        "has_reasoning_content": bool(message.get("reasoning_content")),
        "reasoning_content_chars": len(str(message.get("reasoning_content") or "")),
        "usage": data.get("usage") if isinstance(data, dict) else None,
        "timings": data.get("timings") if isinstance(data, dict) else None,
    }
    if message.get("reasoning_content"):
        summary["reasoning_preview"] = str(message.get("reasoning_content"))[:600]
    return json.dumps(summary, ensure_ascii=False)


def openai_compatible_request_options(settings, provider, options=None):
    request_options = {}
    if provider == "openai-compatible" and llama_mode_enabled(settings):
        request_options.update(llama_cpp_default_options(settings))
    request_options.update(dict(options or {}))
    return request_options


def default_openai_compatible_temperature(settings, provider):
    if provider == "openai-compatible" and llama_mode_enabled(settings):
        return settings.get("llama_temperature") or 0.78
    return settings.get("ollama_temperature") or 0.8


def default_openai_compatible_timeout(settings, provider):
    if provider == "openai-compatible" and llama_mode_enabled(settings):
        return settings.get("llama_timeout") or 240
    return settings.get("ollama_timeout") or 240


def llama_mode_enabled(settings):
    return settings.get("openai_compatible_llama_mode") is True


def detect_llama_context_window(settings):
    fallback = int(float(settings.get("llama_context_window") or 4096))
    if not llama_mode_enabled(settings):
        return fallback
    base_url = provider_base_url(settings)
    if not base_url:
        return fallback
    props_url = f"{llama_server_root_url(base_url)}/props"
    try:
        with urllib.request.urlopen(props_url, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return fallback
    generation_settings = data.get("default_generation_settings") or {}
    params = generation_settings.get("params") or {}
    try:
        return int(generation_settings.get("n_ctx") or params.get("n_ctx") or fallback)
    except (TypeError, ValueError):
        return fallback


def llama_server_root_url(base_url):
    url = str(base_url or "").rstrip("/")
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3] or ""
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")


def llama_cpp_default_options(settings):
    options = {
        "num_predict": settings.get("llama_max_tokens") or 1800,
        "top_p": settings.get("llama_top_p") or 0.9,
        "request_timeout": settings.get("llama_timeout") or 240,
        "cache_prompt": settings.get("llama_cache_prompt") is not False,
        "enable_thinking": settings.get("llama_enable_thinking") is True,
    }
    for key in ["top_k", "min_p", "repeat_penalty", "repeat_last_n"]:
        setting_key = f"llama_{key}"
        value = settings.get(setting_key)
        if value not in {None, "", 0}:
            options[key] = value
    if settings.get("llama_timings_per_token") is True:
        options["timings_per_token"] = True
    return options


def add_llama_cpp_payload_options(payload, request_options):
    for key in ["top_k", "repeat_last_n"]:
        value = request_options.pop(key, None)
        if value not in {None, "", 0}:
            payload[key] = int(value)
    for key in ["min_p", "repeat_penalty"]:
        value = request_options.pop(key, None)
        if value not in {None, "", 0}:
            payload[key] = float(value)
    for key in ["cache_prompt", "timings_per_token"]:
        value = request_options.pop(key, None)
        if value is not None:
            payload[key] = value is True
    enable_thinking = request_options.pop("enable_thinking", None)
    if enable_thinking is not None:
        payload["chat_template_kwargs"] = {
            **(payload.get("chat_template_kwargs") or {}),
            "enable_thinking": enable_thinking is True,
        }


def post_chat_completion(provider, base_url, api_key, payload, timeout, verify_ssl=True, use_json_mode=True):
    request_payload = dict(payload)
    if use_json_mode:
        request_payload["response_format"] = {"type": "json_object"}
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        urlopen_kwargs = {"timeout": timeout}
        if not verify_ssl:
            urlopen_kwargs["context"] = ssl._create_unverified_context()
        with urllib.request.urlopen(request, **urlopen_kwargs) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if use_json_mode and exc.code in {400, 422} and "response_format" in body:
            return post_chat_completion(provider, base_url, api_key, payload, timeout, verify_ssl, use_json_mode=False)
        raise RuntimeError(f"{provider} HTTP {exc.code}: {compact_error_body(body)}") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                f"{provider} SSL certificate verification failed. "
                "Fix the certificate chain or disable SSL verification for this provider in settings. "
                f"Details: {exc.reason}"
            ) from exc
        raise RuntimeError(f"{provider} connection error: {exc.reason}") from exc


def provider_api_key(settings, provider):
    if provider == "openai":
        return str(settings.get("openai_api_key") or "").strip()
    return str(settings.get("openai_compatible_api_key") or "").strip()


def provider_verify_ssl(settings, provider):
    key = "openai_verify_ssl" if provider == "openai" else "openai_compatible_verify_ssl"
    return settings.get(key) is not False


def compact_error_body(body):
    text = " ".join(str(body or "").split())
    return text[:600]
