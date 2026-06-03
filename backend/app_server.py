import gc
import json
import mimetypes
import os
import re
import shutil
import stat
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import comfy_client, db, narrative, ollama_client
from .config import ROOT_DIR, STORIES_DIR, STYLE_COVERS_DIR


PUBLIC_DIR = ROOT_DIR / "public"


class AppHandler(BaseHTTPRequestHandler):
    server_version = "TaleWeaver/0.1"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        try:
            if path == "/api/health":
                return self.send_json({"ok": True})
            if path == "/api/settings":
                return self.send_json(db.get_settings())
            if path == "/api/visual-styles":
                return self.send_json({"styles": db.list_visual_styles()})
            if path.startswith("/api/visual-styles/") and path.endswith("/cover"):
                style_id = path.strip("/").split("/")[2]
                return self.serve_visual_style_cover(style_id)
            if path == "/api/ollama/models":
                settings = db.get_settings()
                return self.send_json({"models": ollama_client.list_models(settings.get("ollama_url"))})
            if path == "/api/comfy/status":
                settings = db.get_settings()
                return self.send_json(comfy_client.get_system_stats(settings.get("comfy_url")))
            if path == "/api/comfy/checkpoints":
                settings = db.get_settings()
                return self.send_json({"checkpoints": comfy_client.list_checkpoints(settings.get("comfy_url"))})
            if path == "/api/comfy/workbenches":
                settings = db.get_settings()
                return self.send_json({
                    "workbenches": comfy_client.list_workbenches(comfy_workflows_dir(settings)),
                    "workflows_dir": str(comfy_workflows_dir(settings)),
                })
            if path == "/api/logs":
                limit = (query.get("limit") or ["100"])[0]
                story_id = (query.get("story_id") or [""])[0] or None
                return self.send_json({"logs": db.list_api_logs(story_id, limit)})
            if path.startswith("/api/comfy/object-info/"):
                settings = db.get_settings()
                node_name = path.split("/")[4]
                return self.send_json(comfy_client.get_object_info(settings.get("comfy_url"), node_name))
            if path == "/api/stories":
                return self.send_json({"stories": db.list_stories()})
            if path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                story = db.get_story(story_id)
                if not story:
                    return self.send_error_json(404, "Historia nao encontrada.")
                return self.send_json(story)
            if path == "/api/comfy/view":
                return self.proxy_comfy_view(query)
            if path.startswith("/api/assets/"):
                return self.handle_asset_get(path)
            return self.serve_static(path)
        except Exception as exc:
            return self.send_error_json(500, str(exc))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        payload = {} if self.is_multipart() else self.read_json()

        try:
            if path == "/api/app/shutdown":
                return self.shutdown_app()
            if path == "/api/settings":
                return self.send_json(db.update_settings(payload))
            if path == "/api/visual-styles":
                return self.send_json(db.create_visual_style(payload), 201)
            if path.startswith("/api/visual-styles/") and path.endswith("/cover"):
                style_id = path.strip("/").split("/")[2]
                return self.upload_visual_style_cover(style_id)
            if path == "/api/ai/improve":
                return self.send_json(narrative.improve_text(payload))
            if path == "/api/ai/story-seed":
                return self.send_json(narrative.generate_story_seed(payload))
            if path == "/api/stories":
                return self.send_json(db.create_story(narrative.enrich_story_creation_payload(payload)), 201)
            if path.endswith("/duplicate") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                story = db.duplicate_story(story_id)
                if not story:
                    return self.send_error_json(404, "Historia nao encontrada.")
                db.add_api_log(
                    "local",
                    "story:duplicate",
                    {"source_story_id": story_id},
                    {"story_id": story["id"]},
                    story_id=story["id"],
                )
                return self.send_json(story, 201)
            if path.endswith("/generate-scene") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                story = narrative.generate_scene(story_id, payload.get("user_input") or "")
                if payload.get("generate_images") is False:
                    story["auto_background"] = {"mode": "skipped"}
                else:
                    auto_background = self.ensure_scene_background(story_id, story)
                    if auto_background.get("mode") in {"reused", "carried"}:
                        story = db.get_story(story_id)
                    story["auto_background"] = auto_background
                return self.send_json(story)
            if path.endswith("/characters") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                story = db.get_story(story_id)
                if not story:
                    return self.send_error_json(404, "Historia nao encontrada.")
                character_payload = narrative.complete_character_record(payload, story, latest_scene(story))
                narrative.apply_character_sprite_prompt(character_payload, db.get_settings(), story_id=story_id)
                return self.send_json(db.create_character(story_id, character_payload), 201)
            if path.endswith("/characters/introduce") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                return self.introduce_character(story_id, payload)
            if path.startswith("/api/characters/") and path.endswith("/image-prompt"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    return self.generate_character_image_prompt(parts[2], payload)
            if path.endswith("/memory") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                story = db.add_memory_entry(
                    story_id,
                    payload.get("entry_type") or "note",
                    payload.get("content") or "",
                    payload.get("importance") or 3,
                )
                if not story:
                    return self.send_error_json(404, "Historia nao encontrada.")
                return self.send_json(story, 201)
            if path.endswith("/lore") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                story = db.add_lore_entry(
                    story_id,
                    payload.get("title") or "Entrada de lore",
                    payload.get("content") or "",
                    payload.get("entry_type") or "note",
                )
                if not story:
                    return self.send_error_json(404, "Historia nao encontrada.")
                return self.send_json(story, 201)
            if path.endswith("/generate-image") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                return self.generate_image(story_id, payload)
            return self.send_error_json(404, "Endpoint nao encontrado.")
        except Exception as exc:
            return self.send_error_json(500, str(exc))

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        payload = self.read_json()

        try:
            if len(parts) == 3 and parts[:2] == ["api", "stories"]:
                story = db.update_story(parts[2], payload)
                if not story:
                    return self.send_error_json(404, "Historia nao encontrada.")
                return self.send_json(story)
            if len(parts) == 3 and parts[:2] == ["api", "scenes"]:
                story = db.update_scene(parts[2], payload)
                if not story:
                    return self.send_error_json(404, "Cena nao encontrada.")
                return self.send_json(story)
            if len(parts) == 3 and parts[:2] == ["api", "characters"]:
                return self.send_json(db.update_character(parts[2], payload))
            if len(parts) == 3 and parts[:2] == ["api", "memory"]:
                story = db.update_memory_entry(parts[2], payload)
                if not story:
                    return self.send_error_json(404, "Memoria nao encontrada.")
                return self.send_json(story)
            if len(parts) == 3 and parts[:2] == ["api", "lore"]:
                story = db.update_lore_entry(parts[2], payload)
                if not story:
                    return self.send_error_json(404, "Lore nao encontrado.")
                return self.send_json(story)
            if len(parts) == 3 and parts[:2] == ["api", "visual-styles"]:
                style = db.update_visual_style(parts[2], payload)
                if not style:
                    return self.send_error_json(404, "Estilo nao encontrado.")
                return self.send_json(style)
            return self.send_error_json(404, "Endpoint nao encontrado.")
        except Exception as exc:
            return self.send_error_json(500, str(exc))

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        parts = parsed.path.strip("/").split("/")

        try:
            if len(parts) == 3 and parts[:2] == ["api", "stories"]:
                return self.delete_story(parts[2])
            if len(parts) == 3 and parts[:2] == ["api", "assets"]:
                return self.delete_asset(parts[2])
            if len(parts) == 3 and parts[:2] == ["api", "memory"]:
                story = db.delete_memory_entry(parts[2])
                if not story:
                    return self.send_error_json(404, "Memoria nao encontrada.")
                return self.send_json(story)
            if len(parts) == 3 and parts[:2] == ["api", "lore"]:
                story = db.delete_lore_entry(parts[2])
                if not story:
                    return self.send_error_json(404, "Lore nao encontrado.")
                return self.send_json(story)
            if len(parts) == 3 and parts[:2] == ["api", "visual-styles"]:
                return self.delete_visual_style(parts[2])
            return self.send_error_json(404, "Endpoint nao encontrado.")
        except Exception as exc:
            return self.send_error_json(500, str(exc))

    def delete_story(self, story_id):
        story = db.delete_story(story_id)
        deleted_dir = False
        delete_error = ""
        target = (STORIES_DIR / story_id).resolve()
        stories_root = STORIES_DIR.resolve()
        folder_exists = target.exists() and target.is_dir()
        if is_relative_to(target, stories_root) and folder_exists:
            deleted_dir, delete_error = delete_path_with_retries(target)
        if not story and not folder_exists:
            return self.send_error_json(404, "Historia nao encontrada.")

        db.add_api_log(
            "local",
            "story:delete",
            {"story_id": story_id},
            {"story_found": bool(story), "deleted_dir": deleted_dir, "delete_error": delete_error},
            story_id=story_id,
        )
        return self.send_json({
            "deleted": True,
            "story": story,
            "deleted_dir": deleted_dir,
            "delete_error": delete_error,
        })

    def upload_visual_style_cover(self, style_id):
        style = db.get_visual_style(style_id)
        if not style:
            return self.send_error_json(404, "Estilo nao encontrado.")
        upload = self.read_multipart_file("image")
        if not upload or not upload.get("body"):
            return self.send_error_json(400, "Imagem nao enviada.")

        original_name = upload.get("filename") or "cover.png"
        extension = Path(original_name).suffix.lower()
        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            extension = ".png"
        STYLE_COVERS_DIR.mkdir(parents=True, exist_ok=True)
        relative_path = STYLE_COVERS_DIR.relative_to(ROOT_DIR) / f"{style_id}{extension}"
        target = ROOT_DIR / relative_path
        target.write_bytes(upload["body"])

        previous = style.get("cover_path")
        if previous and previous != relative_path.as_posix():
            previous_target = (ROOT_DIR / previous).resolve()
            if is_relative_to(previous_target, STYLE_COVERS_DIR.resolve()) and previous_target.exists():
                try:
                    previous_target.unlink()
                except OSError:
                    pass

        updated = db.update_visual_style(style_id, {"cover_path": relative_path.as_posix()})
        return self.send_json(updated)

    def serve_visual_style_cover(self, style_id):
        style = db.get_visual_style(style_id)
        if not style or not style.get("cover_path"):
            return self.send_error_json(404, "Capa do estilo nao encontrada.")
        target = (ROOT_DIR / style["cover_path"]).resolve()
        if not is_relative_to(target, STYLE_COVERS_DIR.resolve()) or not target.exists() or not target.is_file():
            return self.send_error_json(404, "Arquivo da capa nao encontrado.")
        content_type = mimetypes.guess_type(str(target))[0] or "image/png"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def delete_visual_style(self, style_id):
        style = db.get_visual_style(style_id)
        if not style:
            return self.send_error_json(404, "Estilo nao encontrado.")
        if style.get("cover_path"):
            target = (ROOT_DIR / style["cover_path"]).resolve()
            if is_relative_to(target, STYLE_COVERS_DIR.resolve()) and target.exists() and target.is_file():
                try:
                    target.unlink()
                except OSError:
                    pass
        deleted = db.delete_visual_style(style_id)
        return self.send_json({"deleted": True, "style": deleted})

    def generate_image(self, story_id, payload):
        settings = db.get_settings()
        asset_type = payload.get("asset_type") or "background"
        visual_style = db.visual_style_for_story(story_id) if asset_type == "sprite" else None
        style_settings = (visual_style or {}).get("advanced_settings") or {}
        requested_workbench = payload.get("workbench") or style_workbench(visual_style) or default_workbench_for_asset(settings, asset_type)
        width = int(payload.get("width") or settings.get("image_width") or 1024)
        height = int(payload.get("height") or settings.get("image_height") or 576)
        steps = int(settings.get("background_steps") or 28)
        cfg = float(settings.get("background_cfg") or 6.5)
        negative_prompt = ""
        prompt = payload.get("prompt") or ""
        source_prompt = prompt
        prompt_source = "local"
        if asset_type == "sprite":
            width = int(payload.get("width") or style_settings.get("width") or settings.get("sprite_width") or 640)
            height = int(payload.get("height") or style_settings.get("height") or settings.get("sprite_height") or 960)
            steps = int(style_settings.get("steps") or settings.get("sprite_steps") or 24)
            cfg = float(style_settings.get("cfg") or settings.get("sprite_cfg") or 5.0)
            character = db.get_character(payload.get("character_id")) if payload.get("character_id") else None
            prompt = (prompt or (character or {}).get("visual_prompt") or "").strip()
            source_prompt = prompt
            if not prompt:
                return self.send_error_json(400, "Prompt de imagem do personagem vazio.")
            prompt = apply_style_prompt(visual_style, prompt)
            prompt_source = "visual-style" if visual_style else "local"
            negative_prompt = (visual_style or {}).get("negative_prompt") or ""
        elif asset_type == "background":
            source_prompt = prompt.strip()
            story = db.get_story(story_id) or {}
            scene = find_scene_for_payload(story, payload) if story else {}
            if scene:
                scene_for_prompt = dict(scene)
                scene_for_prompt["background_prompt"] = source_prompt or scene.get("background_prompt") or ""
                prompt = narrative.build_background_visual_prompt(story, scene_for_prompt)
                prompt_source = "local:background-robust"
            else:
                prompt = source_prompt

        prompt_profile = prompt_profile_for_workbench(settings, requested_workbench)
        if prompt_profile and asset_type != "sprite":
            prompt = narrative.generate_workbench_visual_prompt(
                prompt,
                asset_type,
                requested_workbench,
                prompt_profile,
                prompt,
                story_id=story_id,
            )
            prompt_source = "ollama:workbench-profile"

        sampler = settings.get("comfy_sampler")
        scheduler = settings.get("comfy_scheduler")
        if asset_type == "sprite":
            sampler = style_settings.get("sampler_name") or settings.get("sprite_sampler") or sampler
            scheduler = style_settings.get("scheduler") or settings.get("sprite_scheduler") or scheduler

        checkpoint = payload.get("checkpoint") or style_settings.get("ckpt_name") or settings.get("comfy_checkpoint")
        preserve_workbench_settings = not bool(visual_style and style_settings)
        result, workbench_id = self.queue_comfy_image(
            settings,
            asset_type,
            prompt,
            width,
            height,
            checkpoint,
            steps,
            cfg,
            sampler,
            scheduler,
            requested_workbench,
            negative_prompt,
            preserve_workbench_settings,
        )
        db.add_api_log(
            "comfyui",
            "prompt:image",
            {
                "asset_type": asset_type,
                "width": width,
                "height": height,
                "checkpoint": checkpoint,
                "workbench": workbench_id,
                "steps": steps,
                "cfg": cfg,
                "sampler": sampler,
                "scheduler": scheduler,
                "prompt_source": prompt_source,
                "visual_style_id": (visual_style or {}).get("id") or "",
                "negative_prompt": negative_prompt,
                "workbench_generation_settings": "preserved" if workbench_id and preserve_workbench_settings else "app",
                "source_prompt": source_prompt,
                "prompt": prompt,
            },
            result,
            story_id=story_id,
        )
        asset_id = db.add_asset(
            story_id,
            {
                "asset_type": asset_type,
                "character_id": payload.get("character_id"),
                "scene_id": payload.get("scene_id"),
                "expression": payload.get("expression"),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "remote_ref": result.get("prompt_id", ""),
                "metadata": {"workbench": workbench_id, "visual_style_id": (visual_style or {}).get("id") or "", **result},
            },
        )
        return self.send_json({"asset_id": asset_id, "queued": result})

    def generate_character_image_prompt(self, character_id, payload):
        character = db.get_character(character_id)
        if not character:
            return self.send_error_json(404, "Personagem nao encontrado.")

        settings = db.get_settings()
        visual_style = db.visual_style_for_story(character.get("story_id"))
        workbench_id = payload.get("workbench") or style_workbench(visual_style) or default_workbench_for_asset(settings, "sprite")
        prompt_profile = prompt_profile_for_workbench(settings, workbench_id)
        expression = payload.get("expression") or "neutral"
        instructions = payload.get("instructions") or ""
        source_prompt = narrative.build_sprite_source_prompt(character, expression, instructions)
        fallback = narrative.build_sprite_visual_prompt(
            character,
            expression,
            instructions,
        )
        visual_prompt = narrative.generate_workbench_visual_prompt(
            source_prompt,
            "sprite",
            workbench_id,
            prompt_profile,
            fallback,
            story_id=character.get("story_id"),
        )
        updated = db.update_character(character_id, {"visual_prompt": visual_prompt})
        db.add_api_log(
            "local",
            "character:image-prompt",
            {"character_id": character_id, "workbench": workbench_id},
            {"visual_prompt": visual_prompt},
            story_id=character.get("story_id"),
        )
        return self.send_json(updated)

    def introduce_character(self, story_id, payload):
        story = db.get_story(story_id)
        if not story:
            return self.send_error_json(404, "Historia nao encontrada.")

        name = (payload.get("name") or payload.get("display_name") or "").strip()
        if not name and isinstance(payload.get("candidate"), dict):
            candidate = payload.get("candidate")
            name = (candidate.get("display_name") or candidate.get("temporary_name") or candidate.get("name") or "").strip()
        if not name:
            return self.send_error_json(400, "Nome do personagem vazio.")

        existing = find_character_by_name(story.get("characters") or [], name)
        if existing:
            return self.send_json({"character": existing, "story": story, "already_exists": True})

        scene = find_scene_for_payload(story, payload)
        character_payload = narrative.enrich_introduced_character(story, scene, payload)
        if not character_payload.get("name"):
            character_payload["name"] = name
        character = db.create_character(story_id, character_payload)
        updated_story = db.get_story(story_id)
        db.add_api_log(
            "local",
            "character:introduce",
            {"story_id": story_id, "scene_id": scene.get("id") if scene else "", "name": name},
            {"character_id": character.get("id"), "name": character.get("name")},
            story_id=story_id,
        )
        return self.send_json({"character": character, "story": updated_story, "already_exists": False}, 201)

    def queue_comfy_image(
        self,
        settings,
        asset_type,
        prompt,
        width,
        height,
        checkpoint,
        steps,
        cfg,
        sampler,
        scheduler,
        requested_workbench="",
        negative_prompt="",
        preserve_generation_settings=True,
    ):
        workbench_id = requested_workbench or default_workbench_for_asset(settings, asset_type)
        if workbench_id:
            if settings.get("comfy_free_memory_between_workbench_runs") is not False:
                free_result = comfy_client.free_memory(settings.get("comfy_url"))
                db.add_api_log(
                    "comfyui",
                    "memory:free-before-workbench",
                    {"workbench": workbench_id, "asset_type": asset_type},
                    free_result,
                )
            return (
                comfy_client.queue_workbench_image(
                    settings.get("comfy_url"),
                    comfy_workflows_dir(settings),
                    workbench_id,
                    prompt,
                    width,
                    height,
                    asset_type,
                    "" if preserve_generation_settings else checkpoint,
                    steps,
                    cfg,
                    sampler,
                    scheduler,
                    negative_prompt,
                    preserve_generation_settings,
                ),
                workbench_id,
            )
        return (
            comfy_client.queue_simple_image(
                settings.get("comfy_url"),
                prompt,
                width,
                height,
                asset_type,
                checkpoint,
                steps,
                cfg,
                sampler,
                scheduler,
                negative_prompt,
            ),
            "",
        )

    def ensure_scene_background(self, story_id, story):
        scenes = story.get("scenes") or []
        scene = scenes[-1] if scenes else None
        if not scene or not scene.get("background_prompt"):
            return {"mode": "none"}
        if scene.get("background_asset_id"):
            return {"mode": "existing", "asset_id": scene.get("background_asset_id")}

        previous_scene, previous_background = self.find_previous_scene_background(story, scene)
        location_changed = scene_location_changed(scene)
        if previous_background and location_changed is False:
            db.set_scene_background(scene["id"], previous_background["id"])
            db.add_api_log(
                "local",
                "background:carry-forward",
                {
                    "scene_id": scene["id"],
                    "prompt": scene.get("background_prompt"),
                    "previous_scene_id": previous_scene.get("id") if previous_scene else "",
                },
                {"asset_id": previous_background["id"], "asset_prompt": previous_background.get("prompt")},
                story_id=story_id,
            )
            return {"mode": "carried", "asset_id": previous_background["id"]}

        if previous_background and location_changed is None and previous_scene:
            previous_prompt = previous_scene.get("background_prompt") or previous_background.get("prompt") or ""
            if prompt_similarity(normalize_prompt(scene.get("background_prompt")), normalize_prompt(previous_prompt)) >= 0.42:
                db.set_scene_background(scene["id"], previous_background["id"])
                db.add_api_log(
                    "local",
                    "background:carry-forward",
                    {
                        "scene_id": scene["id"],
                        "prompt": scene.get("background_prompt"),
                        "previous_scene_id": previous_scene.get("id"),
                        "reason": "similar prompt",
                    },
                    {"asset_id": previous_background["id"], "asset_prompt": previous_background.get("prompt")},
                    story_id=story_id,
                )
                return {"mode": "carried", "asset_id": previous_background["id"]}

        reusable = self.find_reusable_background(story, scene.get("background_prompt"))
        if reusable:
            db.set_scene_background(scene["id"], reusable["id"])
            db.add_api_log(
                "local",
                "background:reuse",
                {"scene_id": scene["id"], "prompt": scene.get("background_prompt")},
                {"asset_id": reusable["id"], "asset_prompt": reusable.get("prompt")},
                story_id=story_id,
            )
            return {"mode": "reused", "asset_id": reusable["id"]}

        try:
            settings = db.get_settings()
            source_prompt = (scene.get("background_prompt") or "").strip()
            visual_prompt = narrative.build_background_visual_prompt(story, scene)
            workbench_id = default_workbench_for_asset(settings, "background")
            prompt_profile = prompt_profile_for_workbench(settings, workbench_id)
            if prompt_profile:
                visual_prompt = narrative.generate_workbench_visual_prompt(
                    visual_prompt,
                    "background",
                    workbench_id,
                    prompt_profile,
                    source_prompt or visual_prompt,
                    story_id=story_id,
                )
            result, workbench_id = self.queue_comfy_image(
                settings,
                "background",
                visual_prompt,
                int(settings.get("image_width") or 1024),
                int(settings.get("image_height") or 576),
                settings.get("comfy_checkpoint"),
                int(settings.get("background_steps") or 28),
                float(settings.get("background_cfg") or 6.5),
                settings.get("comfy_sampler"),
                settings.get("comfy_scheduler"),
            )
            db.add_api_log(
                "comfyui",
                "prompt:auto-background",
                {
                    "scene_id": scene["id"],
                    "source_prompt": source_prompt,
                    "prompt": visual_prompt,
                    "location": scene_location(scene),
                    "location_changed": scene_location_changed(scene),
                    "checkpoint": settings.get("comfy_checkpoint"),
                    "workbench": workbench_id,
                    "steps": int(settings.get("background_steps") or 28),
                    "cfg": float(settings.get("background_cfg") or 6.5),
                    "sampler": settings.get("comfy_sampler"),
                    "scheduler": settings.get("comfy_scheduler"),
                },
                result,
                story_id=story_id,
            )
            asset_id = db.add_asset(
                story_id,
                {
                    "asset_type": "background",
                    "scene_id": scene["id"],
                    "prompt": visual_prompt,
                    "remote_ref": result.get("prompt_id", ""),
                    "metadata": {"auto": True, "workbench": workbench_id, **result},
                },
            )
            return {"mode": "queued", "asset_id": asset_id, "prompt_id": result.get("prompt_id")}
        except Exception as exc:
            db.add_api_log(
                "comfyui",
                "prompt:auto-background",
                {"scene_id": scene["id"], "prompt": scene.get("background_prompt")},
                status="error",
                error=str(exc),
                story_id=story_id,
            )
            return {"mode": "error", "error": str(exc)}

    def find_previous_scene_background(self, story, current_scene):
        scenes = story.get("scenes") or []
        assets = story.get("assets") or []
        assets_by_id = {asset.get("id"): asset for asset in assets if asset.get("asset_type") == "background"}
        for scene in reversed(scenes[:-1]):
            asset = assets_by_id.get(scene.get("background_asset_id"))
            if asset and asset.get("url"):
                return scene, asset
            for candidate in assets:
                if (
                    candidate.get("asset_type") == "background"
                    and candidate.get("scene_id") == scene.get("id")
                    and candidate.get("url")
                ):
                    return scene, candidate
        return None, None

    def find_reusable_background(self, story, prompt):
        candidates = [
            asset for asset in (story.get("assets") or [])
            if asset.get("asset_type") == "background" and asset.get("url") and asset.get("prompt")
        ]
        if not candidates:
            return None
        prompt_key = normalize_prompt(prompt)
        best = None
        best_score = 0
        for asset in candidates:
            asset_key = normalize_prompt(asset.get("prompt"))
            score = prompt_similarity(prompt_key, asset_key)
            if score > best_score:
                best = asset
                best_score = score
        return best if best_score >= 0.62 else None

    def handle_asset_get(self, path):
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[0] != "api" or parts[1] != "assets":
            return self.send_error_json(404, "Asset nao encontrado.")
        asset_id = parts[2]
        action = parts[3]
        if action == "result":
            return self.resolve_asset(asset_id)
        if action == "file":
            return self.serve_asset_file(asset_id)
        return self.send_error_json(404, "Acao de asset invalida.")

    def resolve_asset(self, asset_id):
        asset = db.get_asset(asset_id)
        if not asset:
            return self.send_error_json(404, "Asset nao encontrado.")
        if asset.get("file_path"):
            return self.send_json({"ready": True, "asset": asset})

        settings = db.get_settings()
        prompt_id = asset.get("remote_ref")
        if not prompt_id:
            return self.send_json({"ready": False, "asset": asset})

        image = comfy_client.get_first_history_image(settings.get("comfy_url"), prompt_id)
        if not image:
            return self.send_json({"ready": False, "asset": asset})

        body, content_type = comfy_client.download_image(settings.get("comfy_url"), image)
        db.add_api_log(
            "comfyui",
            "history:view-image",
            {"prompt_id": prompt_id},
            {"image": image, "content_type": content_type, "bytes": len(body)},
            story_id=asset.get("story_id"),
        )
        relative_path = self.asset_relative_path(asset, image, content_type)
        target = ROOT_DIR / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)

        updated = db.update_asset_file(
            asset_id,
            relative_path.as_posix(),
            {"comfy_image": image, "content_type": content_type},
        )
        if settings.get("comfy_free_memory_between_workbench_runs") is not False and asset.get("metadata", {}).get("workbench"):
            try:
                free_result = comfy_client.free_memory(settings.get("comfy_url"))
                db.add_api_log(
                    "comfyui",
                    "memory:free-after-asset",
                    {"asset_id": asset_id, "workbench": asset.get("metadata", {}).get("workbench")},
                    free_result,
                    story_id=asset.get("story_id"),
                )
            except Exception as exc:
                db.add_api_log(
                    "comfyui",
                    "memory:free-after-asset",
                    {"asset_id": asset_id, "workbench": asset.get("metadata", {}).get("workbench")},
                    status="error",
                    error=str(exc),
                    story_id=asset.get("story_id"),
                )
        return self.send_json({"ready": True, "asset": updated})

    def asset_relative_path(self, asset, image, content_type):
        extension = Path(image.get("filename") or "").suffix
        if not extension:
            extension = ".jpg" if "jpeg" in content_type else ".png"
        if asset.get("asset_type") == "background":
            folder = STORIES_DIR / asset["story_id"] / "backgrounds"
            filename = f"{asset['id']}{extension}"
        elif asset.get("asset_type") == "sprite":
            character_id = asset.get("character_id") or "unknown"
            folder = STORIES_DIR / asset["story_id"] / "characters" / character_id
            expression = sanitize_path_component(asset.get("expression") or "neutral")
            filename = f"{expression}_{asset['id']}{extension}"
        else:
            folder = STORIES_DIR / asset["story_id"] / "metadata"
            filename = f"{asset['id']}{extension}"
        return folder.relative_to(ROOT_DIR) / filename

    def serve_asset_file(self, asset_id):
        asset = db.get_asset(asset_id)
        if not asset or not asset.get("file_path"):
            return self.send_error_json(404, "Arquivo do asset ainda nao existe.")
        target = (ROOT_DIR / asset["file_path"]).resolve()
        data_root = (ROOT_DIR / "data").resolve()
        if not str(target).startswith(str(data_root)) or not target.exists():
            return self.send_error_json(404, "Arquivo do asset nao encontrado.")
        content_type = asset.get("metadata", {}).get("content_type") or mimetypes.guess_type(str(target))[0] or "image/png"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def delete_asset(self, asset_id):
        asset = db.get_asset(asset_id)
        if not asset:
            return self.send_error_json(404, "Asset nao encontrado.")

        deleted_file = False
        delete_error = ""
        file_path = asset.get("file_path")
        if file_path:
            target = (ROOT_DIR / file_path).resolve()
            data_root = (ROOT_DIR / "data").resolve()
            if is_relative_to(target, data_root) and target.exists() and target.is_file():
                deleted_file, delete_error = delete_path_with_retries(target)

        deleted = db.delete_asset(asset_id)
        db.add_api_log(
            "local",
            "asset:delete",
            {"asset_id": asset_id},
            {"asset": deleted, "deleted_file": deleted_file, "delete_error": delete_error},
            story_id=asset.get("story_id"),
        )
        return self.send_json({
            "deleted": True,
            "asset": deleted,
            "deleted_file": deleted_file,
            "delete_error": delete_error,
        })

    def proxy_comfy_view(self, query):
        settings = db.get_settings()
        prompt_id = (query.get("prompt_id") or [""])[0]
        if not prompt_id:
            return self.send_error_json(400, "prompt_id ausente.")

        history = comfy_client.get_history(settings.get("comfy_url"), prompt_id)
        entry = history.get(prompt_id) or {}
        outputs = entry.get("outputs") or {}
        image = None
        for output in outputs.values():
            images = output.get("images") or []
            if images:
                image = images[0]
                break
        if not image:
            return self.send_error_json(404, "Imagem ainda nao esta pronta.")

        params = urllib.parse.urlencode(
            {
                "filename": image.get("filename", ""),
                "type": image.get("type", "output"),
                "subfolder": image.get("subfolder", ""),
            }
        )
        with urllib.request.urlopen(f"{settings.get('comfy_url').rstrip('/')}/view?{params}", timeout=30) as response:
            body = response.read()
            content_type = response.headers.get("content-type") or "image/png"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, path):
        if path == "/":
            path = "/index.html"
        target = (PUBLIC_DIR / path.lstrip("/")).resolve()
        if not str(target).startswith(str(PUBLIC_DIR.resolve())) or not target.exists() or target.is_dir():
            return self.send_error_json(404, "Arquivo nao encontrado.")
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def is_multipart(self):
        return "multipart/form-data" in (self.headers.get("Content-Type") or "")

    def read_multipart_file(self, field_name):
        content_type = self.headers.get("Content-Type") or ""
        match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
        if not match:
            return None
        boundary = match.group("boundary").strip().strip('"').encode("utf-8")
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        delimiter = b"--" + boundary
        for part in body.split(delimiter):
            if not part or part in {b"--\r\n", b"--"}:
                continue
            part = part.strip(b"\r\n")
            header_blob, separator, content = part.partition(b"\r\n\r\n")
            if not separator:
                continue
            headers = header_blob.decode("utf-8", errors="ignore")
            disposition = parse_content_disposition(headers)
            if disposition.get("name") != field_name:
                continue
            if content.endswith(b"\r\n"):
                content = content[:-2]
            return {
                "filename": disposition.get("filename") or "",
                "body": content,
            }
        return None

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, message):
        self.send_json({"error": message}, status)

    def shutdown_app(self):
        db.add_api_log("local", "app:shutdown", {}, {"ok": True})
        self.send_json({"ok": True, "message": "Servidor encerrando."})

        def stop_server():
            time.sleep(0.25)
            self.server.shutdown()
            self.server.server_close()

        threading.Thread(target=stop_server, daemon=True).start()

    def log_message(self, fmt, *args):
        print(f"[TaleWeaver] {self.address_string()} - {fmt % args}")


