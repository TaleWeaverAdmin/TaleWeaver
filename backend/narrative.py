import json
import html
import math
import re
import time
import unicodedata

from . import db
from . import ai_client
from .ai_client import chat_json
from .prompts import COMPACT_NARRATOR_SYSTEM_PROMPT, CONTEXT_STATS_KEY, NARRATOR_SYSTEM_PROMPT, build_narrative_context, build_narrator_user_prompt, compact

OFFICIAL_EXPRESSIONS = {"neutral", "happy", "sad", "angry", "thoughtful", "surprised", "embarrassed", "scared"}
CHARACTER_EXPRESSION_KEYS = ["happy", "sad", "angry", "thoughtful", "surprised", "embarrassed", "scared"]

ESTIMATED_CHARS_PER_TOKEN = 3.2

COMPACT_CONTEXT_PREFERRED_LIMITS = {
    "participation_mode": 700,
    "story_core": 950,
    "current_story_memory": 1200,
    "story_progress": 700,
    "active_character_brief": 950,
    "character_visual_state": 1100,
    "recent_scene_states": 1250,
    "visual_state": 420,
    "scene_cast_state": 760,
    "speaker_focus": 760,
    "player_choice": 420,
    "directives": 260,
    "output_requirements": 3600,
    "task": 260,
}

COMPACT_CONTEXT_MAX_LIMITS = {
    "participation_mode": 900,
    "story_core": 1500,
    "current_story_memory": 1800,
    "story_progress": 950,
    "active_character_brief": 1500,
    "character_visual_state": 1600,
    "recent_scene_states": 2300,
    "visual_state": 520,
    "scene_cast_state": 850,
    "speaker_focus": 850,
    "player_choice": 520,
    "directives": 360,
    "output_requirements": 4200,
    "task": 320,
}

COMPACT_CONTEXT_MIN_LIMITS = {
    "participation_mode": 500,
    "story_core": 520,
    "current_story_memory": 450,
    "story_progress": 420,
    "active_character_brief": 520,
    "character_visual_state": 520,
    "recent_scene_states": 520,
    "visual_state": 220,
    "scene_cast_state": 620,
    "speaker_focus": 620,
    "player_choice": 360,
    "directives": 220,
    "output_requirements": 3000,
    "task": 220,
}

COMPACT_CONTEXT_REDUCTION_ORDER = [
    "recent_scene_states",
    "story_progress",
    "story_core",
    "current_story_memory",
    "visual_state",
    "scene_cast_state",
    "speaker_focus",
    "active_character_brief",
    "character_visual_state",
    "player_choice",
    "directives",
    "task",
    "output_requirements",
    "participation_mode",
]


IMPROVE_SYSTEM_PROMPT = """You improve planning text for an AI-generated visual novel.

Return only valid JSON. Do not include markdown, HTML, CSS, or text outside JSON.

Required format:
{
  "improved_text": "improved text"
}

Rules:
- Preserve the user's intent, names, facts, and limits.
- Return plain text inside JSON string values. Do not wrap text in HTML tags, Markdown, color spans, inline styles, CSS, or formatting annotations.
- Do not contradict the original text.
- Expand with useful details for narrative continuity and image generation.
- Write normal narrative/planning fields in the requested output language from the user message.
- If the field is a visual prompt, write clear reusable English tags/descriptive prompt text.
- For world/lore, detail rules, conflicts, culture, locations, history, and dramatic possibilities.
- For characters, detail appearance, personality, voice, goals, fears, contradictions, and narrative hooks.
"""


STORY_SEED_SYSTEM_PROMPT = """SYSTEM:

You are a visual novel worldbuilder and narrative designer.

Return only valid JSON. Do not include markdown, comments, explanations, or text outside JSON.

Your job is to expand the user's story idea into a strong long-running visual novel setup.

Priorities:

Preserve the user's core idea and important details.
Do not summarize away rich lore. Expand it.
Create conflicts strong enough to sustain a long story.
Avoid generic archetypes unless they have a specific twist.
Do not automatically create a love interest, mentor, childhood friend, chosen-one helper, or evil priest unless the story clearly needs it.
Characters must have their own goals, fears, secrets, and reasons to oppose or help the protagonist.
The starting_message must be an opening scene in the requested language, not a welcome/tutorial message.
Narrative fields must be written in the requested narrative language.
visual_prompt fields must be in English and must describe only that specific character, not other characters beside them.

Participation mode rules:
- The user prompt will specify Participation mode: first_person, third_person, or narrator. You must follow it when writing lore, starting_message, player_character, and choices.
- first_person: starting_message may use immersive first-person narration because the user is the protagonist. The user-protagonist must not need a sprite.
- third_person: starting_message must use external third-person narration. Do not write "I", "my", "we", "you", or "your" as narration. The protagonist is visible and user-controlled.
- narrator: starting_message must use external cinematic narration. Do not write "I", "my", "we", "you", or "your" as narration. The user is not a character; player_character is only a narrative protagonist if needed.

Required JSON format:
{
"title": "short evocative title",
"genre": "comma-separated genres",
"tone": "narrative tone",
"visual_style": "generic visual style",
"content_rating": "user-defined content rating",
"language": "pt-BR | en-US",
"lore": "rich world description with history, rules, current crisis, factions, mysteries, and long-term conflict",
"starting_location": "short starting location",
"starting_message": "opening scene in the requested narrative language",
"player_character": {
"name": "protagonist name or Jogador/Player",
"role": "role",
"species": "species",
"gender": "gender",
"character_type": "narrative type",
"aliases": "comma-separated aliases",
"description": "general description",
"appearance": "appearance",
"physical": "detailed physical appearance",
"personality": "personality with contradictions",
"clothing": "specific outfit/clothing",
"background": "background history",
"goals": "goals, fears, and internal conflict",
"visual_prompt": "english visual prompt for this character sprite only"
},
"characters": [
{
"name": "name",
"role": "role",
"species": "species",
"gender": "gender",
"character_type": "narrative type",
"aliases": "comma-separated aliases",
"description": "general description",
"physical": "detailed physical appearance",
"personality": "personality with contradictions",
"clothing": "specific outfit/clothing",
"relationship": "relationship to the protagonist, including tension or conflict",
"secret_or_conflict": "what this character hides, wants, fears, or may become",
"visual_prompt": "english visual prompt for this character sprite only"
}
]
}

Rules:

Create 2 to 4 initial characters.
At least one character should complicate the protagonist's choices emotionally or morally.
At least one character should have a secret connected to the world's central mystery.
Do not make every character immediately loyal to the protagonist.
Do not make the lore short. It should be dense enough to guide many future scenes.
Keep visual_prompt concise, concrete, and usable for anime/semi-realistic visual novel sprites.
"""


COMPACT_STORY_SEED_SYSTEM_PROMPT = """SYSTEM:

You are a visual novel worldbuilder.

Return one valid compact JSON object only. No markdown, no code fences, no comments, no text outside JSON.

Use plain strings. Do not put raw line breaks inside JSON string values. Avoid double quotes inside prose; use apostrophes.

Required JSON:
{
"title":"short title",
"genre":"comma-separated genres",
"tone":"tone",
"visual_style":"visual style",
"content_rating":"rating",
"language":"pt-BR | en-US",
"lore":"compact but rich world setup, 6 to 10 sentences",
"starting_location":"short starting location",
"starting_message":"opening VN scene, 4 to 7 sentences",
"player_character":{"name":"name","role":"role","species":"species","gender":"gender","character_type":"type","aliases":"aliases","description":"description","appearance":"appearance","physical":"physical appearance","personality":"personality","clothing":"specific clothing","background":"background","goals":"goals and fears","visual_prompt":"English sprite prompt"},
"characters":[{"name":"name","role":"role","species":"species","gender":"gender","character_type":"type","aliases":"aliases","description":"description","physical":"appearance","personality":"personality","clothing":"specific clothing","relationship":"relationship and tension","secret_or_conflict":"secret or conflict","visual_prompt":"English sprite prompt"}]
}

Rules:
- Preserve the user's idea.
- Create exactly 2 initial characters.
- Narrative text must use the requested language.
- Respect the requested participation mode in starting_message and player_character.
- For narrator or third_person mode, starting_message must be external third-person/cinematic narration, not "I/my/we/you/your" narration.
- For first_person mode, starting_message may be immersive first-person narration.
- visual_prompt fields must be English.
- Keep every field concise and valid JSON.
"""


def generate_story_seed(payload):
    prompt = clean(payload.get("prompt"))
    if not prompt:
        raise ValueError("Descreva a ideia da historia antes de gerar a criacao inicial.")

    settings = ai_client.settings_for_ai_role(db.get_settings(), "story")
    participation_mode = db.normalize_participation_mode(payload.get("participation_mode") or payload.get("point_of_view"))
    seed_prompt = story_seed_system_prompt(settings)
    seed_options = story_seed_generation_options(settings)
    messages = [
        {"role": "system", "content": seed_prompt},
        {
            "role": "user",
            "content": (
                f"Requested narrative language: {language_instruction(settings.get('default_language'))}\n\n"
                f"Participation mode: {participation_mode}\n"
                f"{story_seed_participation_instruction(participation_mode)}\n\n"
                f"Story idea:\n{prompt}\n\nGenerate the creation JSON."
            ),
        },
    ]
    seed_request = {
        "model": settings.get("ollama_model"),
        "messages": messages,
        "llama_context_window": active_llama_context_window(settings) if use_llama_cpp_settings(settings) else settings.get("llama_context_window"),
        "seed_tokens": seed_options.get("num_predict") if isinstance(seed_options, dict) else None,
        "seed_prompt_mode": "compact-local-json" if seed_prompt == COMPACT_STORY_SEED_SYSTEM_PROMPT else "full",
    }
    try:
        db.add_api_log(
            "ollama",
            "chat:story-seed",
            seed_request,
            status="started",
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            story_seed_temperature(settings),
            seed_options,
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:story-seed",
            seed_request,
            result,
        )
        seed = normalize_story_seed(result, prompt, participation_mode)
        seed["participation_mode"] = participation_mode
        validate_story_seed(seed)
        return seed
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:story-seed",
            seed_request,
            raw_model_response_payload(exc),
            status="error",
            error=str(exc),
        )
        raise RuntimeError(f"IA de geracao de historia falhou: {exc}") from exc


def story_seed_system_prompt(settings):
    if use_llama_cpp_settings(settings):
        context_window = active_llama_context_window(settings)
        if context_window <= 8192:
            return COMPACT_STORY_SEED_SYSTEM_PROMPT
    return STORY_SEED_SYSTEM_PROMPT


def raw_model_response_payload(exc):
    content = getattr(exc, "content", "")
    if content:
        return {"raw_response": content}
    return None


def story_seed_generation_options(settings):
    if use_llama_cpp_settings(settings):
        tokens = bounded_int(settings.get("llama_max_tokens"), 500, 8000, 1800)
        options = llama_cpp_generation_options(settings, tokens, include_repeat=True)
        options["num_predict"] = tokens
        options["request_timeout"] = bounded_float(settings.get("llama_timeout"), 30, 1800, 300)
        return options
    tokens = bounded_int(settings.get("ollama_num_predict"), 500, 8000, 1600)
    return ollama_generation_options(settings, tokens)


def story_seed_temperature(settings):
    if use_llama_cpp_settings(settings):
        return 0.35
    return active_text_temperature(settings)


def story_seed_participation_instruction(mode):
    if mode == "third_person":
        return (
            "The user controls the protagonist, but the protagonist is visible as a normal character in scenes. "
            "Create player_character as the user-controlled protagonist with appearance, personality, background, goals, conflict, clothing, and a sprite visual_prompt. "
            "starting_message must be external third-person narration using the protagonist name or he/she/they; do not write I, my, we, you, or your as narration. "
            "Choices must be actions, speech, secrets, confrontations, or decisions available to that protagonist."
        )
    if mode == "narrator":
        return (
            "The user is outside the story and guides the whole narrative. Do not create a user avatar. "
            "If the story needs a protagonist, player_character may describe a narrative protagonist only, not the user, and they should be treated as a regular story character. "
            "starting_message must be external cinematic narration using character names or neutral camera language; do not write I, my, we, you, or your as narration. "
            "Choices may direct the wider story, shift focus between characters, create events, or change the dramatic situation."
        )
    return (
        "The user is the protagonist and experiences the story directly in first person. "
        "Create player_character as the user-protagonist with personality, appearance, background, goals, and internal conflict, but its visual_prompt must be blank because this character must not have a sprite or appear in characters_on_screen. "
        "Choices must be actions, speech, reactions, or decisions available to the user-protagonist."
    )


def extract_json_string_field(text, field):
    pattern = re.compile(rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"\\])*)"', re.S)
    match = pattern.search(str(text or ""))
    if not match:
        return ""
    value = match.group(1)
    try:
        return json.loads(f'"{value}"')
    except Exception:
        return value.replace("\\n", "\n").replace('\\"', '"')


def extract_json_object_text(text, field):
    marker = f'"{field}"'
    source = str(text or "")
    start = source.find(marker)
    if start < 0:
        return ""
    brace = source.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace, len(source)):
        char = source[index]
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
                return source[brace : index + 1]
    return source[brace:]


def extract_json_array_text(text, field):
    marker = f'"{field}"'
    source = str(text or "")
    start = source.find(marker)
    if start < 0:
        return ""
    bracket = source.find("[", start)
    if bracket < 0:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(bracket, len(source)):
        char = source[index]
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
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return source[bracket : index + 1]
    return source[bracket:]


def salvage_seed_characters_from_text(text):
    source = str(text or "")
    characters = []
    cursor = 0
    while len(characters) < 2:
        start = source.find("{", cursor)
        if start < 0:
            break
        item_text = extract_balanced_object_from_text(source, start)
        if not item_text:
            break
        cursor = start + len(item_text)
        name = clean(extract_json_string_field(item_text, "name"))
        if not name:
            continue
        characters.append(
            {
                "name": name,
                "role": clean(extract_json_string_field(item_text, "role")),
                "species": clean(extract_json_string_field(item_text, "species")),
                "gender": clean(extract_json_string_field(item_text, "gender")),
                "character_type": clean(extract_json_string_field(item_text, "character_type")),
                "aliases": clean(extract_json_string_field(item_text, "aliases")),
                "description": clean(extract_json_string_field(item_text, "description")),
                "physical": clean(extract_json_string_field(item_text, "physical")),
                "personality": clean(extract_json_string_field(item_text, "personality")),
                "clothing": clean(extract_json_string_field(item_text, "clothing")),
                "relationship": clean(extract_json_string_field(item_text, "relationship")),
                "visual_prompt": clean(extract_json_string_field(item_text, "visual_prompt")),
            }
        )
    return characters


def extract_balanced_object_from_text(text, start=0):
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
    return text[start:]


def normalize_name(value):
    return str(value or "").strip().lower()


