import os
import subprocess
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from . import db
from .config import ROOT_DIR


COMFY_JOB_TIMEOUT_SECONDS = 60 * 60
COMFY_TEXT_AI_RESUME_DELAY_SECONDS = 2.0

_lock = threading.RLock()
_processes = {
    "llama": {"process": None, "started_by_app": False},
    "story_ai": {"process": None, "started_by_app": False},
    "scene_ai": {"process": None, "started_by_app": False},
    "comfy": {"process": None, "started_by_app": False},
}
_active_comfy_jobs = {}
_llama_resume_after_comfy = False
_llama_resume_timer = None
_active_text_ai_role = None


def autostart_services(settings=None):
    settings = settings or db.get_settings()
    results = {}
    for service in ("story_ai", "scene_ai", "comfy"):
        config = service_config(settings, service)
        if not config["start_with_app"]:
            results[service] = {"started": False, "reason": "disabled"}
            continue
        try:
            results[service] = start_service(service, settings, reason="app-start")
        except Exception as exc:
            results[service] = {"started": False, "error": str(exc)}
            db.add_api_log("local", f"script:{service}:start", config, status="error", error=str(exc))
    return results


def service_status(settings=None):
    settings = settings or db.get_settings()
    with _lock:
        cleanup_process_refs()
        return {
            "llama": status_for_service(settings, "llama"),
            "story_ai": status_for_service(settings, "story_ai"),
            "scene_ai": status_for_service(settings, "scene_ai"),
            "comfy": status_for_service(settings, "comfy"),
            "active_comfy_jobs": len(_active_comfy_jobs),
            "llama_paused_for_comfy": _llama_resume_after_comfy,
            "active_text_ai_role": active_text_ai_service(settings),
        }


def start_service(service, settings=None, reason="manual"):
    global _active_text_ai_role
    settings = settings or db.get_settings()
    config = service_config(settings, service)

    with _lock:
        cleanup_process_refs()
        current = _processes[service].get("process")
        listener_pids = local_listener_pids(config.get("url"))
        if not config["command"]:
            if listener_pids:
                if is_text_ai_service(service):
                    _active_text_ai_role = service
                return {"started": False, "reason": "already_listening_without_script", "pids": listener_pids}
            raise ValueError(f"Comando de inicializacao do {config['label']} nao configurado.")
        if current and current.poll() is None and listener_pids:
            if is_text_ai_service(service):
                _active_text_ai_role = service
            return {"started": False, "reason": "already_started_by_app", "pid": current.pid, "listener_pids": listener_pids}
        if current and current.poll() is None and config.get("url") and not listener_pids:
            ok, error = terminate_process_tree(current.pid)
            db.add_api_log(
                "local",
                f"script:{service}:cleanup-stale-shell",
                {"pid": current.pid, **safe_config(config)},
                {"stopped": ok},
                status="ok" if ok else "error",
                error=error,
            )
            _processes[service] = {"process": None, "started_by_app": False}

        if listener_pids:
            if reason == "app-start" and config["start_with_app"]:
                stopped = []
                for pid in listener_pids:
                    ok, error = terminate_process_tree(pid)
                    stopped.append({"pid": pid, "stopped": ok, "error": error})
                db.add_api_log(
                    "local",
                    f"script:{service}:restart-existing-listener",
                    {"reason": reason, **safe_config(config)},
                    {"listeners": stopped},
                    status="ok" if all(item.get("stopped") for item in stopped) else "error",
                    error="; ".join(item.get("error") or "" for item in stopped if item.get("error")),
                )
                time.sleep(1.0)
            else:
                if is_text_ai_service(service):
                    _active_text_ai_role = service
                return {"started": False, "reason": "already_listening", "pids": listener_pids}

        cwd = Path(config["cwd"] or ROOT_DIR).expanduser()
        if not cwd.exists() or not cwd.is_dir():
            raise FileNotFoundError(f"Pasta de execucao do {config['label']} nao encontrada: {cwd}")

        process = launch_process(config, cwd)
        _processes[service] = {"process": process, "started_by_app": True}
        if is_text_ai_service(service):
            _active_text_ai_role = service

    result = {"started": True, "pid": process.pid, "reason": reason, "show_window": config["show_window"]}
    db.add_api_log("local", f"script:{service}:start", safe_config(config), result)
    return result