def run(host="127.0.0.1", port=3000):
    db.init_db()
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"TaleWeaver running at http://{host}:{port}")
    server.serve_forever()


def comfy_workflows_dir(settings):
    configured = settings.get("comfy_workflows_dir")
    if configured:
        return Path(configured)
    comfy_root = settings.get("comfy_root") or ""
    return Path(comfy_root) / "user" / "default" / "workflows"


def default_workbench_for_asset(settings, asset_type):
    if asset_type == "background":
        return settings.get("comfy_background_workbench") or ""
    if asset_type == "sprite":
        return settings.get("comfy_sprite_workbench") or ""
    if asset_type in {"sprite_edit", "sprite_variation"}:
        return settings.get("comfy_sprite_edit_workbench") or ""
    return ""


def style_workbench(style):
    return (style or {}).get("sprite_workbench") or ""


def apply_style_prompt(style, prompt):
    style = style or {}
    parts = [
        style.get("prompt_prefix") or "",
        prompt or "",
        style.get("prompt_suffix") or "",
    ]
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())


def prompt_profile_for_workbench(settings, workbench_id):
    if not workbench_id:
        return None
    profiles = settings.get("comfy_prompt_profiles")
    if not isinstance(profiles, dict):
        return None
    profile = profiles.get(workbench_id)
    if not isinstance(profile, dict):
        return None
    if profile.get("style") or profile.get("example"):
        return profile
    return None