def normalize_story_seed(raw, prompt, participation_mode=None):
    settings = ai_client.settings_for_ai_role(db.get_settings(), "story")
    language = normalize_language(raw.get("language")) if clean(raw.get("language")) else ""
    player = raw.get("player_character") if isinstance(raw.get("player_character"), dict) else {}
    characters = raw.get("characters") if isinstance(raw.get("characters"), list) else []
    participation_mode = db.normalize_participation_mode(participation_mode or raw.get("participation_mode") or raw.get("point_of_view"))
    if participation_mode == "first_person":
        player["visual_prompt"] = ""
    starting_message = clean(raw.get("starting_message"))
    starting_message = repair_seed_starting_message_perspective(starting_message, participation_mode, player)
    return {
        "title": clean(raw.get("title")),
        "genre": clean(raw.get("genre")),
        "tone": clean(raw.get("tone")),
        "visual_style": clean(raw.get("visual_style")),
        "content_rating": clean(raw.get("content_rating")),
        "participation_mode": participation_mode,
        "language": language,
        "lore": clean(raw.get("lore")),
        "starting_location": clean(raw.get("starting_location")),
        "starting_message": starting_message,
        "player_character": {
            "name": clean(player.get("name")),
            "role": clean(player.get("role")),
            "species": clean(player.get("species")),
            "gender": clean(player.get("gender")),
            "character_type": clean(player.get("character_type")) or clean(player.get("type")),
            "aliases": clean(player.get("aliases")),
            "description": clean(player.get("description")),
            "appearance": clean(player.get("appearance")),
            "physical": clean(player.get("physical")) or clean(player.get("appearance")),
            "personality": clean(player.get("personality")),
            "clothing": clean(player.get("clothing")),
            "background": clean(player.get("background")),
            "goals": clean(player.get("goals")),
            "visual_prompt": clean(player.get("visual_prompt")),
        },
        "characters": [normalize_seed_character(item) for item in characters[:4] if isinstance(item, dict) and clean(item.get("name"))],
    }


def normalize_seed_character(item):
    return {
        "name": clean(item.get("name")),
        "role": clean(item.get("role")),
        "species": clean(item.get("species")),
        "gender": clean(item.get("gender")),
        "character_type": clean(item.get("character_type")) or clean(item.get("type")),
        "aliases": clean(item.get("aliases")),
        "description": clean(item.get("description")),
        "physical": clean(item.get("physical")) or clean(item.get("appearance")),
        "personality": clean(item.get("personality")),
        "clothing": clean(item.get("clothing")),
        "relationship": clean(item.get("relationship")),
        "visual_prompt": clean(item.get("visual_prompt")),
    }


def validate_story_seed(seed):
    required = ["title", "genre", "tone", "visual_style", "language", "lore", "starting_location", "starting_message"]
    missing = [field for field in required if not clean((seed or {}).get(field))]
    player = (seed or {}).get("player_character") if isinstance((seed or {}).get("player_character"), dict) else {}
    if not clean(player.get("name")):
        missing.append("player_character.name")
    if not isinstance((seed or {}).get("characters"), list) or not (seed or {}).get("characters"):
        missing.append("characters")
    if missing:
        raise ValueError(f"Resposta de geracao de historia invalida: campos ausentes: {', '.join(missing)}.")


def repair_seed_starting_message_perspective(text, participation_mode, player):
    text = clean(text)
    if participation_mode not in {"narrator", "third_person"}:
        return text
    if not first_person_or_reader_address_match(text):
        return text
    raise ValueError("Resposta de geracao de historia invalida: starting_message viola o modo de participacao.")


def enrich_story_creation_payload(payload):
    payload = dict(payload or {})
    payload["participation_mode"] = db.normalize_participation_mode(payload.get("participation_mode") or payload.get("point_of_view"))
    payload["language"] = story_language(payload)
    language = payload["language"]
    player = dict(payload.get("player_character") or {})
    player_is_user = payload["participation_mode"] != "narrator"
    use_player_character = player_is_user or character_has_content(player)
    if payload["participation_mode"] == "first_person":
        player["visual_prompt"] = ""
    characters = [dict(character) for character in payload.get("characters") or [] if isinstance(character, dict)]
    player_needs_enrichment = needs_creation_enrichment(player, require_visual_prompt=payload["participation_mode"] != "first_person")
    if not player_needs_enrichment and not any(needs_creation_enrichment(character) for character in characters):
        payload["player_character"] = complete_character_record(player, payload, None, is_player=player_is_user) if use_player_character else {}
        payload["characters"] = [complete_character_record(character, payload, None) for character in characters]
        apply_creation_sprite_prompts(payload, db.get_settings())
        return payload

    settings = ai_client.settings_for_ai_role(db.get_settings(), "story")
    visual_style = db.get_visual_style(payload.get("visual_style_id"))
    workbench_id = visual_style_workbench(visual_style, settings, "sprite")
    prompt_profile = prompt_profile_from_visual_style(visual_style, settings, "sprite")
    sources = [{"slot": "player_character", "index": -1, "character": player}] if use_player_character else []
    sources.extend({"slot": "characters", "index": index, "character": character} for index, character in enumerate(characters))
    system = (
        "You enrich visual novel character records for story creation. "
        "Return only valid JSON. Do not add new characters. "
        "Infer missing fields from the supplied descriptions without contradicting user data. "
        f"Write narrative fields in {language_instruction(payload.get('language'))}. "
        "Write visual_prompt in English for a ComfyUI visual novel sprite."
    )
    user = (
        "Required JSON format:\n"
        "{\"player_character\": {...}, \"characters\": [{...}]}\n\n"
        "For every character, fill every field even when it was missing or weak: species, gender, character_type, aliases, "
        "description, physical, personality, clothing, role, relationship, secrets, speech_style, visual_prompt.\n"
        f"Narrative fields must be in {language_instruction(payload.get('language'))}. "
        "Do not leave blank strings. Use 'nenhum alias conhecido' / 'no known aliases' only when aliases are truly unknown.\n"
        "For visual_prompt, use only these character fields as source: species, gender, physical, clothing. "
        "Do not use personality, role, relationship, backstory, aliases, or secrets in visual_prompt. "
        "visual_prompt must be entirely in English and include full-body front-view sprite framing. One character only.\n\n"
        f"Sprite workbench prompt style:\n{prompt_profile.get('style') or '(natural-language sprite prompt)'}\n\n"
        f"Sprite workbench example:\n{prompt_profile.get('example') or '(none)'}\n\n"
        f"Story title: {payload.get('title') or ''}\n"
        f"Genre: {payload.get('genre') or ''}\n"
        f"Tone: {payload.get('tone') or ''}\n"
        f"Visual style: {payload.get('visual_style') or ''}\n"
        f"Lore: {clean(payload.get('lore'))[:1200]}\n\n"
        f"Characters to enrich:\n{json.dumps(sources, ensure_ascii=False)}"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        db.add_api_log(
            "ollama",
            "chat:creation-character-enrichment",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "characters": sources},
            status="started",
        )
        result = chat_json(settings.get("ollama_url"), settings.get("ollama_model"), messages, 0.4, settings=settings)
        db.add_api_log(
            "ollama",
            "chat:creation-character-enrichment",
            {"model": settings.get("ollama_model"), "workbench": workbench_id},
            result,
        )
        payload["player_character"] = complete_character_record(
            merge_character_enrichment(player, result.get("player_character") if isinstance(result, dict) else {}),
            payload,
            None,
            is_player=player_is_user,
        ) if use_player_character else {}
        if use_player_character and player_needs_enrichment:
            validate_ai_character_record(
                payload["player_character"],
                "personagem do jogador",
                require_visual_prompt=False,
            )
        enriched_characters = result.get("characters") if isinstance(result, dict) and isinstance(result.get("characters"), list) else []
        payload["characters"] = [
            complete_character_record(
                merge_character_enrichment(character, enriched_characters[index] if index < len(enriched_characters) else {}),
                payload,
                None,
            )
            for index, character in enumerate(characters)
        ]
        for index, character in enumerate(payload["characters"]):
            if index < len(characters) and needs_creation_enrichment(characters[index]):
                validate_ai_character_record(character, f"personagem inicial {index + 1}", require_visual_prompt=False)
        apply_creation_sprite_prompts(payload, settings)
        if use_player_character and player_needs_enrichment:
            validate_ai_character_record(
                payload["player_character"],
                "personagem do jogador",
                require_visual_prompt=payload["participation_mode"] != "first_person",
            )
        for index, character in enumerate(payload["characters"]):
            if index < len(characters) and needs_creation_enrichment(characters[index]):
                validate_ai_character_record(character, f"personagem inicial {index + 1}")
        return payload
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:creation-character-enrichment",
            {"model": settings.get("ollama_model"), "workbench": workbench_id},
            status="error",
            error=str(exc),
        )
        raise RuntimeError(f"IA de geracao de historia falhou ao enriquecer personagens: {exc}") from exc


def character_has_content(character):
    if not isinstance(character, dict):
        return False
    return any(clean(value) for value in character.values() if not isinstance(value, (dict, list)))


def needs_creation_enrichment(character, require_visual_prompt=True):
    if not clean(character.get("name")):
        return False
    required = [
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
    ]
    if require_visual_prompt:
        required.append("visual_prompt")
    return any(not clean(character.get(field)) for field in required)


def sprite_prompt_profile(settings, workbench_id):
    profiles = settings.get("comfy_prompt_profiles")
    if isinstance(profiles, dict) and isinstance(profiles.get(workbench_id), dict):
        return profiles.get(workbench_id)
    return {}


def prompt_profile_from_visual_style(style, settings=None, asset_type="sprite"):
    settings = settings or db.get_settings()
    style = style or {}
    normalized_type = normalize_prompt_asset_type(asset_type)
    fields = {
        "sprite": ("sprite_prompt_command", "sprite_prompt_example"),
        "background": ("background_prompt_command", "background_prompt_example"),
        "appearance": ("appearance_prompt_command", "appearance_prompt_example"),
    }[normalized_type]
    profile = {
        "style": clean(style.get(fields[0])),
        "example": clean(style.get(fields[1])),
    }
    if profile["style"] or profile["example"]:
        return profile

    if normalized_type == "appearance":
        sprite_profile = {
            "style": clean(style.get("sprite_prompt_command")),
            "example": clean(style.get("sprite_prompt_example")),
        }
        if sprite_profile["style"] or sprite_profile["example"]:
            return sprite_profile

    workbench_id = visual_style_workbench(style, settings, "background" if normalized_type == "background" else "sprite")
    return sprite_prompt_profile(settings, workbench_id)


def normalize_prompt_asset_type(asset_type):
    text = str(asset_type or "").strip().lower()
    aliases = {
        "sprites": "sprite",
        "sprite": "sprite",
        "character": "sprite",
        "characters": "sprite",
        "cenario": "background",
        "cenarios": "background",
        "cenário": "background",
        "cenários": "background",
        "background": "background",
        "backgrounds": "background",
        "appearance": "appearance",
        "appearances": "appearance",
        "aparencia": "appearance",
        "aparencias": "appearance",
        "aparência": "appearance",
        "aparências": "appearance",
    }
    return aliases.get(text, "sprite")


def apply_creation_sprite_prompts(payload, settings):
    settings = settings or db.get_settings()
    visual_style = db.get_visual_style((payload or {}).get("visual_style_id"))
    workbench_id = sprite_workbench_for_story_payload(payload, settings)
    participation_mode = db.normalize_participation_mode(payload.get("participation_mode") or payload.get("point_of_view"))
    characters = []
    player = payload.get("player_character")
    if isinstance(player, dict) and player:
        if participation_mode == "first_person":
            player["visual_prompt"] = ""
        else:
            characters.append(player)
    characters.extend(character for character in payload.get("characters") or [] if isinstance(character, dict))
    for character in characters:
        apply_character_sprite_prompt(
            character,
            settings,
            workbench_id=workbench_id,
            prompt_asset_type="sprite",
            visual_style=visual_style,
        )


def apply_character_sprite_prompt(character, settings=None, story_id=None, expression="neutral", workbench_id=None, prompt_asset_type="sprite", visual_style=None):
    settings = settings or db.get_settings()
    workbench_id = workbench_id if workbench_id is not None else sprite_workbench_for_story_id(story_id, settings)
    visual_style = visual_style if visual_style is not None else (db.visual_style_for_story(story_id) if story_id else None)
    prompt_profile = prompt_profile_from_visual_style(visual_style, settings, prompt_asset_type)
    if not (prompt_profile.get("style") or prompt_profile.get("example")) and workbench_id:
        prompt_profile = sprite_prompt_profile(settings, workbench_id)
    source_prompt = build_sprite_source_prompt(character, expression, "")
    fallback = clean(character.get("visual_prompt"))
    character["visual_prompt"] = generate_workbench_visual_prompt(
        source_prompt,
        "sprite",
        workbench_id,
        prompt_profile,
        fallback,
        story_id=story_id,
        ai_role="story",
    )
    return character


