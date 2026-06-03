import json
import random
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path


def get_system_stats(base_url):
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/system_stats", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def list_checkpoints(base_url):
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/object_info/CheckpointLoaderSimple", timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
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


def get_object_info(base_url, node_name):
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/object_info/{urllib.parse.quote(node_name)}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def free_memory(base_url, unload_models=True, free_memory_flag=True):
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/free",
        data=json.dumps({"unload_models": bool(unload_models), "free_memory": bool(free_memory_flag)}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8") or "{}"
    return json.loads(body)


def queue_simple_image(
    base_url,
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
):
    workflow = build_workflow(prompt, width, height, asset_type, checkpoint, steps, cfg, sampler_name, scheduler, negative_prompt)
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/prompt",
        data=json.dumps({"prompt": workflow}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def queue_workbench_image(
    base_url,
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
):
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
    )
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/prompt",
        data=json.dumps({"prompt": workflow}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_history(base_url, prompt_id):
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/history/{prompt_id}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def get_first_history_image(base_url, prompt_id):
    history = get_history(base_url, prompt_id)
    entry = history.get(prompt_id) or {}
    outputs = entry.get("outputs") or {}
    for output in outputs.values():
        images = output.get("images") or []
        if images:
            return images[0]
    return None


def download_image(base_url, image):
    params = urllib.parse.urlencode(
        {
            "filename": image.get("filename", ""),
            "type": image.get("type", "output"),
            "subfolder": image.get("subfolder", ""),
        }
    )
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/view?{params}", timeout=60) as response:
        return response.read(), response.headers.get("content-type") or "image/png"


def build_view_url(prompt_result, local_proxy_prefix="/api/comfy/view"):
    prompt_id = prompt_result.get("prompt_id")
    if not prompt_id:
        return ""
    return f"{local_proxy_prefix}?prompt_id={urllib.parse.quote(prompt_id)}"


def build_workflow(prompt, width, height, asset_type, checkpoint, steps, cfg, sampler_name, scheduler, negative_prompt=""):
    positive = build_positive_prompt(prompt, asset_type, checkpoint)
    negative = negative_prompt or build_negative_prompt(asset_type, checkpoint, prompt)

    return {
        "3": {
            "inputs": {
                "seed": random.randint(1, 18446744073709551615),
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
        for key in ("text", "value", "prompt", "positive_prompt", "negative_prompt", "width", "height", "seed", "steps", "cfg", "sampler_name", "scheduler", "ckpt_name"):
            if key in node_inputs:
                inputs.add(key)
    return sorted(inputs)


def apply_workbench_inputs(workflow, prompt, width, height, asset_type, checkpoint, steps, cfg, sampler_name, scheduler, negative_prompt="", preserve_generation_settings=True):
    workflow = deepcopy(workflow)
    positive = str(prompt or "").strip()
    negative = negative_prompt or build_negative_prompt(asset_type, checkpoint, prompt)
    assigned_positive = False
    assigned_negative = False

    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type") or ""
        inputs = node.get("inputs") or {}
        meta_title = ((node.get("_meta") or {}).get("title") or node.get("title") or "").lower()
        existing_text = first_string_input(inputs).lower()

        if not preserve_generation_settings and "width" in inputs and is_plain_value(inputs.get("width")):
            inputs["width"] = int(width or inputs.get("width") or 1024)
        if not preserve_generation_settings and "height" in inputs and is_plain_value(inputs.get("height")):
            inputs["height"] = int(height or inputs.get("height") or 576)
        if "seed" in inputs and is_plain_value(inputs.get("seed")):
            inputs["seed"] = random.randint(1, 18446744073709551615)
        if not preserve_generation_settings and "steps" in inputs and is_plain_value(inputs.get("steps")):
            inputs["steps"] = int(steps or inputs.get("steps") or 28)
        if not preserve_generation_settings and "cfg" in inputs and is_plain_value(inputs.get("cfg")):
            inputs["cfg"] = float(cfg or inputs.get("cfg") or 6.5)
        if not preserve_generation_settings and "sampler_name" in inputs and is_plain_value(inputs.get("sampler_name")) and sampler_name:
            inputs["sampler_name"] = sampler_name
        if not preserve_generation_settings and "scheduler" in inputs and is_plain_value(inputs.get("scheduler")) and scheduler:
            inputs["scheduler"] = scheduler
        if "ckpt_name" in inputs and is_plain_value(inputs.get("ckpt_name")) and checkpoint:
            inputs["ckpt_name"] = checkpoint
        if class_type == "SaveImage" and "filename_prefix" in inputs and is_plain_value(inputs.get("filename_prefix")):
            inputs["filename_prefix"] = "TaleWeaver"

        text_key = editable_text_key(inputs)
        if not text_key:
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

    return workflow


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
        return (
            f"{quality} anime visual novel background, empty environment, no people, no characters, "
            f"wide establishing shot, coherent architecture, rich atmospheric lighting, depth, clean composition, {prompt}"
        )
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
        common.extend(["person", "people", "human", "character", "face", "portrait", "body"])
    elif asset_type == "sprite":
        common.extend(["multiple people", "crowd", "scenery focus", "busy background", "detailed background", "shadow on wall"])
        common.extend(["2boys", "2girls", "two people", "twins", "duplicate person", "split screen", "panel layout", "comic panel", "frame", "border"])
        gender = infer_gender_tags(prompt)
        if "male" in gender:
            common.extend(["1girl", "woman", "female", "breasts", "dress", "skirt"])
        elif "female" in gender:
            common.extend(["1boy", "man", "male", "beard", "mustache"])
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
