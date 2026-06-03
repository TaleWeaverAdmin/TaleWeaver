import json
import shutil
import sqlite3
import time
import uuid
from pathlib import Path

from .config import DATA_DIR, DB_PATH, ROOT_DIR, STORIES_DIR, DEFAULT_SETTINGS


def now_ms():
    return int(time.time() * 1000)


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORIES_DIR.mkdir(parents=True, exist_ok=True)
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
                visual_prompt TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                importance TEXT NOT NULL DEFAULT 'secondary',
                is_player INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE
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
                asset_type TEXT NOT NULL,
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
            """
        )
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
            },
        )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )


def ensure_columns(conn, table, columns):
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


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
    return {row["key"]: json_load(row["value"], row["value"]) for row in rows}


def update_settings(values):
    with connect() as conn:
        for key, value in values.items():
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
    fields = ["title", "genre", "tone", "visual_style", "content_rating", "language", "status", "lore", "summary"]
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
                id, title, genre, tone, visual_style, content_rating, language,
                status, lore, player_character, summary, current_scene_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, NULL, ?, ?)
            """,
            (
                new_story_id,
                f"Copia de {story['title']}",
                story["genre"],
                story["tone"],
                story["visual_style"],
                story["content_rating"],
                story["language"],
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
                    visual_prompt, status, importance, is_player, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    id, story_id, character_id, scene_id, asset_type, expression, prompt,
                    negative_prompt, file_path, remote_ref, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_asset_id,
                    new_story_id,
                    new_character_id,
                    new_scene_id,
                    row["asset_type"],
                    row["expression"],
                    row["prompt"],
                    row["negative_prompt"],
                    new_file_path,
                    row["remote_ref"],
                    row["metadata"],
                    timestamp,
                ),
            )

        for old_scene_id, old_asset_id in scene_backgrounds.items():
            if old_asset_id and old_asset_id in asset_map:
                conn.execute(
                    "UPDATE scenes SET background_asset_id = ? WHERE id = ?",
                    (asset_map[old_asset_id], scene_map[old_scene_id]),
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
        target = STORIES_DIR / new_story_id / "characters" / (character_id or "unknown") / f"{expression or 'neutral'}_{new_asset_id}{extension}"
    else:
        target = STORIES_DIR / new_story_id / "metadata" / f"{new_asset_id}{extension}"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    except OSError:
        return ""
    return target.relative_to(ROOT_DIR).as_posix()


def get_story(story_id):
    with connect() as conn:
        story = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not story:
            return None
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
    data = serialize_story(story)
    data["characters"] = [serialize_character(row) for row in characters]
    data["scenes"] = [serialize_scene(row) for row in scenes]
    data["memory_entries"] = [row_to_dict(row) for row in memory]
    data["lore_entries"] = [row_to_dict(row) for row in lore]
    data["assets"] = [serialize_asset(row) for row in assets]
    return data


def create_story(payload):
    timestamp = now_ms()
    story_id = new_id("story")
    player = payload.get("player_character") or {}
    lore = payload.get("lore") or ""
    starting_message = payload.get("starting_message") or ""

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO stories (
                id, title, genre, tone, visual_style, content_rating, language,
                status, lore, player_character, summary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (
                story_id,
                payload.get("title") or "Historia sem titulo",
                payload.get("genre") or "",
                payload.get("tone") or "",
                payload.get("visual_style") or "",
                payload.get("content_rating") or "",
                payload.get("language") or "pt-BR",
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
    player = payload.get("player_character") or {}
    characters = [player, *(payload.get("characters") or [])]
    starting_message = payload.get("starting_message") or ""
    starting_location = payload.get("starting_location") or ""
    present = detect_initial_characters(characters, starting_message)
    if not present and player.get("name"):
        present = [player]
    return {
        "title": starting_location or "Primeira cena",
        "scene_text": starting_message,
        "dialogues": [{"character": "Narrador", "expression": "neutral", "text": starting_message}],
        "choices": ["Observar o ambiente", "Falar com alguem presente", "Avancar com cautela"],
        "characters_on_screen": [
            {"name": character.get("name"), "position": position_for_index(index, len(present)), "expression": "neutral"}
            for index, character in enumerate(present[:4])
            if character.get("name")
        ],
        "background_prompt": build_initial_background_prompt(payload),
        "memory_updates": {
            "summary": compact_text(starting_message, 420),
            "facts": [f"Local inicial: {starting_location}"] if starting_location else [],
        },
        "raw_ai_response": {
            "location": starting_location,
            "location_changed": True,
            "new_characters_detected": [],
        },
        "user_input": "Mensagem inicial da historia",
    }


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
        "empty visual novel background, no people, no characters, no faces, no silhouettes, no text, no UI",
        "no people",
        payload.get("visual_style") or "visual novel style",
        payload.get("starting_location") or "",
        compact_text(payload.get("starting_message") or "", 260),
        "specific architecture and spatial layout",
        "environmental storytelling objects tied to the opening conflict",
        "clear material textures",
        "distinct foreground, midground, and background depth",
        "establishing shot",
        "cinematic atmospheric lighting",
        "cohesive color palette",
        "high detail polished anime visual novel background art",
    ]
    return ", ".join(part for part in parts if part)


def compact_text(value, limit):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def insert_character(conn, story_id, data, is_player=False, importance="secondary"):
    timestamp = now_ms()
    character_id = new_id("char")
    conn.execute(
        """
        INSERT INTO characters (
            id, story_id, name, species, gender, character_type, aliases, description,
            physical, personality, clothing, role, relationship, secrets, speech_style,
            visual_prompt, status, importance, is_player, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
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
            data.get("visual_prompt") or "",
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


def update_character(character_id, payload):
    timestamp = now_ms()
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
        "visual_prompt",
        "status",
        "importance",
    ]
    updates = [field for field in fields if field in payload]
    if not updates:
        return get_character(character_id)
    sql = ", ".join([f"{field} = ?" for field in updates] + ["updated_at = ?"])
    values = [payload[field] for field in updates] + [timestamp, character_id]
    with connect() as conn:
        conn.execute(f"UPDATE characters SET {sql} WHERE id = ?", values)
    return get_character(character_id)


def add_asset(story_id, payload):
    timestamp = now_ms()
    asset_id = new_id("asset")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO generated_assets (
                id, story_id, character_id, scene_id, asset_type, expression, prompt,
                negative_prompt, file_path, remote_ref, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                story_id,
                payload.get("character_id"),
                payload.get("scene_id"),
                payload.get("asset_type") or "image",
                payload.get("expression") or "",
                payload.get("prompt") or "",
                payload.get("negative_prompt") or "",
                payload.get("file_path") or "",
                payload.get("remote_ref") or "",
                json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
                timestamp,
            ),
        )
    return asset_id


def set_scene_background(scene_id, asset_id):
    with connect() as conn:
        conn.execute(
            "UPDATE scenes SET background_asset_id = ? WHERE id = ?",
            (asset_id, scene_id),
        )


def add_api_log(provider, operation, request_payload=None, response_payload=None, status="ok", error="", story_id=None):
    timestamp = now_ms()
    log_id = new_id("log")
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
                json.dumps(request_payload, ensure_ascii=False) if request_payload is not None else "",
                json.dumps(response_payload, ensure_ascii=False) if response_payload is not None else "",
                status,
                error,
                timestamp,
            ),
        )
    return log_id


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
        conn.execute("DELETE FROM generated_assets WHERE id = ?", (asset_id,))
    return asset


def serialize_story(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["player_character"] = json_load(data.get("player_character"), {})
    data["main_characters"] = data.get("main_characters") or ""
    data["scene_count"] = data.get("scene_count") or 0
    data["character_count"] = data.get("character_count") or 0
    data["cover_url"] = f"/api/assets/{data['cover_asset_id']}/file" if data.get("cover_asset_id") else ""
    return data


def serialize_character(row):
    return row_to_dict(row)


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
    data["metadata"] = json_load(data.get("metadata"), {})
    data["url"] = f"/api/assets/{data['id']}/file" if data.get("file_path") else ""
    return data


def serialize_api_log(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["request_payload"] = json_load(data.get("request_payload"), data.get("request_payload") or "")
    data["response_payload"] = json_load(data.get("response_payload"), data.get("response_payload") or "")
    return data
