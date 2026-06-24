import json
import copy
import re
import shutil
import sqlite3
import time
import unicodedata
import uuid
from pathlib import Path

from .config import DATA_DIR, DB_PATH, ROOT_DIR, STORIES_DIR, STYLE_COVERS_DIR, DEFAULT_SETTINGS, DEFAULT_VISUAL_STYLES

SECRET_SETTING_KEYS = {
    "openai_api_key",
    "openai_compatible_api_key",
    "story_ai_openai_compatible_api_key",
    "scene_ai_openai_compatible_api_key",
}
MASKED_SECRET_VALUE = "********"
OFFICIAL_EXPRESSIONS = ["neutral", "happy", "sad", "angry", "thoughtful", "surprised", "embarrassed", "scared"]
EXPRESSION_PROMPT_KEYS = [item for item in OFFICIAL_EXPRESSIONS if item != "neutral"]


def now_ms():
    return int(time.time() * 1000)


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def normalize_participation_mode(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "first": "first_person",
        "first_person": "first_person",
        "primeira": "first_person",
        "primeira_pessoa": "first_person",
        "1": "first_person",
        "third": "third_person",
        "third_person": "third_person",
        "terceira": "third_person",
        "terceira_pessoa": "third_person",
        "3": "third_person",
        "narrator": "narrator",
        "narrador": "narrator",
        "narrative": "narrator",
    }
    return aliases.get(text, "first_person")


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORIES_DIR.mkdir(parents=True, exist_ok=True)
    STYLE_COVERS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stories (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT,
                tone TEXT,
                visual_style TEXT,
                visual_style_id TEXT,
                participation_mode TEXT NOT NULL DEFAULT 'first_person',
                content_rating TEXT,
                language TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                lore TEXT,
                player_character TEXT,
                summary TEXT,
                current_scene_id TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                name TEXT NOT NULL,
                species TEXT,
                gender TEXT,
                character_type TEXT,
                aliases TEXT,
                description TEXT,
                physical TEXT,
                personality TEXT,
                clothing TEXT,
                role TEXT,
                relationship TEXT,
                secrets TEXT,
                speech_style TEXT,
                ai_role_summary TEXT,
                ai_personality_summary TEXT,
                ai_voice_summary TEXT,
                ai_prompt_brief TEXT,
                visual_prompt TEXT,
                expression_prompts TEXT NOT NULL DEFAULT '{}',
                active_appearance_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                importance TEXT NOT NULL DEFAULT 'secondary',
                is_player INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_appearances (
                id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                label TEXT,
                primary_asset_id TEXT,
                neutral_asset_id TEXT,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY(primary_asset_id) REFERENCES generated_assets(id) ON DELETE SET NULL,
                FOREIGN KEY(neutral_asset_id) REFERENCES generated_assets(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                scene_order INTEGER NOT NULL,
                title TEXT,
                scene_text TEXT,
                dialogues TEXT NOT NULL DEFAULT '[]',
                choices TEXT NOT NULL DEFAULT '[]',
                characters_on_screen TEXT NOT NULL DEFAULT '[]',
                background_prompt TEXT,
                background_asset_id TEXT,
                memory_updates TEXT NOT NULL DEFAULT '{}',
                raw_ai_response TEXT,
                user_input TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS lore_entries (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                entry_type TEXT NOT NULL DEFAULT 'note',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS generated_assets (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                character_id TEXT,
                scene_id TEXT,
                appearance_id TEXT,
                asset_type TEXT NOT NULL,
                base_asset_id TEXT,
                expression TEXT,
                prompt TEXT,
                negative_prompt TEXT,
                file_path TEXT,
                remote_ref TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE,
                FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE SET NULL,
                FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS story_references (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                label TEXT,
                file_path TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS story_scenarios (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                prompt TEXT,
                enhanced_prompt TEXT,
                asset_id TEXT,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE,
                FOREIGN KEY(asset_id) REFERENCES generated_assets(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS choices (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                scene_id TEXT NOT NULL,
                choice_text TEXT NOT NULL,
                chosen INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE,
                FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS api_logs (
                id TEXT PRIMARY KEY,
                story_id TEXT,
                provider TEXT NOT NULL,
                operation TEXT NOT NULL,
                request_payload TEXT,
                response_payload TEXT,
                status TEXT NOT NULL,
                error TEXT,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS visual_styles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                prompt_prefix TEXT,
                prompt_suffix TEXT,
                negative_prompt TEXT,
                sprite_workbench TEXT,
                background_workbench TEXT,
                background_prompt_prefix TEXT,
                background_prompt_suffix TEXT,
                background_negative_prompt TEXT,
                background_settings TEXT NOT NULL DEFAULT '{}',
                sprite_prompt_command TEXT,
                sprite_prompt_example TEXT,
                background_prompt_command TEXT,
                background_prompt_example TEXT,
                appearance_workbench TEXT,
                appearance_prompt_command TEXT,
                appearance_prompt_example TEXT,
                appearance_reference_workbench TEXT,
                appearance_reference_prompt_command TEXT,
                appearance_reference_prompt_example TEXT,
                expressions_enabled INTEGER NOT NULL DEFAULT 0,
                expression_prompts_visible INTEGER NOT NULL DEFAULT 0,
                expression_workbench TEXT,
                expression_prompts TEXT NOT NULL DEFAULT '{}',
                cover_path TEXT,
                advanced_settings TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """
        )
        ensure_columns(conn, "stories", {"visual_style_id": "TEXT", "participation_mode": "TEXT NOT NULL DEFAULT 'first_person'"})
        ensure_columns(
            conn,
            "visual_styles",
            {
                "background_workbench": "TEXT",
                "background_prompt_prefix": "TEXT",
                "background_prompt_suffix": "TEXT",
                "background_negative_prompt": "TEXT",
                "background_settings": "TEXT NOT NULL DEFAULT '{}'",
                "sprite_prompt_command": "TEXT",
                "sprite_prompt_example": "TEXT",
                "background_prompt_command": "TEXT",
                "background_prompt_example": "TEXT",
                "appearance_workbench": "TEXT",
                "appearance_prompt_command": "TEXT",
                "appearance_prompt_example": "TEXT",
                "appearance_reference_workbench": "TEXT",
                "appearance_reference_prompt_command": "TEXT",
                "appearance_reference_prompt_example": "TEXT",
                "expressions_enabled": "INTEGER NOT NULL DEFAULT 0",
                "expression_prompts_visible": "INTEGER NOT NULL DEFAULT 0",
                "expression_workbench": "TEXT",
                "expression_prompts": "TEXT NOT NULL DEFAULT '{}'",
            },
        )
        ensure_columns(conn, "generated_assets", {"base_asset_id": "TEXT", "appearance_id": "TEXT"})
        ensure_columns(
            conn,
            "characters",
            {
                "species": "TEXT",
                "gender": "TEXT",
                "character_type": "TEXT",
                "aliases": "TEXT",
                "description": "TEXT",
                "clothing": "TEXT",
                "ai_role_summary": "TEXT",
                "ai_personality_summary": "TEXT",
                "ai_voice_summary": "TEXT",
                "ai_prompt_brief": "TEXT",
                "expression_prompts": "TEXT NOT NULL DEFAULT '{}'",
                "active_appearance_id": "TEXT",
            },
        )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
        )
        seed_visual_styles(conn)
        backfill_visual_style_backgrounds(conn)
        run_once(conn, "cleanup_visual_style_background_prompts_v1", cleanup_visual_style_background_prompts)
        run_once(conn, "story_scenarios_v1", backfill_story_scenarios)
        run_once(conn, "character_ai_summaries_v3", backfill_character_ai_summaries)


def ensure_columns(conn, table, columns):
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def run_once(conn, key, callback):
    marker = f"migration:{key}"
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (marker,)).fetchone()
    if row:
        return
    callback(conn)
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (marker, json.dumps(True)))


def backfill_story_scenarios(conn):
    timestamp = now_ms()
    stories = conn.execute("SELECT id, current_scene_id FROM stories").fetchall()
    for story in stories:
        scenes = conn.execute(
            "SELECT * FROM scenes WHERE story_id = ? AND background_asset_id IS NOT NULL ORDER BY scene_order",
            (story["id"],),
        ).fetchall()
        scenarios_by_key = {}
        for scene in scenes:
            asset = conn.execute(
                "SELECT * FROM generated_assets WHERE id = ? AND asset_type = 'background'",
                (scene["background_asset_id"],),
            ).fetchone()
            if not asset:
                continue
            raw = json_load(scene["raw_ai_response"], {})
            location = raw.get("location") if isinstance(raw, dict) else ""
            if isinstance(location, dict):
                location = location.get("name") or location.get("title") or ""
            description = str(scene["background_prompt"] or "").strip()
            name = str(location or friendly_scenario_name(description)).strip()
            key = normalize_scenario_name(name)
            metadata = json_load(asset["metadata"], {})
            scenario = scenarios_by_key.get(key)
            is_active = 1 if scene["id"] == story["current_scene_id"] else 0
            if is_active:
                conn.execute("UPDATE story_scenarios SET is_active = 0 WHERE story_id = ?", (story["id"],))
            if scenario:
                conn.execute(
                    "UPDATE story_scenarios SET asset_id = ?, description = ?, prompt = ?, enhanced_prompt = ?, is_active = CASE WHEN ? = 1 THEN 1 ELSE is_active END, updated_at = ? WHERE id = ?",
                    (
                        asset["id"],
                        description or scenario["description"],
                        metadata.get("source_prompt") or description or scenario["prompt"],
                        asset["prompt"] or scenario["enhanced_prompt"],
                        is_active,
                        timestamp,
                        scenario["id"],
                    ),
                )
                scenario = dict(scenario)
                scenario.update({"asset_id": asset["id"], "description": description})
                scenarios_by_key[key] = scenario
                continue
            scenario_id = new_id("scenario")
            conn.execute(
                """
                INSERT INTO story_scenarios (
                    id, story_id, name, description, prompt, enhanced_prompt,
                    asset_id, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scenario_id, story["id"], name, description,
                    metadata.get("source_prompt") or description, asset["prompt"] or "",
                    asset["id"], is_active, asset["created_at"] or timestamp, timestamp,
                ),
            )
            scenarios_by_key[key] = {
                "id": scenario_id, "description": description, "prompt": metadata.get("source_prompt") or description,
                "enhanced_prompt": asset["prompt"] or "", "asset_id": asset["id"],
            }


def backfill_character_ai_summaries(conn):
    timestamp = now_ms()
    rows = conn.execute("SELECT * FROM characters").fetchall()
    for row in rows:
        source = row_to_dict(row)
        source["ai_role_summary"] = ""
        source["ai_personality_summary"] = ""
        source["ai_voice_summary"] = ""
        source["ai_prompt_brief"] = ""
        data = normalize_character_ai_summaries(source)
        conn.execute(
            """
            UPDATE characters
            SET ai_role_summary = ?, ai_personality_summary = ?, ai_voice_summary = ?,
                ai_prompt_brief = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("ai_role_summary") or "",
                data.get("ai_personality_summary") or "",
                data.get("ai_voice_summary") or "",
                data.get("ai_prompt_brief") or "",
                timestamp,
                row["id"],
            ),
        )


def normalize_scenario_name(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    stopwords = {"a", "as", "da", "das", "de", "do", "dos", "em", "na", "nas", "no", "nos", "o", "os"}
    return " ".join(word for word in re.findall(r"[a-z0-9]+", text) if word not in stopwords)


def friendly_scenario_name(description):
    text = " ".join(str(description or "").strip().split())
    if not text:
        return "Cenario sem nome"
    first = re.split(r"[.!?]", text, maxsplit=1)[0].strip(" ,;:-")
    words = first.split()[:7]
    name = " ".join(words).strip()
    return name[:72] or "Cenario sem nome"


def row_to_dict(row):
    return dict(row) if row else None


def json_load(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def get_settings():
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings = dict(DEFAULT_SETTINGS)
    settings.update({row["key"]: json_load(row["value"], row["value"]) for row in rows})
    return settings


def public_settings():
    settings = get_settings()
    for key in SECRET_SETTING_KEYS:
        if settings.get(key):
            settings[key] = MASKED_SECRET_VALUE
    return settings


def update_settings(values):
    with connect() as conn:
        for key, value in values.items():
            if key in SECRET_SETTING_KEYS and (value is None or value == "" or value == MASKED_SECRET_VALUE):
                continue
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value)),
            )
    return get_settings()


def list_stories():
    with connect() as conn:
        stories = conn.execute(
            """
            SELECT s.*, (
                SELECT group_concat(name, ', ')
                FROM characters c
                WHERE c.story_id = s.id AND c.importance IN ('main', 'player')
            ) AS main_characters, (
                SELECT COUNT(*)
                FROM scenes sc
                WHERE sc.story_id = s.id
            ) AS scene_count, (
                SELECT COUNT(*)
                FROM characters cc
                WHERE cc.story_id = s.id
            ) AS character_count, (
                SELECT ga.id
                FROM generated_assets ga
                WHERE ga.story_id = s.id
                  AND ga.asset_type = 'background'
                  AND ga.file_path != ''
                ORDER BY ga.created_at DESC
                LIMIT 1
            ) AS cover_asset_id
            FROM stories s
            ORDER BY s.updated_at DESC
            """
        ).fetchall()
    return [serialize_story(row) for row in stories]


def update_story(story_id, payload):
    timestamp = now_ms()
    if "participation_mode" in payload or "point_of_view" in payload:
        payload["participation_mode"] = normalize_participation_mode(payload.get("participation_mode") or payload.get("point_of_view"))
    fields = ["title", "genre", "tone", "visual_style", "visual_style_id", "participation_mode", "content_rating", "language", "status", "lore", "summary"]
    updates = [field for field in fields if field in payload]
    if not updates:
        return get_story(story_id)
    sql = ", ".join([f"{field} = ?" for field in updates] + ["updated_at = ?"])
    values = [payload[field] for field in updates] + [timestamp, story_id]
    with connect() as conn:
        conn.execute(f"UPDATE stories SET {sql} WHERE id = ?", values)
    return get_story(story_id)


def delete_story(story_id):
    story = get_story(story_id)
    if not story:
        return None
    with connect() as conn:
        conn.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    return story


def add_memory_entry(story_id, entry_type, content, importance=3):
    timestamp = now_ms()
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not exists:
            return None
        conn.execute(
            "INSERT INTO memory_entries VALUES (?, ?, ?, ?, ?, ?)",
            (new_id("mem"), story_id, entry_type or "note", content or "", int(importance or 3), timestamp),
        )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def update_memory_entry(memory_id, payload):
    timestamp = now_ms()
    fields = ["entry_type", "content", "importance"]
    updates = [field for field in fields if field in payload]
    with connect() as conn:
        row = conn.execute("SELECT * FROM memory_entries WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            return None
        story_id = row["story_id"]
        if updates:
            sql = ", ".join([f"{field} = ?" for field in updates])
            values = [
                int(payload[field] or 1) if field == "importance" else payload[field]
                for field in updates
            ]
            values.append(memory_id)
            conn.execute(f"UPDATE memory_entries SET {sql} WHERE id = ?", values)
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def delete_memory_entry(memory_id):
    timestamp = now_ms()
    with connect() as conn:
        row = conn.execute("SELECT * FROM memory_entries WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            return None
        story_id = row["story_id"]
        conn.execute("DELETE FROM memory_entries WHERE id = ?", (memory_id,))
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def add_lore_entry(story_id, title, content, entry_type="note"):
    timestamp = now_ms()
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not exists:
            return None
        conn.execute(
            "INSERT INTO lore_entries VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id("lore"), story_id, title or "Entrada de lore", content or "", entry_type or "note", timestamp, timestamp),
        )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def update_lore_entry(lore_id, payload):
    timestamp = now_ms()
    fields = ["title", "content", "entry_type"]
    updates = [field for field in fields if field in payload]
    with connect() as conn:
        row = conn.execute("SELECT * FROM lore_entries WHERE id = ?", (lore_id,)).fetchone()
        if not row:
            return None
        story_id = row["story_id"]
        if updates:
            sql = ", ".join([f"{field} = ?" for field in updates] + ["updated_at = ?"])
            values = [payload[field] for field in updates] + [timestamp, lore_id]
            conn.execute(f"UPDATE lore_entries SET {sql} WHERE id = ?", values)
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def delete_lore_entry(lore_id):
    timestamp = now_ms()
    with connect() as conn:
        row = conn.execute("SELECT * FROM lore_entries WHERE id = ?", (lore_id,)).fetchone()
        if not row:
            return None
        story_id = row["story_id"]
        conn.execute("DELETE FROM lore_entries WHERE id = ?", (lore_id,))
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def seed_visual_styles(conn):
    count = conn.execute("SELECT COUNT(*) FROM visual_styles").fetchone()[0]
    if count:
        return
    timestamp = now_ms()
    for item in DEFAULT_VISUAL_STYLES:
        conn.execute(
            """
            INSERT INTO visual_styles (
                id, name, prompt_prefix, prompt_suffix, negative_prompt,
                sprite_workbench, background_workbench, background_prompt_prefix,
                background_prompt_suffix, background_negative_prompt, background_settings,
                sprite_prompt_command, sprite_prompt_example, background_prompt_command,
                background_prompt_example, appearance_workbench, appearance_prompt_command, appearance_prompt_example,
                appearance_reference_workbench, appearance_reference_prompt_command, appearance_reference_prompt_example,
                expressions_enabled, expression_prompts_visible, expression_workbench,
                expression_prompts, cover_path, advanced_settings, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("style"),
                item.get("name") or "Estilo",
                item.get("prompt_prefix") or "",
                item.get("prompt_suffix") or "",
                item.get("negative_prompt") or "",
                item.get("sprite_workbench") or "",
                item.get("background_workbench") or "",
                item.get("background_prompt_prefix") or "",
                item.get("background_prompt_suffix") or "",
                item.get("background_negative_prompt") or "",
                json.dumps(item.get("background_settings") or {}, ensure_ascii=False),
                item.get("sprite_prompt_command") or "",
                item.get("sprite_prompt_example") or "",
                item.get("background_prompt_command") or "",
                item.get("background_prompt_example") or "",
                item.get("appearance_workbench") or "",
                item.get("appearance_prompt_command") or "",
                item.get("appearance_prompt_example") or "",
                item.get("appearance_reference_workbench") or "",
                item.get("appearance_reference_prompt_command") or "",
                item.get("appearance_reference_prompt_example") or "",
                1 if item.get("expressions_enabled") else 0,
                1 if item.get("expression_prompts_visible") else 0,
                item.get("expression_workbench") or "",
                json.dumps(normalize_expression_prompts(item.get("expression_prompts") or {}), ensure_ascii=False),
                item.get("cover_path") or "",
                json.dumps(item.get("advanced_settings") or {}, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )


def backfill_visual_style_backgrounds(conn):
    defaults = {item.get("name"): item for item in DEFAULT_VISUAL_STYLES}
    timestamp = now_ms()
    rows = conn.execute("SELECT * FROM visual_styles").fetchall()
    for row in rows:
        item = defaults.get(row["name"])
        if not item:
            continue
        updates = {}
        for field in [
            "background_workbench",
            "background_prompt_prefix",
            "background_prompt_suffix",
            "background_negative_prompt",
        ]:
            if not row[field] and item.get(field):
                updates[field] = item.get(field)
        current_settings = json_load(row["background_settings"], {})
        if not current_settings and item.get("background_settings"):
            updates["background_settings"] = json.dumps(item.get("background_settings") or {}, ensure_ascii=False)
        if not updates:
            continue
        sql = ", ".join([f"{field} = ?" for field in updates] + ["updated_at = ?"])
        conn.execute(
            f"UPDATE visual_styles SET {sql} WHERE id = ?",
            [*updates.values(), timestamp, row["id"]],
        )


LEGACY_BACKGROUND_POSITIVE_NOISE = [
    "empty visual novel background",
    "empty environment",
    "unique memorable landmark",
    "environment details tied to the current story conflict",
    "specific props and visual clues",
    "specific architecture and spatial layout",
    "distinct foreground, midground, and background depth",
    "layered foreground, midground, and background depth",
    "detailed architecture, props, materials, lighting, atmosphere, and color palette",
    "wide establishing shot",
    "environment-focused composition",
    "detailed environment art",
    "environmental storytelling objects",
    "environmental storytelling",
    "moody environmental storytelling",
    "still background plate with no moving subjects",
    "detailed static background plate",
    "static empty scene composition",
    "layered foreground midground background",
    "clear material textures",
    "cinematic atmospheric lighting",
    "cinematic lighting",
    "cohesive color palette",
    "high detail environment concept art",
    "high detail polished anime visual novel background art",
    "polished anime visual novel background art",
    "polished anime background art",
    "polished anime background",
    "polished background art",
    "high detail",
    "no people",
    "no characters",
    "no humans",
    "no faces",
    "no bodies",
    "no silhouettes",
    "no crowd",
    "no human action",
    "no text",
    "no UI",
]

LEGACY_BACKGROUND_SUFFIX_VALUES = {
    "wide establishing shot, detailed environment art, layered foreground midground background, polished anime background",
    "atmospheric fantasy lighting, rich architecture, visible props, detailed materials, polished background art",
    "clean cel shading, nostalgic 1990s anime color design, detailed static background plate",
    "film lighting, realistic materials, deep composition, high detail environment concept art",
    "strong inked shadows, dramatic contrast, moody environmental storytelling, detailed background art",
    "strong inked shadows, dramatic contrast, visible props, detailed materials, moody background art",
}

def cleanup_visual_style_background_prompts(conn):
    timestamp = now_ms()
    rows = conn.execute(
        "SELECT id, background_prompt_prefix, background_prompt_suffix FROM visual_styles"
    ).fetchall()
    for row in rows:
        cleaned_prefix = clean_legacy_background_positive(row["background_prompt_prefix"])
        cleaned_suffix = clean_legacy_background_positive(row["background_prompt_suffix"])
        updates = {}
        if cleaned_prefix != (row["background_prompt_prefix"] or ""):
            updates["background_prompt_prefix"] = cleaned_prefix
        if cleaned_suffix != (row["background_prompt_suffix"] or ""):
            updates["background_prompt_suffix"] = cleaned_suffix
        if not updates:
            continue
        sql = ", ".join([f"{field} = ?" for field in updates] + ["updated_at = ?"])
        conn.execute(
            f"UPDATE visual_styles SET {sql} WHERE id = ?",
            [*updates.values(), timestamp, row["id"]],
        )


def clean_legacy_background_positive(value):
    result = str(value or "").strip()
    if not result:
        return ""
    if result.lower() in {item.lower() for item in LEGACY_BACKGROUND_SUFFIX_VALUES}:
        return ""
    for phrase in LEGACY_BACKGROUND_POSITIVE_NOISE:
        result = re.sub(rf"\s*,?\s*{re.escape(phrase)}\s*,?", ", ", result, flags=re.I)
    result = re.sub(r"\s*,\s*,+", ", ", result)
    result = re.sub(r"^\s*,\s*|\s*,\s*$", "", result)
    return " ".join(result.split())


def list_visual_styles():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM visual_styles
            ORDER BY
                CASE name
                    WHEN 'Anime VN' THEN 0
                    WHEN 'Fantasia painterly' THEN 1
                    WHEN 'Anime retro' THEN 2
                    WHEN 'Cinematico realista' THEN 3
                    WHEN 'Quadrinhos escuro' THEN 4
                    ELSE 10
                END,
                created_at,
                name COLLATE NOCASE
            """
        ).fetchall()
    return [serialize_visual_style(row) for row in rows]


def get_visual_style(style_id):
    if not style_id:
        return None
    with connect() as conn:
        row = conn.execute("SELECT * FROM visual_styles WHERE id = ?", (style_id,)).fetchone()
    return serialize_visual_style(row)


def create_visual_style(payload):
    timestamp = now_ms()
    style_id = new_id("style")
    data = normalize_visual_style_payload(payload)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO visual_styles (
                id, name, prompt_prefix, prompt_suffix, negative_prompt,
                sprite_workbench, background_workbench, background_prompt_prefix,
                background_prompt_suffix, background_negative_prompt, background_settings,
                sprite_prompt_command, sprite_prompt_example, background_prompt_command,
                background_prompt_example, appearance_workbench, appearance_prompt_command, appearance_prompt_example,
                appearance_reference_workbench, appearance_reference_prompt_command, appearance_reference_prompt_example,
                expressions_enabled, expression_prompts_visible, expression_workbench,
                expression_prompts, cover_path, advanced_settings, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                style_id,
                data["name"],
                data["prompt_prefix"],
                data["prompt_suffix"],
                data["negative_prompt"],
                data["sprite_workbench"],
                data["background_workbench"],
                data["background_prompt_prefix"],
                data["background_prompt_suffix"],
                data["background_negative_prompt"],
                json.dumps(data["background_settings"], ensure_ascii=False),
                data["sprite_prompt_command"],
                data["sprite_prompt_example"],
                data["background_prompt_command"],
                data["background_prompt_example"],
                data["appearance_workbench"],
                data["appearance_prompt_command"],
                data["appearance_prompt_example"],
                data["appearance_reference_workbench"],
                data["appearance_reference_prompt_command"],
                data["appearance_reference_prompt_example"],
                1 if data["expressions_enabled"] else 0,
                1 if data["expression_prompts_visible"] else 0,
                data["expression_workbench"],
                json.dumps(data["expression_prompts"], ensure_ascii=False),
                data["cover_path"],
                json.dumps(data["advanced_settings"], ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
    return get_visual_style(style_id)


def update_visual_style(style_id, payload):
    data = normalize_visual_style_payload(payload, partial=True)
    fields = [
        "name",
        "prompt_prefix",
        "prompt_suffix",
        "negative_prompt",
        "sprite_workbench",
        "background_workbench",
        "background_prompt_prefix",
        "background_prompt_suffix",
        "background_negative_prompt",
        "background_settings",
        "sprite_prompt_command",
        "sprite_prompt_example",
        "background_prompt_command",
        "background_prompt_example",
        "appearance_workbench",
        "appearance_prompt_command",
        "appearance_prompt_example",
        "appearance_reference_workbench",
        "appearance_reference_prompt_command",
        "appearance_reference_prompt_example",
        "expressions_enabled",
        "expression_prompts_visible",
        "expression_workbench",
        "expression_prompts",
        "cover_path",
        "advanced_settings",
    ]
    updates = [field for field in fields if field in data]
    if not updates:
        return get_visual_style(style_id)
    timestamp = now_ms()
    sql = ", ".join([f"{field} = ?" for field in updates] + ["updated_at = ?"])
    values = [
        json.dumps(data[field], ensure_ascii=False) if field in {"advanced_settings", "background_settings", "expression_prompts"} else (1 if data[field] else 0) if field in {"expressions_enabled", "expression_prompts_visible"} else data[field]
        for field in updates
    ] + [timestamp, style_id]
    with connect() as conn:
        conn.execute(f"UPDATE visual_styles SET {sql} WHERE id = ?", values)
    return get_visual_style(style_id)


def delete_visual_style(style_id):
    style = get_visual_style(style_id)
    if not style:
        return None
    with connect() as conn:
        conn.execute("UPDATE stories SET visual_style_id = NULL WHERE visual_style_id = ?", (style_id,))
        conn.execute("DELETE FROM visual_styles WHERE id = ?", (style_id,))
    return style


def visual_style_for_story(story_id):
    if not story_id:
        return None
    with connect() as conn:
        story = conn.execute("SELECT visual_style_id FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not story or not story["visual_style_id"]:
            return None
        row = conn.execute("SELECT * FROM visual_styles WHERE id = ?", (story["visual_style_id"],)).fetchone()
    return serialize_visual_style(row)


def normalize_visual_style_payload(payload, partial=False):
    payload = payload or {}
    data = {}
    text_fields = [
        "name",
        "prompt_prefix",
        "prompt_suffix",
        "negative_prompt",
        "sprite_workbench",
        "background_workbench",
        "background_prompt_prefix",
        "background_prompt_suffix",
        "background_negative_prompt",
        "sprite_prompt_command",
        "sprite_prompt_example",
        "background_prompt_command",
        "background_prompt_example",
        "appearance_workbench",
        "appearance_prompt_command",
        "appearance_prompt_example",
        "appearance_reference_workbench",
        "appearance_reference_prompt_command",
        "appearance_reference_prompt_example",
        "cover_path",
        "expression_workbench",
    ]
    for field in text_fields:
        if field in payload:
            data[field] = str(payload.get(field) or "").strip()
    for field in ["expressions_enabled", "expression_prompts_visible"]:
        if field in payload:
            data[field] = bool(payload.get(field))
    if not partial or "name" in data:
        data["name"] = data.get("name") or "Novo estilo"
    if "advanced_settings" in payload:
        settings = payload.get("advanced_settings")
        data["advanced_settings"] = settings if isinstance(settings, dict) else {}
    elif not partial:
        data["advanced_settings"] = {}
    if "background_settings" in payload:
        settings = payload.get("background_settings")
        data["background_settings"] = settings if isinstance(settings, dict) else {}
    elif not partial:
        data["background_settings"] = {}
    if "expression_prompts" in payload:
        data["expression_prompts"] = normalize_expression_prompts(payload.get("expression_prompts"))
    elif not partial:
        data["expression_prompts"] = {}
    if not partial:
        for field in text_fields:
            data.setdefault(field, "")
        data.setdefault("expressions_enabled", False)
        data.setdefault("expression_prompts_visible", False)
    return data


def normalize_expression(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in OFFICIAL_EXPRESSIONS else "neutral"


def normalize_expression_prompts(value):
    source = value if isinstance(value, dict) else {}
    result = {}
    for expression in EXPRESSION_PROMPT_KEYS:
        prompts = source.get(expression) or []
        if isinstance(prompts, str):
            prompts = [prompts]
        clean_prompts = []
        for index, item in enumerate(prompts):
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("prompt") or "").strip()
                prompt_id = str(item.get("id") or "").strip()
            else:
                text = str(item or "").strip()
                prompt_id = ""
            if not text:
                continue
            clean_prompts.append({
                "id": prompt_id or f"{expression}_{index + 1}",
                "text": text,
            })
        result[expression] = clean_prompts
    return result


def update_scene(scene_id, payload):
    timestamp = now_ms()
    scalar_fields = ["title", "scene_text", "background_prompt", "user_input"]
    json_fields = ["dialogues", "choices", "characters_on_screen", "memory_updates", "raw_ai_response"]
    updates = []
    values = []

    with connect() as conn:
        row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if not row:
            return None
        story_id = row["story_id"]

        for field in scalar_fields:
            if field in payload:
                updates.append(f"{field} = ?")
                values.append(payload[field] or "")
        for field in json_fields:
            if field in payload:
                updates.append(f"{field} = ?")
                values.append(json.dumps(payload[field] or ([] if field != "memory_updates" else {}), ensure_ascii=False))

        if updates:
            values.append(scene_id)
            conn.execute(f"UPDATE scenes SET {', '.join(updates)} WHERE id = ?", values)

        if "choices" in payload:
            conn.execute("DELETE FROM choices WHERE scene_id = ?", (scene_id,))
            for choice in payload.get("choices") or []:
                conn.execute(
                    "INSERT INTO choices VALUES (?, ?, ?, ?, 0, ?)",
                    (new_id("choice"), story_id, scene_id, str(choice), timestamp),
                )

        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def duplicate_story(story_id):
    timestamp = now_ms()
    new_story_id = new_id("story")
    character_map = {}
    appearance_map = {}
    scene_map = {}
    asset_map = {}
    scene_backgrounds = {}

    with connect() as conn:
        story = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not story:
            return None

        conn.execute(
            """
            INSERT INTO stories (
                id, title, genre, tone, visual_style, participation_mode, content_rating, language,
                visual_style_id, status, lore, player_character, summary, current_scene_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, NULL, ?, ?)
            """,
            (
                new_story_id,
                f"Copia de {story['title']}",
                story["genre"],
                story["tone"],
                story["visual_style"],
                normalize_participation_mode(story["participation_mode"] if "participation_mode" in story.keys() else ""),
                story["content_rating"],
                story["language"],
                story["visual_style_id"],
                story["lore"],
                story["player_character"],
                story["summary"],
                timestamp,
                timestamp,
            ),
        )

        for row in conn.execute("SELECT * FROM characters WHERE story_id = ?", (story_id,)).fetchall():
            new_character_id = new_id("char")
            character_map[row["id"]] = new_character_id
            conn.execute(
                """
                INSERT INTO characters (
                    id, story_id, name, species, gender, character_type, aliases, description,
                    physical, personality, clothing, role, relationship, secrets, speech_style,
                    visual_prompt, expression_prompts, active_appearance_id, status, importance, is_player, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    new_character_id,
                    new_story_id,
                    row["name"],
                    row["species"],
                    row["gender"],
                    row["character_type"],
                    row["aliases"],
                    row["description"],
                    row["physical"],
                    row["personality"],
                    row["clothing"],
                    row["role"],
                    row["relationship"],
                    row["secrets"],
                    row["speech_style"],
                    row["visual_prompt"],
                    row["expression_prompts"] if "expression_prompts" in row.keys() else "{}",
                    row["status"],
                    row["importance"],
                    row["is_player"],
                    timestamp,
                    timestamp,
                ),
            )

        for row in conn.execute(
            "SELECT * FROM scenes WHERE story_id = ? ORDER BY scene_order",
            (story_id,),
        ).fetchall():
            new_scene_id = new_id("scene")
            scene_map[row["id"]] = new_scene_id
            scene_backgrounds[row["id"]] = row["background_asset_id"]
            conn.execute(
                """
                INSERT INTO scenes (
                    id, story_id, scene_order, title, scene_text, dialogues, choices,
                    characters_on_screen, background_prompt, background_asset_id,
                    memory_updates, raw_ai_response, user_input, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (
                    new_scene_id,
                    new_story_id,
                    row["scene_order"],
                    row["title"],
                    row["scene_text"],
                    row["dialogues"],
                    row["choices"],
                    row["characters_on_screen"],
                    row["background_prompt"],
                    row["memory_updates"],
                    row["raw_ai_response"],
                    row["user_input"],
                    timestamp,
                ),
            )

        for row in conn.execute("SELECT * FROM memory_entries WHERE story_id = ?", (story_id,)).fetchall():
            conn.execute(
                "INSERT INTO memory_entries VALUES (?, ?, ?, ?, ?, ?)",
                (new_id("mem"), new_story_id, row["entry_type"], row["content"], row["importance"], timestamp),
            )

        for row in conn.execute("SELECT * FROM lore_entries WHERE story_id = ?", (story_id,)).fetchall():
            conn.execute(
                "INSERT INTO lore_entries VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id("lore"), new_story_id, row["title"], row["content"], row["entry_type"], timestamp, timestamp),
            )

        for row in conn.execute("SELECT * FROM choices WHERE story_id = ?", (story_id,)).fetchall():
            new_scene_id = scene_map.get(row["scene_id"])
            if not new_scene_id:
                continue
            conn.execute(
                "INSERT INTO choices VALUES (?, ?, ?, ?, ?, ?)",
                (new_id("choice"), new_story_id, new_scene_id, row["choice_text"], row["chosen"], timestamp),
            )

        create_story_dirs(new_story_id)
        for row in conn.execute("SELECT * FROM generated_assets WHERE story_id = ?", (story_id,)).fetchall():
            new_asset_id = new_id("asset")
            new_character_id = character_map.get(row["character_id"])
            new_scene_id = scene_map.get(row["scene_id"])
            new_file_path = duplicate_asset_file(
                row["file_path"],
                new_story_id,
                new_asset_id,
                row["asset_type"],
                new_character_id,
                row["expression"],
            )
            asset_map[row["id"]] = new_asset_id
            conn.execute(
                """
                INSERT INTO generated_assets (
                    id, story_id, character_id, scene_id, appearance_id, asset_type, base_asset_id, expression, prompt,
                    negative_prompt, file_path, remote_ref, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_asset_id,
                    new_story_id,
                    new_character_id,
                    new_scene_id,
                    row["appearance_id"] if "appearance_id" in row.keys() else "",
                    row["asset_type"],
                    row["base_asset_id"] if "base_asset_id" in row.keys() else "",
                    row["expression"],
                    row["prompt"],
                    row["negative_prompt"],
                    new_file_path,
                    row["remote_ref"],
                    row["metadata"],
                    timestamp,
                ),
            )

        for row in conn.execute(
            """
            SELECT ca.* FROM character_appearances ca
            JOIN characters c ON c.id = ca.character_id
            WHERE c.story_id = ?
            ORDER BY ca.created_at ASC
            """,
            (story_id,),
        ).fetchall():
            new_character_id = character_map.get(row["character_id"])
            if not new_character_id:
                continue
            new_appearance_id = new_id("appearance")
            appearance_map[row["id"]] = new_appearance_id
            conn.execute(
                """
                INSERT INTO character_appearances (
                    id, character_id, label, primary_asset_id, neutral_asset_id, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_appearance_id,
                    new_character_id,
                    row["label"],
                    asset_map.get(row["primary_asset_id"], ""),
                    asset_map.get(row["neutral_asset_id"], ""),
                    row["is_active"],
                    timestamp,
                    timestamp,
                ),
            )
            if row["is_active"]:
                conn.execute(
                    "UPDATE characters SET active_appearance_id = ? WHERE id = ?",
                    (new_appearance_id, new_character_id),
                )

        for old_scene_id, old_asset_id in scene_backgrounds.items():
            if old_asset_id and old_asset_id in asset_map:
                conn.execute(
                    "UPDATE scenes SET background_asset_id = ? WHERE id = ?",
                    (asset_map[old_asset_id], scene_map[old_scene_id]),
                )

        for old_asset_id, new_asset_id in asset_map.items():
            old_row = conn.execute("SELECT base_asset_id FROM generated_assets WHERE id = ?", (old_asset_id,)).fetchone()
            old_base_id = old_row["base_asset_id"] if old_row and "base_asset_id" in old_row.keys() else ""
            if old_base_id and old_base_id in asset_map:
                conn.execute(
                    "UPDATE generated_assets SET base_asset_id = ? WHERE id = ?",
                    (asset_map[old_base_id], new_asset_id),
                )
            elif old_base_id == old_asset_id:
                conn.execute(
                    "UPDATE generated_assets SET base_asset_id = ? WHERE id = ?",
                    (new_asset_id, new_asset_id),
                )
        for old_appearance_id, new_appearance_id in appearance_map.items():
            conn.execute(
                "UPDATE generated_assets SET appearance_id = ? WHERE story_id = ? AND appearance_id = ?",
                (new_appearance_id, new_story_id, old_appearance_id),
            )

        for row in conn.execute("SELECT * FROM story_scenarios WHERE story_id = ?", (story_id,)).fetchall():
            conn.execute(
                """
                INSERT INTO story_scenarios (
                    id, story_id, name, description, prompt, enhanced_prompt,
                    asset_id, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("scenario"), new_story_id, row["name"], row["description"], row["prompt"],
                    row["enhanced_prompt"], asset_map.get(row["asset_id"], ""), row["is_active"], timestamp, timestamp,
                ),
            )

        current_scene_id = scene_map.get(story["current_scene_id"])
        if current_scene_id:
            conn.execute(
                "UPDATE stories SET current_scene_id = ? WHERE id = ?",
                (current_scene_id, new_story_id),
            )

    return get_story(new_story_id)


def duplicate_asset_file(file_path, new_story_id, new_asset_id, asset_type, character_id, expression):
    if not file_path:
        return ""
    source = (ROOT_DIR / file_path).resolve()
    data_root = DATA_DIR.resolve()
    if not str(source).startswith(str(data_root)) or not source.exists() or not source.is_file():
        return ""

    extension = source.suffix or ".png"
    if asset_type == "background":
        target = STORIES_DIR / new_story_id / "backgrounds" / f"{new_asset_id}{extension}"
    elif asset_type == "sprite":
        safe_expression = sanitize_path_component(expression or "neutral")
        target = STORIES_DIR / new_story_id / "characters" / (character_id or "unknown") / f"{safe_expression}_{new_asset_id}{extension}"
    else:
        target = STORIES_DIR / new_story_id / "metadata" / f"{new_asset_id}{extension}"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    except OSError:
        return ""
    return target.relative_to(ROOT_DIR).as_posix()


def sanitize_path_component(value, fallback="asset"):
    text = str(value or "").strip()
    text = re.sub(r'[<>:"/\\\\|?*]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = text.replace(" ", "_")
    text = re.sub(r"_+", "_", text)
    return text or fallback


def get_story(story_id):
    ensure_appearances_for_story(story_id)
    with connect() as conn:
        story = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not story:
            return None
        ensure_character_ai_summaries(conn, story_id)
        characters = conn.execute(
            "SELECT * FROM characters WHERE story_id = ? ORDER BY is_player DESC, name",
            (story_id,),
        ).fetchall()
        scenes = conn.execute(
            "SELECT * FROM scenes WHERE story_id = ? ORDER BY scene_order",
            (story_id,),
        ).fetchall()
        memory = conn.execute(
            "SELECT * FROM memory_entries WHERE story_id = ? ORDER BY created_at DESC LIMIT 80",
            (story_id,),
        ).fetchall()
        lore = conn.execute(
            "SELECT * FROM lore_entries WHERE story_id = ? ORDER BY updated_at DESC",
            (story_id,),
        ).fetchall()
        assets = conn.execute(
            "SELECT * FROM generated_assets WHERE story_id = ? ORDER BY created_at DESC",
            (story_id,),
        ).fetchall()
        appearances = conn.execute(
            """
            SELECT ca.* FROM character_appearances ca
            JOIN characters c ON c.id = ca.character_id
            WHERE c.story_id = ?
            ORDER BY ca.created_at DESC
            """,
            (story_id,),
        ).fetchall()
        scenarios = conn.execute(
            "SELECT * FROM story_scenarios WHERE story_id = ? ORDER BY is_active DESC, updated_at DESC, name COLLATE NOCASE",
            (story_id,),
        ).fetchall()
        style = None
        if story["visual_style_id"]:
            style = conn.execute("SELECT * FROM visual_styles WHERE id = ?", (story["visual_style_id"],)).fetchone()
    data = serialize_story(story)
    data["visual_style_record"] = serialize_visual_style(style)
    data["characters"] = [serialize_character(row) for row in characters]
    data["scenes"] = [serialize_scene(row) for row in scenes]
    data["memory_entries"] = [row_to_dict(row) for row in memory]
    data["lore_entries"] = [row_to_dict(row) for row in lore]
    data["assets"] = [serialize_asset(row) for row in assets]
    data["appearances"] = [serialize_appearance(row) for row in appearances]
    data["scenarios"] = [serialize_story_scenario(row, assets) for row in scenarios]
    return data


def story_before_latest_scene_for_regeneration(story_id):
    story = get_story(story_id)
    if not story:
        raise ValueError("Historia nao encontrada.")
    scenes = story.get("scenes") or []
    if len(scenes) <= 1:
        raise ValueError("Nao ha cena anterior para regenerar a cena atual.")
    current_scene = scenes[-1]
    previous_scene = scenes[-2]
    snapshot = copy.deepcopy(story)
    snapshot["scenes"] = copy.deepcopy(scenes[:-1])
    snapshot["current_scene_id"] = previous_scene.get("id")
    snapshot["summary"] = previous_scene_summary(snapshot, previous_scene)
    snapshot["memory_entries"] = filtered_memory_before_regenerated_scene(
        snapshot.get("memory_entries") or [],
        current_scene,
    )
    return snapshot, current_scene


def previous_scene_summary(story, previous_scene):
    memory_updates = previous_scene.get("memory_updates") or {}
    if isinstance(memory_updates, dict) and memory_updates.get("summary"):
        return memory_updates.get("summary")
    for entry in story.get("memory_entries") or []:
        if entry.get("entry_type") == "summary" and entry.get("content"):
            return entry.get("content")
    return story.get("summary") or ""


def filtered_memory_before_regenerated_scene(memory_entries, current_scene):
    scene_created_at = int(current_scene.get("created_at") or 0)
    scene_updates = current_scene.get("memory_updates") or {}
    summary = str(scene_updates.get("summary") or "") if isinstance(scene_updates, dict) else ""
    facts = {str(fact) for fact in (scene_updates.get("facts") or [])} if isinstance(scene_updates, dict) else set()
    filtered = []
    for entry in memory_entries or []:
        created_at = int(entry.get("created_at") or 0)
        entry_type = entry.get("entry_type") or ""
        content = str(entry.get("content") or "")
        if scene_created_at and created_at >= scene_created_at and entry_type == "summary" and summary and content == summary:
            continue
        if scene_created_at and created_at >= scene_created_at and entry_type == "fact" and content in facts:
            continue
        filtered.append(entry)
    return filtered


def create_story(payload):
    timestamp = now_ms()
    story_id = new_id("story")
    participation_mode = normalize_participation_mode(payload.get("participation_mode") or payload.get("point_of_view"))
    payload["participation_mode"] = participation_mode
    player = payload.get("player_character") or {}
    lore = payload.get("lore") or ""
    starting_message = payload.get("starting_message") or ""
    if participation_mode == "first_person" and isinstance(player, dict):
        player["visual_prompt"] = ""
    if isinstance(player, dict) and player.get("name"):
        player = normalize_character_ai_summaries(player)
        payload["player_character"] = player
    payload["characters"] = [
        normalize_character_ai_summaries(character)
        for character in payload.get("characters") or []
        if isinstance(character, dict)
    ]

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO stories (
                id, title, genre, tone, visual_style, participation_mode, content_rating, language,
                visual_style_id, status, lore, player_character, summary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (
                story_id,
                payload.get("title") or "Historia sem titulo",
                payload.get("genre") or "",
                payload.get("tone") or "",
                payload.get("visual_style") or "",
                participation_mode,
                payload.get("content_rating") or "",
                payload.get("language") or "pt-BR",
                payload.get("visual_style_id") or "",
                lore,
                json.dumps(player, ensure_ascii=False),
                "A historia ainda esta no inicio.",
                timestamp,
                timestamp,
            ),
        )
        if lore:
            conn.execute(
                "INSERT INTO lore_entries VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id("lore"), story_id, "Lore inicial", lore, "world", timestamp, timestamp),
            )
        if player.get("name"):
            if participation_mode == "narrator":
                insert_character(conn, story_id, player, is_player=False, importance="main")
            else:
                insert_character(conn, story_id, player, is_player=True, importance="player")
        for character in payload.get("characters") or []:
            if character.get("name"):
                insert_character(conn, story_id, character, is_player=False, importance="main")
        conn.execute(
            "INSERT INTO memory_entries VALUES (?, ?, 'summary', ?, 5, ?)",
            (
                new_id("mem"),
                story_id,
                "A historia foi criada com uma primeira cena definida." if starting_message else "A historia foi criada e aguarda a primeira cena.",
                timestamp,
            ),
        )
    create_story_dirs(story_id)
    if starting_message:
        add_scene(story_id, build_initial_scene(payload))
    return get_story(story_id)


def build_initial_scene(payload):
    participation_mode = normalize_participation_mode(payload.get("participation_mode") or payload.get("point_of_view"))
    player = payload.get("player_character") or {}
    characters = [player, *(payload.get("characters") or [])]
    visual_characters = characters[1:] if participation_mode == "first_person" else characters
    starting_message = payload.get("starting_message") or ""
    starting_location = payload.get("starting_location") or ""
    present = detect_initial_characters(visual_characters, starting_message)
    if not present and player.get("name") and participation_mode != "first_person":
        present = [player]
    return {
        "title": starting_location or "Primeira cena",
        "scene_text": starting_message,
        "dialogues": [{"character": "Narrador", "expression": "neutral", "text": starting_message}],
        "choices": initial_choices_for_mode(participation_mode),
        "characters_on_screen": [
            {"name": character.get("name"), "position": position_for_index(index, len(present)), "expression": "neutral"}
            for index, character in enumerate(present[:4])
            if character.get("name")
        ],
        "background_prompt": build_initial_background_prompt(payload),
        "memory_updates": {
            "summary": compact_text(starting_message, 420),
            "facts": ([f"Local inicial: {starting_location}"] if starting_location else []) + [f"Modo de participacao: {participation_mode}."],
        },
        "raw_ai_response": {
            "location": starting_location,
            "location_changed": True,
            "new_characters_detected": [],
        },
        "user_input": "Mensagem inicial da historia",
    }


def initial_choices_for_mode(participation_mode):
    if participation_mode == "narrator":
        return ["Aprofundar o conflito central", "Mudar o foco para outro personagem", "Criar uma consequencia imediata"]
    if participation_mode == "third_person":
        return ["Fazer o protagonista observar o ambiente", "Fazer o protagonista falar com alguem presente", "Fazer o protagonista avancar com cautela"]
    return ["Observar o ambiente", "Falar com alguem presente", "Avancar com cautela"]


def detect_initial_characters(characters, text):
    lowered = (text or "").lower()
    detected = []
    for character in characters:
        name = str(character.get("name") or "")
        aliases = str(character.get("aliases") or "")
        names = [name, *[alias.strip() for alias in aliases.split(",")]]
        if any(item and item.lower() in lowered for item in names):
            detected.append(character)
    return detected


def position_for_index(index, total):
    if total <= 1:
        return "center"
    if total == 2:
        return ["left", "right"][index]
    return ["left", "center", "right", "center"][index]


def build_initial_background_prompt(payload):
    parts = [
        payload.get("starting_location") or "",
        compact_text(payload.get("starting_message") or "", 260),
        "concrete environment description",
        "spatial layout",
        "foreground, midground, and background depth",
        "visible props, materials, lighting, atmosphere, and color palette",
    ]
    return ", ".join(part for part in parts if part)


def compact_text(value, limit):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def compact_ai_summary(value, limit=110, fallback=""):
    text = " ".join(str(value or fallback or "").replace("\r", " ").split())
    if not text:
        return ""
    if len(text) <= limit:
        return text.rstrip(" .") + "."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    first_sentence = next((sentence.strip() for sentence in sentences if sentence.strip()), "")
    if first_sentence and len(first_sentence) <= limit + 45:
        return first_sentence.rstrip(" .") + "."
    selected = []
    length = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        extra = len(sentence) + (1 if selected else 0)
        if selected and length + extra > limit:
            break
        if not selected and len(sentence) > limit:
            break
        selected.append(sentence)
        length += extra
    if selected:
        return " ".join(selected).rstrip(" .") + "."
    fragment = compact_ai_fragment(first_sentence or text, limit)
    if fragment:
        return fragment.rstrip(" .") + "."
    words = text.split()
    selected_words = []
    length = 0
    for word in words:
        extra = len(word) + (1 if selected_words else 0)
        if selected_words and length + extra > limit:
            break
        if not selected_words and extra > limit:
            selected_words.append(word[:limit].rstrip(" ,.;:"))
            break
        selected_words.append(word)
        length += extra
    return " ".join(selected_words).rstrip(" ,.;:") + "."


def compact_ai_fragment(value, limit):
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    candidates = []
    for separator in ["; ", ", ", " que ", " quando ", " enquanto ", " mas ", " e "]:
        if separator in text:
            part = text.split(separator, 1)[0].strip(" ,.;:")
            if 18 <= len(part) <= limit:
                candidates.append(part)
    if candidates:
        return max(candidates, key=len)
    return ""


def build_ai_prompt_brief(data):
    name = " ".join(str((data or {}).get("name") or "Unnamed character").split())
    role = compact_ai_summary((data or {}).get("ai_role_summary"), 80, (data or {}).get("role") or (data or {}).get("character_type") or (data or {}).get("description"))
    personality = compact_ai_summary((data or {}).get("ai_personality_summary"), 90, (data or {}).get("personality") or (data or {}).get("description"))
    voice = compact_ai_summary((data or {}).get("ai_voice_summary"), 90, (data or {}).get("speech_style") or (data or {}).get("voice"))
    return f"{name} | Role: {role} Personality: {personality} Voice: {voice}"


def normalize_character_ai_summaries(data):
    result = dict(data or {})
    result["ai_role_summary"] = compact_ai_summary(
        result.get("ai_role_summary"),
        80,
        result.get("role") or result.get("character_type") or result.get("description"),
    )
    result["ai_personality_summary"] = compact_ai_summary(
        result.get("ai_personality_summary"),
        90,
        result.get("personality") or result.get("description"),
    )
    result["ai_voice_summary"] = compact_ai_summary(
        result.get("ai_voice_summary"),
        90,
        result.get("speech_style") or result.get("voice"),
    )
    result["ai_prompt_brief"] = build_ai_prompt_brief(result)
    return result


def log_api_event(conn, provider, operation, request_payload=None, response_payload=None, status="ok", error="", story_id=None):
    conn.execute(
        """
        INSERT INTO api_logs (
            id, story_id, provider, operation, request_payload, response_payload, status, error, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("log"),
            story_id,
            provider,
            operation,
            json.dumps(request_payload or {}, ensure_ascii=False),
            json.dumps(response_payload or {}, ensure_ascii=False),
            status,
            error,
            now_ms(),
        ),
    )


def ensure_character_ai_summaries(conn, story_id):
    rows = conn.execute(
        """
        SELECT * FROM characters
        WHERE story_id = ?
          AND (
            ai_role_summary IS NULL OR TRIM(ai_role_summary) = ''
            OR ai_personality_summary IS NULL OR TRIM(ai_personality_summary) = ''
            OR ai_voice_summary IS NULL OR TRIM(ai_voice_summary) = ''
            OR ai_prompt_brief IS NULL OR TRIM(ai_prompt_brief) = ''
          )
        """,
        (story_id,),
    ).fetchall()
    for row in rows:
        data = normalize_character_ai_summaries(row_to_dict(row))
        conn.execute(
            """
            UPDATE characters
            SET ai_role_summary = ?, ai_personality_summary = ?, ai_voice_summary = ?,
                ai_prompt_brief = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("ai_role_summary") or "",
                data.get("ai_personality_summary") or "",
                data.get("ai_voice_summary") or "",
                data.get("ai_prompt_brief") or "",
                now_ms(),
                row["id"],
            ),
        )
        log_api_event(
            conn,
            "local",
            "character_ai_summary_missing",
            {"character_id": row["id"], "name": row["name"]},
            {
                "ai_prompt_brief": data.get("ai_prompt_brief") or "",
                "generated_missing_summary": True,
            },
            story_id=story_id,
        )


def insert_character(conn, story_id, data, is_player=False, importance="secondary"):
    timestamp = now_ms()
    character_id = new_id("char")
    data = normalize_character_ai_summaries(data)
    conn.execute(
        """
        INSERT INTO characters (
            id, story_id, name, species, gender, character_type, aliases, description,
            physical, personality, clothing, role, relationship, secrets, speech_style,
            ai_role_summary, ai_personality_summary, ai_voice_summary, ai_prompt_brief,
            visual_prompt, expression_prompts, status, importance, is_player, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
        """,
        (
            character_id,
            story_id,
            data.get("name") or "",
            data.get("species") or "",
            data.get("gender") or "",
            data.get("character_type") or data.get("type") or "",
            data.get("aliases") or "",
            data.get("description") or data.get("background") or "",
            data.get("physical") or data.get("appearance") or "",
            data.get("personality") or "",
            data.get("clothing") or "",
            data.get("role") or "",
            data.get("relationship") or "",
            data.get("secrets") or "",
            data.get("speech_style") or "",
            data.get("ai_role_summary") or "",
            data.get("ai_personality_summary") or "",
            data.get("ai_voice_summary") or "",
            data.get("ai_prompt_brief") or "",
            data.get("visual_prompt") or "",
            json.dumps(normalize_character_expression_prompts(data.get("expression_prompts")), ensure_ascii=False),
            importance,
            1 if is_player else 0,
            timestamp,
            timestamp,
        ),
    )
    return character_id


def create_story_dirs(story_id):
    base = STORIES_DIR / story_id
    for child in ["backgrounds", "characters", "metadata"]:
        (base / child).mkdir(parents=True, exist_ok=True)


def add_scene(story_id, scene):
    timestamp = now_ms()
    with connect() as conn:
        last_order = conn.execute(
            "SELECT COALESCE(MAX(scene_order), 0) FROM scenes WHERE story_id = ?",
            (story_id,),
        ).fetchone()[0]
        scene_id = new_id("scene")
        conn.execute(
            """
            INSERT INTO scenes (
                id, story_id, scene_order, title, scene_text, dialogues, choices,
                characters_on_screen, background_prompt, memory_updates,
                raw_ai_response, user_input, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scene_id,
                story_id,
                last_order + 1,
                scene.get("title") or f"Cena {last_order + 1}",
                scene.get("scene_text") or "",
                json.dumps(scene.get("dialogues") or [], ensure_ascii=False),
                json.dumps(scene.get("choices") or [], ensure_ascii=False),
                json.dumps(scene.get("characters_on_screen") or [], ensure_ascii=False),
                scene.get("background_prompt") or "",
                json.dumps(scene.get("memory_updates") or {}, ensure_ascii=False),
                json.dumps(scene.get("raw_ai_response") or scene, ensure_ascii=False),
                scene.get("user_input") or "",
                timestamp,
            ),
        )
        for choice in scene.get("choices") or []:
            conn.execute(
                "INSERT INTO choices VALUES (?, ?, ?, ?, 0, ?)",
                (new_id("choice"), story_id, scene_id, str(choice), timestamp),
            )
        apply_memory_updates(conn, story_id, scene.get("memory_updates") or {}, timestamp)
        summary = scene.get("memory_updates", {}).get("summary")
        if summary:
            conn.execute(
                "UPDATE stories SET summary = ?, current_scene_id = ?, updated_at = ? WHERE id = ?",
                (summary, scene_id, timestamp, story_id),
            )
        else:
            conn.execute(
                "UPDATE stories SET current_scene_id = ?, updated_at = ? WHERE id = ?",
                (scene_id, timestamp, story_id),
            )
    return get_story(story_id)


def replace_latest_scene(story_id, expected_scene_id, scene, previous_scene=None):
    timestamp = now_ms()
    with connect() as conn:
        current = conn.execute(
            "SELECT * FROM scenes WHERE story_id = ? ORDER BY scene_order DESC LIMIT 1",
            (story_id,),
        ).fetchone()
        if not current:
            raise ValueError("Nenhuma cena encontrada para regenerar.")
        if expected_scene_id and current["id"] != expected_scene_id:
            raise ValueError("A cena atual mudou antes da regeneracao terminar.")
        if int(current["scene_order"] or 0) <= 1:
            raise ValueError("Nao ha cena anterior para regenerar a cena atual.")

        remove_scene_memory_updates(conn, story_id, serialize_scene(current))
        conn.execute("DELETE FROM choices WHERE scene_id = ?", (current["id"],))
        conn.execute(
            "UPDATE generated_assets SET scene_id = '' WHERE scene_id = ? AND asset_type = 'background'",
            (current["id"],),
        )
        conn.execute(
            """
            UPDATE scenes SET
                title = ?,
                scene_text = ?,
                dialogues = ?,
                choices = ?,
                characters_on_screen = ?,
                background_prompt = ?,
                background_asset_id = NULL,
                memory_updates = ?,
                raw_ai_response = ?,
                user_input = ?,
                created_at = ?
            WHERE id = ?
            """,
            (
                scene.get("title") or f"Cena {current['scene_order']}",
                scene.get("scene_text") or "",
                json.dumps(scene.get("dialogues") or [], ensure_ascii=False),
                json.dumps(scene.get("choices") or [], ensure_ascii=False),
                json.dumps(scene.get("characters_on_screen") or [], ensure_ascii=False),
                scene.get("background_prompt") or "",
                json.dumps(scene.get("memory_updates") or {}, ensure_ascii=False),
                json.dumps(scene.get("raw_ai_response") or scene, ensure_ascii=False),
                scene.get("user_input") or "",
                timestamp,
                current["id"],
            ),
        )
        for choice in scene.get("choices") or []:
            conn.execute(
                "INSERT INTO choices VALUES (?, ?, ?, ?, 0, ?)",
                (new_id("choice"), story_id, current["id"], str(choice), timestamp),
            )
        apply_memory_updates(conn, story_id, scene.get("memory_updates") or {}, timestamp)
        summary = scene.get("memory_updates", {}).get("summary")
        if not summary and previous_scene:
            previous_updates = previous_scene.get("memory_updates") or {}
            summary = previous_updates.get("summary") if isinstance(previous_updates, dict) else ""
        conn.execute(
            "UPDATE stories SET summary = COALESCE(NULLIF(?, ''), summary), current_scene_id = ?, updated_at = ? WHERE id = ?",
            (summary or "", current["id"], timestamp, story_id),
        )
    return get_story(story_id)


def remove_scene_memory_updates(conn, story_id, scene):
    updates = scene.get("memory_updates") or {}
    if not isinstance(updates, dict):
        return
    scene_created_at = int(scene.get("created_at") or 0)
    summary = str(updates.get("summary") or "")
    if summary:
        conn.execute(
            """
            DELETE FROM memory_entries
            WHERE story_id = ? AND entry_type = 'summary' AND content = ? AND created_at >= ?
            """,
            (story_id, summary, scene_created_at),
        )
    for fact in updates.get("facts") or []:
        conn.execute(
            """
            DELETE FROM memory_entries
            WHERE story_id = ? AND entry_type = 'fact' AND content = ? AND created_at >= ?
            """,
            (story_id, str(fact), scene_created_at),
        )


def apply_memory_updates(conn, story_id, updates, timestamp):
    summary = updates.get("summary")
    if summary:
        conn.execute(
            "INSERT INTO memory_entries VALUES (?, ?, 'summary', ?, 5, ?)",
            (new_id("mem"), story_id, summary, timestamp),
        )
    for fact in updates.get("facts") or []:
        conn.execute(
            "INSERT INTO memory_entries VALUES (?, ?, 'fact', ?, 3, ?)",
            (new_id("mem"), story_id, str(fact), timestamp),
        )


def create_character(story_id, payload):
    with connect() as conn:
        character_id = insert_character(conn, story_id, payload, False, payload.get("importance") or "secondary")
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (now_ms(), story_id))
    return get_character(character_id)


def get_character(character_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
    return serialize_character(row)


def normalize_character_key(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def delete_character(character_id):
    character = get_character(character_id)
    if not character:
        return None
    story_id = character.get("story_id")
    character_key = normalize_character_key(character.get("name"))
    timestamp = now_ms()
    with connect() as conn:
        asset_rows = conn.execute(
            "SELECT * FROM generated_assets WHERE character_id = ?",
            (character_id,),
        ).fetchall()
        assets = [serialize_asset(row) for row in asset_rows]
        scene_rows = conn.execute(
            "SELECT id, characters_on_screen FROM scenes WHERE story_id = ?",
            (story_id,),
        ).fetchall()
        for row in scene_rows:
            cast = json_load(row["characters_on_screen"], [])
            filtered = [
                item for item in cast
                if normalize_character_key(item.get("name") if isinstance(item, dict) else item) != character_key
            ]
            if filtered != cast:
                conn.execute(
                    "UPDATE scenes SET characters_on_screen = ? WHERE id = ?",
                    (json.dumps(filtered, ensure_ascii=False), row["id"]),
                )
        conn.execute("DELETE FROM generated_assets WHERE character_id = ?", (character_id,))
        conn.execute("DELETE FROM characters WHERE id = ?", (character_id,))
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return {
        "character": character,
        "assets": assets,
        "story": get_story(story_id),
    }


def update_character(character_id, payload):
    timestamp = now_ms()
    current = get_character(character_id) or {}
    fields = [
        "name",
        "species",
        "gender",
        "character_type",
        "aliases",
        "description",
        "physical",
        "personality",
        "clothing",
        "role",
        "relationship",
        "secrets",
        "speech_style",
        "ai_role_summary",
        "ai_personality_summary",
        "ai_voice_summary",
        "ai_prompt_brief",
        "visual_prompt",
        "expression_prompts",
        "status",
        "importance",
    ]
    if any(field in payload for field in ["ai_role_summary", "ai_personality_summary", "ai_voice_summary", "ai_prompt_brief", "name", "role", "character_type", "description", "personality", "speech_style"]):
        payload = normalize_character_ai_summaries({**current, **payload})
    updates = [field for field in fields if field in payload]
    if not updates:
        return get_character(character_id)
    sql = ", ".join([f"{field} = ?" for field in updates] + ["updated_at = ?"])
    values = [
        json.dumps(normalize_character_expression_prompts(payload[field]), ensure_ascii=False)
        if field == "expression_prompts" else payload[field]
        for field in updates
    ] + [timestamp, character_id]
    with connect() as conn:
        conn.execute(f"UPDATE characters SET {sql} WHERE id = ?", values)
        if any(field in updates for field in ["ai_role_summary", "ai_personality_summary", "ai_voice_summary", "ai_prompt_brief"]):
            log_api_event(
                conn,
                "local",
                "character_ai_summary_saved",
                {"character_id": character_id, "fields": updates},
                {
                    "ai_prompt_brief": payload.get("ai_prompt_brief") or "",
                    "ai_role_summary": payload.get("ai_role_summary") or "",
                    "ai_personality_summary": payload.get("ai_personality_summary") or "",
                    "ai_voice_summary": payload.get("ai_voice_summary") or "",
                },
                story_id=current.get("story_id"),
            )
    return get_character(character_id)


def add_asset(story_id, payload):
    timestamp = now_ms()
    asset_id = new_id("asset")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO generated_assets (
                id, story_id, character_id, scene_id, appearance_id, asset_type, base_asset_id, expression, prompt,
                negative_prompt, file_path, remote_ref, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                story_id,
                payload.get("character_id"),
                payload.get("scene_id"),
                payload.get("appearance_id") or "",
                payload.get("asset_type") or "image",
                payload.get("base_asset_id") or "",
                normalize_expression(payload.get("expression")) if (payload.get("asset_type") or "") == "sprite" else (payload.get("expression") or ""),
                payload.get("prompt") or "",
                payload.get("negative_prompt") or "",
                payload.get("file_path") or "",
                payload.get("remote_ref") or "",
                json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
                timestamp,
            ),
        )
    return asset_id


def list_story_references(story_id):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM story_references WHERE story_id = ? ORDER BY created_at DESC",
            (story_id,),
        ).fetchall()
    return [serialize_story_reference(row) for row in rows]


def get_story_reference(reference_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM story_references WHERE id = ?", (reference_id,)).fetchone()
    return serialize_story_reference(row)


def normalize_story_reference_label(value):
    return str(value or "").strip().casefold()


def find_story_reference_by_label(story_id, label):
    target = normalize_story_reference_label(label)
    if not target:
        return None
    with connect() as conn:
        rows = conn.execute("SELECT * FROM story_references WHERE story_id = ?", (story_id,)).fetchall()
        row = next((item for item in rows if normalize_story_reference_label(item["label"]) == target), None)
    return serialize_story_reference(row)


def add_story_reference(story_id, label, file_path):
    reference_id = new_id("reference")
    timestamp = now_ms()
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM stories WHERE id = ?", (story_id,)).fetchone():
            return None
        duplicate = conn.execute("SELECT label FROM story_references WHERE story_id = ?", (story_id,)).fetchall()
        if any(normalize_story_reference_label(row["label"]) == normalize_story_reference_label(label) for row in duplicate):
            raise ValueError("Ja existe uma referencia com esse nome nesta historia.")
        conn.execute(
            "INSERT INTO story_references (id, story_id, label, file_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (reference_id, story_id, str(label or "Referencia").strip(), str(file_path or ""), timestamp),
        )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story_reference(reference_id)


def rename_story_reference(reference_id, label):
    label = str(label or "").strip()
    if not label:
        raise ValueError("O nome da referencia nao pode ficar vazio.")
    timestamp = now_ms()
    with connect() as conn:
        reference = conn.execute("SELECT * FROM story_references WHERE id = ?", (reference_id,)).fetchone()
        if not reference:
            return None
        rows = conn.execute(
            "SELECT id, label FROM story_references WHERE story_id = ? AND id != ?",
            (reference["story_id"], reference_id),
        ).fetchall()
        if any(normalize_story_reference_label(row["label"]) == normalize_story_reference_label(label) for row in rows):
            raise ValueError("Ja existe uma referencia com esse nome nesta historia.")
        conn.execute("UPDATE story_references SET label = ? WHERE id = ?", (label, reference_id))
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, reference["story_id"]))
    return get_story_reference(reference_id)


def delete_story_reference(reference_id):
    reference = get_story_reference(reference_id)
    if not reference:
        return None
    with connect() as conn:
        conn.execute("DELETE FROM story_references WHERE id = ?", (reference_id,))
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (now_ms(), reference["story_id"]))
    return reference


def get_story_scenario(scenario_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM story_scenarios WHERE id = ?", (scenario_id,)).fetchone()
        asset = conn.execute("SELECT * FROM generated_assets WHERE id = ?", (row["asset_id"],)).fetchone() if row and row["asset_id"] else None
    return serialize_story_scenario(row, [asset] if asset else [])


def find_story_scenario_by_name(story_id, name):
    target = normalize_scenario_name(name)
    if not target:
        return None
    with connect() as conn:
        rows = conn.execute("SELECT * FROM story_scenarios WHERE story_id = ?", (story_id,)).fetchall()
        row = next((item for item in rows if normalize_scenario_name(item["name"]) == target), None)
        asset = conn.execute("SELECT * FROM generated_assets WHERE id = ?", (row["asset_id"],)).fetchone() if row and row["asset_id"] else None
    return serialize_story_scenario(row, [asset] if asset else [])


def create_story_scenario(story_id, payload, active=False):
    timestamp = now_ms()
    name = str((payload or {}).get("name") or "").strip()
    if not name:
        return None
    asset_id = str((payload or {}).get("asset_id") or "").strip()
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM stories WHERE id = ?", (story_id,)).fetchone():
            return None
        if asset_id:
            asset = conn.execute(
                "SELECT 1 FROM generated_assets WHERE id = ? AND story_id = ? AND asset_type = 'background'",
                (asset_id, story_id),
            ).fetchone()
            if not asset:
                return None
        if active:
            conn.execute("UPDATE story_scenarios SET is_active = 0 WHERE story_id = ?", (story_id,))
        scenario_id = new_id("scenario")
        conn.execute(
            """
            INSERT INTO story_scenarios (
                id, story_id, name, description, prompt, enhanced_prompt,
                asset_id, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_id, story_id, name,
                str(payload.get("description") or "").strip(),
                str(payload.get("prompt") or "").strip(),
                str(payload.get("enhanced_prompt") or "").strip(),
                asset_id, 1 if active else 0, timestamp, timestamp,
            ),
        )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story_scenario(scenario_id)


def upsert_story_scenario(story_id, name, description, prompt, enhanced_prompt, asset_id, active=True):
    existing = find_story_scenario_by_name(story_id, name)
    if not existing:
        return create_story_scenario(
            story_id,
            {
                "name": name or friendly_scenario_name(description),
                "description": description,
                "prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "asset_id": asset_id,
            },
            active=active,
        )
    timestamp = now_ms()
    with connect() as conn:
        if active:
            conn.execute("UPDATE story_scenarios SET is_active = 0 WHERE story_id = ?", (story_id,))
        conn.execute(
            """
            UPDATE story_scenarios SET
                description = CASE WHEN ? != '' THEN ? ELSE description END,
                prompt = CASE WHEN ? != '' THEN ? ELSE prompt END,
                enhanced_prompt = CASE WHEN ? != '' THEN ? ELSE enhanced_prompt END,
                asset_id = CASE WHEN ? != '' THEN ? ELSE asset_id END,
                is_active = CASE WHEN ? = 1 THEN 1 ELSE is_active END,
                updated_at = ?
            WHERE id = ?
            """,
            (
                description, description, prompt, prompt, enhanced_prompt, enhanced_prompt,
                asset_id, asset_id, 1 if active else 0, timestamp, existing["id"],
            ),
        )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story_scenario(existing["id"])


def activate_story_scenario(story_id, scenario_id):
    timestamp = now_ms()
    with connect() as conn:
        scenario = conn.execute(
            "SELECT * FROM story_scenarios WHERE id = ? AND story_id = ?",
            (scenario_id, story_id),
        ).fetchone()
        if not scenario or not scenario["asset_id"]:
            return None
        asset = conn.execute(
            "SELECT * FROM generated_assets WHERE id = ? AND story_id = ? AND asset_type = 'background' AND file_path != ''",
            (scenario["asset_id"], story_id),
        ).fetchone()
        if not asset:
            return None
        story = conn.execute("SELECT current_scene_id FROM stories WHERE id = ?", (story_id,)).fetchone()
        conn.execute("UPDATE story_scenarios SET is_active = 0 WHERE story_id = ?", (story_id,))
        conn.execute("UPDATE story_scenarios SET is_active = 1, updated_at = ? WHERE id = ?", (timestamp, scenario_id))
        if story and story["current_scene_id"]:
            scene = conn.execute("SELECT raw_ai_response FROM scenes WHERE id = ?", (story["current_scene_id"],)).fetchone()
            raw = json_load(scene["raw_ai_response"], {}) if scene else {}
            raw = raw if isinstance(raw, dict) else {}
            raw["location"] = scenario["name"]
            raw["location_changed"] = True
            background_prompt = scenario["prompt"] or scenario["description"] or ""
            conn.execute(
                "UPDATE scenes SET background_asset_id = ?, background_prompt = ?, raw_ai_response = ? WHERE id = ?",
                (asset["id"], background_prompt, json.dumps(raw, ensure_ascii=False), story["current_scene_id"]),
            )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def replace_story_scenario_asset(story_id, scenario_id, asset_id, prompt, enhanced_prompt):
    timestamp = now_ms()
    with connect() as conn:
        scenario = conn.execute(
            "SELECT * FROM story_scenarios WHERE id = ? AND story_id = ?",
            (scenario_id, story_id),
        ).fetchone()
        asset = conn.execute(
            "SELECT * FROM generated_assets WHERE id = ? AND story_id = ? AND asset_type = 'background' AND file_path != ''",
            (asset_id, story_id),
        ).fetchone()
        if not scenario or not asset:
            return None
        old_asset_id = scenario["asset_id"] or ""
        conn.execute(
            "UPDATE story_scenarios SET asset_id = ?, prompt = ?, enhanced_prompt = ?, updated_at = ? WHERE id = ?",
            (asset_id, prompt or scenario["prompt"], enhanced_prompt or asset["prompt"] or "", timestamp, scenario_id),
        )
        if scenario["is_active"]:
            story = conn.execute("SELECT current_scene_id FROM stories WHERE id = ?", (story_id,)).fetchone()
            if story and story["current_scene_id"]:
                conn.execute(
                    "UPDATE scenes SET background_asset_id = ?, background_prompt = ? WHERE id = ?",
                    (asset_id, prompt or scenario["prompt"] or scenario["description"] or "", story["current_scene_id"]),
                )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return {"story": get_story(story_id), "old_asset_id": old_asset_id}


def delete_story_scenario(story_id, scenario_id):
    scenario = get_story_scenario(scenario_id)
    if not scenario or scenario.get("story_id") != story_id:
        return None
    with connect() as conn:
        conn.execute("DELETE FROM story_scenarios WHERE id = ?", (scenario_id,))
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (now_ms(), story_id))
        scene_refs = conn.execute("SELECT COUNT(*) FROM scenes WHERE background_asset_id = ?", (scenario.get("asset_id") or "",)).fetchone()[0]
        scenario_refs = conn.execute("SELECT COUNT(*) FROM story_scenarios WHERE asset_id = ?", (scenario.get("asset_id") or "",)).fetchone()[0]
    return {"scenario": scenario, "asset_deletable": bool(scenario.get("asset_id") and not scene_refs and not scenario_refs), "story": get_story(story_id)}


def asset_is_referenced(asset_id):
    if not asset_id:
        return False
    with connect() as conn:
        scene_refs = conn.execute("SELECT COUNT(*) FROM scenes WHERE background_asset_id = ?", (asset_id,)).fetchone()[0]
        scenario_refs = conn.execute("SELECT COUNT(*) FROM story_scenarios WHERE asset_id = ?", (asset_id,)).fetchone()[0]
    return bool(scene_refs or scenario_refs)


def update_asset_base(asset_id, base_asset_id):
    with connect() as conn:
        conn.execute(
            "UPDATE generated_assets SET base_asset_id = ? WHERE id = ?",
            (base_asset_id or "", asset_id),
        )
    return get_asset(asset_id)


def create_character_appearance(character_id, label="", primary_asset_id="", neutral_asset_id="", active=True):
    character = get_character(character_id)
    if not character:
        return None
    timestamp = now_ms()
    appearance_id = new_id("appearance")
    with connect() as conn:
        if active:
            conn.execute("UPDATE character_appearances SET is_active = 0 WHERE character_id = ?", (character_id,))
        conn.execute(
            """
            INSERT INTO character_appearances (
                id, character_id, label, primary_asset_id, neutral_asset_id, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appearance_id,
                character_id,
                label or "Aparencia",
                primary_asset_id or neutral_asset_id or "",
                neutral_asset_id or primary_asset_id or "",
                1 if active else 0,
                timestamp,
                timestamp,
            ),
        )
        if primary_asset_id or neutral_asset_id:
            conn.execute(
                "UPDATE generated_assets SET appearance_id = ? WHERE id IN (?, ?)",
                (appearance_id, primary_asset_id or "", neutral_asset_id or ""),
            )
            base_id = primary_asset_id or neutral_asset_id
            conn.execute(
                "UPDATE generated_assets SET appearance_id = ? WHERE base_asset_id = ?",
                (appearance_id, base_id),
            )
        if active:
            conn.execute(
                "UPDATE characters SET active_appearance_id = ?, updated_at = ? WHERE id = ?",
                (appearance_id, timestamp, character_id),
            )
    return get_appearance(appearance_id)


def get_appearance(appearance_id):
    if not appearance_id:
        return None
    with connect() as conn:
        row = conn.execute("SELECT * FROM character_appearances WHERE id = ?", (appearance_id,)).fetchone()
    return serialize_appearance(row)


def is_initial_appearance(character_id, appearance_id):
    if not character_id or not appearance_id:
        return False
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id FROM character_appearances
            WHERE character_id = ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (character_id,),
        ).fetchone()
    return bool(row and row["id"] == appearance_id)


def replace_character_appearance_asset(character_id, appearance_id, asset_id):
    if not character_id or not appearance_id or not asset_id:
        return None
    timestamp = now_ms()
    with connect() as conn:
        appearance = conn.execute(
            "SELECT * FROM character_appearances WHERE id = ? AND character_id = ?",
            (appearance_id, character_id),
        ).fetchone()
        asset = conn.execute(
            "SELECT * FROM generated_assets WHERE id = ? AND character_id = ? AND asset_type = 'sprite' AND file_path != ''",
            (asset_id, character_id),
        ).fetchone()
        if not appearance or not asset:
            return None

        old_asset_ids = {
            value for value in [appearance["primary_asset_id"], appearance["neutral_asset_id"]]
            if value and value != asset_id
        }
        new_related_rows = conn.execute(
            "SELECT id FROM generated_assets WHERE id = ? OR base_asset_id = ?",
            (asset_id, asset_id),
        ).fetchall()
        new_related_ids = {row["id"] for row in new_related_rows}
        old_related_ids = set()
        if old_asset_ids:
            placeholders = ",".join("?" for _ in old_asset_ids)
            old_related_rows = conn.execute(
                f"""
                SELECT id FROM generated_assets
                WHERE appearance_id = ?
                   OR id IN ({placeholders})
                   OR base_asset_id IN ({placeholders})
                """,
                (appearance_id, *old_asset_ids, *old_asset_ids),
            ).fetchall()
        else:
            old_related_rows = conn.execute(
                "SELECT id FROM generated_assets WHERE appearance_id = ?",
                (appearance_id,),
            ).fetchall()
        old_related_ids = {row["id"] for row in old_related_rows} - new_related_ids

        if old_related_ids:
            placeholders = ",".join("?" for _ in old_related_ids)
            conn.execute(
                f"DELETE FROM generated_assets WHERE id IN ({placeholders})",
                tuple(old_related_ids),
            )
        conn.execute(
            "UPDATE generated_assets SET appearance_id = ?, base_asset_id = ? WHERE id = ?",
            (appearance_id, asset_id, asset_id),
        )
        conn.execute(
            "UPDATE generated_assets SET appearance_id = ? WHERE base_asset_id = ?",
            (appearance_id, asset_id),
        )
        conn.execute(
            """
            UPDATE character_appearances
            SET primary_asset_id = ?, neutral_asset_id = ?, updated_at = ?
            WHERE id = ? AND character_id = ?
            """,
            (asset_id, asset_id, timestamp, appearance_id, character_id),
        )
        story_id = conn.execute("SELECT story_id FROM characters WHERE id = ?", (character_id,)).fetchone()["story_id"]
        conn.execute("UPDATE characters SET updated_at = ? WHERE id = ?", (timestamp, character_id))
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def set_active_appearance(character_id, appearance_id):
    timestamp = now_ms()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM character_appearances WHERE id = ? AND character_id = ?",
            (appearance_id, character_id),
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE character_appearances SET is_active = 0 WHERE character_id = ?", (character_id,))
        conn.execute(
            "UPDATE character_appearances SET is_active = 1, updated_at = ? WHERE id = ?",
            (timestamp, appearance_id),
        )
        conn.execute(
            "UPDATE characters SET active_appearance_id = ?, updated_at = ? WHERE id = ?",
            (appearance_id, timestamp, character_id),
        )
        story_id = conn.execute("SELECT story_id FROM characters WHERE id = ?", (character_id,)).fetchone()["story_id"]
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, story_id))
    return get_story(story_id)


def ensure_appearances_for_story(story_id):
    timestamp = now_ms()
    with connect() as conn:
        characters = conn.execute("SELECT id, active_appearance_id FROM characters WHERE story_id = ?", (story_id,)).fetchall()
        for character in characters:
            assets = conn.execute(
                """
                SELECT * FROM generated_assets
                WHERE story_id = ? AND character_id = ? AND asset_type = 'sprite' AND file_path != ''
                ORDER BY created_at ASC
                """,
                (story_id, character["id"]),
            ).fetchall()
            base_assets = [
                row for row in assets
                if normalize_expression(row["expression"]) == "neutral"
                and (not row["base_asset_id"] or row["base_asset_id"] == row["id"])
            ]
            for index, asset in enumerate(base_assets):
                appearance_id = asset["appearance_id"] if "appearance_id" in asset.keys() else ""
                existing = conn.execute(
                    "SELECT id FROM character_appearances WHERE id = ? OR primary_asset_id = ? OR neutral_asset_id = ?",
                    (appearance_id or "", asset["id"], asset["id"]),
                ).fetchone()
                if existing:
                    appearance_id = existing["id"]
                else:
                    appearance_id = new_id("appearance")
                    conn.execute(
                        """
                        INSERT INTO character_appearances (
                            id, character_id, label, primary_asset_id, neutral_asset_id, is_active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                        """,
                        (
                            appearance_id,
                            character["id"],
                            "Inicial" if index == 0 else f"Aparencia {index + 1}",
                            asset["id"],
                            asset["id"],
                            asset["created_at"] or timestamp,
                            timestamp,
                        ),
                    )
                conn.execute("UPDATE generated_assets SET appearance_id = ? WHERE id = ?", (appearance_id, asset["id"]))
                conn.execute("UPDATE generated_assets SET appearance_id = ? WHERE base_asset_id = ?", (appearance_id, asset["id"]))

            rows = conn.execute(
                "SELECT id FROM character_appearances WHERE character_id = ? ORDER BY created_at DESC",
                (character["id"],),
            ).fetchall()
            appearance_ids = [row["id"] for row in rows]
            active_id = character["active_appearance_id"] if "active_appearance_id" in character.keys() else ""
            if active_id not in appearance_ids and appearance_ids:
                active_id = appearance_ids[0]
                conn.execute(
                    "UPDATE characters SET active_appearance_id = ?, updated_at = ? WHERE id = ?",
                    (active_id, timestamp, character["id"]),
                )
            conn.execute("UPDATE character_appearances SET is_active = 0 WHERE character_id = ?", (character["id"],))
            if active_id:
                conn.execute("UPDATE character_appearances SET is_active = 1 WHERE id = ?", (active_id,))


def add_sprite_expression_asset(base_asset, expression, file_path="", metadata=None, prompt=None, negative_prompt=None, remote_ref=None):
    if not base_asset:
        return None
    return add_asset(
        base_asset["story_id"],
        {
            "asset_type": "sprite",
            "character_id": base_asset.get("character_id"),
            "scene_id": base_asset.get("scene_id"),
            "appearance_id": base_asset.get("appearance_id"),
            "base_asset_id": base_asset.get("base_asset_id") or base_asset.get("id"),
            "expression": expression,
            "prompt": base_asset.get("prompt") if prompt is None else prompt,
            "negative_prompt": base_asset.get("negative_prompt") if negative_prompt is None else negative_prompt,
            "file_path": file_path,
            "remote_ref": base_asset.get("remote_ref") if remote_ref is None else remote_ref,
            "metadata": metadata or {},
        },
    )


def set_scene_background(scene_id, asset_id):
    with connect() as conn:
        conn.execute(
            "UPDATE scenes SET background_asset_id = ? WHERE id = ?",
            (asset_id, scene_id),
        )


def add_api_log(provider, operation, request_payload=None, response_payload=None, status="ok", error="", story_id=None):
    timestamp = now_ms()
    log_id = new_id("log")
    provider, request_payload = normalize_ai_log_payload(provider, operation, request_payload)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO api_logs (
                id, story_id, provider, operation, request_payload, response_payload,
                status, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                story_id,
                provider,
                operation,
                json.dumps(redact_secrets(request_payload), ensure_ascii=False) if request_payload is not None else "",
                json.dumps(redact_secrets(response_payload), ensure_ascii=False) if response_payload is not None else "",
                status,
                redact_secret_text(error),
                timestamp,
            ),
        )
    return log_id


def normalize_ai_log_payload(provider, operation, request_payload):
    if provider != "ollama" or not str(operation or "").startswith("chat:"):
        return provider, request_payload
    settings = get_settings()
    ai_provider = str(settings.get("ai_provider") or "ollama").strip() or "ollama"
    payload = request_payload if isinstance(request_payload, dict) else {}
    payload = dict(payload)
    payload["provider"] = ai_provider
    payload["model"] = ai_model_from_settings(settings)
    base_url = ai_base_url_from_settings(settings)
    if base_url:
        payload["base_url"] = base_url
    return ai_provider, payload


def ai_model_from_settings(settings):
    provider = str(settings.get("ai_provider") or "ollama").strip()
    if provider == "openai":
        return settings.get("openai_model") or ""
    if provider == "openai-compatible":
        return settings.get("openai_compatible_model") or ""
    return settings.get("ollama_model") or ""


def ai_base_url_from_settings(settings):
    provider = str(settings.get("ai_provider") or "ollama").strip()
    if provider == "openai":
        return settings.get("openai_base_url") or ""
    if provider == "openai-compatible":
        return settings.get("openai_compatible_base_url") or ""
    return settings.get("ollama_url") or ""


def redact_secrets(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if "api_key" in lowered or lowered in {"authorization", "token", "secret", "password"}:
                result[key] = MASKED_SECRET_VALUE if item else ""
            else:
                result[key] = redact_secrets(item)
        return result
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        return redact_secret_text(value)
    return value


def redact_secret_text(value):
    text = str(value or "")
    if not text:
        return ""
    try:
        settings = get_settings()
    except Exception:
        settings = {}
    for key in SECRET_SETTING_KEYS:
        secret = settings.get(key)
        if secret:
            text = text.replace(str(secret), MASKED_SECRET_VALUE)
    return text


def list_api_logs(story_id=None, limit=100):
    limit = max(1, min(int(limit or 100), 500))
    with connect() as conn:
        if story_id:
            rows = conn.execute(
                "SELECT * FROM api_logs WHERE story_id = ? OR story_id IS NULL ORDER BY created_at DESC LIMIT ?",
                (story_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM api_logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [serialize_api_log(row) for row in rows]


def get_asset(asset_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM generated_assets WHERE id = ?", (asset_id,)).fetchone()
    return serialize_asset(row)


def update_asset_file(asset_id, file_path, metadata):
    timestamp = now_ms()
    with connect() as conn:
        row = conn.execute("SELECT * FROM generated_assets WHERE id = ?", (asset_id,)).fetchone()
        if not row:
            return None
        merged = json_load(row["metadata"], {})
        merged.update(metadata or {})
        conn.execute(
            "UPDATE generated_assets SET file_path = ?, metadata = ? WHERE id = ?",
            (file_path, json.dumps(merged, ensure_ascii=False), asset_id),
        )
        if row["asset_type"] == "background" and row["scene_id"]:
            conn.execute(
                "UPDATE scenes SET background_asset_id = ? WHERE id = ?",
                (asset_id, row["scene_id"]),
            )
        conn.execute("UPDATE stories SET updated_at = ? WHERE id = ?", (timestamp, row["story_id"]))
    return get_asset(asset_id)


def delete_asset(asset_id):
    asset = get_asset(asset_id)
    if not asset:
        return None
    with connect() as conn:
        if asset.get("asset_type") == "background":
            conn.execute(
                "UPDATE scenes SET background_asset_id = NULL WHERE background_asset_id = ?",
                (asset_id,),
            )
        if asset.get("asset_type") == "sprite":
            appearance_id = asset.get("appearance_id") or ""
            character_id = asset.get("character_id") or ""
            conn.execute("DELETE FROM generated_assets WHERE base_asset_id = ? AND id != ?", (asset_id, asset_id))
            if appearance_id and (not asset.get("base_asset_id") or asset.get("base_asset_id") == asset_id):
                conn.execute("DELETE FROM character_appearances WHERE id = ?", (appearance_id,))
                remaining = conn.execute(
                    "SELECT id FROM character_appearances WHERE character_id = ? ORDER BY created_at DESC LIMIT 1",
                    (character_id,),
                ).fetchone()
                next_id = remaining["id"] if remaining else ""
                if next_id:
                    conn.execute("UPDATE character_appearances SET is_active = 0 WHERE character_id = ?", (character_id,))
                    conn.execute("UPDATE character_appearances SET is_active = 1 WHERE id = ?", (next_id,))
                conn.execute(
                    "UPDATE characters SET active_appearance_id = ? WHERE id = ?",
                    (next_id, character_id),
                )
        conn.execute("DELETE FROM generated_assets WHERE id = ?", (asset_id,))
    return asset


def serialize_story(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["player_character"] = json_load(data.get("player_character"), {})
    data["participation_mode"] = normalize_participation_mode(data.get("participation_mode"))
    data["main_characters"] = data.get("main_characters") or ""
    data["scene_count"] = data.get("scene_count") or 0
    data["character_count"] = data.get("character_count") or 0
    data["cover_url"] = f"/api/assets/{data['cover_asset_id']}/file" if data.get("cover_asset_id") else ""
    return data


def serialize_visual_style(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["advanced_settings"] = json_load(data.get("advanced_settings"), {})
    data["background_settings"] = json_load(data.get("background_settings"), {})
    data["expressions_enabled"] = bool(data.get("expressions_enabled"))
    data["expression_prompts_visible"] = bool(data.get("expression_prompts_visible"))
    data["expression_prompts"] = normalize_expression_prompts(json_load(data.get("expression_prompts"), {}))
    data["cover_url"] = f"/api/visual-styles/{data['id']}/cover?v={data.get('updated_at') or 0}" if data.get("cover_path") else ""
    return data


def serialize_character(row):
    data = row_to_dict(row)
    if data:
        data["expression_prompts"] = normalize_character_expression_prompts(json_load(data.get("expression_prompts"), {}))
    return data


def normalize_character_expression_prompts(value):
    if isinstance(value, str):
        value = json_load(value, {})
    source = value if isinstance(value, dict) else {}
    return {
        expression: str(source.get(expression) or "").strip()
        for expression in EXPRESSION_PROMPT_KEYS
    }


def serialize_appearance(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["is_active"] = bool(data.get("is_active"))
    return data


def serialize_scene(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["dialogues"] = json_load(data.get("dialogues"), [])
    data["choices"] = json_load(data.get("choices"), [])
    data["characters_on_screen"] = json_load(data.get("characters_on_screen"), [])
    data["memory_updates"] = json_load(data.get("memory_updates"), {})
    data["raw_ai_response"] = json_load(data.get("raw_ai_response"), {})
    return data


def serialize_asset(row):
    data = row_to_dict(row)
    if not data:
        return None
    if data.get("asset_type") == "sprite":
        data["expression"] = normalize_expression(data.get("expression"))
        data["base_asset_id"] = data.get("base_asset_id") or ""
        data["appearance_id"] = data.get("appearance_id") or ""
    data["metadata"] = json_load(data.get("metadata"), {})
    data["url"] = f"/api/assets/{data['id']}/file" if data.get("file_path") else ""
    return data


def serialize_story_reference(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["url"] = f"/api/story-references/{data['id']}/file" if data.get("file_path") else ""
    return data


def serialize_story_scenario(row, assets=None):
    data = row_to_dict(row)
    if not data:
        return None
    assets = assets or []
    asset = next((item for item in assets if item and item["id"] == data.get("asset_id")), None)
    asset_data = serialize_asset(asset) if asset else (get_asset(data.get("asset_id")) if data.get("asset_id") else None)
    data["is_active"] = bool(data.get("is_active"))
    data["image_path"] = (asset_data or {}).get("file_path") or ""
    data["url"] = (asset_data or {}).get("url") or ""
    data["asset"] = asset_data
    return data


def serialize_api_log(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["request_payload"] = json_load(data.get("request_payload"), data.get("request_payload") or "")
    data["response_payload"] = json_load(data.get("response_payload"), data.get("response_payload") or "")
    return data
