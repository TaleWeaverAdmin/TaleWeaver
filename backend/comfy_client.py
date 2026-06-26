import json
import mimetypes
import random
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path

COMFY_PROVIDERS = {"local_standard", "remote_standard", "comfy_cloud"}
COMFY_PROVIDER_SLOTS = {
    "sprite": "sprite_comfy_provider",
    "background": "background_comfy_provider",
    "appearance": "appearance_comfy_provider",
    "appearance_reference": "appearance_reference_comfy_provider",
    "expression": "expression_comfy_provider",
}


def normalize_comfy_provider(provider):
    text = str(provider or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in COMFY_PROVIDERS else "local_standard"


def comfy_default_provider(settings):
    return normalize_comfy_provider((settings or {}).get("comfy_default_provider") or "local_standard")


def comfy_provider_for_style_slot(settings, visual_style, slot):
    field = COMFY_PROVIDER_SLOTS.get(str(slot or "").strip())
    value = (visual_style or {}).get(field) if field else ""
    return normalize_comfy_provider(value or comfy_default_provider(settings))


def is_remote_comfy_provider(provider):
    return normalize_comfy_provider(provider) in {"remote_standard", "comfy_cloud"}


def build_comfy_url(settings, provider, path):
    provider = normalize_comfy_provider(provider)
    path = "/" + str(path or "").lstrip("/")
    if provider == "remote_standard":
        base = str((settings or {}).get("comfy_remote_url") or "").strip()
        prefix = str((settings or {}).get("comfy_remote_api_prefix") or "").strip()
    elif provider == "comfy_cloud":
        base = str((settings or {}).get("comfy_cloud_url") or "https://cloud.comfy.org").strip()
        prefix = str((settings or {}).get("comfy_cloud_api_prefix") or "/api").strip()
    else:
        base = str((settings or {}).get("comfy_url") or "http://127.0.0.1:8188").strip()
        prefix = ""
    if not base:
        raise ValueError(f"ComfyUI provider {provider} nao tem URL configurada.")
    prefix = "/" + prefix.strip("/") if prefix else ""
    return f"{base.rstrip('/')}{prefix}{path}"


def build_comfy_headers(settings, provider, content_type="application/json"):
    provider = normalize_comfy_provider(provider)
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if provider == "remote_standard":
        auth_type = str((settings or {}).get("comfy_remote_auth_type") or "none").strip().lower()
        token = str((settings or {}).get("comfy_remote_auth_token") or "")
        if auth_type == "bearer" and token:
            headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "x_api_key" and token:
            headers["X-API-Key"] = token
        elif auth_type == "custom_header" and token:
            name = str((settings or {}).get("comfy_remote_auth_header_name") or "").strip()
            if name:
                headers[name] = token
    elif provider == "comfy_cloud":
        token = str((settings or {}).get("comfy_cloud_auth_token") or "")
        if token:
            headers["X-API-Key"] = token
    return headers


def comfy_workflows_dir_for_provider(settings, provider):
    provider = normalize_comfy_provider(provider)
    if provider == "remote_standard":
        configured = (settings or {}).get("comfy_remote_workflows_dir") or (settings or {}).get("comfy_workflows_dir")
    elif provider == "comfy_cloud":
        configured = (settings or {}).get("comfy_cloud_workflows_dir") or (settings or {}).get("comfy_workflows_dir")
    else:
        configured = (settings or {}).get("comfy_workflows_dir")
    if configured:
        return Path(configured)
    comfy_root = (settings or {}).get("comfy_root") or ""
    return Path(comfy_root) / "user" / "default" / "workflows"


def _is_settings(value):
    return isinstance(value, dict)


def _request_url(settings_or_base_url, provider, path):
    if _is_settings(settings_or_base_url):
        return build_comfy_url(settings_or_base_url, provider, path)
    return f"{str(settings_or_base_url or '').rstrip('/')}/" + str(path or "").lstrip("/")


def _request_headers(settings_or_base_url, provider, content_type="application/json"):
    if _is_settings(settings_or_base_url):
        return build_comfy_headers(settings_or_base_url, provider, content_type)
    return {"Content-Type": content_type} if content_type else {}


def _error_message(provider, exc, operation):
    provider = normalize_comfy_provider(provider)
    prefix = f"ComfyUI provider {provider} failed"
    if isinstance(exc, urllib.error.HTTPError):
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        detail = " ".join(detail.split())[:600]
        if exc.code in {401, 403}:
            reason = "unauthorized or invalid API key"
        elif exc.code == 404:
            reason = "endpoint not found or provider does not expose the expected API"
        elif exc.code == 429:
            reason = "rate limit"
        elif exc.code == 400:
            lower = detail.lower()
            if "checkpoint" in lower or "model" in lower:
                reason = "missing model or checkpoint"
            elif "class_type" in lower or "node" in lower:
                reason = "missing node or invalid workflow"
            else:
                reason = "invalid workflow or request"
        else:
            reason = f"HTTP {exc.code}"
        return f"{prefix}: {reason} during {operation}" + (f". Detail: {detail}" if detail else "")
    if isinstance(exc, urllib.error.URLError):
        return f"{prefix}: server unreachable during {operation}. Detail: {exc.reason}"
    if isinstance(exc, FileNotFoundError):
        return f"{prefix}: workflow file or upload image missing during {operation}. Detail: {exc}"
    return f"{prefix}: {operation} failed. Detail: {exc}"


def comfy_verify_ssl(settings, provider):
    if not _is_settings(settings):
        return True
    provider = normalize_comfy_provider(provider)
    if provider == "remote_standard":
        return settings.get("comfy_remote_verify_ssl") is not False
    if provider == "comfy_cloud":
        return settings.get("comfy_cloud_verify_ssl") is not False
    return True


def _ssl_context_for(settings_or_base_url, provider):
    if _is_settings(settings_or_base_url) and not comfy_verify_ssl(settings_or_base_url, provider):
        return ssl._create_unverified_context()
    return None


def _urlopen_json(request, provider, operation, timeout, settings_or_base_url=None):
    try:
        context = _ssl_context_for(settings_or_base_url, provider)
        kwargs = {"timeout": timeout}
        if context is not None:
            kwargs["context"] = context
        with urllib.request.urlopen(request, **kwargs) as response:
            body = response.read().decode("utf-8") or "{}"
        return json.loads(body)
    except Exception as exc:
        raise RuntimeError(_error_message(provider, exc, operation)) from exc


def _urlopen_bytes(url_or_request, provider, operation, timeout, settings_or_base_url=None):
    try:
        context = _ssl_context_for(settings_or_base_url, provider)
        kwargs = {"timeout": timeout}
        if context is not None:
            kwargs["context"] = context
        with urllib.request.urlopen(url_or_request, **kwargs) as response:
            return response.read(), response.headers.get("content-type") or "image/png"
    except Exception as exc:
        raise RuntimeError(_error_message(provider, exc, operation)) from exc


def is_timeout_error(exc):
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError):
        return is_timeout_error(exc.reason)
    return False