def parse_content_disposition(headers):
    result = {}
    for line in headers.splitlines():
        if not line.lower().startswith("content-disposition:"):
            continue
        for item in line.split(";")[1:]:
            key, separator, value = item.strip().partition("=")
            if separator:
                result[key.strip().lower()] = value.strip().strip('"')
    return result


def delete_path_with_retries(target, attempts=6):
    target = Path(target)
    errors = []
    for attempt in range(attempts):
        try:
            if not target.exists():
                return True, ""
            if target.is_dir():
                shutil.rmtree(target, onerror=retry_remove_after_chmod)
            else:
                make_writable(target)
                target.unlink()
            if target.exists():
                raise OSError(f"Caminho ainda existe apos tentativa de remocao: {target}")
            return True, ""
        except OSError as exc:
            errors.append(str(exc))
            gc.collect()
            time.sleep(0.2 * (attempt + 1))
    if os.name == "nt" and target.exists():
        deleted, error = delete_path_with_powershell(target)
        if deleted:
            return True, ""
        if error:
            errors.append(error)
    return (not target.exists(), "" if not target.exists() else (errors[-1] if errors else "Falha ao remover arquivo."))


def delete_path_with_powershell(target):
    command = "& { param($target) $ErrorActionPreference = 'Stop'; Remove-Item -LiteralPath $target -Recurse -Force }"
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
                str(Path(target)),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if completed.returncode == 0 and not Path(target).exists():
        return True, ""
    error = (completed.stderr or completed.stdout or f"PowerShell Remove-Item saiu com codigo {completed.returncode}").strip()
    return False, error