def activate_text_ai_role(role, settings=None):
    settings = settings or db.get_settings()
    target = "story_ai" if role == "story" else "scene_ai" if role == "scene" else ""
    if not target:
        raise ValueError(f"Perfil de IA desconhecido: {role}")

    active = active_text_ai_service(settings)
    if active and active != target and not same_service_target(settings, target, active):
        stop_service(active, settings, reason=f"switch-to-{target}", allow_external=True)

    if role == "story":
        if active is None and not same_service_target(settings, "story_ai", "llama"):
            stop_service("llama", settings, reason="switch-to-story-ai", allow_external=True)
        result = start_service("story_ai", settings, reason="switch-to-story-ai")
        return wait_for_text_ai_ready("story_ai", settings, result)
    if role == "scene":
        result = start_service("scene_ai", settings, reason="switch-to-scene-ai")
        return wait_for_text_ai_ready("scene_ai", settings, result)


def is_text_ai_service(service):
    return service in {"llama", "story_ai", "scene_ai"}


def active_text_ai_service(settings=None):
    settings = settings or db.get_settings()
    with _lock:
        cleanup_process_refs()
        if _active_text_ai_role and text_ai_service_has_runtime(settings, _active_text_ai_role):
            return _active_text_ai_role
        for service in ("scene_ai", "story_ai", "llama"):
            if text_ai_service_has_runtime(settings, service, require_tracked_process=True):
                return service
    return None


def text_ai_service_has_runtime(settings, service, require_tracked_process=False):
    if not is_text_ai_service(service):
        return False
    config = service_config(settings, service)
    process = _processes.get(service, {}).get("process")
    listener_pids = local_listener_pids(config.get("url"))
    if process and process.poll() is None:
        return bool(listener_pids or not config.get("url"))
    return bool(listener_pids and not require_tracked_process and _active_text_ai_role == service)


def same_service_target(settings, left, right):
    left_config = service_config(settings, left)
    right_config = service_config(settings, right)
    left_command = normalized_service_command(left_config)
    right_command = normalized_service_command(right_config)
    if left_command and right_command:
        return left_command == right_command
    left_url = normalized_service_url(left_config.get("url"))
    right_url = normalized_service_url(right_config.get("url"))
    return bool(left_url and right_url and left_url == right_url and not (left_command or right_command))


def normalized_service_url(url):
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    parsed = urllib.parse.urlparse(text)
    host = (parsed.hostname or "").lower()
    if host == "localhost":
        host = "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme or 'http'}://{host}:{port}{path}"


def normalized_service_command(config):
    command = normalize_startup_command(config.get("command") or "").lower()
    cwd = str(config.get("cwd") or "").strip().lower()
    if not command:
        return ""
    return f"{cwd}|{command}"


def wait_for_text_ai_ready(service, settings=None, result=None):
    settings = settings or db.get_settings()
    config = service_config(settings, service)
    url = config.get("url")
    if not url:
        return result or {"ready": True, "reason": "no_url_configured"}

    timeout = text_ai_startup_timeout(settings, service)
    started_at = time.time()
    ready, detail = wait_for_http_ready(url, service, settings, timeout)
    elapsed = round(time.time() - started_at, 2)
    payload = {**(result or {}), "ready": ready, "ready_after_seconds": elapsed, "readiness": detail}
    db.add_api_log(
        "local",
        f"script:{service}:ready",
        {"timeout_seconds": timeout, **safe_config(config)},
        payload,
        status="ok" if ready else "error",
        error="" if ready else detail.get("error", ""),
    )
    if not ready:
        label = config.get("label") or service
        raise RuntimeError(
            f"{label} foi iniciado, mas ainda nao ficou pronto em {timeout}s. "
            f"Ultimo erro: {detail.get('error') or 'sem resposta'}"
        )
    return payload


def text_ai_startup_timeout(settings, service):
    candidates = [
        settings.get(f"script_{service}_startup_timeout"),
        settings.get(f"{service}_llama_timeout"),
        settings.get("llama_timeout"),
        settings.get("ollama_timeout"),
        180,
    ]
    for value in candidates:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return max(15, min(600, number))
    return 180


def wait_for_http_ready(url, service, settings, timeout):
    deadline = time.time() + timeout
    last_error = ""
    endpoints = readiness_endpoints(url, service, settings)
    while time.time() < deadline:
        for endpoint in endpoints:
            ok, error = http_endpoint_ready(endpoint)
            if ok:
                return True, {"endpoint": endpoint}
            last_error = error or last_error
        process = _processes.get(service, {}).get("process")
        if process and process.poll() is not None:
            last_error = f"processo encerrou com codigo {process.returncode}"
            return False, {"endpoints": endpoints, "error": last_error}
        time.sleep(0.5)
    return False, {"endpoints": endpoints, "error": last_error or "timeout aguardando API responder"}