def generate_character_expression_prompts(story_id, character_ids=None, only_missing=True, ai_role="story"):
    story = db.get_story(story_id)
    if not story:
        raise ValueError("Historia nao encontrada.")
    requested_ids = {str(item) for item in (character_ids or []) if str(item or "").strip()}
    characters = []
    for character in story.get("characters") or []:
        if requested_ids and character.get("id") not in requested_ids:
            continue
        if story.get("participation_mode") == "first_person" and character.get("is_player"):
            continue
        if only_missing and expression_prompts_complete(character.get("expression_prompts")):
            continue
        characters.append(character)
    if not characters:
        return story

    settings = ai_client.settings_for_ai_role(db.get_settings(), ai_role or "story")
    visual_style = story.get("visual_style_record") or db.visual_style_for_story(story_id) or {}
    character_sources = [
        {
            "character_id": character.get("id"),
            "name": character.get("name"),
            "personality": character.get("personality"),
            "role": character.get("role"),
            "relationship": character.get("relationship"),
            "speech_style": character.get("speech_style"),
        }
        for character in characters
    ]
    style_context = {
        "name": visual_style.get("name") or story.get("visual_style") or "",
    }
    system = (
        "You create character-specific expression editing prompts for visual novel sprites. "
        "Return one valid JSON object only. Do not use markdown. All prompt values must be in English. "
        "Every prompt must be short and tailored only to that character's personality, temperament, and emotional behavior. "
        "Describe only the new facial expression and a simple pose, body-language cue, or hand gesture. Change only expression and pose. "
        "Never describe or redesign the character's face, hair, body, skin, species, gender, clothing, accessories, tattoos, colors, lighting, background, camera, framing, or art style. "
        "Never include image-generation quality tags, model tags, years, scores, artist/style tags, or the character's base visual description. "
        "Use at most 45 words before the preservation clause. "
        "Every prompt must end with this exact preservation clause: keep the same character, same face, same hairstyle, same outfit, same body, same proportions, same visual style, same framing. "
        "Do not add neutral and do not reuse identical prompts across characters."
    )
    user = (
        "Return this exact structure for every supplied character:\n"
        '{"characters":[{"character_id":"...","name":"...","expression_prompts":'
        '{"happy":"...","sad":"...","angry":"...","thoughtful":"...","surprised":"...","embarrassed":"...","scared":"..."}}]}\n\n'
        f"Selected visual style name (context only; do not repeat it in prompts):\n{json.dumps(style_context, ensure_ascii=False)}\n\n"
        f"Characters:\n{json.dumps(character_sources, ensure_ascii=False)}"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    request_log = {
        "story_id": story_id,
        "character_ids": [character.get("id") for character in characters],
        "visual_style_id": visual_style.get("id") or story.get("visual_style_id") or "",
        "model": settings.get("ollama_model"),
    }
    db.add_api_log("ollama", "expression_prompts_generation_started", request_log, status="started", story_id=story_id)
    try:
        result = chat_json(settings.get("ollama_url"), settings.get("ollama_model"), messages, 0.3, settings=settings)
        generated = result.get("characters") if isinstance(result, dict) else None
        if not isinstance(generated, list):
            raise ValueError("Resposta sem a lista characters.")
        generated_by_id = {clean(item.get("character_id")): item for item in generated if isinstance(item, dict) and clean(item.get("character_id"))}
        generated_by_name = {normalize_person_key(item.get("name")): item for item in generated if isinstance(item, dict) and normalize_person_key(item.get("name"))}
        seen_prompts = set()
        for character in characters:
            item = generated_by_id.get(character.get("id")) or generated_by_name.get(normalize_person_key(character.get("name")))
            prompts = normalize_generated_expression_prompts((item or {}).get("expression_prompts"))
            missing = [key for key in CHARACTER_EXPRESSION_KEYS if not prompts.get(key)]
            if missing:
                raise ValueError(f"Prompts ausentes para {character.get('name')}: {', '.join(missing)}.")
            for expression, prompt in prompts.items():
                validate_generated_expression_prompt(prompt, character.get("name"), expression)
                normalized_prompt = folded_match_text(prompt)
                if normalized_prompt in seen_prompts:
                    raise ValueError(f"Prompt duplicado entre personagens: {character.get('name')} / {expression}.")
                seen_prompts.add(normalized_prompt)
            db.update_character(character.get("id"), {"expression_prompts": prompts})
            db.add_api_log(
                "ollama",
                "expression_prompts_generated_for_character",
                {"character_id": character.get("id"), "character_name": character.get("name")},
                {"expression_prompts": prompts},
                story_id=story_id,
            )
        updated = db.get_story(story_id)
        db.add_api_log(
            "ollama",
            "expression_prompts_generation_finished",
            request_log,
            {"generated_count": len(characters)},
            story_id=story_id,
        )
        return updated
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "expression_prompts_generation_failed",
            request_log,
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        raise RuntimeError(f"Nao foi possivel gerar os prompts de expressao: {exc}") from exc


def normalize_generated_expression_prompts(value):
    source = value if isinstance(value, dict) else {}
    return {key: clean(source.get(key)) for key in CHARACTER_EXPRESSION_KEYS}


def expression_prompts_complete(value):
    prompts = normalize_generated_expression_prompts(value)
    return all(expression_prompt_is_edit_only(prompts.get(key)) for key in CHARACTER_EXPRESSION_KEYS)


def validate_generated_expression_prompt(prompt, character_name, expression):
    text = clean(prompt)
    required = [
        "same character",
        "same face",
        "same hairstyle",
        "same outfit",
        "same body",
        "same proportions",
        "same visual style",
        "same framing",
    ]
    missing = [marker for marker in required if marker not in text.lower()]
    if missing:
        raise ValueError(
            f"Prompt invalido para {character_name} / {expression}: preservacao ausente ({', '.join(missing)})."
        )
    if looks_portuguese_text(text):
        raise ValueError(f"Prompt invalido para {character_name} / {expression}: o texto deve estar em ingles.")
    if not expression_prompt_is_edit_only(text):
        raise ValueError(
            f"Prompt invalido para {character_name} / {expression}: deve conter somente expressao, pose e preservacao."
        )


def expression_prompt_is_edit_only(prompt):
    text = clean(prompt)
    if not text:
        return False
    lowered = text.lower()
    forbidden = [
        "masterpiece",
        "best quality",
        "score_",
        "year 20",
        "visual novel sprite",
        "single character",
        "realistic anime",
        "watercolor",
        "cinematic lighting",
        "detailed iris",
        "highly detailed",
        "wearing ",
        "waist-up",
        "full body",
        "half body",
        "from head to",
    ]
    if any(marker in lowered for marker in forbidden):
        return False
    preservation_clause = (
        "keep the same character, same face, same hairstyle, same outfit, same body, "
        "same proportions, same visual style, same framing"
    )
    if preservation_clause not in lowered:
        return False
    content = lowered.split("keep the same character", 1)[0]
    return len(re.findall(r"\b[\w'-]+\b", content)) <= 45


def sprite_workbench_for_story_payload(payload, settings):
    style = db.get_visual_style((payload or {}).get("visual_style_id"))
    return visual_style_workbench(style, settings, "sprite")


def sprite_workbench_for_story_id(story_id, settings):
    style = db.visual_style_for_story(story_id)
    return visual_style_workbench(style, settings, "sprite")


def visual_style_workbench(style, settings=None, asset_type="sprite"):
    settings = settings or db.get_settings()
    style = style or {}
    normalized = normalize_prompt_asset_type(asset_type)
    if normalized == "background":
        return style.get("background_workbench") or settings.get("comfy_background_workbench") or ""
    if normalized == "appearance":
        return style.get("appearance_workbench") or style.get("sprite_workbench") or settings.get("comfy_sprite_workbench") or ""
    return style.get("sprite_workbench") or settings.get("comfy_sprite_workbench") or ""


def merge_character_enrichment(original, enriched):
    original = dict(original or {})
    enriched = enriched if isinstance(enriched, dict) else {}
    for field in [
        "species",
        "gender",
        "character_type",
        "aliases",
        "description",
        "physical",
        "appearance",
        "personality",
        "clothing",
        "role",
        "relationship",
        "secrets",
        "speech_style",
        "visual_prompt",
    ]:
        value = enriched.get(field)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if clean(str(item)))
        if not clean(original.get(field)) and clean(value):
            original[field] = clean(value)
    if not clean(original.get("physical")) and clean(original.get("appearance")):
        original["physical"] = clean(original.get("appearance"))
    if not clean(original.get("description")) and clean(original.get("background")):
        original["description"] = clean(original.get("background"))
    return original


def complete_character_record(character, story=None, scene=None, is_player=False):
    character = dict(character or {})
    if not clean(character.get("physical")) and clean(character.get("appearance")):
        character["physical"] = clean(character.get("appearance"))
    if not clean(character.get("description")) and clean(character.get("background")):
        character["description"] = clean(character.get("background"))
    if not clean(character.get("character_type")) and clean(character.get("role")):
        character["character_type"] = clean(character.get("role"))
    return character


def validate_ai_character_record(character, label="personagem", require_visual_prompt=True):
    character = character if isinstance(character, dict) else {}
    required = ["name", "description", "physical", "personality", "clothing", "role"]
    if require_visual_prompt:
        required.append("visual_prompt")
    missing = [field for field in required if not clean(character.get(field))]
    if missing:
        raise ValueError(f"Resposta de IA invalida para {label}: campos ausentes: {', '.join(missing)}.")


def looks_portuguese_text(value):
    raw_text = clean(value).lower()
    text = folded_match_text(raw_text)
    if not text:
        return False
    markers = [
        "aparencia",
        "aparência",
        "roupa",
        "vestimenta",
        "olhos",
        "cabelo",
        "pele",
        "homem",
        "mulher",
        "jovem",
        "idoso",
        "idosa",
        "personagem",
        "corpo inteiro",
        "frente",
        "masculino",
        "feminino",
        "couro",
        "manto",
        "fivela",
        "botas",
        "gastas",
        "remendada",
        "maos",
        "antebraco",
        "castanhos",
        "cansados",
    ]
    words = set(re.findall(r"[a-zA-ZÀ-ÿ0-9]+", text))
    for marker in markers:
        folded_marker = folded_match_text(marker)
        if not folded_marker:
            continue
        if " " in folded_marker:
            if re.search(rf"(?<!\w){re.escape(folded_marker)}(?!\w)", text):
                return True
            continue
        if folded_marker in words:
            return True
    return any(char in raw_text for char in "ãõçáéíóúâêô")


def enrich_introduced_character(story, scene, payload):
    candidate = introduced_candidate_from_payload(payload)
    if not clean(candidate.get("name")):
        candidate["name"] = clean(payload.get("name"))
    settings = ai_client.settings_for_ai_role(db.get_settings(), "scene")
    visual_style = db.visual_style_for_story((story or {}).get("id"))
    workbench_id = visual_style_workbench(visual_style, settings, "sprite")
    prompt_profile = prompt_profile_from_visual_style(visual_style, settings, "sprite")
    scene = scene or {}
    story = story or {}
    language = story_language(story)
    system = (
        "You create a complete visual novel character record for a newly introduced speaker. "
        f"Return only valid JSON. All narrative fields must be written in {language_instruction(language)}. "
        "Write visual_prompt entirely in English for a ComfyUI visual novel sprite. "
        "Do not leave generic placeholders. Do not use a different language for narrative fields."
    )
    user = (
        "Required JSON format:\n"
        "{"
        "\"name\":\"\", \"species\":\"\", \"gender\":\"\", \"character_type\":\"\", "
        "\"aliases\":\"\", \"description\":\"\", \"physical\":\"\", \"personality\":\"\", "
        "\"clothing\":\"\", \"role\":\"\", \"relationship\":\"\", \"speech_style\":\"\", "
        "\"visual_prompt\":\"\""
        "}\n\n"
        "Create a character who belongs to this world and story, not just someone who appeared in the scene. "
        "The description must explain their apparent place in the setting, the tension they bring, and one or two concrete details that make them memorable. "
        "Personality must include motivation, contradiction, and how they react under pressure. "
        "Role and relationship must connect them to the current conflict or protagonist. "
        "Speech style must describe rhythm, vocabulary, emotional restraint, or verbal habits. "
        "If the candidate only contains a weak phrase such as 'personagem presente em cena' or 'apareceu surpreso', ignore that weakness and infer from the story, scene text, and dialogue. "
        f"Narrative fields must be in {language_instruction(language)}: species, gender, character_type, aliases, description, physical, personality, clothing, role, relationship, secrets, speech_style. "
        "Do not leave any field empty.\n\n"
        "For visual_prompt, use only species, gender, physical, and clothing as source. "
        "Do not use personality, role, relationship, backstory, aliases, or secrets in visual_prompt. "
        "visual_prompt must include one character only, full-body, standing, front-view visual novel sprite framing.\n\n"
        f"Sprite workbench prompt style:\n{prompt_profile.get('style') or '(natural-language sprite prompt)'}\n\n"
        f"Sprite workbench example:\n{prompt_profile.get('example') or '(none)'}\n\n"
        f"Story title: {story.get('title') or ''}\n"
        f"Genre: {story.get('genre') or ''}\n"
        f"Tone: {story.get('tone') or ''}\n"
        f"Visual style: {story.get('visual_style') or ''}\n"
        f"Lore: {clean(story.get('lore'))[:1000]}\n\n"
        f"Current scene title: {scene.get('title') or ''}\n"
        f"Current scene text: {clean(scene.get('scene_text'))[:1000]}\n"
        f"Current scene dialogues: {json.dumps((scene.get('dialogues') or [])[-6:], ensure_ascii=False)}\n"
        f"Current characters on screen: {json.dumps(scene.get('characters_on_screen') or [], ensure_ascii=False)}\n\n"
        f"New speaker candidate:\n{json.dumps(candidate, ensure_ascii=False)}"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        db.add_api_log(
            "ollama",
            "chat:introduced-character",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "candidate": candidate},
            status="started",
            story_id=story.get("id"),
        )
        result = chat_json(settings.get("ollama_url"), settings.get("ollama_model"), messages, 0.4, settings=settings)
        db.add_api_log(
            "ollama",
            "chat:introduced-character",
            {"model": settings.get("ollama_model"), "workbench": workbench_id},
            result,
            story_id=story.get("id"),
        )
        character = merge_introduced_character(candidate, result if isinstance(result, dict) else {})
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:introduced-character",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "candidate": candidate},
            status="error",
            error=str(exc),
            story_id=story.get("id"),
        )
        raise RuntimeError(f"IA de narrativa falhou ao criar personagem: {exc}") from exc
    character = complete_character_record(character, story, scene)
    validate_ai_character_record(character, "personagem introduzido")
    apply_character_sprite_prompt(character, settings, story_id=story.get("id"))
    character["importance"] = character.get("importance") or "secondary"
    character["is_player"] = 0
    return character


def introduced_candidate_from_payload(payload):
    payload = payload if isinstance(payload, dict) else {}
    source = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else payload
    name = (
        clean(payload.get("name")) or
        clean(source.get("display_name")) or
        clean(source.get("temporary_name")) or
        clean(source.get("name"))
    )
    return {
        "name": name,
        "species": clean(source.get("species")),
        "gender": clean(source.get("gender")),
        "character_type": clean(source.get("character_type") or source.get("type")),
        "aliases": clean(source.get("aliases")),
        "description": meaningful_character_text(source.get("description") or source.get("suggested_description")),
        "physical": clean(source.get("physical") or source.get("appearance") or source.get("suggested_physical")),
        "personality": clean(source.get("personality") or source.get("suggested_personality")),
        "clothing": clean(source.get("clothing") or source.get("outfit") or source.get("suggested_clothing")),
        "role": clean(source.get("role") or source.get("suggested_role")),
        "relationship": clean(source.get("relationship") or source.get("suggested_relationship") or source.get("reason")),
        "speech_style": clean(source.get("speech_style") or source.get("suggested_speech_style")),
        "visual_prompt": clean(source.get("visual_prompt") or source.get("suggested_visual_prompt")),
        "importance": clean(source.get("importance")) or "secondary",
    }


def merge_introduced_character(original, enriched):
    character = dict(original or {})
    enriched = enriched if isinstance(enriched, dict) else {}
    for field in [
        "name",
        "species",
        "gender",
        "character_type",
        "aliases",
        "description",
        "physical",
        "appearance",
        "personality",
        "clothing",
        "role",
        "relationship",
        "speech_style",
        "visual_prompt",
    ]:
        value = enriched.get(field)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if clean(str(item)))
        if clean(value):
            target = "physical" if field == "appearance" and not clean(character.get("physical")) else field
            character[target] = clean(value)
    return character


def meaningful_character_text(value):
    value = clean(value)
    if not value or is_generic_introduced_text(value):
        return ""
    return value


def is_generic_introduced_text(value):
    text = clean(value).lower()
    if not text:
        return True
    generic_patterns = [
        "personagem presente em cena",
        "personagem introduzido nesta cena",
        "personagem introduzido falando",
        "com expressao",
        "com expressão",
        "apareceu na cena",
        "presente na cena",
        "personagem secundario",
        "personagem secundário",
    ]
    return any(pattern in text for pattern in generic_patterns) and len(text) < 180


def character_text(character):
    return " ".join(
        clean(character.get(field)).lower()
        for field in ["name", "role", "description", "background", "appearance", "physical", "personality", "clothing"]
        if clean(character.get(field))
    )