def retry_remove_after_chmod(func, path, _exc_info):
    try:
        make_writable(Path(path))
        func(path)
    except OSError:
        pass


def make_writable(path):
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    except OSError:
        pass


def is_relative_to(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def find_scene_for_payload(story, payload):
    scene_id = payload.get("scene_id") or payload.get("sceneId")
    scenes = story.get("scenes") or []
    if scene_id:
        for scene in scenes:
            if scene.get("id") == scene_id:
                return scene
    return scenes[-1] if scenes else {}


def latest_scene(story):
    scenes = story.get("scenes") or []
    return scenes[-1] if scenes else {}


def find_character_by_name(characters, name):
    key = normalized_person_name(name)
    if not key:
        return None
    for character in characters:
        names = [character.get("name")]
        aliases = character.get("aliases") or ""
        names.extend(alias.strip() for alias in str(aliases).split(","))
        if any(normalized_person_name(item) == key for item in names if item):
            return character
    return None


def normalized_person_name(value):
    return str(value or "").strip().lower()


def scene_location_changed(scene):
    raw = scene.get("raw_ai_response") if isinstance(scene, dict) else {}
    if not isinstance(raw, dict):
        return None
    value = raw.get("location_changed")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "sim", "1"}:
            return True
        if normalized in {"false", "no", "nao", "não", "0"}:
            return False
    return None


