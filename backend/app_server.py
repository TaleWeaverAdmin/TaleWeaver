import gc
import json
import mimetypes
import os
import re
import shutil
import secrets
import stat
import subprocess
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import ai_client, comfy_client, db, narrative, service_manager
from .config import ROOT_DIR, STORIES_DIR, STYLE_COVERS_DIR


PUBLIC_DIR = ROOT_DIR / "public"
ICONS_DIR = ROOT_DIR / "icons"
OFFICIAL_EXPRESSIONS = ["neutral", "happy", "sad", "angry", "thoughtful", "surprised", "embarrassed", "scared"]
SPRITE_EXPRESSION_KEYS = [item for item in OFFICIAL_EXPRESSIONS if item != "neutral"]


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
                return self.send_json(db.public_settings())
            if path == "/api/scripts/status":
                return self.send_json(service_manager.service_status(db.get_settings()))
            if path == "/api/visual-styles":
                return self.send_json({"styles": db.list_visual_styles()})
            if path.startswith("/api/visual-styles/") and path.endswith("/cover"):
                style_id = path.strip("/").split("/")[2]
                return self.serve_visual_style_cover(style_id)
            if path == "/api/ollama/models":
                settings = db.get_settings()
                return self.send_json({"models": ai_client.list_ollama_models(settings)})
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
            if path.startswith("/icons/"):
                return self.serve_icon(path)
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
                db.update_settings(payload)
                return self.send_json(db.public_settings())
            if path == "/api/visual-styles/prompt-test":
                return self.test_visual_style_prompt(payload)
            if path == "/api/visual-styles":
                return self.send_json(db.create_visual_style(payload), 201)
            if path.startswith("/api/visual-styles/") and path.endswith("/cover"):
                style_id = path.strip("/").split("/")[2]
                return self.upload_visual_style_cover(style_id)
            if path == "/api/ai/improve":
                return self.send_json(narrative.improve_text(payload))
            if path == "/api/ai/story-seed":
                service_manager.activate_text_ai_role("story", db.get_settings())
                return self.send_json(narrative.generate_story_seed(payload))
            if path == "/api/stories":
                service_manager.activate_text_ai_role("story", db.get_settings())
                return self.send_json(db.create_story(narrative.enrich_story_creation_payload(payload)), 201)
            if path.endswith("/expression-prompts") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                service_manager.activate_text_ai_role("story", db.get_settings())
                return self.send_json(narrative.generate_character_expression_prompts(story_id, only_missing=True, ai_role="story"))
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
                service_manager.activate_text_ai_role("scene", db.get_settings())
                story = narrative.generate_scene(story_id, payload.get("user_input") or "", payload.get("speaker_focus"))
                story = self.apply_scene_appearance_updates(story_id, story)
                if payload.get("generate_images") is False:
                    story["auto_background"] = {"mode": "skipped"}
                else:
                    auto_background = self.ensure_scene_background(story_id, story)
                    appearance_update_results = story.get("appearance_update_results")
                    if auto_background.get("mode") in {"reused", "carried"}:
                        story = db.get_story(story_id)
                        if appearance_update_results:
                            story["appearance_update_results"] = appearance_update_results
                    story["auto_background"] = auto_background
                return self.send_json(story)
            if path.endswith("/regenerate-scene") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                service_manager.activate_text_ai_role("scene", db.get_settings())
                return self.regenerate_current_scene(story_id, payload)
            if path.endswith("/characters") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                story = db.get_story(story_id)
                if not story:
                    return self.send_error_json(404, "Historia nao encontrada.")
                service_manager.activate_text_ai_role("scene", db.get_settings())
                character_payload = narrative.complete_character_record(payload, story, latest_scene(story))
                narrative.apply_character_sprite_prompt(character_payload, db.get_settings(), story_id=story_id)
                return self.send_json(db.create_character(story_id, character_payload), 201)
            if path.endswith("/characters/introduce") and path.startswith("/api/stories/"):
                story_id = path.split("/")[3]
                service_manager.activate_text_ai_role("scene", db.get_settings())
                return self.introduce_character(story_id, payload)
            if path.startswith("/api/characters/") and path.endswith("/image-prompt"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    service_manager.activate_text_ai_role("scene", db.get_settings())
                    return self.generate_character_image_prompt(parts[2], payload)
            if path.startswith("/api/characters/") and path.endswith("/expression-prompts"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    character = db.get_character(parts[2])
                    if not character:
                        return self.send_error_json(404, "Personagem nao encontrado.")
                    service_manager.activate_text_ai_role("scene", db.get_settings())
                    story = narrative.generate_character_expression_prompts(
                        character.get("story_id"),
                        character_ids=[parts[2]],
                        only_missing=True,
                        ai_role="scene",
                    )
                    return self.send_json(story)
            if path.startswith("/api/characters/") and path.endswith("/appearances"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    service_manager.activate_text_ai_role("story", db.get_settings())
                    return self.generate_character_appearance(parts[2], payload)
            if path.startswith("/api/characters/") and "/appearances/" in path:
                parts = path.strip("/").split("/")
                if len(parts) == 6 and parts[:2] == ["api", "characters"] and parts[3] == "appearances" and parts[5] == "regenerate":
                    service_manager.activate_text_ai_role("story", db.get_settings())
                    return self.regenerate_character_appearance(parts[2], parts[4], payload)
                if len(parts) == 6 and parts[:2] == ["api", "characters"] and parts[3] == "appearances" and parts[5] == "replace":
                    return self.replace_regenerated_appearance(parts[2], parts[4], payload)
            if path.startswith("/api/assets/") and "/expressions/" in path and path.endswith("/regenerate"):
                parts = path.strip("/").split("/")
                if len(parts) == 6 and parts[:2] == ["api", "assets"] and parts[3] == "expressions":
                    return self.regenerate_sprite_expression(parts[2], parts[4], payload)
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
                previous_character = db.get_character(parts[2])
                character = db.update_character(parts[2], payload)
                if payload.get("expression_prompts") is not None and character:
                    before = (previous_character or {}).get("expression_prompts") or {}
                    after = character.get("expression_prompts") or {}
                    changed = [key for key in SPRITE_EXPRESSION_KEYS if before.get(key) != after.get(key)]
                    db.add_api_log(
                        "local",
                        "expression_prompt_saved",
                        {"character_id": parts[2], "expressions": changed},
                        story_id=character.get("story_id"),
                    )
                return self.send_json(character)
            if len(parts) == 6 and parts[:2] == ["api", "characters"] and parts[3] == "appearances" and parts[5] == "activate":
                story = db.set_active_appearance(parts[2], parts[4])
                if not story:
                    return self.send_error_json(404, "Aparencia nao encontrada.")
                return self.send_json(story)
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
            if len(parts) == 3 and parts[:2] == ["api", "characters"]:
                return self.delete_character(parts[2])
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
        visual_style = db.visual_style_for_story(story_id) if asset_type in {"sprite", "background"} else None
        style_settings = (visual_style or {}).get("advanced_settings") or {}
        background_settings = (visual_style or {}).get("background_settings") or {}
        requested_workbench = payload.get("workbench") or style_workbench(visual_style, asset_type) or default_workbench_for_asset(settings, asset_type)
        width = int(payload.get("width") or settings.get("image_width") or 1024)
        height = int(payload.get("height") or settings.get("image_height") or 576)
        steps = int(settings.get("background_steps") or 28)
        cfg = float(settings.get("background_cfg") or 6.5)
        negative_prompt = ""
        prompt = payload.get("prompt") or ""
        source_prompt = prompt
        prompt_source = "local"
        expression_prompts = None
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
            if style_expressions_enabled(visual_style):
                expression_prompts = (character or {}).get("expression_prompts") or {}
                missing_expression_prompts = [
                    expression for expression in SPRITE_EXPRESSION_KEYS
                    if not str(expression_prompts.get(expression) or "").strip()
                ]
                if missing_expression_prompts:
                    db.add_api_log(
                        "local",
                        "expression_prompt_missing_for_character",
                        {
                            "character_id": (character or {}).get("id") or payload.get("character_id") or "",
                            "missing": missing_expression_prompts,
                        },
                        status="error",
                        error="Prompts de expressao ausentes.",
                        story_id=story_id,
                    )
                    return self.send_error_json(400, "Gere os prompts de expressao do personagem antes dos sprites.")
                payload["expression"] = "neutral"
        elif asset_type == "background":
            source_prompt = prompt.strip()
            width = int(payload.get("width") or background_settings.get("width") or settings.get("image_width") or 1024)
            height = int(payload.get("height") or background_settings.get("height") or settings.get("image_height") or 576)
            steps = int(payload.get("steps") or background_settings.get("steps") or settings.get("background_steps") or 28)
            cfg = float(payload.get("cfg") or background_settings.get("cfg") or settings.get("background_cfg") or 6.5)
            story = db.get_story(story_id) or {}
            scene = find_scene_for_payload(story, payload) if story else {}
            prompt = narrative.normalize_background_visual_prompt(source_prompt or (scene or {}).get("background_prompt") or "")
            if not prompt:
                return self.send_error_json(400, "Prompt de cenario vazio.")
            prompt_source = "scene:background-prompt" if scene and not payload.get("prompt_is_visual") else "user:background-edit"
            negative_prompt = background_negative_prompt(visual_style)

        prompt_profile = prompt_profile_for_visual_style(settings, visual_style, asset_type, requested_workbench)
        if prompt_profile and asset_type != "sprite" and not payload.get("prompt_is_visual"):
            prompt = narrative.generate_workbench_visual_prompt(
                source_prompt or prompt,
                asset_type,
                requested_workbench,
                prompt_profile,
                prompt,
                story_id=story_id,
            )
            prompt_source = "ollama:workbench-profile"
        if asset_type == "background":
            prompt = narrative.finalize_background_comfy_prompt(apply_background_style_prompt(visual_style, prompt))

        sampler = settings.get("comfy_sampler")
        scheduler = settings.get("comfy_scheduler")
        if asset_type == "sprite":
            sampler = style_settings.get("sampler_name") or settings.get("sprite_sampler") or sampler
            scheduler = style_settings.get("scheduler") or settings.get("sprite_scheduler") or scheduler
        elif asset_type == "background":
            sampler = payload.get("sampler_name") or background_settings.get("sampler_name") or sampler
            scheduler = payload.get("scheduler") or background_settings.get("scheduler") or scheduler

        checkpoint = payload.get("checkpoint") or (
            style_settings.get("ckpt_name") if asset_type == "sprite" else background_settings.get("ckpt_name")
        ) or settings.get("comfy_checkpoint")
        generation_settings = style_settings if asset_type == "sprite" else background_settings
        allowed_override_fields = generation_override_fields_for_workbench(settings, requested_workbench)
        generation_overrides = generation_overrides_for_style(
            generation_settings,
            payload if asset_type == "background" else None,
            allowed_override_fields,
        )
        generation_overrides = ensure_generation_seed_override(generation_overrides, allowed_override_fields)
        preserve_workbench_settings = not bool((visual_style and generation_settings) or generation_overrides)
        comfy_token = service_manager.begin_comfy_generation(settings, reason=f"manual:{asset_type}")
        try:
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
                generation_overrides,
                expression_prompts=expression_prompts,
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
                    "generation_overrides": generation_overrides or {},
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
                    "expression": normalize_expression(payload.get("expression")),
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "remote_ref": result.get("prompt_id", ""),
                    "metadata": {
                        "workbench": workbench_id,
                        "visual_style_id": (visual_style or {}).get("id") or "",
                        "source_prompt": source_prompt,
                        "expression_group": bool(asset_type == "sprite" and style_expressions_enabled(visual_style)),
                        **result,
                    },
                },
            )
            if asset_type == "sprite" and style_expressions_enabled(visual_style):
                db.update_asset_base(asset_id, asset_id)
            if asset_type == "sprite" and payload.get("character_id"):
                db.create_character_appearance(
                    payload.get("character_id"),
                    payload.get("appearance_label") or "Aparencia",
                    asset_id,
                    asset_id,
                    active=True,
                )
            service_manager.attach_comfy_generation(comfy_token, asset_id=asset_id, prompt_id=result.get("prompt_id", ""))
            comfy_token = None
        except Exception as exc:
            db.add_api_log(
                "comfyui",
                "prompt:image",
                {
                    "asset_type": asset_type,
                    "width": width,
                    "height": height,
                    "checkpoint": checkpoint,
                    "requested_workbench": requested_workbench,
                    "prompt_source": prompt_source,
                    "source_prompt": source_prompt,
                    "prompt": prompt,
                },
                status="error",
                error=str(exc),
                story_id=story_id,
            )
            raise
        finally:
            if comfy_token:
                service_manager.end_comfy_generation(comfy_token, settings=settings, reason="queue-failed")
        return self.send_json({"asset_id": asset_id, "queued": result})

    def generate_character_image_prompt(self, character_id, payload):
        character = db.get_character(character_id)
        if not character:
            return self.send_error_json(404, "Personagem nao encontrado.")

        settings = db.get_settings()
        visual_style = db.visual_style_for_story(character.get("story_id"))
        workbench_id = payload.get("workbench") or style_workbench(visual_style) or default_workbench_for_asset(settings, "sprite")
        prompt_profile = prompt_profile_for_visual_style(settings, visual_style, "sprite", workbench_id)
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
            ai_role="scene",
        )
        updated = db.update_character(character_id, {"visual_prompt": visual_prompt})
        db.add_api_log(
            "local",
            "character:image-prompt",
            {
                "character_id": character_id,
                "workbench": workbench_id,
                "clothing": character.get("clothing") or "",
                "source_prompt": source_prompt,
                "prompt_profile_applied": bool(prompt_profile),
                "prompt_profile_style": (prompt_profile or {}).get("style") or "",
                "prompt_profile_example": (prompt_profile or {}).get("example") or "",
            },
            {"visual_prompt": visual_prompt},
            story_id=character.get("story_id"),
        )
        return self.send_json(updated)

    def generate_character_appearance(self, character_id, payload):
        character = db.get_character(character_id)
        if not character:
            return self.send_error_json(404, "Personagem nao encontrado.")
        source_prompt = str(payload.get("prompt") or "").strip()
        if not source_prompt:
            return self.send_error_json(400, "Descreva o que mudar na aparencia.")
        reference_asset_id = payload.get("reference_asset_id") or ""
        reference_asset = db.get_asset(reference_asset_id)
        if not reference_asset or reference_asset.get("asset_type") != "sprite" or not reference_asset.get("file_path"):
            return self.send_error_json(400, "Sprite de referencia invalido ou ainda sem arquivo local.")

        settings = db.get_settings()
        visual_style = db.visual_style_for_story(character.get("story_id"))
        workbench_id = payload.get("workbench") or style_workbench(visual_style, "appearance")
        if not workbench_id:
            return self.send_error_json(400, "Configure o Workflow de Alterar Aparencia no estilo atual.")

        prompt = source_prompt
        prompt_source = "user"
        prompt_profile = {
            "style": (visual_style or {}).get("appearance_prompt_command") or "",
            "example": (visual_style or {}).get("appearance_prompt_example") or "",
        }
        if payload.get("improve_prompt") and prompt_profile and (prompt_profile.get("style") or prompt_profile.get("example")):
            prompt = narrative.generate_workbench_visual_prompt(
                source_prompt,
                "appearance",
                workbench_id,
                prompt_profile,
                source_prompt,
                story_id=character.get("story_id"),
                ai_role="story",
            )
            prompt_source = "ollama:appearance-profile"

        style_settings = (visual_style or {}).get("advanced_settings") or {}
        width = int(payload.get("width") or style_settings.get("width") or settings.get("sprite_width") or 640)
        height = int(payload.get("height") or style_settings.get("height") or settings.get("sprite_height") or 960)
        steps = int(style_settings.get("steps") or settings.get("sprite_steps") or 24)
        cfg = float(style_settings.get("cfg") or settings.get("sprite_cfg") or 5.0)
        sampler = style_settings.get("sampler_name") or settings.get("sprite_sampler") or settings.get("comfy_sampler")
        scheduler = style_settings.get("scheduler") or settings.get("sprite_scheduler") or settings.get("comfy_scheduler")
        checkpoint = style_settings.get("ckpt_name") or settings.get("comfy_checkpoint")
        negative_prompt = (visual_style or {}).get("negative_prompt") or ""
        allowed_override_fields = generation_override_fields_for_workbench(settings, workbench_id)
        generation_overrides = generation_overrides_for_style(style_settings, allowed_fields=allowed_override_fields)
        generation_overrides = ensure_generation_seed_override(generation_overrides, allowed_override_fields)
        preserve_workbench_settings = not bool((visual_style and style_settings) or generation_overrides)
        reference_path = (ROOT_DIR / reference_asset["file_path"]).resolve()
        comfy_token = service_manager.begin_comfy_generation(settings, reason="appearance")
        try:
            result, workbench_id = self.queue_comfy_image(
                settings,
                "sprite",
                prompt,
                width,
                height,
                checkpoint,
                steps,
                cfg,
                sampler,
                scheduler,
                workbench_id,
                negative_prompt,
                preserve_workbench_settings,
                generation_overrides,
                reference_path,
            )
            asset_id = db.add_asset(
                character.get("story_id"),
                {
                    "asset_type": "sprite",
                    "character_id": character_id,
                    "scene_id": payload.get("scene_id"),
                    "expression": "neutral",
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "remote_ref": result.get("prompt_id", ""),
                    "metadata": {
                        "appearance_generation": True,
                        "expression_group": bool(style_expressions_enabled(visual_style)),
                        "reference_asset_id": reference_asset_id,
                        "workbench": workbench_id,
                        "visual_style_id": (visual_style or {}).get("id") or "",
                        "source_prompt": source_prompt,
                        "prompt_source": prompt_source,
                        **result,
                    },
                },
            )
            db.update_asset_base(asset_id, asset_id)
            db.create_character_appearance(
                character_id,
                compact_label(source_prompt),
                asset_id,
                asset_id,
                active=True,
            )
            service_manager.attach_comfy_generation(comfy_token, asset_id=asset_id, prompt_id=result.get("prompt_id", ""))
            comfy_token = None
            db.add_api_log(
                "comfyui",
                "prompt:appearance-generate",
                {
                    "character_id": character_id,
                    "reference_asset_id": reference_asset_id,
                    "workbench": workbench_id,
                    "prompt": prompt,
                    "source_prompt": source_prompt,
                    "prompt_source": prompt_source,
                    "generation_overrides": generation_overrides,
                },
                result,
                story_id=character.get("story_id"),
            )
            return self.send_json({"asset_id": asset_id, "queued": result})
        except Exception as exc:
            db.add_api_log(
                "comfyui",
                "prompt:appearance-generate",
                {"character_id": character_id, "reference_asset_id": reference_asset_id, "workbench": workbench_id, "prompt": prompt},
                status="error",
                error=str(exc),
                story_id=character.get("story_id"),
            )
            raise
        finally:
            if comfy_token:
                service_manager.end_comfy_generation(comfy_token, settings=settings, reason="queue-failed")

    def regenerate_character_appearance(self, character_id, target_appearance_id, payload):
        character = db.get_character(character_id)
        if not character:
            return self.send_error_json(404, "Personagem nao encontrado.")
        target_appearance = db.get_appearance(target_appearance_id)
        if not target_appearance or target_appearance.get("character_id") != character_id:
            return self.send_error_json(404, "Aparencia alvo nao encontrada.")
        if db.is_initial_appearance(character_id, target_appearance_id):
            return self.send_error_json(400, "A aparencia inicial nao pode ser substituida por esta funcao.")

        source_prompt = str(payload.get("prompt") or "").strip()
        if not source_prompt:
            return self.send_error_json(400, "Descreva o que mudar na aparencia.")
        reference_appearance_id = payload.get("reference_appearance_id") or target_appearance_id
        reference_appearance = db.get_appearance(reference_appearance_id)
        if not reference_appearance or reference_appearance.get("character_id") != character_id:
            return self.send_error_json(400, "Aparencia de referencia invalida.")
        reference_asset_id = reference_appearance.get("neutral_asset_id") or reference_appearance.get("primary_asset_id") or ""
        reference_asset = db.get_asset(reference_asset_id)
        if not reference_asset or reference_asset.get("asset_type") != "sprite" or not reference_asset.get("file_path"):
            return self.send_error_json(400, "Aparencia de referencia invalida ou ainda sem imagem local.")

        settings = db.get_settings()
        visual_style = db.visual_style_for_story(character.get("story_id"))
        workbench_id = payload.get("workbench") or style_workbench(visual_style, "appearance")
        if not workbench_id:
            return self.send_error_json(400, "Configure o Workflow de Alterar Aparencia no estilo atual.")

        prompt = source_prompt
        prompt_source = "user"
        prompt_profile = prompt_profile_for_visual_style(settings, visual_style, "appearance", workbench_id)
        if payload.get("improve_prompt") and prompt_profile and (prompt_profile.get("style") or prompt_profile.get("example")):
            prompt = narrative.generate_workbench_visual_prompt(
                source_prompt,
                "appearance",
                workbench_id,
                prompt_profile,
                source_prompt,
                story_id=character.get("story_id"),
                ai_role="story",
            )
            prompt_source = "ollama:appearance-profile"

        style_settings = (visual_style or {}).get("advanced_settings") or {}
        width = int(payload.get("width") or style_settings.get("width") or settings.get("sprite_width") or 640)
        height = int(payload.get("height") or style_settings.get("height") or settings.get("sprite_height") or 960)
        steps = int(style_settings.get("steps") or settings.get("sprite_steps") or 24)
        cfg = float(style_settings.get("cfg") or settings.get("sprite_cfg") or 5.0)
        sampler = style_settings.get("sampler_name") or settings.get("sprite_sampler") or settings.get("comfy_sampler")
        scheduler = style_settings.get("scheduler") or settings.get("sprite_scheduler") or settings.get("comfy_scheduler")
        checkpoint = style_settings.get("ckpt_name") or settings.get("comfy_checkpoint")
        negative_prompt = (visual_style or {}).get("negative_prompt") or ""
        allowed_override_fields = generation_override_fields_for_workbench(settings, workbench_id)
        generation_overrides = generation_overrides_for_style(style_settings, allowed_fields=allowed_override_fields)
        generation_overrides = ensure_generation_seed_override(generation_overrides, allowed_override_fields)
        preserve_workbench_settings = not bool((visual_style and style_settings) or generation_overrides)
        reference_path = (ROOT_DIR / reference_asset["file_path"]).resolve()
        comfy_token = service_manager.begin_comfy_generation(settings, reason="appearance-replace")
        try:
            result, resolved_workbench_id = self.queue_comfy_image(
                settings,
                "sprite",
                prompt,
                width,
                height,
                checkpoint,
                steps,
                cfg,
                sampler,
                scheduler,
                workbench_id,
                negative_prompt,
                preserve_workbench_settings,
                generation_overrides,
                reference_path,
            )
            asset_id = db.add_asset(
                character.get("story_id"),
                {
                    "asset_type": "sprite",
                    "character_id": character_id,
                    "scene_id": payload.get("scene_id"),
                    "appearance_id": target_appearance_id,
                    "expression": "neutral",
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "remote_ref": result.get("prompt_id", ""),
                    "metadata": {
                        "appearance_replace": True,
                        "appearance_generation": True,
                        "expression_group": bool(style_expressions_enabled(visual_style)),
                        "reference_asset_id": reference_asset_id,
                        "reference_appearance_id": reference_appearance_id,
                        "target_appearance_id": target_appearance_id,
                        "workbench": resolved_workbench_id,
                        "visual_style_id": (visual_style or {}).get("id") or "",
                        "source_prompt": source_prompt,
                        "prompt_source": prompt_source,
                        "prompt_profile_applied": prompt_source == "ollama:appearance-profile",
                        **result,
                    },
                },
            )
            db.update_asset_base(asset_id, asset_id)
            service_manager.attach_comfy_generation(comfy_token, asset_id=asset_id, prompt_id=result.get("prompt_id", ""))
            comfy_token = None
            db.add_api_log(
                "comfyui",
                "prompt:appearance-replace",
                {
                    "character_id": character_id,
                    "target_appearance_id": target_appearance_id,
                    "reference_appearance_id": reference_appearance_id,
                    "reference_asset_id": reference_asset_id,
                    "workbench": resolved_workbench_id,
                    "prompt": prompt,
                    "source_prompt": source_prompt,
                    "prompt_source": prompt_source,
                    "generation_overrides": generation_overrides,
                },
                result,
                story_id=character.get("story_id"),
            )
            return self.send_json({"asset_id": asset_id, "target_appearance_id": target_appearance_id, "queued": result})
        except Exception as exc:
            db.add_api_log(
                "comfyui",
                "prompt:appearance-replace",
                {"character_id": character_id, "target_appearance_id": target_appearance_id, "reference_appearance_id": reference_appearance_id, "workbench": workbench_id, "prompt": prompt},
                status="error",
                error=str(exc),
                story_id=character.get("story_id"),
            )
            raise
        finally:
            if comfy_token:
                service_manager.end_comfy_generation(comfy_token, settings=settings, reason="queue-failed")

    def replace_regenerated_appearance(self, character_id, target_appearance_id, payload):
        character = db.get_character(character_id)
        if not character:
            return self.send_error_json(404, "Personagem nao encontrado.")
        if db.is_initial_appearance(character_id, target_appearance_id):
            return self.send_error_json(400, "A aparencia inicial nao pode ser substituida por esta funcao.")
        asset_id = payload.get("asset_id") or ""
        asset = db.get_asset(asset_id)
        if not asset or asset.get("character_id") != character_id or asset.get("asset_type") != "sprite" or not asset.get("file_path"):
            return self.send_error_json(400, "A nova imagem ainda nao esta pronta.")
        story = db.replace_character_appearance_asset(character_id, target_appearance_id, asset_id)
        if not story:
            return self.send_error_json(404, "Nao foi possivel substituir a aparencia.")
        db.add_api_log(
            "local",
            "appearance:replace-finalized",
            {"character_id": character_id, "target_appearance_id": target_appearance_id, "asset_id": asset_id},
            {"updated": True},
            story_id=story.get("id"),
        )
        return self.send_json(story)

    def apply_scene_appearance_updates(self, story_id, story):
        scene = latest_scene(story)
        updates = normalized_scene_appearance_updates(story, scene)
        if not updates:
            return story
        results = []
        for update in updates:
            try:
                results.append(self.apply_single_appearance_update(story_id, story, scene, update))
            except Exception as exc:
                results.append({"mode": "error", "error": str(exc), "update": update})
                db.add_api_log(
                    "local",
                    "appearance:update-error",
                    {"scene_id": scene.get("id") if scene else "", "update": update},
                    status="error",
                    error=str(exc),
                    story_id=story_id,
                )
        db.add_api_log(
            "local",
            "appearance:updates-applied",
            {"scene_id": scene.get("id") if scene else "", "updates": updates},
            {"results": results},
            story_id=story_id,
        )
        updated_story = db.get_story(story_id) or story
        updated_story["appearance_update_results"] = {"results": results}
        return updated_story

    def regenerate_current_scene(self, story_id, payload):
        try:
            previous_story, current_scene = db.story_before_latest_scene_for_regeneration(story_id)
        except ValueError as exc:
            return self.send_error_json(400, str(exc))
        has_custom_input = "user_input" in payload
        user_input = str(payload.get("user_input") if has_custom_input else current_scene.get("user_input") or "")
        if has_custom_input and not user_input.strip():
            return self.send_error_json(400, "Digite um novo input antes de regenerar.")
        generated_scene = narrative.generate_scene(
            story_id,
            user_input,
            payload.get("speaker_focus"),
            story_override=previous_story,
            save=False,
        )
        previous_scene = (previous_story.get("scenes") or [])[-1] if previous_story.get("scenes") else None
        story = db.replace_latest_scene(story_id, current_scene.get("id"), generated_scene, previous_scene=previous_scene)
        story = self.apply_scene_appearance_updates(story_id, story)
        if payload.get("generate_images") is False:
            story["auto_background"] = {"mode": "skipped"}
        else:
            auto_background = self.ensure_scene_background(story_id, story)
            appearance_update_results = story.get("appearance_update_results")
            if auto_background.get("mode") in {"reused", "carried"}:
                story = db.get_story(story_id)
                if appearance_update_results:
                    story["appearance_update_results"] = appearance_update_results
            story["auto_background"] = auto_background
        db.add_api_log(
            "local",
            "scene:regenerate",
            {
                "replaced_scene_id": current_scene.get("id"),
                "scene_order": current_scene.get("scene_order"),
                "custom_input": has_custom_input,
                "user_input": user_input,
            },
            {"story_id": story_id, "current_scene_id": story.get("current_scene_id")},
            story_id=story_id,
        )
        return self.send_json(story)

    def apply_single_appearance_update(self, story_id, story, scene, update):
        character = story_character_for_update(story, update.get("character"))
        if not character:
            return appearance_update_skip(update, "character_not_found", "Personagem nao encontrado.")
        action = update.get("action")
        if action in {"switch_existing", "revert_existing"}:
            appearance = find_character_appearance_for_update(story, character, update.get("target_appearance_id"))
            if not appearance:
                return appearance_update_skip(update, "target_appearance_not_found", "Aparencia alvo nao encontrada.")
            if update.get("activate_after_generation", True):
                db.set_active_appearance(character["id"], appearance["id"])
            return {"mode": action, "character_id": character["id"], "appearance_id": appearance["id"], "activated": bool(update.get("activate_after_generation", True))}
        if action == "create_new":
            return self.queue_appearance_update_generation(story_id, story, scene, character, update)
        return appearance_update_skip(update, "invalid_action", "Acao de aparencia invalida.")

    def queue_appearance_update_generation(self, story_id, story, scene, character, update):
        base_appearance = find_character_appearance_for_update(
            story,
            character,
            update.get("based_on_appearance_id") or character.get("active_appearance_id"),
        )
        if not base_appearance:
            return appearance_update_skip(update, "base_appearance_not_found", "Aparencia base nao encontrada.")
        reference_asset_id = base_appearance.get("neutral_asset_id") or base_appearance.get("primary_asset_id") or ""
        reference_asset = db.get_asset(reference_asset_id)
        if not reference_asset or reference_asset.get("asset_type") != "sprite" or not reference_asset.get("file_path"):
            return appearance_update_skip(update, "reference_image_missing", "Aparencia base ainda nao tem imagem local de referencia.")
        settings = db.get_settings()
        visual_style = db.visual_style_for_story(story_id)
        workbench_id = style_workbench(visual_style, "appearance")
        if not workbench_id:
            return appearance_update_skip(update, "appearance_workflow_missing", "Configure o Workflow de Alterar Aparencia no estilo atual.")
        source_prompt = appearance_update_change_prompt(update)
        if not source_prompt:
            return appearance_update_skip(update, "change_prompt_missing", "Prompt de alteracao de aparencia ausente.")
        prompt = source_prompt
        prompt_source = "appearance-update"
        prompt_profile = prompt_profile_for_visual_style(settings, visual_style, "appearance", workbench_id)
        if prompt_profile and (prompt_profile.get("style") or prompt_profile.get("example")):
            prompt = narrative.generate_workbench_visual_prompt(
                source_prompt,
                "appearance",
                workbench_id,
                prompt_profile,
                source_prompt,
                story_id=story_id,
                ai_role="story",
            )
            prompt_source = "ollama:appearance-profile"

        style_settings = (visual_style or {}).get("advanced_settings") or {}
        width = int(style_settings.get("width") or settings.get("sprite_width") or 640)
        height = int(style_settings.get("height") or settings.get("sprite_height") or 960)
        steps = int(style_settings.get("steps") or settings.get("sprite_steps") or 24)
        cfg = float(style_settings.get("cfg") or settings.get("sprite_cfg") or 5.0)
        sampler = style_settings.get("sampler_name") or settings.get("sprite_sampler") or settings.get("comfy_sampler")
        scheduler = style_settings.get("scheduler") or settings.get("sprite_scheduler") or settings.get("comfy_scheduler")
        checkpoint = style_settings.get("ckpt_name") or settings.get("comfy_checkpoint")
        negative_prompt = (visual_style or {}).get("negative_prompt") or ""
        allowed_override_fields = generation_override_fields_for_workbench(settings, workbench_id)
        generation_overrides = generation_overrides_for_style(style_settings, allowed_fields=allowed_override_fields)
        generation_overrides = ensure_generation_seed_override(generation_overrides, allowed_override_fields)
        preserve_workbench_settings = not bool((visual_style and style_settings) or generation_overrides)
        reference_path = (ROOT_DIR / reference_asset["file_path"]).resolve()
        comfy_token = service_manager.begin_comfy_generation(settings, reason="appearance-update")
        try:
            result, resolved_workbench_id = self.queue_comfy_image(
                settings,
                "sprite",
                prompt,
                width,
                height,
                checkpoint,
                steps,
                cfg,
                sampler,
                scheduler,
                workbench_id,
                negative_prompt,
                preserve_workbench_settings,
                generation_overrides,
                reference_path,
            )
            asset_id = db.add_asset(
                story_id,
                {
                    "asset_type": "sprite",
                    "character_id": character["id"],
                    "scene_id": scene.get("id") if scene else "",
                    "expression": "neutral",
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "remote_ref": result.get("prompt_id", ""),
                    "metadata": {
                        "appearance_update": True,
                        "appearance_generation": True,
                        "expression_group": bool(style_expressions_enabled(visual_style)),
                        "reference_asset_id": reference_asset_id,
                        "based_on_appearance_id": base_appearance.get("id"),
                        "workbench": resolved_workbench_id,
                        "visual_style_id": (visual_style or {}).get("id") or "",
                        "source_prompt": source_prompt,
                        "prompt_source": prompt_source,
                        "prompt_profile_applied": prompt_source == "ollama:appearance-profile",
                        "prompt_profile_style": (prompt_profile or {}).get("style") or "",
                        "prompt_profile_example": (prompt_profile or {}).get("example") or "",
                        "reason": update.get("reason") or "",
                        "new_appearance_summary": update.get("new_appearance_summary") or "",
                        **result,
                    },
                },
            )
            db.update_asset_base(asset_id, asset_id)
            appearance = db.create_character_appearance(
                character["id"],
                update.get("new_appearance_name") or update.get("new_appearance_summary") or compact_label(source_prompt),
                asset_id,
                asset_id,
                active=bool(update.get("activate_after_generation", True)),
            )
            service_manager.attach_comfy_generation(comfy_token, asset_id=asset_id, prompt_id=result.get("prompt_id", ""))
            comfy_token = None
            db.add_api_log(
                "comfyui",
                "prompt:appearance-update",
                {
                    "character_id": character["id"],
                    "scene_id": scene.get("id") if scene else "",
                    "reference_asset_id": reference_asset_id,
                    "based_on_appearance_id": base_appearance.get("id"),
                    "workbench": resolved_workbench_id,
                    "prompt": prompt,
                    "source_prompt": source_prompt,
                    "prompt_source": prompt_source,
                    "prompt_profile_applied": prompt_source == "ollama:appearance-profile",
                    "generation_overrides": generation_overrides,
                },
                {"asset_id": asset_id, "appearance_id": (appearance or {}).get("id"), "queued": result},
                story_id=story_id,
            )
            return {
                "mode": "create_new",
                "character_id": character["id"],
                "appearance_id": (appearance or {}).get("id"),
                "asset_id": asset_id,
                "prompt_id": result.get("prompt_id"),
                "activated": bool(update.get("activate_after_generation", True)),
            }
        except Exception as exc:
            db.add_api_log(
                "comfyui",
                "prompt:appearance-update",
                {
                    "character_id": character["id"],
                    "scene_id": scene.get("id") if scene else "",
                    "reference_asset_id": reference_asset_id,
                    "workbench": workbench_id,
                    "prompt": prompt,
                    "source_prompt": source_prompt,
                    "prompt_source": prompt_source,
                },
                status="error",
                error=str(exc),
                story_id=story_id,
            )
            return appearance_update_skip(update, "queue_failed", str(exc))
        finally:
            if comfy_token:
                service_manager.end_comfy_generation(comfy_token, settings=settings, reason="queue-failed")

    def regenerate_sprite_expression(self, base_asset_id, expression, payload):
        expression = normalize_expression(expression)
        if expression == "neutral":
            return self.send_error_json(400, "Regeneracao individual de neutral nao esta habilitada.")
        requested_asset = db.get_asset(base_asset_id)
        if not requested_asset or requested_asset.get("asset_type") != "sprite":
            return self.send_error_json(404, "Sprite base nao encontrado.")
        base_asset = neutral_expression_reference_asset(requested_asset)
        if not base_asset:
            return self.send_error_json(400, "A aparencia selecionada nao possui um sprite neutro local para servir de referencia.")
        character = db.get_character(base_asset.get("character_id")) if base_asset.get("character_id") else None
        prompt = str(((character or {}).get("expression_prompts") or {}).get(expression) or "").strip()
        if not prompt:
            db.add_api_log(
                "local",
                "expression_prompt_missing_for_character",
                {"character_id": base_asset.get("character_id"), "expression": expression},
                status="error",
                error="Prompt de expressao ausente.",
                story_id=base_asset.get("story_id"),
            )
            if character:
                service_manager.activate_text_ai_role("scene", db.get_settings())
                narrative.generate_character_expression_prompts(
                    character.get("story_id"),
                    character_ids=[character.get("id")],
                    only_missing=True,
                    ai_role="scene",
                )
                character = db.get_character(character.get("id"))
                prompt = str(((character or {}).get("expression_prompts") or {}).get(expression) or "").strip()
            if not prompt:
                return self.send_error_json(400, "Gere os prompts de expressao deste personagem antes de regenerar a imagem.")
        settings = db.get_settings()
        visual_style = db.visual_style_for_story(base_asset.get("story_id"))
        workbench_id = payload.get("workbench") or style_workbench(visual_style, "expression")
        if not workbench_id:
            return self.send_error_json(400, "Workflow de Alterar Expressoes nao configurado no estilo.")

        style_settings = (visual_style or {}).get("advanced_settings") or {}
        width = int(payload.get("width") or style_settings.get("width") or settings.get("sprite_width") or 640)
        height = int(payload.get("height") or style_settings.get("height") or settings.get("sprite_height") or 960)
        steps = int(style_settings.get("steps") or settings.get("sprite_steps") or 24)
        cfg = float(style_settings.get("cfg") or settings.get("sprite_cfg") or 5.0)
        sampler = style_settings.get("sampler_name") or settings.get("sprite_sampler") or settings.get("comfy_sampler")
        scheduler = style_settings.get("scheduler") or settings.get("sprite_scheduler") or settings.get("comfy_scheduler")
        checkpoint = style_settings.get("ckpt_name") or settings.get("comfy_checkpoint")
        negative_prompt = (visual_style or {}).get("negative_prompt") or ""
        allowed_override_fields = generation_override_fields_for_workbench(settings, workbench_id)
        generation_overrides = generation_overrides_for_style(style_settings, allowed_fields=allowed_override_fields)
        generation_overrides = ensure_generation_seed_override(generation_overrides, allowed_override_fields)
        preserve_workbench_settings = not bool((visual_style and style_settings) or generation_overrides)
        reference_path = (ROOT_DIR / base_asset["file_path"]).resolve()
        log_context = {
            "character_id": base_asset.get("character_id") or "",
            "appearance_id": base_asset.get("appearance_id") or "",
            "expression": expression,
            "workflow": workbench_id,
            "requested_asset_id": base_asset_id,
            "reference_asset_id": base_asset.get("id") or "",
            "reference_expression": normalize_expression(base_asset.get("expression")),
        }
        if int(payload.get("sequence_index") or 0) == 0:
            db.add_api_log(
                "local",
                "expression_regeneration_selected_count",
                {"selected_count": int(payload.get("selected_count") or 1), **log_context},
                story_id=base_asset.get("story_id"),
            )
        for operation, value in [
            ("expression_regeneration_started", log_context),
            ("expression_regeneration_workflow", {"workflow": workbench_id}),
            ("expression_regeneration_character", {"character_id": base_asset.get("character_id") or ""}),
            ("expression_regeneration_appearance", {"appearance_id": base_asset.get("appearance_id") or ""}),
            ("expression_regeneration_expression", {"expression": expression}),
        ]:
            db.add_api_log("local", operation, value, story_id=base_asset.get("story_id"))
        comfy_token = service_manager.begin_comfy_generation(settings, reason=f"expression:{expression}")
        try:
            result, workbench_id = self.queue_comfy_image(
                settings,
                "sprite",
                prompt,
                width,
                height,
                checkpoint,
                steps,
                cfg,
                sampler,
                scheduler,
                workbench_id,
                negative_prompt,
                preserve_workbench_settings,
                generation_overrides,
                reference_path,
            )
            child_id = db.add_sprite_expression_asset(
                base_asset,
                expression,
                prompt=prompt,
                negative_prompt=negative_prompt,
                remote_ref=result.get("prompt_id", ""),
                metadata={
                    "base_asset_id": base_asset.get("base_asset_id") or base_asset.get("id"),
                    "expression_regeneration": True,
                    "workbench": workbench_id,
                    "visual_style_id": (visual_style or {}).get("id") or "",
                    "source_prompt": prompt,
                    **result,
                },
            )
            service_manager.attach_comfy_generation(comfy_token, asset_id=child_id, prompt_id=result.get("prompt_id", ""))
            comfy_token = None
            db.add_api_log(
                "comfyui",
                "prompt:expression-regenerate",
                {
                    "base_asset_id": base_asset.get("id") or "",
                    "requested_asset_id": base_asset_id,
                    "expression": expression,
                    "workbench": workbench_id,
                    "prompt": prompt,
                    "reference_asset": base_asset.get("id") or "",
                    "reference_expression": normalize_expression(base_asset.get("expression")),
                    "generation_overrides": generation_overrides,
                },
                result,
                story_id=base_asset.get("story_id"),
            )
            return self.send_json({"asset_id": child_id, "queued": result})
        except Exception as exc:
            db.add_api_log(
                "comfyui",
                "prompt:expression-regenerate",
                {
                    "base_asset_id": base_asset.get("id") or "",
                    "requested_asset_id": base_asset_id,
                    "expression": expression,
                    "workbench": workbench_id,
                    "prompt": prompt,
                },
                status="error",
                error=str(exc),
                story_id=base_asset.get("story_id"),
            )
            db.add_api_log(
                "local",
                "expression_regeneration_failed",
                log_context,
                status="error",
                error=str(exc),
                story_id=base_asset.get("story_id"),
            )
            raise
        finally:
            if comfy_token:
                service_manager.end_comfy_generation(comfy_token, settings=settings, reason="queue-failed")

    def test_visual_style_prompt(self, payload):
        settings = db.get_settings()
        style = payload.get("style") if isinstance(payload.get("style"), dict) else {}
        asset_type = narrative.normalize_prompt_asset_type(payload.get("asset_type") or "appearance")
        workbench_type = "background" if asset_type == "background" else ("appearance" if asset_type == "appearance" else "sprite")
        workbench_id = payload.get("workbench") or style_workbench(style, workbench_type) or default_workbench_for_asset(settings, workbench_type)
        prompt_profile = prompt_profile_for_visual_style(settings, style, asset_type, workbench_id)
        appearance = (payload.get("appearance") or "").strip()
        clothing = (payload.get("clothing") or "").strip()
        source_prompt = build_prompt_test_source(asset_type, appearance, clothing)
        if not source_prompt:
            return self.send_error_json(400, "Informe uma aparencia ou vestimenta para testar o prompt.")
        visual_prompt = narrative.generate_workbench_visual_prompt(
            source_prompt,
            asset_type,
            workbench_id,
            prompt_profile,
            source_prompt,
        )
        db.add_api_log(
            "local",
            "style:prompt-test",
            {
                "asset_type": asset_type,
                "workbench": workbench_id,
                "visual_style_id": style.get("id") or "",
                "prompt_profile_applied": bool(prompt_profile),
                "prompt_profile_style": (prompt_profile or {}).get("style") or "",
                "source_prompt": source_prompt,
            },
            {"visual_prompt": visual_prompt},
        )
        return self.send_json({"visual_prompt": visual_prompt})

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
            scene = find_scene_for_payload(story, payload)
            temporary_names = introduced_temporary_names(payload, name)
            updated_story = link_introduced_character_to_scene(story, scene, existing, temporary_names)
            return self.send_json({"character": existing, "story": updated_story, "already_exists": True})

        scene = find_scene_for_payload(story, payload)
        temporary_names = introduced_temporary_names(payload, name)
        character_payload = narrative.enrich_introduced_character(story, scene, payload)
        if not character_payload.get("name"):
            character_payload["name"] = name
        character_payload["aliases"] = merge_aliases(character_payload.get("aliases"), temporary_names)
        character = db.create_character(story_id, character_payload)
        updated_story = link_introduced_character_to_scene(story, scene, character, temporary_names)
        db.add_api_log(
            "local",
            "character:introduce",
            {"story_id": story_id, "scene_id": scene.get("id") if scene else "", "name": name, "temporary_names": temporary_names},
            {"character_id": character.get("id"), "name": character.get("name"), "aliases": character.get("aliases")},
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
        generation_overrides=None,
        input_image_path=None,
        expression_prompts=None,
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
                    generation_overrides,
                    input_image_path,
                    expression_prompts,
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
                (generation_overrides or {}).get("seed"),
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

        reusable = self.find_reusable_background(story, scene)
        if reusable:
            reusable_asset = reusable["asset"]
            db.set_scene_background(scene["id"], reusable_asset["id"])
            db.add_api_log(
                "local",
                "background:reuse",
                {
                    "scene_id": scene["id"],
                    "prompt": scene.get("background_prompt"),
                    "location": scene_location(scene),
                    "reason": reusable.get("reason"),
                    "matched_scene_id": reusable.get("matched_scene_id"),
                    "matched_location": reusable.get("matched_location"),
                    "score": reusable.get("score"),
                },
                {"asset_id": reusable_asset["id"], "asset_prompt": reusable_asset.get("prompt")},
                story_id=story_id,
            )
            return {"mode": "reused", "asset_id": reusable_asset["id"]}

        try:
            settings = db.get_settings()
            visual_style = db.visual_style_for_story(story_id)
            background_settings = (visual_style or {}).get("background_settings") or {}
            source_prompt = (scene.get("background_prompt") or "").strip()
            visual_prompt = narrative.normalize_background_visual_prompt(source_prompt)
            if not visual_prompt:
                return {"mode": "error", "error": "Prompt de cenario vazio."}
            workbench_id = style_workbench(visual_style, "background") or default_workbench_for_asset(settings, "background")
            prompt_profile = prompt_profile_for_visual_style(settings, visual_style, "background", workbench_id)
            if prompt_profile:
                visual_prompt = narrative.generate_workbench_visual_prompt(
                    source_prompt,
                    "background",
                    workbench_id,
                    prompt_profile,
                    visual_prompt,
                    story_id=story_id,
                )
            visual_prompt = narrative.finalize_background_comfy_prompt(apply_background_style_prompt(visual_style, visual_prompt))
            negative_prompt = background_negative_prompt(visual_style)
            width = int(background_settings.get("width") or settings.get("image_width") or 1024)
            height = int(background_settings.get("height") or settings.get("image_height") or 576)
            checkpoint = background_settings.get("ckpt_name") or settings.get("comfy_checkpoint")
            steps = int(background_settings.get("steps") or settings.get("background_steps") or 28)
            cfg = float(background_settings.get("cfg") or settings.get("background_cfg") or 6.5)
            sampler = background_settings.get("sampler_name") or settings.get("comfy_sampler")
            scheduler = background_settings.get("scheduler") or settings.get("comfy_scheduler")
            allowed_override_fields = generation_override_fields_for_workbench(settings, workbench_id)
            generation_overrides = generation_overrides_for_style(background_settings, allowed_fields=allowed_override_fields)
            generation_overrides = ensure_generation_seed_override(generation_overrides, allowed_override_fields)
            preserve_workbench_settings = not bool((visual_style and background_settings) or generation_overrides)
            comfy_token = service_manager.begin_comfy_generation(settings, reason="auto-background")
            try:
                result, workbench_id = self.queue_comfy_image(
                    settings,
                    "background",
                    visual_prompt,
                    width,
                    height,
                    checkpoint,
                    steps,
                    cfg,
                    sampler,
                    scheduler,
                    workbench_id,
                    negative_prompt,
                    preserve_workbench_settings,
                    generation_overrides,
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
                        "checkpoint": checkpoint,
                        "workbench": workbench_id,
                        "steps": steps,
                        "cfg": cfg,
                        "sampler": sampler,
                        "scheduler": scheduler,
                        "generation_overrides": generation_overrides,
                        "negative_prompt": negative_prompt,
                        "visual_style_id": (visual_style or {}).get("id") or "",
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
                        "negative_prompt": negative_prompt,
                        "remote_ref": result.get("prompt_id", ""),
                        "metadata": {"auto": True, "workbench": workbench_id, "visual_style_id": (visual_style or {}).get("id") or "", "source_prompt": source_prompt, **result},
                    },
                )
                service_manager.attach_comfy_generation(comfy_token, asset_id=asset_id, prompt_id=result.get("prompt_id", ""))
                comfy_token = None
            finally:
                if comfy_token:
                    service_manager.end_comfy_generation(comfy_token, settings=settings, reason="queue-failed")
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

    def find_reusable_background(self, story, current_scene):
        scenes = story.get("scenes") or []
        assets = [
            asset for asset in (story.get("assets") or [])
            if asset.get("asset_type") == "background" and asset.get("url")
        ]
        if not assets:
            return None

        assets_by_id = {asset.get("id"): asset for asset in assets}
        current_location = scene_location(current_scene)
        prior_scenes = scenes_before_current(scenes, current_scene)
        for prior_scene in reversed(prior_scenes):
            prior_asset = background_asset_for_scene(prior_scene, assets, assets_by_id)
            if not prior_asset:
                continue
            prior_location = scene_location(prior_scene)
            if locations_match(current_location, prior_location):
                return {
                    "asset": prior_asset,
                    "reason": "matching location",
                    "matched_scene_id": prior_scene.get("id"),
                    "matched_location": prior_location,
                    "score": 1,
                }

        prompt_key = normalize_prompt((current_scene or {}).get("background_prompt"))
        best = None
        best_score = 0
        best_scene = None
        for asset in assets:
            if not asset.get("prompt"):
                continue
            asset_key = normalize_prompt((asset.get("metadata") or {}).get("source_prompt") or asset.get("prompt"))
            score = prompt_similarity(prompt_key, asset_key)
            if score > best_score:
                best = asset
                best_score = score
                best_scene = next((scene for scene in scenes if scene.get("id") == asset.get("scene_id")), None)
        if best and best_score >= 0.62:
            return {
                "asset": best,
                "reason": "similar prompt",
                "matched_scene_id": best.get("scene_id"),
                "matched_location": scene_location(best_scene) if best_scene else "",
                "score": best_score,
            }
        return None

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
            service_manager.end_comfy_generation(asset_id=asset_id, settings=settings, reason="missing-prompt-id")
            return self.send_json({"ready": False, "asset": asset})

        try:
            images, entry = comfy_client.get_history_images(settings.get("comfy_url"), prompt_id)
        except Exception as exc:
            if comfy_client.is_timeout_error(exc):
                return self.send_json({"ready": False, "waiting": True, "asset": asset})
            raise
        if asset.get("metadata", {}).get("expression_group") and asset.get("asset_type") == "sprite":
            return self.resolve_sprite_expression_group(asset, images, entry, settings)

        image = images[0] if images else None
        if not image:
            if comfy_history_entry_failed(entry):
                service_manager.end_comfy_generation(asset_id=asset_id, settings=settings, reason="comfy-error")
                if asset.get("metadata", {}).get("expression_regeneration"):
                    db.add_api_log(
                        "local",
                        "expression_regeneration_failed",
                        {
                            "asset_id": asset_id,
                            "character_id": asset.get("character_id") or "",
                            "appearance_id": asset.get("appearance_id") or "",
                            "expression": asset.get("expression") or "",
                        },
                        status="error",
                        error="O workflow do ComfyUI terminou com erro.",
                        story_id=asset.get("story_id"),
                    )
                return self.send_error_json(502, "O workflow do ComfyUI terminou com erro.")
            return self.send_json({"ready": False, "asset": asset})

        try:
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
            if asset.get("metadata", {}).get("expression_regeneration"):
                db.add_api_log(
                    "local",
                    "expression_regeneration_finished",
                    {
                        "asset_id": asset_id,
                        "character_id": asset.get("character_id") or "",
                        "appearance_id": asset.get("appearance_id") or "",
                        "expression": asset.get("expression") or "",
                        "workflow": asset.get("metadata", {}).get("workbench") or "",
                    },
                    {"file_path": updated.get("file_path") or ""},
                    story_id=asset.get("story_id"),
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
        finally:
            service_manager.end_comfy_generation(asset_id=asset_id, settings=settings, reason="asset-ready")

    def resolve_sprite_expression_group(self, asset, images, entry, settings):
        asset_id = asset.get("id")
        if not images:
            if comfy_history_entry_failed(entry):
                service_manager.end_comfy_generation(asset_id=asset_id, settings=settings, reason="comfy-error")
                return self.send_error_json(502, "O workflow de expressoes do ComfyUI terminou com erro.")
            return self.send_json({"ready": False, "asset": asset})

        expression_images = classify_expression_images(images)
        neutral_image = expression_images.get("neutral") or next(
            (image for image in images if detect_expression_from_image(image) == "neutral"),
            images[0],
        )
        try:
            body, content_type = comfy_client.download_image(settings.get("comfy_url"), neutral_image)
            relative_path = self.asset_relative_path(asset, neutral_image, content_type)
            target = ROOT_DIR / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            updated = db.update_asset_file(
                asset_id,
                relative_path.as_posix(),
                {
                    "comfy_image": neutral_image,
                    "content_type": content_type,
                    "expression_group_resolved": True,
                    "expression_images_found": sorted(expression_images.keys()),
                },
            )
            db.update_asset_base(asset_id, asset_id)
            base_asset = db.get_asset(asset_id)
            character = db.get_character(base_asset.get("character_id")) if base_asset.get("character_id") else None
            character_expression_prompts = (character or {}).get("expression_prompts") or {}
            created = {}
            for expression in SPRITE_EXPRESSION_KEYS:
                expression_image = expression_images.get(expression)
                if expression_image:
                    child_id = db.add_sprite_expression_asset(
                        base_asset,
                        expression,
                        prompt=character_expression_prompts.get(expression) or base_asset.get("prompt"),
                        metadata={
                            "base_asset_id": asset_id,
                            "expression_group_child": True,
                            "fallback_to_base": False,
                            "workbench": asset.get("metadata", {}).get("workbench") or "",
                            "visual_style_id": asset.get("metadata", {}).get("visual_style_id") or "",
                        },
                    )
                    child_asset = db.get_asset(child_id)
                    child_body, child_content_type = comfy_client.download_image(settings.get("comfy_url"), expression_image)
                    child_relative_path = self.asset_relative_path(child_asset, expression_image, child_content_type)
                    child_target = ROOT_DIR / child_relative_path
                    child_target.parent.mkdir(parents=True, exist_ok=True)
                    child_target.write_bytes(child_body)
                    db.update_asset_file(
                        child_id,
                        child_relative_path.as_posix(),
                        {"comfy_image": expression_image, "content_type": child_content_type},
                    )
                    created[expression] = child_id
                else:
                    child_id = db.add_sprite_expression_asset(
                        base_asset,
                        expression,
                        file_path=base_asset.get("file_path") or relative_path.as_posix(),
                        prompt=character_expression_prompts.get(expression) or base_asset.get("prompt"),
                        metadata={
                            "base_asset_id": asset_id,
                            "expression_group_child": True,
                            "fallback_to_base": True,
                            "workbench": asset.get("metadata", {}).get("workbench") or "",
                            "visual_style_id": asset.get("metadata", {}).get("visual_style_id") or "",
                            "content_type": content_type,
                        },
                    )
                    created[expression] = child_id
            db.add_api_log(
                "comfyui",
                "history:view-expression-group",
                {"prompt_id": asset.get("remote_ref"), "asset_id": asset_id},
                {"images": images, "created": created, "base_image": neutral_image},
                story_id=asset.get("story_id"),
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
            return self.send_json({"ready": True, "asset": updated, "expressions": created})
        finally:
            service_manager.end_comfy_generation(asset_id=asset_id, settings=settings, reason="asset-ready")

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
        service_manager.end_comfy_generation(asset_id=asset_id, settings=db.get_settings(), reason="asset-deleted")
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

    def delete_character(self, character_id):
        result = db.delete_character(character_id)
        if not result:
            return self.send_error_json(404, "Personagem nao encontrado.")
        deleted_files = []
        delete_errors = []
        data_root = (ROOT_DIR / "data").resolve()
        for asset in result.get("assets") or []:
            file_path = asset.get("file_path")
            if not file_path:
                continue
            target = (ROOT_DIR / file_path).resolve()
            if is_relative_to(target, data_root) and target.exists() and target.is_file():
                deleted, error = delete_path_with_retries(target)
                if deleted:
                    deleted_files.append(file_path)
                if error:
                    delete_errors.append({"file_path": file_path, "error": error})
        db.add_api_log(
            "local",
            "character:delete",
            {"character_id": character_id},
            {
                "character": result.get("character"),
                "asset_count": len(result.get("assets") or []),
                "deleted_files": deleted_files,
                "delete_errors": delete_errors,
            },
            story_id=(result.get("character") or {}).get("story_id"),
        )
        return self.send_json({
            "deleted": True,
            "character": result.get("character"),
            "deleted_files": deleted_files,
            "delete_errors": delete_errors,
            "story": result.get("story"),
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
        if target.suffix.lower() in {".html", ".js", ".css"}:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_icon(self, path):
        relative = path.removeprefix("/icons/")
        target = (ICONS_DIR / relative).resolve()
        if not str(target).startswith(str(ICONS_DIR.resolve())) or not target.exists() or target.is_dir():
            return self.send_error_json(404, "Icone nao encontrado.")
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
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
    autostart = service_manager.autostart_services(db.get_settings())
    for service, result in autostart.items():
        if result.get("started"):
            print(f"{service} iniciado pelo TaleWeaver (pid {result.get('pid')})")
        elif result.get("error"):
            print(f"Nao foi possivel iniciar {service}: {result.get('error')}")
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


def style_workbench(style, asset_type="sprite"):
    style = style or {}
    if asset_type == "background":
        return style.get("background_workbench") or ""
    if asset_type in {"appearance", "sprite_appearance"}:
        return style.get("appearance_workbench") or ""
    if asset_type in {"expression", "sprite_expression"}:
        return style.get("expression_workbench") or ""
    return style.get("sprite_workbench") or ""


def style_expressions_enabled(style):
    return bool((style or {}).get("expressions_enabled"))


def normalize_expression(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in OFFICIAL_EXPRESSIONS else "neutral"


def compact_label(value, limit=42):
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return "Aparencia"
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def normalized_scene_appearance_updates(story, scene):
    if not scene:
        return []
    raw = narrative.unwrap_scene_payload(scene.get("raw_ai_response") or {})
    updates = raw.get("appearance_updates") if isinstance(raw, dict) else []
    aliases = narrative.character_alias_index((story or {}).get("characters") or [])
    return narrative.normalize_appearance_updates(updates, aliases)


def story_character_for_update(story, name):
    key = narrative.normalize_person_key(name)
    if not key:
        return None
    for character in (story or {}).get("characters") or []:
        names = [character.get("name"), *str(character.get("aliases") or "").split(",")]
        if any(narrative.normalize_person_key(item) == key for item in names if str(item or "").strip()):
            return character
        if narrative.canonical_character_name(name, narrative.character_alias_index([character])) == character.get("name"):
            return character
    return None


def find_character_appearance_for_update(story, character, appearance_id_or_label):
    target = str(appearance_id_or_label or "").strip()
    appearances = [
        appearance for appearance in (story or {}).get("appearances") or []
        if appearance.get("character_id") == character.get("id")
    ]
    if not appearances:
        return None
    if not target:
        active_id = character.get("active_appearance_id") or ""
        return next((item for item in appearances if item.get("id") == active_id or item.get("is_active")), None) or appearances[0]
    normalized_target = normalize_lookup_text(target)
    for appearance in appearances:
        if appearance.get("id") == target:
            return appearance
    for appearance in appearances:
        if normalize_lookup_text(appearance.get("label")) == normalized_target:
            return appearance
    if normalized_target in {"default", "initial", "inicial", "normal"}:
        for appearance in appearances:
            label = normalize_lookup_text(appearance.get("label"))
            if label in {"default", "initial", "inicial"}:
                return appearance
    return None


def appearance_update_change_prompt(update):
    prompt = str(update.get("change_prompt") or "").strip()
    if prompt:
        return prompt
    summary = str(update.get("new_appearance_summary") or update.get("new_appearance_name") or "").strip()
    if not summary:
        return ""
    return (
        f"Change only the character appearance as follows: {summary}. "
        "Keep the same character, same face, same hairstyle, same hair color, same eye color, same body type, "
        "same proportions, same apparent age, same pose when possible, same visual novel sprite style, "
        "same full body framing, and same background. Do not change anything else. Do not add text, logo, or watermark."
    )


def neutral_expression_reference_asset(asset):
    if not asset or asset.get("asset_type") != "sprite":
        return None
    appearance = db.get_appearance(asset.get("appearance_id"))
    candidate_ids = []
    if appearance:
        candidate_ids.extend([appearance.get("neutral_asset_id"), appearance.get("primary_asset_id")])
    candidate_ids.extend([asset.get("base_asset_id"), asset.get("id")])

    seen = set()
    for candidate_id in candidate_ids:
        if not candidate_id or candidate_id in seen:
            continue
        seen.add(candidate_id)
        candidate = db.get_asset(candidate_id)
        if not candidate or candidate.get("asset_type") != "sprite" or not candidate.get("file_path"):
            continue
        if candidate.get("character_id") != asset.get("character_id"):
            continue
        if asset.get("appearance_id") and candidate.get("appearance_id") != asset.get("appearance_id"):
            continue
        if normalize_expression(candidate.get("expression")) != "neutral":
            continue
        return candidate
    return None


def appearance_update_skip(update, code, message):
    return {"mode": "skipped", "code": code, "message": message, "update": update}


def normalize_lookup_text(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def detect_expression_from_image(image):
    filename = Path(str((image or {}).get("filename") or "")).stem.lower()
    tokens = [token for token in re.split(r"[^a-z0-9]+", filename) if token]
    for expression in SPRITE_EXPRESSION_KEYS:
        if expression in tokens or filename.endswith(expression):
            return expression
    return "neutral"


def classify_expression_images(images):
    result = {}
    for image in images or []:
        expression = detect_expression_from_image(image)
        if expression != "neutral" and expression not in result:
            result[expression] = image
    for image in images or []:
        if detect_expression_from_image(image) == "neutral":
            result.setdefault("neutral", image)
            break
    if "neutral" not in result and images:
        result["neutral"] = images[0]
    return result


def apply_style_prompt(style, prompt):
    style = style or {}
    parts = [
        style.get("prompt_prefix") or "",
        prompt or "",
        style.get("prompt_suffix") or "",
    ]
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())


def apply_background_style_prompt(style, prompt):
    style = style or {}
    parts = [
        narrative.sanitize_background_config_prompt(style.get("background_prompt_prefix") or ""),
        prompt or "",
        narrative.sanitize_background_config_prompt(style.get("background_prompt_suffix") or ""),
    ]
    return ", ".join(str(part).strip().strip(",") for part in parts if str(part or "").strip())


def background_negative_prompt(style):
    style = style or {}
    configured = style.get("background_negative_prompt") or ""
    prompt = configured or (
        "main character, foreground person, foreground people, close-up face, detailed face, portrait, "
        "full body in foreground, centered human figure, character focus, action pose, text, logo, watermark"
    )
    return normalize_background_negative_prompt(prompt)


def normalize_background_negative_prompt(prompt):
    broad_people_bans = {
        "people",
        "person",
        "human",
        "humans",
        "character",
        "characters",
        "face",
        "faces",
        "crowd",
        "body",
        "bodies",
        "silhouette",
        "silhouettes",
    }
    parts = []
    seen = set()
    for part in str(prompt or "").split(","):
        item = part.strip()
        key = item.lower()
        if not item or key in broad_people_bans:
            continue
        if key not in seen:
            seen.add(key)
            parts.append(item)
    for item in [
        "main character",
        "foreground person",
        "foreground people",
        "close-up face",
        "detailed face",
        "portrait",
        "centered human figure",
        "character focus",
    ]:
        if item not in seen:
            parts.append(item)
            seen.add(item)
    return ", ".join(parts)


def generation_override_fields_for_workbench(settings, workbench_id):
    if not workbench_id:
        return None
    try:
        workbenches = comfy_client.list_workbenches(comfy_workflows_dir(settings))
    except Exception:
        return None
    workbench = next((item for item in workbenches if item.get("id") == workbench_id), None)
    if not workbench:
        return None
    inputs = set(workbench.get("inputs") or [])
    allowed = set()
    for field in ["width", "height", "steps", "cfg", "sampler_name", "scheduler", "ckpt_name"]:
        if field in inputs:
            allowed.add(field)
    if "seed" in inputs or "noise_seed" in inputs:
        allowed.add("seed")
    return allowed


def generation_overrides_for_style(style_settings, payload=None, allowed_fields=None):
    style_settings = style_settings if isinstance(style_settings, dict) else {}
    payload = payload if isinstance(payload, dict) else {}
    allowed_fields = set(allowed_fields) if allowed_fields is not None else None
    result = {}
    for field in ["width", "height", "seed", "steps", "cfg", "sampler_name", "scheduler", "ckpt_name"]:
        if allowed_fields is not None and field not in allowed_fields:
            continue
        value = payload.get(field) if field in payload else style_settings.get(field)
        if value is None or str(value).strip() == "":
            continue
        if field in {"width", "height", "steps", "seed"}:
            try:
                result[field] = int(str(value).strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Valor invalido para {field}: {value}") from exc
        elif field == "cfg":
            result[field] = float(value)
        else:
            result[field] = str(value).strip()
    return result


def ensure_generation_seed_override(generation_overrides, allowed_fields=None):
    allowed_fields = set(allowed_fields) if allowed_fields is not None else None
    if allowed_fields is not None and "seed" not in allowed_fields:
        return generation_overrides or {}
    result = dict(generation_overrides or {})
    if result.get("seed") in {None, ""}:
        result["seed"] = random_comfy_seed()
    return result


def random_comfy_seed():
    return secrets.randbelow(18446744073709551615) + 1


def comfy_history_entry_failed(entry):
    status = entry.get("status") or {}
    status_text = str(status.get("status_str") or status.get("status") or "").lower()
    if status_text in {"error", "failed"}:
        return True
    messages = status.get("messages") or []
    return any("error" in str(message).lower() or "failed" in str(message).lower() for message in messages)


def prompt_profile_for_visual_style(settings, style, asset_type, workbench_id=""):
    profile = narrative.prompt_profile_from_visual_style(style, settings, asset_type)
    if profile and (profile.get("style") or profile.get("example")):
        return profile
    if not workbench_id:
        return None
    legacy = legacy_prompt_profile_for_workbench(settings, workbench_id)
    return legacy


def legacy_prompt_profile_for_workbench(settings, workbench_id):
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


def build_prompt_test_source(asset_type, appearance, clothing):
    appearance = str(appearance or "").strip()
    clothing = str(clothing or "").strip()
    if narrative.normalize_prompt_asset_type(asset_type) == "background":
        parts = []
        if appearance:
            parts.append(f"Base scene or appearance description: {appearance}")
        if clothing:
            parts.append(f"Additional visual constraints: {clothing}")
        return "\n".join(parts).strip()
    parts = []
    if appearance:
        parts.append(f"Physical appearance: {appearance}")
    if clothing:
        parts.append(f"Clothing - mandatory fixed outfit, preserve exactly and translate to English: {clothing}")
    parts.append(
        "Create the final image prompt in English only. One character only, full body, standing, front view, visual novel sprite framing. Do not invent or replace the outfit."
    )
    return "\n".join(part for part in parts if part).strip()


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


def introduced_temporary_names(payload, fallback_name=""):
    payload = payload if isinstance(payload, dict) else {}
    source = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else payload
    names = [
        fallback_name,
        payload.get("name"),
        payload.get("display_name"),
        payload.get("temporary_name"),
        source.get("temporary_name"),
        source.get("display_name"),
        source.get("name"),
    ]
    result = []
    seen = set()
    for name in names:
        text = str(name or "").strip()
        key = normalized_person_name(text)
        if text and key and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def merge_aliases(existing_aliases, aliases):
    parts = []
    seen = set()
    for value in [existing_aliases, *(aliases or [])]:
        if isinstance(value, str) and "," in value:
            values = [item.strip() for item in value.split(",")]
        else:
            values = [str(value or "").strip()]
        for item in values:
            key = normalized_person_name(item)
            if item and key and key not in seen:
                seen.add(key)
                parts.append(item)
    return ", ".join(parts)


def link_introduced_character_to_scene(story, scene, character, temporary_names):
    if not story or not scene or not character:
        return db.get_story(story.get("id")) if story else {}
    story_id = story.get("id")
    final_name = character.get("name") or ""
    if not story_id or not final_name:
        return db.get_story(story_id)

    aliases = [name for name in (temporary_names or []) if normalized_person_name(name) != normalized_person_name(final_name)]
    if aliases:
        merged_aliases = merge_aliases(character.get("aliases"), aliases)
        if merged_aliases != (character.get("aliases") or ""):
            character = db.update_character(character["id"], {"aliases": merged_aliases})

    origin_order = int(scene.get("scene_order") or 0)
    replace_names = aliases or temporary_names or []
    changed_scene_ids = []
    for item in story.get("scenes") or []:
        if origin_order and int(item.get("scene_order") or 0) < origin_order:
            continue
        payload = replaced_scene_character_payload(item, replace_names, final_name)
        if payload:
            db.update_scene(item["id"], payload)
            changed_scene_ids.append(item["id"])

    if replace_names:
        db.add_memory_entry(
            story_id,
            "scene-state",
            f"Personagem temporario {', '.join(replace_names)} foi consolidado como {final_name}; trate esses nomes como a mesma pessoa daqui em diante.",
            4,
        )
    db.add_api_log(
        "local",
        "character:link-temporary",
        {"story_id": story_id, "scene_id": scene.get("id"), "temporary_names": replace_names, "final_name": final_name},
        {"updated_scene_ids": changed_scene_ids, "aliases": character.get("aliases")},
        story_id=story_id,
    )
    return db.get_story(story_id)


def replaced_scene_character_payload(scene, temporary_names, final_name):
    keys = {normalized_person_name(name) for name in temporary_names or [] if normalized_person_name(name)}
    final_key = normalized_person_name(final_name)
    if not keys or not final_key:
        return {}
    payload = {}
    dialogues, changed_dialogues = replace_dialogue_names(scene.get("dialogues") or [], keys, final_name)
    cast, changed_cast = replace_cast_names(scene.get("characters_on_screen") or [], keys, final_name)
    raw_response, changed_raw = replace_names_in_raw_response(scene.get("raw_ai_response"), keys, final_name)
    if changed_dialogues:
        payload["dialogues"] = dialogues
    if changed_cast:
        payload["characters_on_screen"] = cast
    if changed_raw:
        payload["raw_ai_response"] = raw_response
    return payload


def replace_dialogue_names(dialogues, keys, final_name):
    result = []
    changed = False
    for dialogue in dialogues:
        item = dict(dialogue or {})
        if normalized_person_name(item.get("character")) in keys:
            item["character"] = final_name
            changed = True
        result.append(item)
    return result, changed


def replace_cast_names(cast, keys, final_name):
    result = []
    changed = False
    seen = set()
    for character in cast:
        item = dict(character or {})
        if normalized_person_name(item.get("name")) in keys:
            item["name"] = final_name
            changed = True
        key = normalized_person_name(item.get("name"))
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result, changed


def replace_names_in_raw_response(value, keys, final_name):
    if isinstance(value, list):
        changed = False
        result = []
        for item in value:
            replaced, item_changed = replace_names_in_raw_response(item, keys, final_name)
            result.append(replaced)
            changed = changed or item_changed
        return result, changed
    if isinstance(value, dict):
        changed = False
        result = {}
        for key, item in value.items():
            if key in {"character", "name", "display_name", "temporary_name"} and normalized_person_name(item) in keys:
                result[key] = final_name
                changed = True
            else:
                replaced, item_changed = replace_names_in_raw_response(item, keys, final_name)
                result[key] = replaced
                changed = changed or item_changed
        return result, changed
    return value, False


def latest_scene(story):
    scenes = story.get("scenes") or []
    return scenes[-1] if scenes else {}


def find_character_by_name(characters, name):
    key = normalized_person_name(name)
    if not key:
        return None
    for character in characters:
        names = character_name_variants(character)
        if any(normalized_person_name(item) == key for item in names if item):
            return character
    return None


def character_name_variants(character):
    name = str((character or {}).get("name") or "").strip()
    aliases = str((character or {}).get("aliases") or "").strip()
    names = []
    if name:
        names.append(name)
        parts = name.split()
        if parts:
            names.extend([parts[0], parts[-1]])
            for title in ["professor", "professora", "prof", "dr", "dra", "senhor", "senhora", "sr", "sra", "mr", "ms", "sir", "lady", "lord"]:
                names.append(f"{title} {parts[0]}")
                names.append(f"{title} {name}")
    names.extend(alias.strip() for alias in re.split(r"[,;/|]", aliases) if alias.strip())
    return names


def normalized_person_name(value):
    text = re.sub(r"[^\wÀ-ÿ\s'-]", " ", str(value or "").strip().lower())
    return " ".join(text.split())


def scene_location_changed(scene):
    raw = scene.get("raw_ai_response") if isinstance(scene, dict) else {}
    raw = unwrap_scene_payload(raw)
    if not isinstance(raw, dict):
        return None
    value = raw.get("location_changed")
    if value is None and isinstance(raw.get("location"), dict):
        value = raw["location"].get("location_changed")
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
    raw = unwrap_scene_payload(raw)
    if isinstance(raw, dict):
        location = raw.get("location")
        if isinstance(location, dict):
            return location.get("name") or location.get("title") or ""
        return location or raw.get("current_location") or ""
    return ""


LOCATION_STOPWORDS = {
    "a", "an", "as", "at", "da", "das", "de", "del", "do", "dos", "el", "em",
    "en", "in", "la", "na", "nas", "no", "nos", "of", "on", "o", "os", "the",
}


def folded_ascii_text(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def location_tokens(value):
    words = re.findall(r"[a-z0-9]+", folded_ascii_text(value))
    return {word for word in words if len(word) > 1 and word not in LOCATION_STOPWORDS}


def locations_match(left, right):
    left_tokens = location_tokens(left)
    right_tokens = location_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    if left_tokens == right_tokens:
        return True
    overlap = left_tokens & right_tokens
    if len(overlap) < 2:
        return False
    return len(overlap) / min(len(left_tokens), len(right_tokens)) >= 0.8


def scenes_before_current(scenes, current_scene):
    current_id = (current_scene or {}).get("id")
    if current_id:
        for index, scene in enumerate(scenes):
            if scene.get("id") == current_id:
                return scenes[:index]
    return scenes[:-1]


def background_asset_for_scene(scene, assets, assets_by_id):
    asset = assets_by_id.get((scene or {}).get("background_asset_id"))
    if asset and asset.get("url"):
        return asset
    scene_id = (scene or {}).get("id")
    return next(
        (
            asset for asset in assets
            if asset.get("asset_type") == "background" and asset.get("scene_id") == scene_id and asset.get("url")
        ),
        None,
    )


def unwrap_scene_payload(raw):
    if not isinstance(raw, dict):
        return {}
    for key in ("scene", "next_scene", "visual_novel_scene", "result"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return raw


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