def improve_text(payload):
    text = clean(payload.get("text"))
    if not text:
        raise ValueError("Texto ausente para melhoria por IA.")

    settings = ai_client.settings_for_ai_role(db.get_settings(), "scene")
    output_language = language_instruction(settings.get("default_language"))
    field_label = clean(payload.get("field_label")) or "field"
    field_type = clean(payload.get("field_type")) or "description"
    story_context = payload.get("story_context") or {}
    messages = [
        {"role": "system", "content": IMPROVE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Field type: {field_type}\n"
                f"Field label: {field_label}\n"
                f"Requested output language: {output_language}\n"
                f"Story/character context: {story_context}\n\n"
                f"Original text:\n{text}\n\n"
                "Improve the text now. Keep the output language required by the system rules."
            ),
        },
    ]

    try:
        db.add_api_log(
            "ollama",
            "chat:improve",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="started",
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            active_text_temperature(settings),
            ollama_generation_options(settings, 1600),
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:improve",
            {"model": settings.get("ollama_model"), "messages": messages},
            result,
        )
        improved = clean(result.get("improved_text"))
        if not improved:
            raise ValueError("Resposta de melhoria invalida: campo improved_text vazio.")
        return {"improved_text": improved}
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:improve",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="error",
            error=str(exc),
        )
        raise RuntimeError(f"IA de melhoria de texto falhou: {exc}") from exc


def improve_visual_prompt(text, context=None):
    text = clean(text)
    if not text:
        raise ValueError("Texto ausente para prompt visual por IA.")
    settings = ai_client.settings_for_ai_role(db.get_settings(), "scene")
    messages = [
        {
            "role": "system",
            "content": (
                "You convert descriptions into strong SDXL anime visual novel prompts. "
                "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
                "For characters, write comma-separated booru-style English tags, not prose. "
                "Always include gender/age/body/face/hair/outfit/expression/pose when known. "
                "Use tags like: 1boy, 1girl, old man, mature male, bald, narrow eyes, full body, standing, visual novel sprite. "
                "For environments, write concise English visual tags and composition. "
                "Preserve fixed traits and avoid copyrighted artist names."
            ),
        },
        {
            "role": "user",
            "content": f"Context: {context or {}}\nDescription:\n{text}\n\nCreate the visual prompt.",
        },
    ]
    try:
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            0.35,
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:visual-prompt",
            {"model": settings.get("ollama_model"), "messages": messages},
            result,
        )
        visual_prompt = sanitize_visual_prompt(extract_visual_prompt(result), text, context)
        if not visual_prompt:
            raise ValueError("Resposta de prompt visual invalida: visual_prompt vazio.")
        return visual_prompt
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:visual-prompt",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="error",
            error=str(exc),
        )
        raise RuntimeError(f"IA de prompt visual falhou: {exc}") from exc


def generate_workbench_visual_prompt(source_text, asset_type, workbench_id, prompt_profile, existing_prompt="", story_id=None, ai_role="scene"):
    source_text = clean(source_text)
    existing_prompt = clean(existing_prompt) or source_text
    prompt_profile = prompt_profile if isinstance(prompt_profile, dict) else {}
    style = clean(prompt_profile.get("style"))
    example = clean(prompt_profile.get("example"))
    if not source_text:
        raise ValueError("Texto fonte ausente para gerar prompt visual.")
    if not (style or example):
        if asset_type == "background":
            visual_prompt = normalize_background_visual_prompt(existing_prompt or source_text)
        else:
            visual_prompt = clean(existing_prompt)
        if not visual_prompt:
            raise ValueError("Perfil de prompt ausente e nenhum prompt visual existente foi informado.")
        return visual_prompt

    settings = ai_client.settings_for_ai_role(db.get_settings(), ai_role or "scene")
    source_clothing = extract_source_clothing(source_text)
    translated_clothing = translate_clothing_description_for_prompt(source_clothing, settings, story_id) if source_clothing and asset_type == "sprite" else ""
    if asset_type == "background":
        system = (
            "You adapt visual generation requests for a specific ComfyUI workflow. "
            "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
            "The visual_prompt must follow the workflow prompt style exactly. "
            "Create only an environment/background prompt for visual novel background generation. "
            "Do not name a visual style such as anime, painterly, retro, cinematic, comic, realistic, or similar. The selected style will be added later through the configured background prefix/suffix. "
            "Do not include main characters, foreground people, detailed faces, portraits, bodies in the foreground, or human actions. "
            "If the location would feel artificial when completely empty, you may include only subtle ambient extras such as distant pedestrians, blurred background customers, small background crowd, or indistinct far-background silhouettes. "
            "Any people must be secondary, small, background-only, not centered, not detailed, and must not compete with visual novel sprites. "
            "For intimate, isolated, dramatic, secret, mysterious, or character-focused scenes, prefer no people. "
            "Describe location, architecture, layout, props, materials, lighting, atmosphere, color palette, and depth. "
            "The visual_prompt must be detailed, entirely in English, and suitable for a static wide background. "
            "Use concrete visual details. Do not output abstract instructions such as unique memorable landmark, environmental storytelling objects, or details tied to story conflict. "
            "Do not add copyrighted artist names, watermarks, UI text, or camera metadata."
        )
    else:
        system = (
            "You adapt visual generation requests for a specific ComfyUI workflow. "
            "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
            "The visual_prompt must follow the workflow prompt style exactly. "
            "Preserve fixed character identity traits and requested expression. "
            "For character sprites, Clothing is a mandatory fixed visual trait: keep its concrete garments, colors, materials, accessories, and silhouette. "
            "Never replace the supplied Clothing with clothing from the example prompt or with a generic outfit. "
            "If a separate English clothing translation is supplied, use that translation as the outfit source of truth. "
            "Do not copy untranslated Portuguese clothing prose into the final prompt. "
            "Do not add extra characters, copyrighted artist names, watermarks, UI text, or camera metadata. "
            "The visual_prompt must be entirely in English. Translate any Portuguese source fields into English."
        )
    user_sections = [
        f"Asset type: {asset_type}\nWorkbench id: {workbench_id}",
        f"Prompt style instructions:\n{style or '(none)'}",
    ]
    if example:
        user_sections.append(f"Example prompt for this workbench:\n{example}")
    user_sections.append(f"Source description to convert:\n{source_text}")
    if asset_type == "background" and existing_prompt:
        user_sections.append(f"Existing prompt if useful:\n{existing_prompt}")
    user = "\n\n".join(user_sections)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "messages": messages},
            status="started",
            story_id=story_id,
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            0.3,
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "messages": messages},
            result,
            story_id=story_id,
        )
        visual_prompt = clean(extract_visual_prompt(result))
        if not visual_prompt:
            raise ValueError("Resposta de workbench invalida: visual_prompt vazio.")
        if asset_type == "sprite" and prompt_profile_requests_natural_language(style, example) and looks_like_comma_tag_prompt(visual_prompt):
            retry_prompt = retry_natural_language_workbench_prompt(
                source_text,
                workbench_id,
                style,
                example,
                translated_clothing,
                visual_prompt,
                settings,
                story_id,
            )
            if retry_prompt:
                visual_prompt = retry_prompt
            else:
                raise ValueError("IA nao conseguiu adaptar o prompt ao estilo natural-language configurado.")
        if asset_type == "sprite" and looks_portuguese_text(visual_prompt):
            repaired_prompt = repair_mixed_language_visual_prompt(
                visual_prompt,
                source_text,
                translated_clothing,
                settings,
                story_id,
            )
            if repaired_prompt:
                visual_prompt = repaired_prompt
            else:
                raise ValueError("IA nao conseguiu reparar o prompt visual em ingles.")
        if asset_type == "background":
            return normalize_background_visual_prompt(visual_prompt)
        return finalize_sprite_workbench_prompt(visual_prompt, source_text, translated_clothing, prompt_profile)
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "messages": messages},
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        raise RuntimeError(f"IA de prompt visual falhou: {exc}") from exc


def prompt_profile_requests_natural_language(style, example=""):
    text = folded_match_text(f"{style} {example}")
    markers = [
        "natural-language",
        "natural language",
        "detailed natural-language",
        "detailed text",
        "descriptive text",
        "complete descriptive sentences",
        "complete sentences",
        "descriptive sentences",
        "not only comma tags",
        "do not use short booru tag",
        "do not use tags",
        "not a tag list",
        "no tag list",
        "texto detalhado",
        "detalhadamente em texto",
        "prompt textual",
        "prompts textuais",
        "em texto",
        "enriqueca o prompt",
        "com detalhes",
        "frases completas",
        "nao use tags",
        "sem tags",
        "nao apenas tags",
        "nao somente tags",
    ]
    return any(marker in text for marker in markers)


def folded_match_text(value):
    text = clean(value).lower()
    return "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def looks_like_comma_tag_prompt(prompt):
    text = clean(prompt)
    if len(text) < 40 or "," not in text:
        return False
    segments = [segment.strip() for segment in text.split(",") if segment.strip()]
    if len(segments) < 6:
        return False
    short_segments = sum(1 for segment in segments if len(segment.split()) <= 5)
    sentence_marks = sum(text.count(mark) for mark in ".;")
    return short_segments / len(segments) >= 0.75 and sentence_marks <= max(1, len(segments) // 6)


def retry_natural_language_workbench_prompt(source_text, workbench_id, style, example, translated_clothing, rejected_prompt, settings=None, story_id=None):
    settings = settings or db.get_settings()
    messages = [
        {
            "role": "system",
            "content": (
                "You repair image prompt style violations. "
                "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
                "Rewrite the prompt as detailed natural-language English prose with complete descriptive sentences. "
                "Do not output a comma-separated tag list or booru tags. "
                "Preserve the same character identity, clothing, expression, pose, and visual novel sprite framing."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Workbench id: {workbench_id}\n\n"
                f"Prompt style instructions:\n{style or '(none)'}\n\n"
                f"Example prompt for this workbench:\n{example or '(none)'}\n\n"
                f"Source description:\n{source_text}\n\n"
                f"English clothing translation:\n{translated_clothing or '(not available; translate the clothing yourself)'}\n\n"
                f"Rejected tag-style prompt:\n{rejected_prompt}\n\n"
                "Return one detailed English visual_prompt in full sentences, not tags."
            ),
        },
    ]
    try:
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt-style-retry",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "messages": messages},
            status="started",
            story_id=story_id,
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            0.2,
            ollama_generation_options(settings, 700),
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt-style-retry",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "rejected_prompt": rejected_prompt},
            result,
            story_id=story_id,
        )
        return clean(extract_visual_prompt(result))
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt-style-retry",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "messages": messages},
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        raise RuntimeError(f"IA de reparo de estilo do prompt visual falhou: {exc}") from exc


def finalize_sprite_workbench_prompt(prompt, source_text, translated_clothing="", prompt_profile=None):
    prompt_profile = prompt_profile if isinstance(prompt_profile, dict) else {}
    style = prompt_profile.get("style") or ""
    example = prompt_profile.get("example") or ""
    if prompt_profile_requests_natural_language(style, example):
        if looks_like_comma_tag_prompt(prompt):
            prompt = naturalize_tag_sprite_prompt(prompt, omit_background=prompt_profile_avoids_background(style, example))
        return reinforce_required_clothing_natural(prompt, source_text, translated_clothing)
    return reinforce_required_clothing(prompt, source_text, translated_clothing)


def prompt_profile_avoids_background(style, example=""):
    text = folded_match_text(f"{style} {example}")
    markers = [
        "nao mencione fundo",
        "nao mencione o fundo",
        "sem fundo",
        "apenas o personagem",
        "only the character",
        "do not mention background",
        "no background",
    ]
    return any(marker in text for marker in markers)


def naturalize_tag_sprite_prompt(prompt, omit_background=False):
    tags = [clean(tag) for tag in str(prompt or "").split(",") if clean(tag)]
    if not tags:
        return clean(prompt)
    skip = {
        "solo",
        "single character",
        "full body",
        "standing",
        "front view",
        "visual novel sprite",
        "simple light gray background",
        "simple background",
        "clean lineart",
        "detailed face",
        "detailed eyes",
        "clean silhouette",
    }
    expression = next((tag for tag in tags if "expression" in tag.lower()), "")
    details = [
        tag for tag in tags
        if tag.lower() not in skip
        and not re.match(r"^\d+\s*(boy|girl|person|man|woman)s?$", tag.lower())
        and not tag.lower().startswith("exact outfit:")
    ]
    if expression:
        details = [tag for tag in details if tag != expression]
    detail_text = ", ".join(details[:18])
    sentences = [
        (
            "A single character is shown as a full-body visual novel sprite, standing in a front-facing pose."
            if omit_background
            else "A single character is shown as a full-body visual novel sprite, standing in a front-facing pose on a simple light background."
        ),
    ]
    if detail_text:
        sentences.append(f"The character's visible design includes {detail_text}.")
    if expression:
        sentences.append(f"The character wears a {expression.replace(' expression', '')} expression.")
    sentences.append("The composition should keep a clean silhouette, clear facial detail, and polished anime visual-novel linework.")
    return " ".join(sentences)


def build_sprite_source_prompt(character, expression=None, user_prompt=""):
    character = character or {}
    parts = []
    for label, value in [
        ("Species", character.get("species")),
        ("Gender", character.get("gender")),
        ("Physical appearance", character.get("physical")),
        ("Clothing - mandatory fixed outfit, preserve exactly and translate to English", character.get("clothing")),
    ]:
        value = clean(value)
        if value:
            parts.append(f"{label}: {value}")
    return "\n".join(parts)


def build_sprite_visual_prompt(character, expression=None, user_prompt=""):
    character = character or {}
    tags = [
        "single character",
        "visual novel sprite",
    ]
    for value in [
        character.get("species"),
        character.get("gender"),
        character.get("physical"),
        character.get("clothing"),
    ]:
        text = clean(value)
        if text:
            tags.append(text)
    expression = clean(expression)
    if expression and expression != "neutral":
        tags.append(f"{expression} expression")
    user_prompt = clean(user_prompt)
    if user_prompt:
        tags.append(user_prompt)
    tags.append("clean silhouette")
    tags.append("clear facial detail")
    tags.append("polished anime visual novel linework")
    return ", ".join(dedupe_text_parts(tags))


def dedupe_text_parts(parts):
    seen = set()
    output = []
    for part in parts:
        text = clean(part)
        key = folded_match_text(text)
        if text and key not in seen:
            seen.add(key)
            output.append(text)
    return output


def translate_clothing_description_for_prompt(clothing, settings=None, story_id=None):
    clothing = clean(clothing)
    if not clothing:
        return ""
    settings = settings or db.get_settings()
    messages = [
        {
            "role": "system",
            "content": (
                "You translate character clothing descriptions into concise English visual-generation prompt text. "
                "Return only valid JSON: {\"clothing_prompt\":\"...\"}. "
                "Preserve every concrete garment, color, material, accessory, and silhouette. "
                "Fix obvious mistranslations and wording mistakes, but do not invent new outfit pieces. "
                "Use natural English tags or short garment phrases suitable for an anime visual novel sprite prompt."
            ),
        },
        {
            "role": "user",
            "content": f"Clothing description:\n{clothing}\n\nTranslate and normalize only this outfit.",
        },
    ]
    try:
        db.add_api_log(
            "ollama",
            "chat:clothing-prompt",
            {"model": settings.get("ollama_model"), "messages": messages, "clothing": clothing},
            status="started",
            story_id=story_id,
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            0.2,
            ollama_generation_options(settings, 300),
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:clothing-prompt",
            {"model": settings.get("ollama_model"), "clothing": clothing},
            result,
            story_id=story_id,
        )
        translated = clean(result.get("clothing_prompt") if isinstance(result, dict) else "")
        if not translated or looks_portuguese_text(translated):
            raise ValueError("Resposta de traducao de roupa invalida.")
        return translated
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:clothing-prompt",
            {"model": settings.get("ollama_model"), "messages": messages, "clothing": clothing},
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        raise RuntimeError(f"IA de traducao de roupa falhou: {exc}") from exc