def scene_location(scene):
    raw = scene.get("raw_ai_response") if isinstance(scene, dict) else {}
    if isinstance(raw, dict):
        return raw.get("location") or ""
    return ""


def sanitize_path_component(value, fallback="asset"):
    text = str(value or "").strip()
    text = re.sub(r'[<>:"/\\\\|?*]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = text.replace(" ", "_")
    text = re.sub(r"_+", "_", text)
    return text or fallback


def normalize_prompt(prompt):
    words = re.findall(r"[a-zA-Z0-9]+", (prompt or "").lower())
    stop = {
        "the", "and", "with", "from", "into", "visual", "novel", "anime",
        "background", "detailed", "cinematic", "lighting", "shot", "wide",
        "no", "people", "characters", "at", "in", "on", "of", "a", "an",
    }
    return {word for word in words if len(word) > 2 and word not in stop}


def prompt_similarity(left, right):
    if not left or not right:
        return 0
    overlap = len(left & right)
    return overlap / max(len(left), len(right))


def build_sprite_source_prompt(prompt, character, expression):
    parts = []
    if character:
        parts.extend(
            [
                f"Name: {character.get('name')}",
                f"Physical appearance: {character.get('physical')}",
                f"Personality: {character.get('personality')}",
                f"Role: {character.get('role')}",
                f"Relationship: {character.get('relationship')}",
                f"Fixed visual prompt: {character.get('visual_prompt')}",
            ]
        )
    if prompt:
        parts.append(f"User visual prompt: {prompt}")
    if expression:
        parts.append(f"Expression: {expression}")
    parts.append("Outfit: visual novel clothing or costume appropriate to the character role and user visual prompt")
    return "\n".join(part for part in parts if part and not part.endswith(": None"))