def get_system_stats(settings_or_base_url, provider="local_standard"):
    status_path = "/object_info" if _is_settings(settings_or_base_url) and normalize_comfy_provider(provider) == "comfy_cloud" else "/system_stats"
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, status_path),
        headers=_request_headers(settings_or_base_url, provider, None),
    )
    return _urlopen_json(request, provider, "connection test", 5, settings_or_base_url)


def list_checkpoints(settings_or_base_url, provider="local_standard"):
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, "/object_info/CheckpointLoaderSimple"),
        headers=_request_headers(settings_or_base_url, provider, None),
    )
    data = _urlopen_json(request, provider, "checkpoint list", 5, settings_or_base_url)
    return data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]


def list_workbenches(workflows_dir):
    root = Path(workflows_dir or "").expanduser()
    if not root.exists() or not root.is_dir():
        return []

    workbenches = []
    for path in sorted(root.rglob("*.json")):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            workflow_format = detect_workflow_format(data)
        except (OSError, json.JSONDecodeError) as exc:
            workflow_format = "invalid"
            data = {}
            error = str(exc)
        else:
            error = ""

        rel_path = path.relative_to(root).as_posix()
        workbenches.append(
            {
                "id": rel_path,
                "name": path.stem.replace("_", " ").replace("-", " "),
                "path": str(path),
                "format": workflow_format,
                "executable": workflow_format == "api",
                "inputs": detect_workbench_inputs(data) if workflow_format == "api" else [],
                "error": error,
            }
        )
    return workbenches