def repair_mixed_language_visual_prompt(prompt, source_text, translated_clothing="", settings=None, story_id=None):
    prompt = clean(prompt)
    if not prompt:
        return ""
    settings = settings or db.get_settings()
    messages = [
        {
            "role": "system",
            "content": (
                "You repair mixed-language image prompts. "
                "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
                "Rewrite the entire prompt in English. Preserve character identity, pose, framing, expression, and outfit. "
                "Use concise comma-separated visual tags or short English garment phrases. "
                "Do not add new clothing, scenery, extra characters, UI text, or copyrighted artist names."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Prompt to repair:\n{prompt}\n\n"
                f"Original source description:\n{source_text}\n\n"
                f"English clothing translation if available:\n{translated_clothing or '(none)'}\n\n"
                "Return one clean English visual prompt."
            ),
        },
    ]
    try:
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt-repair",
            {"model": settings.get("ollama_model"), "messages": messages, "prompt": prompt},
            status="started",
            story_id=story_id,
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            0.15,
            ollama_generation_options(settings, 500),
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt-repair",
            {"model": settings.get("ollama_model"), "prompt": prompt},
            result,
            story_id=story_id,
        )
        repaired = clean(extract_visual_prompt(result))
        if not repaired or looks_portuguese_text(repaired):
            raise ValueError("Resposta de reparo de prompt visual invalida.")
        return repaired
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt-repair",
            {"model": settings.get("ollama_model"), "messages": messages, "prompt": prompt},
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        raise RuntimeError(f"IA de reparo de prompt visual falhou: {exc}") from exc


def reinforce_required_clothing(prompt, source_text, translated_clothing=""):
    prompt = clean(prompt)
    clothing = extract_source_clothing(source_text)
    required_clothing = clean(translated_clothing) or clothing
    if not required_clothing:
        return prompt
    if clothing_already_present(prompt, required_clothing) or (clothing and clothing_already_present(prompt, clothing)):
        return prompt
    if looks_portuguese_text(required_clothing) and not looks_portuguese_text(prompt):
        return prompt
    required = required_clothing_prompt(required_clothing)
    return dedupe_tags([prompt, required])


def reinforce_required_clothing_natural(prompt, source_text, translated_clothing=""):
    prompt = clean(prompt)
    clothing = extract_source_clothing(source_text)
    required_clothing = clean(translated_clothing) or clothing
    if not required_clothing:
        return prompt
    if clothing_already_present(prompt, required_clothing) or (clothing and clothing_already_present(prompt, clothing)):
        return prompt
    if looks_portuguese_text(required_clothing) and not looks_portuguese_text(prompt):
        return prompt
    if not prompt:
        return f"A single character is shown as a full-body visual novel sprite. The outfit must preserve exactly: {required_clothing}."
    suffix = "" if prompt.endswith((".", "!", "?")) else "."
    return f"{prompt}{suffix} The outfit must preserve exactly: {required_clothing}."


def extract_source_clothing(source_text):
    text = str(source_text or "")
    for line in text.splitlines():
        if line.lower().startswith("clothing"):
            _, _, value = line.partition(":")
            return clean(value)
    return ""


def clothing_already_present(prompt, clothing):
    prompt_text = clean(prompt).lower()
    clothing_text = clean(clothing).lower()
    if not prompt_text or not clothing_text:
        return False
    markers = clothing_markers(clothing_text)
    matched = {marker for marker in markers if marker and marker in prompt_text}
    if not matched:
        return False
    specific = matched - nonspecific_clothing_markers()
    return bool(specific) or len(matched) >= 2


def clothing_markers(clothing_text):
    markers = set()
    for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", clothing_text.lower()):
        if len(token) >= 4:
            markers.add(token)
    return markers


def nonspecific_clothing_markers():
    return {
        "black", "white", "blue", "green", "gold", "golden", "silver", "red",
        "brown", "gray", "grey", "dark", "light", "heavy", "thin", "soft",
        "linen", "leather", "cotton", "silk", "wool", "metal", "metallic",
    }


def required_clothing_prompt(clothing):
    return f"exact outfit: {clean(clothing)}"


def build_background_visual_prompt(story, scene):
    story = story or {}
    scene = scene or {}
    prompt = clean(scene.get("background_prompt"))
    return normalize_background_visual_prompt(prompt)


def improve_background_visual_prompt(story, scene, source_prompt="", settings=None, story_id=None):
    story = story or {}
    scene = scene or {}
    source_prompt = clean(source_prompt) or clean(scene.get("background_prompt"))
    if not source_prompt:
        raise ValueError("Prompt base de cenario ausente.")

    settings = settings or db.get_settings()
    recent_context = {
        "story_title": story.get("title") or "",
        "genre": story.get("genre") or "",
        "tone": story.get("tone") or "",
        "lore": clean(story.get("lore"))[:1600],
        "summary": clean(story.get("summary"))[:1200],
        "recent_memory": [
            clean(entry.get("content"))[:260]
            for entry in (story.get("memory_entries") or [])[-8:]
            if clean(entry.get("content"))
        ],
        "recent_lore": [
            {"title": clean(entry.get("title"))[:80], "content": clean(entry.get("content"))[:320]}
            for entry in (story.get("lore_entries") or [])[-6:]
            if clean(entry.get("content"))
        ],
        "scene_title": scene.get("title") or "",
        "scene_text": scene.get("scene_text") or "",
        "dialogues": [
            {
                "character": clean(dialogue.get("character"))[:80],
                "text": clean(dialogue.get("text"))[:220],
            }
            for dialogue in (scene.get("dialogues") or [])[-8:]
            if isinstance(dialogue, dict)
        ],
        "choices": [clean(choice)[:180] for choice in (scene.get("choices") or [])[:4]],
        "location": scene.get("location") or "",
        "scene_background_prompt": source_prompt,
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You create final positive image prompts for visual novel background generation. "
                "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
                "Write the visual_prompt entirely in English. "
                "Do not name a visual style such as anime, painterly, retro, cinematic, comic, realistic, or similar. The selected style will be added later through the configured background prefix/suffix. "
                "Analyze the story, lore, current scene, dialogue, location, and base background prompt before writing. "
                "Transform short, vague, Portuguese, or generic location prompts into concrete, detailed English environment descriptions. "
                "Describe mainly the place itself: architecture, spatial layout, foreground/midground/background layers, props, materials, weather, time of day, lighting, atmosphere, and color palette. "
                "Use concrete visual details, not abstract instructions. The following ideas are internal guidance only and must not appear verbatim in the final prompt: unique memorable landmark; environment details tied to the current story conflict; specific props and visual clues; environmental storytelling objects; still background plate with no moving subjects. "
                "Usually avoid people so the background does not compete with visual novel sprites. Do not include main characters, foreground people, large faces, detailed bodies, portraits, or human actions. "
                "For public locations that would look artificial when empty, such as busy city street, crowded cafe, market, commercial street, school hallway, station, or festival square, you may include only subtle ambient extras: distant pedestrians, blurred background customers, small background crowd, or indistinct silhouettes far in the background. "
                "Any people must be secondary, small, not centered, not detailed, background-only, and integrated into the environment. "
                "For intimate, isolated, dramatic, secret, mysterious, or character-focused locations, prefer no people. "
                "Do not include negative prompt text, UI text, watermark text, camera metadata, or copyrighted artist names."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Scene context:\n{json.dumps(recent_context, ensure_ascii=False)}\n\n"
                f"Base background prompt:\n{source_prompt}\n\n"
                "Create the final concrete positive prompt for ComfyUI."
            ),
        },
    ]
    try:
        db.add_api_log(
            "ollama",
            "chat:background-prompt",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="started",
            story_id=story_id,
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            0.35,
            ollama_generation_options(settings, 700),
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:background-prompt",
            {"model": settings.get("ollama_model"), "source_prompt": source_prompt},
            result,
            story_id=story_id,
        )
        visual_prompt = normalize_background_visual_prompt(extract_visual_prompt(result))
        if visual_prompt and background_prompt_needs_repair(visual_prompt):
            repaired = repair_background_visual_prompt(visual_prompt, recent_context, settings, story_id)
            visual_prompt = repaired
        if not visual_prompt:
            raise ValueError("Resposta de cenario invalida: visual_prompt vazio.")
        return visual_prompt
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:background-prompt",
            {"model": settings.get("ollama_model"), "messages": messages, "source_prompt": source_prompt},
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        raise RuntimeError(f"IA de cenario falhou: {exc}") from exc


def background_prompt_needs_repair(prompt):
    prompt = clean(prompt)
    if not prompt:
        return False
    lower = prompt.lower()
    if looks_portuguese_text(prompt):
        return True
    if len(re.findall(r"[a-zA-Z]+", prompt)) < 10:
        return True
    return any(phrase.lower() in lower for phrase in ABSTRACT_BACKGROUND_PHRASES + BACKGROUND_BASE_STYLE_PHRASES)


def repair_background_visual_prompt(prompt, context, settings=None, story_id=None):
    prompt = clean(prompt)
    if not prompt:
        raise ValueError("Prompt de cenario ausente para reparo.")
    settings = settings or db.get_settings()
    messages = [
        {
            "role": "system",
            "content": (
                "Repair a ComfyUI positive prompt for a background environment. "
                "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
                "Rewrite the prompt entirely in English. "
                "Keep only concrete environment details: location, layout, props, materials, weather, time of day, lighting, atmosphere, palette, and depth. "
                "Remove abstract instructions, negative prompt text, visual style labels, character names, main characters, foreground people, detailed faces, UI text, and watermarks. "
                "Do not add anime, painterly, retro, cinematic, comic, realistic, or visual novel style labels."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Context:\n{json.dumps(context or {}, ensure_ascii=False)}\n\n"
                f"Prompt to repair:\n{prompt}\n\n"
                "Return the cleaned final positive prompt."
            ),
        },
    ]
    try:
        db.add_api_log(
            "ollama",
            "chat:background-prompt-repair",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="started",
            story_id=story_id,
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            0.2,
            ollama_generation_options(settings, 500),
            settings=settings,
        )
        db.add_api_log(
            "ollama",
            "chat:background-prompt-repair",
            {"model": settings.get("ollama_model"), "prompt": prompt},
            result,
            story_id=story_id,
        )
        repaired = normalize_background_visual_prompt(extract_visual_prompt(result))
        if not repaired or background_prompt_needs_repair(repaired):
            raise ValueError("Resposta de reparo de cenario invalida.")
        return repaired
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:background-prompt-repair",
            {"model": settings.get("ollama_model"), "messages": messages, "prompt": prompt},
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        raise RuntimeError(f"IA de reparo de cenario falhou: {exc}") from exc


def normalize_background_visual_prompt(prompt):
    prompt = clean(prompt)
    if not prompt:
        return ""
    return dedupe_tags([strip_background_base_phrases(prompt)])


def finalize_background_comfy_prompt(prompt):
    prompt = clean(prompt)
    if not prompt:
        return ""
    return dedupe_tags([sanitize_background_config_prompt(prompt)])


def sanitize_background_config_prompt(prompt):
    result = strip_background_instruction_phrases(prompt)
    result = re.sub(r"\s*,\s*,+", ", ", result)
    result = re.sub(r"^\s*,\s*|\s*,\s*$", "", result)
    return clean(result)


ABSTRACT_BACKGROUND_PHRASES = [
    "empty visual novel background",
    "unique memorable landmark",
    "environment details tied to the current story conflict",
    "specific props and visual clues",
    "still background plate with no moving subjects",
    "environmental storytelling objects",
    "environmental storytelling",
    "environmental storytelling objects tied to the opening conflict",
    "specific architecture and spatial layout",
    "distinct foreground, midground, and background depth",
    "layered foreground, midground, and background depth",
    "detailed architecture, props, materials, lighting, atmosphere, and color palette",
    "wide establishing shot",
    "environment-focused composition",
    "detailed environment art",
    "clear material textures",
    "cinematic lighting",
    "cinematic atmospheric lighting",
    "cohesive color palette",
    "high detail",
    "high detail environment concept art",
    "high detail polished anime visual novel background art",
    "polished anime visual novel background art",
    "polished anime background art",
    "polished anime background",
    "polished background art",
    "detailed static background plate",
    "static empty scene composition",
    "empty environment",
    "moody environmental storytelling",
    "layered foreground midground background",
    "foreground, midground, and background depth",
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
    "empty",
]

BACKGROUND_BASE_STYLE_PHRASES = [
    "anime style",
    "anime background",
    "anime visual novel background",
    "visual novel background",
    "visual novel style",
    "Anime VN",
    "Fantasia painterly",
    "Anime retro",
    "Cinematico realista",
    "Quadrinhos escuro",
]


def strip_background_base_phrases(prompt):
    result = strip_background_instruction_phrases(prompt)
    for phrase in BACKGROUND_BASE_STYLE_PHRASES:
        result = re.sub(rf"\s*,?\s*{re.escape(phrase)}\s*,?", ", ", result, flags=re.I)
    result = re.sub(r"\s*,\s*,+", ", ", result)
    result = re.sub(r"^\s*,\s*|\s*,\s*$", "", result)
    return clean(result)


def strip_background_instruction_phrases(prompt):
    result = clean(prompt)
    for phrase in ABSTRACT_BACKGROUND_PHRASES:
        result = re.sub(rf"\s*,?\s*{re.escape(phrase)}\s*,?", ", ", result, flags=re.I)
    result = re.sub(r"\s*,\s*,+", ", ", result)
    result = re.sub(r"^\s*,\s*|\s*,\s*$", "", result)
    return clean(result)


def gender_prompt_tags(text):
    female_terms = ["mulher", "feminina", "garota", "menina", "senhora", "dona", "vampira", "1girl", "female", "woman", "girl", "lady"]
    male_terms = ["homem", "masculino", "garoto", "menino", "senhor", "dono", "vampiro", "1boy", "male", "man", "boy", "gentleman"]
    if any(has_prompt_term(text, term) for term in female_terms):
        return ["1girl", "adult woman", "female", "feminine face"]
    if any(has_prompt_term(text, term) for term in male_terms):
        return ["1boy", "male", "masculine face"]
    return ["1person"]


def has_prompt_term(text, term):
    if " " in term or term.startswith("1"):
        return term in text
    return re.search(rf"(?<![a-zA-Z]){re.escape(term)}(?![a-zA-Z])", text) is not None


def age_prompt_tags(text):
    if any(term in text for term in ["60", "idoso", "idosa", "elderly", "old man", "old woman"]):
        return ["elderly", "mature adult"]
    if any(term in text for term in ["jovem", "20", "young"]):
        return ["young adult"]
    if any(term in text for term in ["adulto", "adulta", "adult"]):
        return ["adult"]
    return []