def readiness_endpoints(url, service, settings):
    base = str(url or "").rstrip("/")
    if not base:
        return []
    if service in {"story_ai", "scene_ai", "llama"}:
        root = service_root_url(base)
        provider = text_ai_provider_for_service(settings, service)
        if provider == "ollama":
            return [f"{root}/api/tags"]
        endpoints = [f"{root}/health", f"{root}/props"]
        if base.endswith("/v1"):
            endpoints.append(f"{base}/models")
        else:
            endpoints.extend([f"{base}/models", f"{base}/v1/models"])
        return dedupe(endpoints)
    return [base]


def text_ai_provider_for_service(settings, service):
    if service == "story_ai":
        return str(settings.get("story_ai_provider") or settings.get("ai_provider") or "openai-compatible").strip().lower()
    if service == "scene_ai":
        return str(settings.get("scene_ai_provider") or settings.get("ai_provider") or "openai-compatible").strip().lower()
    return str(settings.get("ai_provider") or "openai-compatible").strip().lower()


def service_root_url(url):
    parsed = urllib.parse.urlparse(str(url or "").rstrip("/"))
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3].rstrip("/")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")


def http_endpoint_ready(url):
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=2) as response:
            return 200 <= int(response.status) < 500, ""
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return True, ""
        return False, f"{url} HTTP {exc.code}"
    except Exception as exc:
        return False, f"{url}: {exc}"