def get_object_info(settings_or_base_url, node_name, provider="local_standard"):
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, f"/object_info/{urllib.parse.quote(node_name)}"),
        headers=_request_headers(settings_or_base_url, provider, None),
    )
    return _urlopen_json(request, provider, "object info", 5, settings_or_base_url)


def free_memory(settings_or_base_url, unload_models=True, free_memory_flag=True, provider="local_standard"):
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, "/free"),
        data=json.dumps({"unload_models": bool(unload_models), "free_memory": bool(free_memory_flag)}).encode("utf-8"),
        headers=_request_headers(settings_or_base_url, provider, "application/json"),
        method="POST",
    )
    return _urlopen_json(request, provider, "free memory", 20, settings_or_base_url)


def queue_simple_image(
    settings_or_base_url,
    prompt,
    width=1024,
    height=576,
    asset_type="background",
    checkpoint="illustriousXL_v01.safetensors",
    steps=28,
    cfg=6.5,
    sampler_name="dpmpp_2m_sde_gpu",
    scheduler="karras",
    negative_prompt="",
    seed=None,
    provider="local_standard",
):
    workflow = build_workflow(prompt, width, height, asset_type, checkpoint, steps, cfg, sampler_name, scheduler, negative_prompt, seed)
    payload = {"prompt": workflow}
    if _is_settings(settings_or_base_url) and normalize_comfy_provider(provider) == "comfy_cloud" and settings_or_base_url.get("comfy_cloud_extra_data_api_key") and settings_or_base_url.get("comfy_cloud_auth_token"):
        payload["extra_data"] = {"api_key_comfy_org": settings_or_base_url.get("comfy_cloud_auth_token")}
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, "/prompt"),
        data=json.dumps(payload).encode("utf-8"),
        headers=_request_headers(settings_or_base_url, provider, "application/json"),
        method="POST",
    )
    return _urlopen_json(request, provider, "submit prompt", 30, settings_or_base_url)


def queue_workbench_image(
    settings_or_base_url,
    workflows_dir,
    workbench_id,
    prompt,
    width=1024,
    height=576,
    asset_type="background",
    checkpoint="",
    steps=28,
    cfg=6.5,
    sampler_name="dpmpp_2m_sde_gpu",
    scheduler="karras",
    negative_prompt="",
    preserve_generation_settings=True,
    generation_overrides=None,
    input_image_path=None,
    reference_image_path=None,
    expression_prompts=None,
    provider="local_standard",
):
    input_image = upload_image(settings_or_base_url, input_image_path, provider=provider) if input_image_path else None
    reference_image = upload_image(settings_or_base_url, reference_image_path, provider=provider) if reference_image_path else None
    workflow = load_api_workflow(workflows_dir, workbench_id)
    workflow = apply_workbench_inputs(
        workflow,
        prompt,
        width,
        height,
        asset_type,
        checkpoint,
        steps,
        cfg,
        sampler_name,
        scheduler,
        negative_prompt,
        preserve_generation_settings,
        generation_overrides,
        input_image,
        reference_image,
        expression_prompts,
    )
    payload = {"prompt": workflow}
    if _is_settings(settings_or_base_url) and normalize_comfy_provider(provider) == "comfy_cloud" and settings_or_base_url.get("comfy_cloud_extra_data_api_key") and settings_or_base_url.get("comfy_cloud_auth_token"):
        payload["extra_data"] = {"api_key_comfy_org": settings_or_base_url.get("comfy_cloud_auth_token")}
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, "/prompt"),
        data=json.dumps(payload).encode("utf-8"),
        headers=_request_headers(settings_or_base_url, provider, "application/json"),
        method="POST",
    )
    return _urlopen_json(request, provider, "submit prompt", 30, settings_or_base_url)


def get_history(settings_or_base_url, prompt_id, provider="local_standard"):
    if _is_settings(settings_or_base_url) and normalize_comfy_provider(provider) == "comfy_cloud":
        return get_comfy_cloud_job_history(settings_or_base_url, prompt_id, provider=provider)
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, f"/history/{urllib.parse.quote(str(prompt_id or ''))}"),
        headers=_request_headers(settings_or_base_url, provider, None),
    )
    return _urlopen_json(request, provider, "history/status", 10, settings_or_base_url)