def hair_prompt_tags(text):
    tags = []
    if any(term in text for term in ["careca", "bald"]):
        tags.append("bald")
        return tags
    colors = [
        (["loiro", "loira", "blond", "blonde"], "blonde hair"),
        (["castanho", "castanha", "brown hair"], "brown hair"),
        (["branco", "branca", "white hair"], "white hair"),
        (["preto", "preta", "black hair"], "black hair"),
        (["ruivo", "ruiva", "red hair"], "red hair"),
    ]
    for terms, tag in colors:
        if any(term in text for term in terms):
            tags.append(tag)
            break
    if any(term in text for term in ["longo", "longa", "longos", "longas", "long hair"]):
        tags.append("long hair")
    if any(term in text for term in ["curto", "curta", "short hair"]):
        tags.append("short hair")
    if any(term in text for term in ["bagunçado", "baguncado", "messy"]):
        tags.append("messy hair")
    return tags


def eye_prompt_tags(text):
    colors = [
        (["olhos vermelhos", "red eyes"], "red eyes"),
        (["olhos verdes", "green eyes"], "green eyes"),
        (["olhos azuis", "blue eyes"], "blue eyes"),
        (["olhos claros", "light eyes"], "light-colored eyes"),
        (["olhos escuros", "dark eyes"], "dark eyes"),
    ]
    return [tag for terms, tag in colors if any(term in text for term in terms)][:1]


def body_prompt_tags(text):
    tags = []
    if any(term in text for term in ["alto", "alta", "tall"]):
        tags.append("tall")
    if any(term in text for term in ["magro", "magra", "slender", "thin"]):
        tags.append("slender")
    if any(term in text for term in ["elegante", "elegant"]):
        tags.append("elegant")
    return tags


def outfit_prompt_tags(text):
    if any(term in text for term in ["jaqueta jeans", "denim jacket"]):
        return ["denim jacket", "casual pants"]
    if any(term in text for term in ["jaqueta", "jacket"]):
        return ["jacket", "casual clothes"]
    if any(term in text for term in ["terninho", "suit", "blazer"]):
        return ["tailored black suit", "black blazer", "formal shirt"]
    if any(term in text for term in ["casual", "descolad"]):
        return ["modern casual clothes"]
    if any(term in text for term in ["vestido", "dress"]):
        return ["dress"]
    if any(term in text for term in ["robe", "manto"]):
        return ["fantasy robe"]
    return ["complete outfit"]


def expression_prompt_tags(expression):
    text = normalize_expression(expression)
    mapping = {
        "happy": "smile",
        "sad": "sad expression",
        "angry": "angry expression",
        "surprised": "surprised expression",
        "embarrassed": "embarrassed expression",
        "scared": "scared expression",
        "thoughtful": "thoughtful expression",
        "neutral": "neutral expression",
    }
    for key, value in mapping.items():
        if key in text:
            return [value]
    return ["neutral expression"]


def normalize_expression(value):
    text = clean(value).lower().replace("-", "_").replace(" ", "_")
    return text if text in OFFICIAL_EXPRESSIONS else "neutral"


def extract_visual_prompt(result):
    if not isinstance(result, dict):
        return ""
    direct = clean(result.get("visual_prompt"))
    if direct:
        if direct.startswith("{") and direct.endswith("}"):
            try:
                return extract_visual_prompt(json.loads(direct))
            except json.JSONDecodeError:
                pass
        return direct
    parts = []
    for key in ["character", "characters", "appearance", "expression", "outfit", "pose", "style", "environment", "background", "composition"]:
        value = result.get(key)
        if isinstance(value, list):
            parts.extend(clean(item) for item in value if clean(item))
        elif clean(value):
            parts.append(clean(value))
    return ", ".join(parts)


def sanitize_visual_prompt(prompt, source_text, context=None):
    context = context or {}
    asset_type = context.get("asset_type")
    prompt = clean(prompt).replace("{", "").replace("}", "").replace('"', "")
    prompt = re.sub(r"\b1old man\b", "1boy, old man", prompt, flags=re.I)
    prompt = re.sub(r"\b1elderly man\b", "1boy, elderly man", prompt, flags=re.I)
    prompt = re.sub(r"\b1thin body\b", "thin body", prompt, flags=re.I)

    source = (source_text or "").lower()
    additions = []
    if any(term in source for term in ["homem", "masculino"]):
        additions.extend(["1boy", "male", "masculine"])
    if any(term in source for term in ["senhor", "idoso", "elderly", "old man"]):
        additions.extend(["1boy", "male", "masculine", "old man"])
    if any(term in source for term in ["senhora", "mulher", "feminina", "garota"]):
        additions.extend(["1girl", "female"])
    if any(term in source for term in ["careca", "bald"]):
        additions.append("bald")
    if any(term in source for term in ["magro", "thin", "slender"]):
        additions.append("slender")
    if any(term in source for term in ["alto", "tall"]):
        additions.append("tall")
    if asset_type == "sprite":
        forbidden = [
            "scene:", "environment:", "background:", "lush forest", "ancient ruins",
            "interior", "exterior", "landscape", "forest", "ruins", "room", "hall",
            "castle", "city", "street",
        ]
        pieces = [part.strip() for part in prompt.split(",")]
        pieces = [part for part in pieces if not any(term in part.lower() for term in forbidden)]
        pieces.extend(additions)
        pieces.extend(["solo", "one person only", "visual novel sprite", "full body", "standing pose", "plain white background", "no frame"])
        return dedupe_tags(pieces)

    return dedupe_tags([prompt, *additions])


def dedupe_tags(parts):
    seen = set()
    output = []
    for part in parts:
        for tag in str(part).split(","):
            clean_tag = clean(tag)
            key = clean_tag.lower()
            if clean_tag and key not in seen:
                seen.add(key)
                output.append(clean_tag)
    return ", ".join(output)


def generate_scene(story_id, user_input, speaker_focus=None, story_override=None, save=True):
    story = story_override or db.get_story(story_id)
    if not story:
        raise ValueError("Historia nao encontrada.")

    settings = ai_client.settings_for_ai_role(db.get_settings(), "scene")
    full_narrative_context = build_narrative_context(story, user_input, speaker_focus)
    prompt_mode = active_narrator_prompt_mode(settings)
    system_prompt = active_narrator_system_prompt(settings, prompt_mode)
    log_request_base = {
        "model": settings.get("ollama_model"),
        "system_chars": len(system_prompt),
        "prompt_mode": prompt_mode,
        "llama_context_window": active_text_context_window(settings),
        "user_input": user_input,
        "speaker_focus": speaker_focus,
    }

    result = None
    scene = None
    retry_instruction = ""
    mode_for_validation = db.normalize_participation_mode(story.get("participation_mode") or story.get("point_of_view"))
    max_attempts = active_text_max_attempts(settings)
    if mode_for_validation in {"narrator", "third_person"}:
        max_attempts = max(max_attempts, 2)
    if speaker_focus:
        max_attempts = max(max_attempts, 2)
    for attempt in range(1, max_attempts + 1):
        retry_suffix = ""
        if retry_instruction:
            retry_suffix = f"\n\nRETRY REQUIREMENTS:\n{retry_instruction}"
        narrative_context = full_narrative_context
        compact_budget_log = {}
        if prompt_mode == "compact-local-json":
            narrative_context, compact_budget_log = compact_narrative_context_for_budget(
                full_narrative_context,
                story,
                user_input,
                system_prompt,
                settings,
                attempt=attempt,
                prompt_suffix=retry_suffix,
            )
        base_user_prompt = build_narrator_user_prompt(story, user_input, narrative_context)
        user_prompt = f"{base_user_prompt}{retry_suffix}"
        budget_log = narrator_prompt_budget_log(settings, system_prompt, user_prompt, attempt)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        attempt_request = {
            **log_request_base,
            **compact_budget_log,
            **budget_log,
            "attempt": attempt,
            "context_section_chars": {key: len(str(value or "")) for key, value in narrative_context.items() if key != CONTEXT_STATS_KEY},
            "active_character_brief_chars": len(str(narrative_context.get("active_character_brief") or "")),
            "character_visual_state_chars": len(str(narrative_context.get("character_visual_state") or "")),
            "recent_scene_states_chars": len(str(narrative_context.get("recent_scene_states") or "")),
            "output_requirements_chars": len(str(narrative_context.get("output_requirements") or "")),
            "task_chars": len(str(narrative_context.get("task") or "")),
            "appearance_count_sent": (narrative_context.get(CONTEXT_STATS_KEY) or {}).get("appearance_count_sent", 0),
            "omitted_appearances_count": (narrative_context.get(CONTEXT_STATS_KEY) or {}).get("omitted_appearances_count", 0),
            "base_prompt_chars": len(base_user_prompt),
            "user_prompt_chars": len(user_prompt),
            "prompt_preview": user_prompt,
            "retry_instruction": retry_instruction,
        }
        started = time.perf_counter()
        try:
            db.add_api_log(
                "ollama",
                "chat:narrator",
                attempt_request,
                story_id=story_id,
                status="started",
            )
            result = chat_json(
                settings.get("ollama_url"),
                settings.get("ollama_model"),
                messages,
                active_text_temperature(settings),
                narrator_generation_options(settings, attempt),
                settings=settings,
            )
            scene = stabilize_scene_cast(story, normalize_scene(result, story), user_input, result)
            validate_scene_response(scene)
            repetition = detect_repetitive_scene(story, scene)
            participation_violation = detect_participation_violation(story, scene)
            speaker_focus_violation = detect_speaker_focus_violation(scene, speaker_focus)
            db.add_api_log(
                "ollama",
                "chat:narrator",
                attempt_request,
                {
                    "duration_seconds": round(time.perf_counter() - started, 2),
                    "repetition": repetition,
                    "participation_violation": participation_violation,
                    "speaker_focus_violation": speaker_focus_violation,
                    "raw_ai_response": result,
                    "result": result,
                    "parsed_scene": scene,
                },
                story_id=story_id,
            )
            if speaker_focus_violation and attempt < max_attempts:
                retry_instruction = build_speaker_focus_retry(speaker_focus_violation, speaker_focus)
                continue
            if participation_violation and attempt < max_attempts:
                retry_instruction = build_participation_retry(scene, participation_violation, story)
                continue
            if repetition and attempt < max_attempts:
                retry_instruction = build_anti_repetition_retry(scene, repetition, story)
                continue
            break
        except Exception as exc:
            db.add_api_log(
                "ollama",
                "chat:narrator",
                attempt_request,
                status="error",
                error=str(exc),
                story_id=story_id,
            )
            if attempt < max_attempts:
                retry_instruction = build_json_retry_instruction(exc, attempt)
                continue
            raise RuntimeError(f"IA de narrativa falhou: {exc}") from exc

    if not scene:
        raise RuntimeError("IA de narrativa retornou resposta vazia.")
    scene["user_input"] = user_input
    scene["raw_ai_response"] = result
    if not save:
        return scene
    return db.add_scene(story_id, scene)


def active_narrator_prompt_mode(settings):
    if use_llama_cpp_settings(settings):
        context_window = active_text_context_window(settings)
        if context_window <= 8192:
            return "compact-local-json"
    return "full"


def active_narrator_system_prompt(settings, prompt_mode=None):
    mode = prompt_mode or active_narrator_prompt_mode(settings)
    if mode == "compact-local-json":
        return COMPACT_NARRATOR_SYSTEM_PROMPT
    return NARRATOR_SYSTEM_PROMPT


def compact_narrative_context_for_4k(context):
    result = {}
    for key, value in (context or {}).items():
        if key == CONTEXT_STATS_KEY:
            result[key] = value
        else:
            result[key] = compact_context_section(key, value, COMPACT_CONTEXT_PREFERRED_LIMITS.get(key, 500))
    return result


def compact_narrative_context_for_budget(context, story, user_input, system_prompt, settings, attempt=1, prompt_suffix=""):
    limits = scaled_compact_context_limits(settings, attempt)
    compacted = compact_narrative_context_with_limits(context, limits)
    user_prompt = build_narrator_user_prompt(story, user_input, compacted) + str(prompt_suffix or "")
    budget_log = narrator_prompt_budget_log(settings, system_prompt, user_prompt, attempt)

    while budget_log["estimated_prompt_tokens"] > budget_log["estimated_available_input_tokens"]:
        changed = False
        overflow_tokens = budget_log["estimated_prompt_tokens"] - budget_log["estimated_available_input_tokens"]
        requested_drop = max(120, int(math.ceil(overflow_tokens * ESTIMATED_CHARS_PER_TOKEN)))
        for key in COMPACT_CONTEXT_REDUCTION_ORDER:
            current_limit = int(limits.get(key, COMPACT_CONTEXT_PREFERRED_LIMITS.get(key, 500)))
            minimum = int(COMPACT_CONTEXT_MIN_LIMITS.get(key, 220))
            if current_limit <= minimum:
                continue
            next_limit = max(minimum, current_limit - requested_drop)
            if next_limit == current_limit:
                continue
            limits[key] = next_limit
            changed = True
            break
        if not changed:
            break
        compacted = compact_narrative_context_with_limits(context, limits)
        user_prompt = build_narrator_user_prompt(story, user_input, compacted) + str(prompt_suffix or "")
        budget_log = narrator_prompt_budget_log(settings, system_prompt, user_prompt, attempt)

    budget_log["context_section_limits"] = dict(limits)
    budget_log["context_over_budget"] = budget_log["estimated_prompt_tokens"] > budget_log["estimated_available_input_tokens"]
    return compacted, budget_log


def compact_narrative_context_with_limits(context, limits):
    result = {}
    for key, value in (context or {}).items():
        if key == CONTEXT_STATS_KEY:
            result[key] = value
            continue
        result[key] = compact_context_section(key, value, int(limits.get(key, COMPACT_CONTEXT_PREFERRED_LIMITS.get(key, 500))))
    return result


def compact_context_section(key, value, limit):
    if key == "recent_scene_states":
        return compact_recent_scenes(value, limit)
    return compact(value, limit)


def compact_recent_scenes(value, limit):
    text = str(value or "").replace("\r", "").strip()
    if len(text) <= limit:
        return text
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    selected = []
    available = max(0, limit - 4)
    current_length = 0
    for block in reversed(blocks):
        extra = len(block) + (2 if selected else 0)
        if selected and current_length + extra > available:
            break
        if not selected and extra > available:
            tail = block[-available:].lstrip() if available > 0 else ""
            return f"...\n{tail}".strip()
        selected.insert(0, block)
        current_length += extra
    result = "\n\n".join(selected)
    if len(result) < len(text):
        result = f"...\n{result}"
    if len(result) > limit:
        return compact(result, limit)
    return result


def scaled_compact_context_limits(settings, attempt=1):
    context_window = active_text_context_window(settings)
    output_tokens = active_narrator_output_tokens(settings, attempt)
    available_input_tokens = max(0, context_window - output_tokens - narrator_safety_margin_tokens(context_window))
    scale = max(1.0, min(1.8, available_input_tokens / 4200 if available_input_tokens else 1.0))
    limits = {}
    for key, preferred in COMPACT_CONTEXT_PREFERRED_LIMITS.items():
        maximum = COMPACT_CONTEXT_MAX_LIMITS.get(key, preferred)
        limits[key] = min(maximum, max(preferred, int(preferred * scale)))
    return limits