def dedupe(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def launch_process(config, cwd):
    command = normalize_startup_command(config["command"])
    if os.name == "nt":
        title = powershell_single_quote(f"TaleWeaver {config['label']}")
        if config["show_window"]:
            ps_command = f"$Host.UI.RawUI.WindowTitle = {title}; {command}"
            return subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", ps_command],
                cwd=str(cwd),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        return subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=str(cwd),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    return subprocess.Popen(command, cwd=str(cwd), shell=True, start_new_session=True)


def normalize_startup_command(command):
    text = str(command or "").strip()
    # Handles commands pasted from an interactive PowerShell continuation prompt.
    text = text.replace("`", " ")
    text = text.replace("\r", " ").replace("\n", " ")
    text = " ".join(part for part in text.split() if part != ">>")
    return text


def powershell_single_quote(value):
    return "'" + str(value or "").replace("'", "''") + "'"


def stop_service(service, settings=None, reason="manual", allow_external=False):
    global _active_text_ai_role
    settings = settings or db.get_settings()
    config = service_config(settings, service)
    stopped = []
    errors = []
    initial_listeners = local_listener_pids(config.get("url"))
    had_target = bool(initial_listeners)

    with _lock:
        cleanup_process_refs()
        process = _processes[service].get("process")
        if process and process.poll() is None:
            had_target = True
            ok, error = terminate_process_tree(process.pid)
            if ok:
                stopped.append({"pid": process.pid, "source": "app"})
            else:
                errors.append(error)
            _processes[service] = {"process": None, "started_by_app": False}
            if _active_text_ai_role == service:
                _active_text_ai_role = None

        if allow_external and config["command"]:
            for pid in initial_listeners or local_listener_pids(config.get("url")):
                if pid == os.getpid() or any(item.get("pid") == pid for item in stopped):
                    continue
                ok, error = terminate_process_tree(pid)
                if ok:
                    stopped.append({"pid": pid, "source": "listener"})
                else:
                    errors.append(error)

        if stopped and _active_text_ai_role == service:
            _active_text_ai_role = None

        remaining_listeners = wait_for_no_listeners(config.get("url"))
        if had_target and not remaining_listeners and not stopped:
            stopped.append({"pid": None, "source": "verified-port-closed"})
            errors = []

    result = {"stopped": bool(stopped), "items": stopped, "reason": reason}
    if remaining_listeners:
        result["remaining_listener_pids"] = remaining_listeners
    if errors:
        result["errors"] = errors
    db.add_api_log(
        "local",
        f"script:{service}:stop",
        {"reason": reason, "allow_external": allow_external, **safe_config(config)},
        result,
        status="ok" if stopped and not errors else ("error" if errors else "ok"),
        error="; ".join(errors),
    )
    return result


def begin_comfy_generation(settings=None, reason="comfy-generation"):
    settings = settings or db.get_settings()
    token = uuid.uuid4().hex
    with _lock:
        cancel_pending_text_ai_resume_locked()
        expire_stale_comfy_generations_locked(settings)
        if not _active_comfy_jobs:
            pause_llama_for_comfy_locked(settings)
        _active_comfy_jobs[token] = {"created_at": time.time(), "reason": reason, "asset_id": "", "prompt_id": ""}
    schedule_stale_cleanup()
    return token


def attach_comfy_generation(token, asset_id="", prompt_id=""):
    with _lock:
        job = _active_comfy_jobs.get(token)
        if job is not None:
            job["asset_id"] = asset_id or ""
            job["prompt_id"] = prompt_id or ""


def end_comfy_generation(token=None, asset_id="", settings=None, reason="done"):
    settings = settings or db.get_settings()
    removed = False
    with _lock:
        if token and token in _active_comfy_jobs:
            _active_comfy_jobs.pop(token, None)
            removed = True
        if asset_id:
            for job_token, job in list(_active_comfy_jobs.items()):
                if job.get("asset_id") == asset_id:
                    _active_comfy_jobs.pop(job_token, None)
                    removed = True
        expire_stale_comfy_generations_locked(settings)
        if removed and not _active_comfy_jobs:
            schedule_text_ai_resume_locked(settings, reason)


def pause_llama_for_comfy_locked(settings):
    global _llama_resume_after_comfy
    config = service_config(settings, "scene_ai")
    story_config = service_config(settings, "story_ai")
    legacy_config = service_config(settings, "llama")
    if not config["command"] and not story_config["command"] and not legacy_config["command"]:
        db.add_api_log(
            "local",
            "script:llama:pause-for-comfy",
            safe_config(config),
            {"paused": False, "reason": "scene_ai_command_not_configured"},
        )
        return
    result = stop_service("scene_ai", settings, reason="before-comfy", allow_external=True)
    story_result = {"stopped": False}
    if not same_service_target(settings, "story_ai", "scene_ai"):
        story_result = stop_service("story_ai", settings, reason="before-comfy", allow_external=True)
    legacy_result = stop_service("llama", settings, reason="before-comfy", allow_external=True)
    if result.get("stopped") or story_result.get("stopped") or legacy_result.get("stopped"):
        _llama_resume_after_comfy = True
        return
    remaining = local_listener_pids(config.get("url")) + local_listener_pids(story_config.get("url")) + local_listener_pids(legacy_config.get("url"))
    if remaining:
        raise RuntimeError(f"Nao foi possivel parar a IA de texto antes do ComfyUI. PIDs ainda ativos: {remaining}")


def resume_llama_after_comfy_locked(settings, reason):
    global _llama_resume_after_comfy
    if not _llama_resume_after_comfy:
        return
    _llama_resume_after_comfy = False
    try:
        start_service("scene_ai", settings, reason=f"after-comfy:{reason}")
    except Exception as exc:
        db.add_api_log(
            "local",
            "script:llama:restart-after-comfy",
            safe_config(service_config(settings, "llama")),
            status="error",
            error=str(exc),
        )


def schedule_text_ai_resume_locked(settings, reason):
    global _llama_resume_timer
    cancel_pending_text_ai_resume_locked()
    timer = threading.Timer(
        COMFY_TEXT_AI_RESUME_DELAY_SECONDS,
        resume_text_ai_if_comfy_idle,
        args=(reason,),
    )
    timer.daemon = True
    _llama_resume_timer = timer
    timer.start()


def cancel_pending_text_ai_resume_locked():
    global _llama_resume_timer
    if _llama_resume_timer:
        _llama_resume_timer.cancel()
        _llama_resume_timer = None


def resume_text_ai_if_comfy_idle(reason):
    global _llama_resume_timer
    settings = db.get_settings()
    with _lock:
        _llama_resume_timer = None
        expire_stale_comfy_generations_locked(settings)
        if not _active_comfy_jobs:
            resume_llama_after_comfy_locked(settings, reason)


def schedule_stale_cleanup():
    timer = threading.Timer(COMFY_JOB_TIMEOUT_SECONDS + 5, expire_stale_comfy_generations)
    timer.daemon = True
    timer.start()


def expire_stale_comfy_generations():
    settings = db.get_settings()
    with _lock:
        expired = expire_stale_comfy_generations_locked(settings)
        if expired and not _active_comfy_jobs:
            schedule_text_ai_resume_locked(settings, "stale-timeout")


def expire_stale_comfy_generations_locked(settings):
    now = time.time()
    expired = []
    for token, job in list(_active_comfy_jobs.items()):
        if now - float(job.get("created_at") or now) > COMFY_JOB_TIMEOUT_SECONDS:
            expired.append(job)
            _active_comfy_jobs.pop(token, None)
    if expired:
        db.add_api_log(
            "local",
            "script:comfy:jobs-expired",
            {"timeout_seconds": COMFY_JOB_TIMEOUT_SECONDS},
            {"expired": expired},
        )
    return expired


def status_for_service(settings, service):
    config = service_config(settings, service)
    process = _processes[service].get("process")
    listener_pids = local_listener_pids(config.get("url"))
    return {
        "configured": bool(config["command"]),
        "running_by_app": bool(process and process.poll() is None and (not config.get("url") or listener_pids)),
        "pid": process.pid if process and process.poll() is None else None,
        "listener_pids": listener_pids,
        "start_with_app": config["start_with_app"],
        "show_window": config["show_window"],
    }


def cleanup_process_refs():
    for service, item in _processes.items():
        process = item.get("process")
        if process and process.poll() is not None:
            _processes[service] = {"process": None, "started_by_app": False}


def service_config(settings, service):
    if service == "llama":
        return {
            "label": "Llama",
            "cwd": settings.get("script_llama_cwd") or "",
            "command": settings.get("script_llama_command") or "",
            "start_with_app": settings.get("script_llama_start_with_app") is True,
            "show_window": settings.get("script_llama_show_window") is True,
            "url": llama_url(settings),
        }
    if service == "story_ai":
        return {
            "label": "IA de geracao de historia",
            "cwd": settings.get("script_story_ai_cwd") or "",
            "command": settings.get("script_story_ai_command") or "",
            "start_with_app": settings.get("script_story_ai_start_with_app") is True,
            "show_window": settings.get("script_story_ai_show_window") is True,
            "url": settings.get("story_ai_openai_compatible_base_url") or "",
        }
    if service == "scene_ai":
        return {
            "label": "IA de narrativa",
            "cwd": settings.get("script_scene_ai_cwd") or settings.get("script_llama_cwd") or "",
            "command": settings.get("script_scene_ai_command") or settings.get("script_llama_command") or "",
            "start_with_app": settings.get("script_scene_ai_start_with_app") is True or settings.get("script_llama_start_with_app") is True,
            "show_window": settings.get("script_scene_ai_show_window") is not False and settings.get("script_llama_show_window") is not False,
            "url": settings.get("scene_ai_openai_compatible_base_url") or settings.get("openai_compatible_base_url") or "",
        }
    if service == "comfy":
        return {
            "label": "ComfyUI",
            "cwd": settings.get("script_comfy_cwd") or settings.get("comfy_root") or "",
            "command": settings.get("script_comfy_command") or "",
            "start_with_app": settings.get("script_comfy_start_with_app") is True,
            "show_window": settings.get("script_comfy_show_window") is True,
            "url": settings.get("comfy_url") or "",
        }
    raise ValueError(f"Servico desconhecido: {service}")


def llama_url(settings):
    if settings.get("openai_compatible_llama_mode") is True:
        return settings.get("openai_compatible_base_url") or ""
    return settings.get("openai_compatible_base_url") or ""


def safe_config(config):
    return {
        "label": config.get("label"),
        "cwd": config.get("cwd"),
        "command_configured": bool(config.get("command")),
        "start_with_app": config.get("start_with_app"),
        "show_window": config.get("show_window"),
        "url": config.get("url"),
    }


def local_listener_pids(url):
    parsed = urllib.parse.urlparse(str(url or ""))
    if not parsed.hostname or not parsed.port:
        return []
    if parsed.hostname.lower() not in {"127.0.0.1", "localhost", "::1"}:
        return []
    if os.name != "nt":
        return []
    try:
        completed = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    pids = set()
    port_suffix = f":{parsed.port}"
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local_address = parts[1]
        state = parts[3].upper()
        pid_text = parts[4]
        if state != "LISTENING" or not local_address.endswith(port_suffix):
            continue
        try:
            pids.add(int(pid_text))
        except ValueError:
            continue
    return sorted(pids)


def wait_for_no_listeners(url, timeout=6.0):
    deadline = time.time() + timeout
    last = local_listener_pids(url)
    while last and time.time() < deadline:
        time.sleep(0.25)
        last = local_listener_pids(url)
    return last


def terminate_process_tree(pid):
    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
        if completed.returncode == 0:
            return True, ""
        taskkill_error = (completed.stderr or completed.stdout or f"taskkill saiu com codigo {completed.returncode}").strip()
        try:
            ps = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    f"Stop-Process -Id {int(pid)} -Force -ErrorAction Stop",
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"{taskkill_error}; {exc}"
        if ps.returncode == 0:
            return True, ""
        powershell_error = (ps.stderr or ps.stdout or f"Stop-Process saiu com codigo {ps.returncode}").strip()
        return False, f"{taskkill_error}; {powershell_error}"
    try:
        os.kill(pid, 15)
        return True, ""
    except OSError as exc:
        return False, str(exc)