def get_comfy_cloud_job_history(settings, prompt_id, provider="comfy_cloud"):
    request = urllib.request.Request(
        _request_url(settings, provider, f"/jobs/{urllib.parse.quote(str(prompt_id or ''))}"),
        headers=_request_headers(settings, provider, None),
    )
    data = _urlopen_json(request, provider, "history/status", 10, settings)
    return normalize_comfy_cloud_job_history(prompt_id, data)


def normalize_comfy_cloud_job_history(prompt_id, data):
    job = data.get("job") if isinstance(data, dict) and isinstance(data.get("job"), dict) else data
    job = job if isinstance(job, dict) else {}
    job_id = str(job.get("prompt_id") or job.get("id") or prompt_id or "")
    status = str(
        job.get("status")
        or job.get("state")
        or job.get("status_str")
        or job.get("job_status")
        or ""
    ).strip().lower()
    normalized_status = {
        "completed": "success",
        "complete": "success",
        "succeeded": "success",
        "success": "success",
        "finished": "success",
        "failed": "error",
        "failure": "error",
        "error": "error",
        "cancelled": "error",
        "canceled": "error",
    }.get(status, status or "running")
    error = job.get("error") or job.get("failure_reason") or job.get("message") or ""
    output_source = first_present(job, ["outputs", "output", "result", "results", "artifacts", "assets", "images", "files"])
    images = collect_comfy_cloud_images(output_source) if output_source else []
    outputs = {"cloud": {"images": images}} if images else {}
    history_key = str(prompt_id or job_id or "")
    return {
        history_key: {
            "outputs": outputs,
            "status": {
                "status_str": normalized_status,
                "messages": [["error", error]] if error and normalized_status == "error" else [],
            },
            "comfy_cloud_job": redact_cloud_job_for_history(job),
        }
    }


def collect_comfy_cloud_images(value):
    images = []
    seen = set()

    def add_image(item, node_id="cloud"):
        image = normalize_comfy_cloud_image(item, node_id)
        key = image_identity(image)
        if image and key not in seen:
            seen.add(key)
            images.append(image)

    def walk(item, node_id="cloud"):
        if isinstance(item, str):
            if looks_like_image_url(item):
                add_image(item, node_id)
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{node_id}_{index}")
            return
        if not isinstance(item, dict):
            return
        if is_cloud_image_item(item):
            add_image(item, str(item.get("node_id") or item.get("node") or node_id))
        nested_images = item.get("images")
        if isinstance(nested_images, list):
            for child in nested_images:
                add_image(child, str(item.get("node_id") or item.get("node") or node_id))
        for key, child in item.items():
            if key in {"images"}:
                continue
            walk(child, str(key or node_id))

    walk(value)
    return images


def normalize_comfy_cloud_image(item, node_id="cloud"):
    if isinstance(item, str):
        url = item
        filename = filename_from_url(url) or "comfy_cloud_output.png"
        return {"filename": filename, "type": "output", "subfolder": "", "url": url, "node_id": node_id}
    if not isinstance(item, dict):
        return {}
    url = first_present(item, ["url", "download_url", "image_url", "file_url", "signed_url", "public_url", "src"])
    filename = first_present(item, ["filename", "file_name", "name", "path", "key"]) or filename_from_url(url) or "comfy_cloud_output.png"
    image = dict(item)
    image.setdefault("filename", Path(str(filename)).name or "comfy_cloud_output.png")
    image.setdefault("type", item.get("type") or item.get("output_type") or "output")
    image.setdefault("subfolder", item.get("subfolder") or "")
    image.setdefault("node_id", node_id)
    if url:
        image["url"] = url
    return image


def is_cloud_image_item(item):
    if not isinstance(item, dict):
        return False
    if first_present(item, ["url", "download_url", "image_url", "file_url", "signed_url", "public_url", "src"]):
        return True
    filename = first_present(item, ["filename", "file_name", "name", "path", "key"])
    return bool(filename and str(filename).lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")))


def looks_like_image_url(value):
    text = str(value or "").strip().lower().split("?")[0]
    return text.startswith(("http://", "https://", "/")) and text.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))


def image_identity(image):
    if not isinstance(image, dict):
        return ""
    return "|".join(str(image.get(key) or "") for key in ["url", "filename", "subfolder", "type", "node_id"])


def first_present(source, keys):
    for key in keys:
        value = source.get(key)
        if value is not None and value != "":
            return value
    return ""