def narrator_prompt_budget_log(settings, system_prompt, user_prompt, attempt=1):
    context_window = active_text_context_window(settings)
    configured_output_tokens = active_narrator_output_tokens(settings, attempt)
    reserved_output_tokens = configured_output_tokens
    safety_margin_tokens = narrator_safety_margin_tokens(context_window)
    available_input_tokens = max(0, context_window - reserved_output_tokens - safety_margin_tokens)
    total_prompt_chars = len(str(system_prompt or "")) + len(str(user_prompt or ""))
    estimated_prompt_tokens = estimate_tokens_from_chars(total_prompt_chars)
    estimated_total_tokens = estimated_prompt_tokens + reserved_output_tokens + safety_margin_tokens
    usage_percent = round((estimated_total_tokens / context_window) * 100, 2) if context_window else 0
    return {
        "configured_output_tokens": configured_output_tokens,
        "reserved_output_tokens": reserved_output_tokens,
        "safety_margin_tokens": safety_margin_tokens,
        "estimated_available_input_tokens": available_input_tokens,
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "estimated_total_tokens": estimated_total_tokens,
        "context_usage_percent": usage_percent,
        "token_count_method": "estimated",
        "total_prompt_chars": total_prompt_chars,
        "estimated_chars_per_token": ESTIMATED_CHARS_PER_TOKEN,
    }


def estimate_tokens_from_chars(char_count):
    return int(math.ceil(max(0, int(char_count or 0)) / ESTIMATED_CHARS_PER_TOKEN))


def narrator_safety_margin_tokens(context_window):
    return max(500, min(1200, int(math.ceil(int(context_window or 0) * 0.10))))


def active_text_context_window(settings):
    settings = settings or {}
    cached = settings.get("_active_text_context_window")
    if cached:
        return bounded_int(cached, 1024, 131072, 6144)
    if use_llama_cpp_settings(settings):
        context_window = active_llama_context_window(settings)
    else:
        context_window = bounded_int(settings.get("ollama_context"), 1024, 131072, 6144)
    settings["_active_text_context_window"] = context_window
    return context_window


def active_narrator_output_tokens(settings, attempt=1):
    settings = settings or {}
    if use_llama_cpp_settings(settings):
        first_predict = bounded_int(settings.get("llama_max_tokens"), 500, 6000, 1800)
        retry_predict = bounded_int(settings.get("llama_retry_max_tokens"), 500, 7000, max(first_predict, 2200))
    else:
        first_predict = bounded_int(settings.get("ollama_num_predict"), 500, 6000, 1800)
        retry_predict = bounded_int(settings.get("ollama_retry_num_predict"), 500, 7000, max(first_predict, 2200))
    return retry_predict if int(attempt or 1) > 1 else first_predict


def narrator_generation_options(settings, attempt=1):
    return ollama_generation_options(settings, active_narrator_output_tokens(settings, attempt), include_repeat=True)


def ollama_generation_options(settings, num_predict=None, include_repeat=False):
    settings = settings or {}
    if use_llama_cpp_settings(settings):
        return llama_cpp_generation_options(settings, num_predict, include_repeat)
    options = {
        "num_ctx": bounded_int(settings.get("ollama_context"), 1024, 32768, 6144),
        "think": bool_setting(settings.get("ollama_think"), False),
    }
    if num_predict:
        options["num_predict"] = bounded_int(num_predict, 64, 8000, int(num_predict))
    top_p = bounded_float(settings.get("ollama_top_p"), 0, 1, None)
    if top_p is not None and top_p > 0:
        options["top_p"] = top_p
    top_k = bounded_int(settings.get("ollama_top_k"), 0, 200, None)
    if top_k is not None and top_k > 0:
        options["top_k"] = top_k
    min_p = bounded_float(settings.get("ollama_min_p"), 0, 1, None)
    if min_p is not None and min_p > 0:
        options["min_p"] = min_p
    if include_repeat:
        repeat_penalty = bounded_float(settings.get("ollama_repeat_penalty"), 0.8, 2.0, 1.12)
        repeat_last_n = bounded_int(settings.get("ollama_repeat_last_n"), 0, 4096, 512)
        options["repeat_penalty"] = repeat_penalty
        options["repeat_last_n"] = repeat_last_n
    keep_alive = clean(settings.get("ollama_keep_alive"))
    if keep_alive:
        options["keep_alive"] = keep_alive
    timeout = bounded_float(settings.get("ollama_timeout"), 30, 1800, 240)
    options["request_timeout"] = timeout
    return options


def llama_cpp_generation_options(settings, num_predict=None, include_repeat=False):
    settings = settings or {}
    options = {}
    if num_predict:
        options["num_predict"] = bounded_int(num_predict, 64, 8000, int(num_predict))
    top_p = bounded_float(settings.get("llama_top_p"), 0, 1, None)
    if top_p is not None and top_p > 0:
        options["top_p"] = top_p
    top_k = bounded_int(settings.get("llama_top_k"), 0, 200, None)
    if top_k is not None and top_k > 0:
        options["top_k"] = top_k
    min_p = bounded_float(settings.get("llama_min_p"), 0, 1, None)
    if min_p is not None and min_p > 0:
        options["min_p"] = min_p
    if include_repeat:
        options["repeat_penalty"] = bounded_float(settings.get("llama_repeat_penalty"), 0.8, 2.0, 1.12)
        options["repeat_last_n"] = bounded_int(settings.get("llama_repeat_last_n"), 0, 4096, 512)
    options["enable_thinking"] = bool_setting(settings.get("llama_enable_thinking"), False)
    options["cache_prompt"] = bool_setting(settings.get("llama_cache_prompt"), True)
    if bool_setting(settings.get("llama_timings_per_token"), False):
        options["timings_per_token"] = True
    options["request_timeout"] = bounded_float(settings.get("llama_timeout"), 30, 1800, 240)
    return options


def use_llama_cpp_settings(settings):
    settings = settings or {}
    return (
        str(settings.get("ai_provider") or "ollama").strip().lower() == "openai-compatible"
        and settings.get("openai_compatible_llama_mode") is True
    )


def active_llama_context_window(settings):
    try:
        return bounded_int(ai_client.detect_llama_context_window(settings), 2048, 131072, 4096)
    except Exception:
        return bounded_int((settings or {}).get("llama_context_window"), 2048, 131072, 4096)


def active_text_temperature(settings):
    if use_llama_cpp_settings(settings):
        return bounded_float(settings.get("llama_temperature"), 0, 2, 0.78)
    return bounded_float(settings.get("ollama_temperature"), 0, 2, 0.8)


def active_text_max_attempts(settings):
    if use_llama_cpp_settings(settings):
        return bounded_int(settings.get("llama_max_attempts"), 1, 4, 2)
    return bounded_int(settings.get("ollama_max_attempts"), 1, 4, 2)