def filename_from_url(url):
    if not url:
        return ""
    parsed = urllib.parse.urlparse(str(url))
    filename = Path(urllib.parse.unquote(parsed.path or "")).name
    return filename if filename and "." in filename else ""


def redact_cloud_job_for_history(job):
    if not isinstance(job, dict):
        return {}
    return {
        key: value for key, value in job.items()
        if key not in {"outputs", "output", "result", "results"}
    }


def get_first_history_image(settings_or_base_url, prompt_id, provider="local_standard"):
    history = get_history(settings_or_base_url, prompt_id, provider=provider)
    entry = history.get(prompt_id) or {}
    outputs = entry.get("outputs") or {}
    for output in outputs.values():
        images = output.get("images") or []
        if images:
            return images[0]
    return None


def get_history_images(settings_or_base_url, prompt_id, provider="local_standard"):
    history = get_history(settings_or_base_url, prompt_id, provider=provider)
    entry = history.get(prompt_id) or {}
    outputs = entry.get("outputs") or {}
    images = []
    for node_id, output in outputs.items():
        for image in output.get("images") or []:
            item = dict(image)
            item.setdefault("node_id", node_id)
            images.append(item)
    return images, entry


def download_image(settings_or_base_url, image, provider="local_standard"):
    direct_url = image_download_url(settings_or_base_url, image, provider)
    if direct_url:
        request = urllib.request.Request(
            direct_url,
            headers=_download_headers_for_url(settings_or_base_url, provider, direct_url),
        )
        return _urlopen_bytes(request, provider, "output download", 60, settings_or_base_url)
    params = urllib.parse.urlencode(
        {
            "filename": image.get("filename", ""),
            "type": image.get("type", "output"),
            "subfolder": image.get("subfolder", ""),
        }
    )
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, f"/view?{params}"),
        headers=_request_headers(settings_or_base_url, provider, None),
    )
    return _urlopen_bytes(request, provider, "output download", 60, settings_or_base_url)


def image_download_url(settings_or_base_url, image, provider="local_standard"):
    if not isinstance(image, dict):
        return ""
    provider = normalize_comfy_provider(provider)
    url = first_present(image, ["url", "download_url", "image_url", "file_url", "signed_url", "public_url", "src"])
    if not url:
        return ""
    text = str(url).strip()
    if text.startswith(("http://", "https://")):
        return text
    if not _is_settings(settings_or_base_url):
        return ""
    if text.startswith("/api/") and provider == "comfy_cloud":
        base = str(settings_or_base_url.get("comfy_cloud_url") or "https://cloud.comfy.org").strip().rstrip("/")
        return f"{base}{text}"
    if text.startswith("/"):
        return build_comfy_url(settings_or_base_url, provider, text)
    return build_comfy_url(settings_or_base_url, provider, "/" + text)


def _download_headers_for_url(settings_or_base_url, provider, url):
    if not _is_settings(settings_or_base_url):
        return {}
    parsed = urllib.parse.urlparse(str(url or ""))
    if parsed.scheme in {"http", "https"}:
        api_host = urllib.parse.urlparse(build_comfy_url(settings_or_base_url, provider, "/")).netloc
        if parsed.netloc and parsed.netloc != api_host:
            return {}
    return _request_headers(settings_or_base_url, provider, None)


def upload_image(settings_or_base_url, image_path, provider="local_standard"):
    path = Path(image_path or "")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Imagem de referencia nao encontrada: {image_path}")
    boundary = f"----TaleWeaver{random.randint(100000, 999999)}"
    content_type = mimetypes.guess_type(str(path))[0] or "image/png"
    filename = path.name
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    request = urllib.request.Request(
        _request_url(settings_or_base_url, provider, "/upload/image"),
        data=body,
        headers=_request_headers(settings_or_base_url, provider, f"multipart/form-data; boundary={boundary}"),
        method="POST",
    )
    return _urlopen_json(request, provider, "upload image", 60, settings_or_base_url)


def build_view_url(prompt_result, local_proxy_prefix="/api/comfy/view"):
    prompt_id = prompt_result.get("prompt_id")
    if not prompt_id:
        return ""
    return f"{local_proxy_prefix}?prompt_id={urllib.parse.quote(prompt_id)}"


def build_workflow(prompt, width, height, asset_type, checkpoint, steps, cfg, sampler_name, scheduler, negative_prompt="", seed=None):
    positive = build_positive_prompt(prompt, asset_type, checkpoint)
    negative = negative_prompt or build_negative_prompt(asset_type, checkpoint, prompt)

    return {
        "3": {
            "inputs": {
                "seed": int(seed) if seed not in {None, ""} else random.randint(1, 18446744073709551615),
                "steps": int(steps or 28),
                "cfg": float(cfg or 6.5),
                "sampler_name": sampler_name or "dpmpp_2m_sde_gpu",
                "scheduler": scheduler or "karras",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "4": {
            "inputs": {"ckpt_name": checkpoint or "illustriousXL_v01.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        "5": {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "6": {"inputs": {"text": positive, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"text": negative, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": "TaleWeaver", "images": ["8", 0]}, "class_type": "SaveImage"},
    }


def load_api_workflow(workflows_dir, workbench_id):
    if not workbench_id:
        raise ValueError("Workbench nao informado.")
    root = Path(workflows_dir or "").expanduser().resolve()
    path = (root / workbench_id).resolve()
    if not is_relative_to(path, root) or path.suffix.lower() != ".json":
        raise ValueError("Workbench fora da pasta de workflows permitida.")
    if not path.exists():
        raise FileNotFoundError(f"Workbench nao encontrado: {workbench_id}")

    data = json.loads(path.read_text(encoding="utf-8"))
    workflow_format = detect_workflow_format(data)
    if workflow_format != "api":
        raise ValueError(
            "Este workbench esta no formato visual do editor. "
            "No ComfyUI, use Save/Export API Format e salve o JSON na pasta de workflows."
        )
    return data


def detect_workflow_format(data):
    if not isinstance(data, dict):
        return "unknown"
    if isinstance(data.get("nodes"), list):
        return "ui"
    node_count = 0
    api_node_count = 0
    for value in data.values():
        if isinstance(value, dict):
            node_count += 1
            if "class_type" in value and isinstance(value.get("inputs"), dict):
                api_node_count += 1
    if api_node_count and api_node_count == node_count:
        return "api"
    if api_node_count:
        return "api"
    return "unknown"


def detect_workbench_inputs(workflow):
    inputs = set()
    if not isinstance(workflow, dict):
        return []
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        node_inputs = node.get("inputs") or {}
        for key in ("text", "value", "prompt", "positive_prompt", "negative_prompt", "width", "height", "seed", "noise_seed", "steps", "cfg", "sampler_name", "scheduler", "ckpt_name"):
            if key in node_inputs:
                inputs.add(key)
    return sorted(inputs)


def apply_workbench_inputs(
    workflow,
    prompt,
    width,
    height,
    asset_type,
    checkpoint,
    steps,
    cfg,
    sampler_name,
    scheduler,
    negative_prompt="",
    preserve_generation_settings=True,
    generation_overrides=None,
    input_image=None,
    reference_image=None,
    expression_prompts=None,
):
    workflow = deepcopy(workflow)
    positive = str(prompt or "").strip()
    negative = negative_prompt or build_negative_prompt(asset_type, checkpoint, prompt)
    assigned_positive = False
    assigned_negative = False
    assigned_image = False
    assigned_reference_image = False
    overrides = generation_overrides if isinstance(generation_overrides, dict) else None
    input_image_name = comfy_uploaded_image_name(input_image)
    reference_image_name = comfy_uploaded_image_name(reference_image)
    expression_prompts = expression_prompts if isinstance(expression_prompts, dict) else {}

    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type") or ""
        inputs = node.get("inputs") or {}
        meta_title = ((node.get("_meta") or {}).get("title") or node.get("title") or "").lower()
        existing_text = first_string_input(inputs).lower()

        if should_override_generation_field("width", preserve_generation_settings, overrides) and "width" in inputs and is_plain_value(inputs.get("width")):
            inputs["width"] = int(generation_override_value("width", overrides, width) or inputs.get("width") or 1024)
        if should_override_generation_field("height", preserve_generation_settings, overrides) and "height" in inputs and is_plain_value(inputs.get("height")):
            inputs["height"] = int(generation_override_value("height", overrides, height) or inputs.get("height") or 576)
        seed_value = generation_override_value("seed", overrides, None)
        if seed_value not in {None, ""}:
            for seed_key in ("seed", "noise_seed"):
                if seed_key in inputs and is_plain_value(inputs.get(seed_key)):
                    inputs[seed_key] = int(seed_value)
            if "control_after_generate" in inputs and is_plain_value(inputs.get("control_after_generate")):
                inputs["control_after_generate"] = "fixed"
        if should_override_generation_field("steps", preserve_generation_settings, overrides) and "steps" in inputs and is_plain_value(inputs.get("steps")):
            inputs["steps"] = int(generation_override_value("steps", overrides, steps) or inputs.get("steps") or 28)
        if should_override_generation_field("cfg", preserve_generation_settings, overrides) and "cfg" in inputs and is_plain_value(inputs.get("cfg")):
            inputs["cfg"] = float(generation_override_value("cfg", overrides, cfg) or inputs.get("cfg") or 6.5)
        if should_override_generation_field("sampler_name", preserve_generation_settings, overrides) and "sampler_name" in inputs and is_plain_value(inputs.get("sampler_name")):
            value = generation_override_value("sampler_name", overrides, sampler_name)
            if value:
                inputs["sampler_name"] = value
        if should_override_generation_field("scheduler", preserve_generation_settings, overrides) and "scheduler" in inputs and is_plain_value(inputs.get("scheduler")):
            value = generation_override_value("scheduler", overrides, scheduler)
            if value:
                inputs["scheduler"] = value
        if should_override_generation_field("ckpt_name", preserve_generation_settings, overrides) and "ckpt_name" in inputs and is_plain_value(inputs.get("ckpt_name")):
            value = generation_override_value("ckpt_name", overrides, checkpoint)
            if value:
                inputs["ckpt_name"] = value
        if (
            class_type == "SaveImage"
            and "filename_prefix" in inputs
            and is_plain_value(inputs.get("filename_prefix"))
            and not filename_prefix_has_expression(inputs.get("filename_prefix"))
        ):
            inputs["filename_prefix"] = "TaleWeaver"
        if "image" in inputs and is_plain_value(inputs.get("image")):
            if reference_image_name:
                if not assigned_reference_image and workflow_image_role(meta_title) == "reference":
                    inputs["image"] = reference_image_name
                    assigned_reference_image = True
                elif not assigned_image and workflow_image_role(meta_title) == "main":
                    inputs["image"] = input_image_name
                    assigned_image = True
            elif input_image_name and not assigned_image:
                inputs["image"] = input_image_name
                assigned_image = True

        text_key = editable_text_key(inputs)
        if not text_key:
            continue
        expression_key = expression_key_for_prompt_node(meta_title, existing_text)
        if expression_key and str(expression_prompts.get(expression_key) or "").strip():
            inputs[text_key] = str(expression_prompts[expression_key]).strip()
            continue
        is_negative = "negative" in meta_title or looks_like_negative_prompt(existing_text)
        is_system = "system" in meta_title and "negative" not in meta_title
        if is_negative and preserve_generation_settings and not negative_prompt:
            continue
        if is_negative and not assigned_negative:
            inputs[text_key] = negative
            assigned_negative = True
        elif not is_system and not assigned_positive and looks_like_prompt_field(meta_title, text_key, class_type):
            inputs[text_key] = positive
            assigned_positive = True

    if reference_image_name and (not assigned_image or not assigned_reference_image):
        raise ValueError("O workflow com duas referencias precisa ter nós de imagem nomeados Main e Reference.")
    return workflow


def workflow_image_role(title):
    tokens = {token for token in re.split(r"[^a-z0-9]+", str(title or "").lower()) if token}
    if "reference" in tokens:
        return "reference"
    if "main" in tokens:
        return "main"
    return ""


def expression_key_for_prompt_node(title, text):
    value = f"{title} {text}".lower()
    aliases = {
        "happy": ["happy"],
        "sad": ["sad"],
        "angry": ["angry"],
        "thoughtful": ["thoughtful", "thoughfull"],
        "surprised": ["surprised"],
        "embarrassed": ["embarrassed", "embarrased"],
        "scared": ["scared"],
    }
    for expression, markers in aliases.items():
        if any(re.search(rf"\b{re.escape(marker)}\b", value) for marker in markers):
            return expression
    return ""


def comfy_uploaded_image_name(input_image):
    if not isinstance(input_image, dict):
        return ""
    name = str(input_image.get("name") or "").strip()
    subfolder = str(input_image.get("subfolder") or "").strip().strip("/\\")
    if not name:
        return ""
    return f"{subfolder}/{name}" if subfolder else name


def filename_prefix_has_expression(value):
    text = str(value or "").lower()
    tokens = [token for token in re.split(r"[^a-z0-9]+", text) if token]
    return any(expression in tokens for expression in ["happy", "sad", "angry", "thoughtful", "surprised", "embarrassed", "scared"])


def should_override_generation_field(field, preserve_generation_settings, overrides):
    if overrides is not None:
        return field in overrides and overrides.get(field) not in {None, ""}
    return not preserve_generation_settings


def generation_override_value(field, overrides, fallback):
    if overrides is not None:
        return overrides.get(field)
    return fallback


def editable_text_key(inputs):
    for key in ("text", "value", "prompt", "positive_prompt", "negative_prompt"):
        if key in inputs and is_plain_value(inputs.get(key)):
            return key
    return ""


def first_string_input(inputs):
    for key in ("text", "value", "prompt", "positive_prompt", "negative_prompt"):
        value = inputs.get(key)
        if isinstance(value, str):
            return value
    return ""


def is_plain_value(value):
    return not isinstance(value, list)


def looks_like_negative_prompt(text):
    markers = ["negative", "worst quality", "low quality", "bad anatomy", "watermark", "blurry"]
    return any(marker in text for marker in markers)


def looks_like_prompt_field(title, key, class_type):
    if "negative" in title:
        return False
    if key in {"positive_prompt", "prompt"}:
        return True
    if "prompt" in title or "positive" in title:
        return True
    return class_type in {"CLIPTextEncode", "PrimitiveStringMultiline", "PrimitiveString"}


def is_relative_to(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def build_positive_prompt(prompt, asset_type, checkpoint):
    checkpoint_name = (checkpoint or "").lower()
    if "animagine" in checkpoint_name:
        quality = "masterpiece, best quality, very aesthetic, absurdres,"
    elif "pony" in checkpoint_name:
        quality = "score_9, score_8_up, score_7_up, source_anime, highly detailed,"
    else:
        quality = "masterpiece, best quality, high quality, very detailed, sharp focus,"

    if asset_type == "background":
        return str(prompt or "").strip()
    elif asset_type == "sprite":
        gender_tags = infer_gender_tags(prompt)
        return (
            f"{quality} {gender_tags} anime visual novel character sprite, {prompt}, "
            f"centered, clean silhouette, detailed face, detailed eyes, detailed clothing, consistent character design, "
            f"simple light gray background, transparent-background friendly"
        )
    return f"{quality} anime visual novel illustration, {prompt}"


def build_negative_prompt(asset_type, checkpoint, prompt=""):
    common = [
        "lowres",
        "worst quality",
        "low quality",
        "normal quality",
        "blurry",
        "jpeg artifacts",
        "text",
        "signature",
        "watermark",
        "logo",
        "username",
        "bad anatomy",
        "bad hands",
        "extra fingers",
        "missing fingers",
        "extra limbs",
        "deformed",
        "mutated",
        "cropped",
        "out of frame",
        "duplicate",
    ]
    if asset_type == "background":
        common.extend([
            "main character",
            "foreground person",
            "foreground people",
            "close-up face",
            "detailed face",
            "portrait",
            "full body in foreground",
            "centered human figure",
            "character focus",
        ])
    elif asset_type == "sprite":
        common.extend(["multiple people", "crowd", "scenery focus", "busy background", "detailed background", "shadow on wall"])
        common.extend(["2boys", "2girls", "two people", "twins", "duplicate person", "split screen", "panel layout", "comic panel", "frame", "border"])
    return ", ".join(common)


def infer_gender_tags(prompt):
    text = (prompt or "").lower()
    old_male_terms = ["old man", "elderly man", "senhor idoso"]
    old_female_terms = ["old woman", "elderly woman", "senhora idosa"]
    male_terms = ["1boy", " man", "male", "gentleman", "senhor", "masculine"]
    female_terms = ["1girl", "woman", "female", "lady", "girl", "senhora", "feminine"]
    if any(term in text for term in old_female_terms):
        return "1girl, female, elderly woman,"
    if any(term in text for term in old_male_terms):
        return "1boy, male, elderly man,"
    if any(term in text for term in female_terms):
        return "1girl, female, feminine,"
    if any(term in text for term in male_terms):
        return "1boy, male, masculine,"
    return ""