def bounded_int(value, minimum, maximum, default):
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def bounded_float(value, minimum, maximum, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def bool_setting(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on", "sim"}:
        return True
    if text in {"false", "0", "no", "off", "nao", "não"}:
        return False
    return default


def build_json_retry_instruction(exc, attempt):
    return (
        f"Attempt {attempt} failed to produce valid or complete JSON: {str(exc)[:220]}\n"
        "Answer again with only one valid JSON object, without markdown.\n"
        "If needed, slightly shorten dialogue lines, but preserve real narrative progress and all required fields."
    )


def build_participation_retry(scene, violation, story):
    mode = db.normalize_participation_mode((story or {}).get("participation_mode") or (story or {}).get("point_of_view"))
    return (
        "The previous attempt violated the selected participation mode and MUST NOT be used.\n"
        f"Mode: {mode}.\n"
        f"Reason: {violation.get('reason')}\n"
        f"Rejected text: {compact_context(violation.get('text'), 320)}\n"
        "Rewrite the scene as one valid JSON object.\n"
        "Use external third-person/cinematic narration with character names or neutral descriptions.\n"
        "Do not use first-person or reader-address narration in scene_text or Narrador lines: no I, me, my, mine, we, our, you, your, eu, meu, minha, voce, você.\n"
        "Character dialogue may still use first person when the speaking character talks about themselves."
    )


def build_speaker_focus_retry(violation, speaker_focus):
    name = speaker_focus_name(speaker_focus)
    return (
        "The previous attempt ignored the user's selected on-screen character and MUST NOT be used.\n"
        f"Selected character: {name}.\n"
        f"Problem: {violation.get('reason')}\n"
        f"The new scene must open with {name} speaking, visibly reacting, or taking initiative before any other character takes the focus.\n"
        f"Keep {name} present in characters_on_screen and relevant at the beginning."
    )


def detect_speaker_focus_violation(scene, speaker_focus):
    name = speaker_focus_name(speaker_focus)
    if not name or not scene:
        return None
    opening_text = clean(scene.get("scene_text"))[:280]
    if focus_name_matches_text(name, opening_text):
        return None

    first_character_dialogue = None
    for dialogue in scene.get("dialogues") or []:
        if not isinstance(dialogue, dict):
            continue
        character = clean(dialogue.get("character"))
        if not character or normalize_person_key(character) == "narrador":
            continue
        first_character_dialogue = character
        break

    if first_character_dialogue and normalize_person_key(first_character_dialogue) == normalize_person_key(name):
        return None
    if first_character_dialogue:
        return {
            "reason": f"first character dialogue belongs to {first_character_dialogue}, not {name}",
        }
    return {
        "reason": f"opening narration and dialogues do not visibly center {name}",
    }


def speaker_focus_name(speaker_focus):
    if isinstance(speaker_focus, dict):
        return clean(speaker_focus.get("name") or speaker_focus.get("character"))
    return clean(speaker_focus)


def focus_name_matches_text(name, text):
    normalized_text = normalize_person_key(text)
    normalized_name = normalize_person_key(name)
    if not normalized_name or not normalized_text:
        return False
    if normalized_name in normalized_text:
        return True
    parts = [part for part in normalized_name.split() if len(part) >= 3]
    return any(part in normalized_text for part in parts)


def detect_participation_violation(story, scene):
    mode = db.normalize_participation_mode((story or {}).get("participation_mode") or (story or {}).get("point_of_view"))
    if mode not in {"narrator", "third_person"}:
        return None
    checks = [("scene_text", scene.get("scene_text") or "")]
    for index, dialogue in enumerate(scene.get("dialogues") or []):
        if normalize_person_key((dialogue or {}).get("character")) == "narrador":
            checks.append((f"dialogues[{index}].text", (dialogue or {}).get("text") or ""))
    for field, text in checks:
        match = first_person_or_reader_address_match(text)
        if match:
            return {
                "field": field,
                "term": match,
                "text": text,
                "reason": f"{mode} narration cannot address the reader or narrate from an internal first-person point of view.",
            }
    return None


def first_person_or_reader_address_match(text):
    if not text:
        return ""
    patterns = [
        r"\bI\b",
        r"\bme\b",
        r"\bmy\b",
        r"\bmine\b",
        r"\bmyself\b",
        r"\bwe\b",
        r"\bus\b",
        r"\bour\b",
        r"\bours\b",
        r"\byou\b",
        r"\byour\b",
        r"\byours\b",
        r"\byourself\b",
        r"\beu\b",
        r"\bmeu\b",
        r"\bminha\b",
        r"\bmeus\b",
        r"\bminhas\b",
        r"\bmim\b",
        r"\bcomigo\b",
        r"\bnós\b",
        r"\bnosso\b",
        r"\bnossa\b",
        r"\bnossos\b",
        r"\bnossas\b",
        r"\bvoc[eê]\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return match.group(0)
    return ""


def build_anti_repetition_retry(scene, repetition, story):
    latest = (story.get("scenes") or [])[-1] if story.get("scenes") else {}
    return (
        "The previous attempt was considered repetitive and MUST NOT be used.\n"
        f"Reason: {repetition.get('reason')}\n"
        f"Previous scene: {compact_context(latest.get('title'), 80)} - {compact_context(latest.get('scene_text'), 260)}\n"
        f"Rejected attempt: {compact_context(scene.get('title'), 80)} - {compact_context(scene.get('scene_text'), 260)}\n"
        "Generate a different scene that advances the story state. Include at least one new consequence, concrete clue, irreversible decision, relationship change, character arrival/departure, or practical new objective.\n"
        "Do not repeat the previous choices; offer new and specific next actions."
    )


def detect_repetitive_scene(story, scene):
    scenes = story.get("scenes") or []
    if not scenes or not scene:
        return None
    new_text = scene_signature(scene)
    new_choices = [clean(choice).lower() for choice in scene.get("choices") or []]
    for previous in reversed(scenes[-4:]):
        previous_text = scene_signature(previous)
        similarity = text_similarity(new_text, previous_text)
        same_title = clean(scene.get("title")).lower() and clean(scene.get("title")).lower() == clean(previous.get("title")).lower()
        previous_choices = [clean(choice).lower() for choice in previous.get("choices") or []]
        choices_overlap = overlap_ratio(new_choices, previous_choices)
        if similarity >= 0.72:
            return {"reason": f"narration/dialogue too similar to scene {previous.get('scene_order')} ({similarity:.2f})"}
        if same_title and similarity >= 0.52:
            return {"reason": f"same title and similar content to scene {previous.get('scene_order')} ({similarity:.2f})"}
        if choices_overlap >= 0.8 and similarity >= 0.48:
            return {"reason": f"choices and content similar to scene {previous.get('scene_order')} ({similarity:.2f})"}
    return None


def scene_signature(scene):
    dialogues = []
    for dialogue in scene.get("dialogues") or []:
        if isinstance(dialogue, dict):
            dialogues.append(dialogue.get("text") or "")
    return " ".join(
        [
            clean(scene.get("title")),
            clean(scene.get("scene_text")),
            " ".join(dialogues),
            " ".join(clean(choice) for choice in scene.get("choices") or []),
        ]
    )


def text_similarity(left, right):
    left_tokens = meaningful_tokens(left)
    right_tokens = meaningful_tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(len(left_tokens), len(right_tokens))


def overlap_ratio(left_items, right_items):
    left = {item for item in left_items if item}
    right = {item for item in right_items if item}
    if not left or not right:
        return 0
    return len(left & right) / max(len(left), len(right))


def meaningful_tokens(value):
    stop = {
        "que", "para", "com", "uma", "como", "dos", "das", "por", "mais", "mas", "sem",
        "the", "and", "with", "from", "into", "that", "this", "they", "their",
        "voce", "você", "ela", "ele", "eles", "elas", "seu", "sua", "seus", "suas",
    }
    return {
        token
        for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", str(value or "").lower())
        if len(token) >= 4 and token not in stop
    }


def stabilize_scene_cast(story, scene, user_input, raw_response=None):
    story = story or {}
    scene = dict(scene or {})
    invisible_keys = invisible_player_visual_keys(story)
    previous_scene = (story.get("scenes") or [])[-1] if story.get("scenes") else {}
    previous_visible = [
        dict(item)
        for item in previous_scene.get("characters_on_screen") or []
        if isinstance(item, dict) and clean(item.get("name")) and normalize_person_key(item.get("name")) not in invisible_keys
    ]
    if invisible_keys and scene.get("characters_on_screen"):
        scene["characters_on_screen"] = [
            item for item in scene.get("characters_on_screen") or []
            if normalize_person_key((item or {}).get("name")) not in invisible_keys
        ]
    if not previous_visible and not scene.get("characters_on_screen"):
        return scene

    blocked_names = manual_removed_names_for_next_scene(story, previous_scene, user_input)
    blocked_names.update(direct_exit_names(user_input, previous_visible))
    continuity = normalize_character_continuity(
        first_present_value(unwrap_scene_payload(raw_response), "character_continuity", "cast_continuity", "scene_continuity")
    )
    continuity_by_key = {
        normalize_person_key(item.get("name")): item
        for item in continuity
        if normalize_person_key(item.get("name"))
    }

    current = [
        dict(item)
        for item in scene.get("characters_on_screen") or []
        if isinstance(item, dict) and clean(item.get("name")) and normalize_person_key(item.get("name")) not in invisible_keys
    ]
    if blocked_names:
        current = [item for item in current if normalize_person_key(item.get("name")) not in blocked_names]
        scene["dialogues"] = [
            dialogue for dialogue in scene.get("dialogues") or []
            if normalize_person_key(dialogue.get("character")) not in blocked_names
        ]

    if continuity_by_key:
        current_keys = {normalize_person_key(item.get("name")) for item in current}
        absent_keys = {
            key
            for key, item in continuity_by_key.items()
            if continuity_status_excludes(item.get("status"))
        }
        if absent_keys:
            current = [item for item in current if normalize_person_key(item.get("name")) not in absent_keys]
            scene["dialogues"] = [
                dialogue for dialogue in scene.get("dialogues") or []
                if normalize_person_key(dialogue.get("character")) not in absent_keys
            ]
            current_keys = {normalize_person_key(item.get("name")) for item in current}
        for item in previous_visible:
            key = normalize_person_key(item.get("name"))
            continuity_item = continuity_by_key.get(key)
            if (
                not key
                or key in current_keys
                or key in blocked_names
                or not continuity_item
                or not continuity_status_includes(continuity_item.get("status"))
            ):
                continue
            if len(current) >= 6:
                break
            current.append(
                {
                    "name": clean(item.get("name")),
                    "position": clean(item.get("position")) or "center",
                    "expression": normalize_expression(item.get("expression")),
                }
            )
            current_keys.add(key)
    elif not current and response_location_changed(raw_response) is False:
        for item in previous_visible[:6]:
            key = normalize_person_key(item.get("name"))
            if not key or key in blocked_names:
                continue
            current.append(
                {
                    "name": clean(item.get("name")),
                    "position": clean(item.get("position")) or "center",
                    "expression": normalize_expression(item.get("expression")),
                }
            )

    scene["characters_on_screen"] = current[:6]
    scene["character_continuity"] = continuity
    return scene


def invisible_player_visual_keys(story):
    if db.normalize_participation_mode((story or {}).get("participation_mode") or (story or {}).get("point_of_view")) != "first_person":
        return set()
    player = (story or {}).get("player_character") or {}
    keys = {normalize_person_key(player.get("name"))}
    for alias in str(player.get("aliases") or "").split(","):
        keys.add(normalize_person_key(alias))
    return {key for key in keys if key}


def response_location_changed(raw_response):
    raw = unwrap_scene_payload(raw_response)
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


def continuity_status_includes(status):
    normalized = normalize_continuity_status(status)
    return normalized in {"remains_present", "accompanies", "present", "stays"}


def continuity_status_excludes(status):
    normalized = normalize_continuity_status(status)
    return normalized in {"left_scene", "not_present", "absent", "offscreen", "left"}


def normalize_continuity_status(status):
    text = normalize_person_key(status).replace("-", "_").replace(" ", "_")
    aliases = {
        "remain": "remains_present",
        "remains": "remains_present",
        "stays_present": "remains_present",
        "still_present": "remains_present",
        "presente": "remains_present",
        "continua_presente": "remains_present",
        "acompanha": "accompanies",
        "acompanha_o_protagonista": "accompanies",
        "travels_with": "accompanies",
        "goes_with": "accompanies",
        "left": "left_scene",
        "leaves": "left_scene",
        "exits": "left_scene",
        "sai": "left_scene",
        "saiu": "left_scene",
        "absent": "not_present",
        "off_screen": "offscreen",
        "fora_de_cena": "not_present",
        "nao_presente": "not_present",
        "não_presente": "not_present",
    }
    return aliases.get(text, text)


def manual_removed_names_for_next_scene(story, previous_scene, user_input):
    scene_order = previous_scene.get("scene_order")
    if not scene_order:
        return set()
    user_text = normalize_person_key(user_input)
    removed = set()
    for entry in story.get("memory_entries") or []:
        if (entry.get("entry_type") or "") != "scene-state":
            continue
        content = str(entry.get("content") or "")
        normalized_content = normalize_person_key(content)
        if f"saiu manualmente da cena {scene_order}" not in normalized_content:
            continue
        for character in story.get("characters") or []:
            name = character.get("name") or ""
            key = normalize_person_key(name)
            if key and key in normalized_content and key not in user_text:
                removed.add(key)
    return removed


def direct_exit_names(user_input, visible_characters):
    directives = re.findall(r"\[\[(.*?)\]\]", str(user_input or ""), flags=re.S)
    if not directives:
        return set()
    exit_terms = [
        "sai", "saiu", "some", "sumiu", "sair", "sumir", "remove", "remover",
        "retira", "retire", "deixa a cena", "fora de cena", "leave", "exits",
    ]
    blocked = set()
    for directive in directives:
        text = normalize_person_key(directive)
        if not any(term in text for term in exit_terms):
            continue
        for item in visible_characters:
            key = normalize_person_key(item.get("name"))
            if key and key in text:
                blocked.add(key)
    return blocked


def normalize_person_key(value):
    text = re.sub(r"[^\wÀ-ÿ\s'-]", " ", str(value or "").strip().lower())
    return " ".join(text.split())


def normalize_scene(raw, story=None):
    raw = unwrap_scene_payload(raw)
    scene_text = clean(first_present(raw, "scene_text", "narration", "narrative", "description"))
    dialogues = normalize_dialogues(first_present_value(raw, "dialogues", "dialogue", "lines"))
    story = story or {}
    aliases = character_alias_index(story.get("characters") or [])
    dialogues = resolve_dialogue_character_names(dialogues, aliases)
    on_screen = resolve_on_screen_character_names(
        normalize_on_screen(first_present_value(raw, "characters_on_screen", "cast", "characters")),
        aliases,
    )
    new_characters = filter_existing_new_characters(
        first_present_value(raw, "new_characters_detected", "new_characters") if isinstance(first_present_value(raw, "new_characters_detected", "new_characters"), list) else [],
        aliases,
    )
    return {
        "title": clean(first_present(raw, "title", "name_of_the_scene", "scene_title", "name")) or scene_location_title(raw),
        "scene_text": scene_text,
        "dialogues": dialogues,
        "choices": normalize_choices(raw.get("choices")),
        "background_prompt": clean(first_present(raw, "background_prompt", "background")),
        "character_continuity": normalize_character_continuity(first_present_value(raw, "character_continuity", "cast_continuity", "scene_continuity")),
        "characters_on_screen": on_screen,
        "new_characters_detected": new_characters,
        "memory_updates": normalize_memory(raw.get("memory_updates")),
        "appearance_updates": normalize_appearance_updates(first_present_value(raw, "appearance_updates", "appearance_changes", "visual_updates"), aliases),
    }


def validate_scene_response(scene):
    missing = []
    if not clean(scene.get("title")):
        missing.append("title")
    if not clean(scene.get("scene_text")) and not scene.get("dialogues"):
        missing.append("scene_text/dialogues")
    if not scene.get("choices"):
        missing.append("choices")
    if not clean(scene.get("background_prompt")):
        missing.append("background_prompt")
    if missing:
        raise ValueError(f"Resposta de cena invalida: campos ausentes ou vazios: {', '.join(missing)}.")


TITLE_WORDS = {
    "professor",
    "professora",
    "prof",
    "dr",
    "dra",
    "doutor",
    "doutora",
    "sr",
    "sra",
    "senhor",
    "senhora",
    "sir",
    "lady",
    "lord",
}


def character_alias_index(characters):
    index = {}
    for character in characters or []:
        canonical = clean((character or {}).get("name"))
        if not canonical:
            continue
        for alias in character_name_variants(character):
            key = normalize_person_key(alias)
            if key and key not in index:
                index[key] = canonical
    return index


def character_name_variants(character):
    name = clean((character or {}).get("name"))
    variants = set()
    if name:
        variants.add(name)
        parts = [part for part in re.split(r"\s+", name) if part]
        if parts:
            variants.add(parts[0])
            variants.add(parts[-1])
        if len(parts) >= 2:
            variants.add(" ".join(parts[:2]))
        for title in TITLE_WORDS:
            if parts:
                variants.add(f"{title} {parts[0]}")
            variants.add(f"{title} {name}")
    aliases = clean((character or {}).get("aliases"))
    for alias in re.split(r"[,;/|]", aliases):
        alias = clean(alias)
        if alias:
            variants.add(alias)
            alias_parts = [part for part in re.split(r"\s+", alias) if part]
            if alias_parts:
                variants.add(alias_parts[0])
                variants.add(alias_parts[-1])
    return variants


def canonical_character_name(name, aliases):
    key = normalize_person_key(name)
    if not key:
        return ""
    if key in aliases:
        return aliases[key]
    without_title = " ".join(part for part in key.split() if part not in TITLE_WORDS)
    return aliases.get(without_title, clean(name))


def resolve_dialogue_character_names(dialogues, aliases):
    result = []
    for dialogue in dialogues or []:
        item = dict(dialogue)
        character = clean(item.get("character"))
        if normalize_person_key(character) != "narrador":
            item["character"] = canonical_character_name(character, aliases) or character
        result.append(item)
    return result


def resolve_on_screen_character_names(on_screen, aliases):
    result = []
    seen = set()
    for item in on_screen or []:
        entry = dict(item)
        entry["name"] = canonical_character_name(entry.get("name"), aliases) or clean(entry.get("name"))
        key = normalize_person_key(entry.get("name"))
        if key and key not in seen:
            seen.add(key)
            result.append(entry)
    return result


def filter_existing_new_characters(candidates, aliases):
    result = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        names = [
            candidate.get("display_name"),
            candidate.get("temporary_name"),
            candidate.get("name"),
        ]
        alias_text = clean(candidate.get("aliases"))
        names.extend([item.strip() for item in re.split(r"[,;/|]", alias_text) if item.strip()])
        if any(normalize_person_key(name) in aliases or canonical_character_name(name, aliases) != clean(name) for name in names if clean(name)):
            continue
        result.append(candidate)
    return result


def unwrap_scene_payload(raw):
    if not isinstance(raw, dict):
        return {}
    for key in ("scene", "next_scene", "visual_novel_scene", "result"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return raw


def scene_location_title(raw):
    location = raw.get("location") if isinstance(raw, dict) else None
    if isinstance(location, dict):
        return clean(location.get("name") or location.get("title"))
    return ""


def normalize_dialogues(value):
    if not isinstance(value, list):
        return []
    dialogues = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        text = clean(item.get("text"))
        if not text:
            text = clean(first_present(item, "line", "speech", "voice", "utterance", "dialogue", "content"))
        if not text and isinstance(item.get("lines"), list):
            text = "\n".join(clean(line) for line in item.get("lines") if clean(line))
        if not text:
            continue
        character = clean(first_present(item, "character", "speaker", "speaker_name", "name"))
        dialogues.append(
            {
                "character": character or "Narrador",
                "expression": normalize_expression(item.get("expression")),
                "text": text,
            }
        )
    return dialogues


def normalize_choices(value):
    if not isinstance(value, list):
        return []
    choices = []
    for choice in value[:5]:
        if isinstance(choice, dict):
            text = clean(first_present(choice, "text", "label", "choice", "action"))
        else:
            text = clean(choice)
        if text:
            choices.append(text)
    return choices


def normalize_on_screen(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:6]:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "name": clean(item.get("name")),
                "position": clean(item.get("position")) or "center",
                "expression": normalize_expression(item.get("expression")),
            }
        )
    return [item for item in result if item["name"]]


def normalize_character_continuity(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:8]:
        if not isinstance(item, dict):
            continue
        name = clean(first_present(item, "name", "character", "character_name"))
        status = normalize_continuity_status(first_present(item, "status", "state", "presence", "decision"))
        reason = clean(first_present(item, "reason", "why", "explanation"))
        if not name:
            continue
        result.append({"name": name, "status": status or "not_present", "reason": reason})
    return result


def normalize_appearance_updates(value, aliases=None):
    if not isinstance(value, list):
        return []
    aliases = aliases or {}
    result = []
    for item in value[:6]:
        if not isinstance(item, dict):
            continue
        character = canonical_character_name(
            first_present(item, "character", "name", "character_name"),
            aliases,
        )
        if not character:
            continue
        action = clean(first_present(item, "action", "type")).lower().strip().replace("-", "_").replace(" ", "_")
        if action not in {"create_new", "switch_existing", "revert_existing"}:
            continue
        update = {
            "character": character,
            "action": action,
            "reason": clean(first_present(item, "reason", "why", "explanation")),
            "activate_after_generation": normalize_bool(item.get("activate_after_generation"), True),
        }
        if action == "create_new":
            update.update(
                {
                    "based_on_appearance_id": clean(first_present(item, "based_on_appearance_id", "base_appearance_id", "source_appearance_id")),
                    "new_appearance_name": clean(first_present(item, "new_appearance_name", "appearance_name", "label")),
                    "new_appearance_summary": clean(first_present(item, "new_appearance_summary", "summary", "description")),
                    "change_prompt": clean(first_present(item, "change_prompt", "prompt", "visual_prompt")),
                }
            )
        else:
            update["target_appearance_id"] = clean(first_present(item, "target_appearance_id", "appearance_id", "target_id"))
        result.append(update)
    return result


def normalize_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "sim", "1"}:
            return True
        if text in {"false", "no", "nao", "não", "0"}:
            return False
    return default


def first_present(mapping, *keys):
    if not isinstance(mapping, dict):
        return ""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and clean(value):
            return value
        if value not in {None, ""} and not isinstance(value, (dict, list)):
            return str(value)
    return ""


def first_present_value(mapping, *keys):
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def normalize_memory(value):
    if not isinstance(value, dict):
        return {"summary": "", "facts": []}
    facts = value.get("facts") if isinstance(value.get("facts"), list) else []
    return {"summary": clean(value.get("summary")), "facts": [clean(fact) for fact in facts if clean(fact)]}


STYLE_OR_SCRIPT_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9:-]*(?:\s+[^<>]*)?>")


def clean(value):
    if not isinstance(value, str):
        return ""
    text = html.unescape(value).strip()
    text = STYLE_OR_SCRIPT_RE.sub("", text)
    text = HTML_TAG_RE.sub("", text)
    return text.strip()


def normalize_language(value):
    text = clean(value).lower()
    if text in {"en", "en-us", "en_us", "english", "ingles", "inglês"}:
        return "en-US"
    return "pt-BR"


def story_language(story):
    story = story or {}
    settings = db.get_settings()
    return normalize_language(story.get("language") or settings.get("default_language") or "pt-BR")


def is_portuguese(language):
    return normalize_language(language).startswith("pt")


def language_instruction(language):
    return "Brazilian Portuguese" if is_portuguese(language) else "English"


def compact_context(value, limit):
    text = clean(value).replace("\r", " ")
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
