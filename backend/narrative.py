import json
import re
import time

from . import db
from .ollama_client import chat_json
from .prompts import NARRATOR_SYSTEM_PROMPT, build_narrative_context, build_narrator_user_prompt


IMPROVE_SYSTEM_PROMPT = """Voce melhora textos de planejamento para uma visual novel gerada por IA.

Responda somente com JSON valido, sem markdown e sem texto fora do JSON.

Formato obrigatorio:
{
  "improved_text": "texto melhorado"
}

Regras:
- Preserve a intencao, nomes, fatos e limites informados pelo usuario.
- Nao contradiga o texto original.
- Expanda com detalhes uteis para narrativa, continuidade e geracao de imagens.
- Escreva em portugues brasileiro, exceto se o campo for prompt visual; nesse caso escreva em ingles.
- Para mundo/lore, detalhe regras, conflitos, cultura, locais, historia e possibilidades dramaticas.
- Para personagem, detalhe aparencia, personalidade, voz, objetivos, medos, contradicoes e ganchos narrativos.
- Para prompt visual, produza tags/descritivo em ingles, claro e reutilizavel.
"""


STORY_SEED_SYSTEM_PROMPT = """Voce e um designer de visual novel local.

Responda somente com JSON valido, sem markdown e sem texto fora do JSON.

Formato obrigatorio:
{
  "title": "titulo curto",
  "genre": "generos separados por virgula",
  "tone": "tom narrativo",
  "visual_style": "estilo visual generico",
  "content_rating": "classificacao de conteudo definida pelo usuario",
  "language": "pt-BR | en-US",
  "lore": "descricao do mundo, conflito inicial e regras importantes",
  "starting_location": "local inicial curto",
  "starting_message": "primeira mensagem/cena em portugues",
  "player_character": {
    "name": "nome do protagonista ou Jogador",
    "role": "papel",
    "species": "especie",
    "gender": "genero",
    "character_type": "tipo narrativo",
    "aliases": "apelidos separados por virgula",
    "description": "descricao geral",
    "appearance": "aparencia",
    "physical": "aparencia fisica detalhada",
    "personality": "personalidade",
    "clothing": "vestimenta",
    "background": "historico",
    "goals": "objetivos e medos",
    "visual_prompt": "english visual prompt for sprite"
  },
  "characters": [
    {
      "name": "nome",
      "role": "papel",
      "species": "especie",
      "gender": "genero",
      "character_type": "tipo narrativo",
      "aliases": "apelidos separados por virgula",
      "description": "descricao geral",
      "physical": "aparencia fisica",
      "personality": "personalidade",
      "clothing": "vestimenta",
      "relationship": "relacao com o protagonista",
      "visual_prompt": "english visual prompt for sprite"
    }
  ]
}

Regras:
- Escreva campos narrativos no idioma solicitado pelo usuario.
- Prompt visual deve ficar em ingles.
- Preserve a intencao do usuario.
- Use personagens e conflitos fortes o bastante para sustentar uma historia longa.
"""


def generate_story_seed(payload):
    prompt = clean(payload.get("prompt"))
    if not prompt:
        return fallback_story_seed("")

    settings = db.get_settings()
    messages = [
        {"role": "system", "content": STORY_SEED_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Idioma desejado para campos narrativos: {language_instruction(settings.get('default_language'))}\n\n"
                f"Ideia da historia:\n{prompt}\n\nGere o JSON de criacao."
            ),
        },
    ]
    try:
        db.add_api_log(
            "ollama",
            "chat:story-seed",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="started",
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            float(settings.get("ollama_temperature") or 0.8),
            {
                "num_ctx": int(settings.get("ollama_context") or 8192),
                "num_predict": 1600,
            },
        )
        db.add_api_log(
            "ollama",
            "chat:story-seed",
            {"model": settings.get("ollama_model"), "messages": messages},
            result,
        )
        return normalize_story_seed(result, prompt)
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:story-seed",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="error",
            error=str(exc),
        )
        seed = fallback_story_seed(prompt)
        seed["warning"] = f"Ollama indisponivel: {str(exc)[:180]}"
        return seed


def normalize_story_seed(raw, prompt):
    settings = db.get_settings()
    language = normalize_language(raw.get("language") or settings.get("default_language"))
    player = raw.get("player_character") if isinstance(raw.get("player_character"), dict) else {}
    characters = raw.get("characters") if isinstance(raw.get("characters"), list) else []
    return {
        "title": clean(raw.get("title")) or title_from_prompt(prompt),
        "genre": clean(raw.get("genre")) or "drama, misterio",
        "tone": clean(raw.get("tone")) or "dramatico, imersivo",
        "visual_style": clean(raw.get("visual_style")) or "anime visual novel",
        "content_rating": clean(raw.get("content_rating")),
        "language": language,
        "lore": clean(raw.get("lore")) or prompt,
        "starting_location": clean(raw.get("starting_location")),
        "starting_message": clean(raw.get("starting_message")),
        "player_character": {
            "name": clean(player.get("name")) or "Jogador",
            "role": clean(player.get("role")) or "protagonista",
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


def fallback_story_seed(prompt):
    settings = db.get_settings()
    language = normalize_language(settings.get("default_language"))
    title = title_from_prompt(prompt)
    return {
        "title": title,
        "genre": "drama interativo, misterio",
        "tone": "cinematico, tenso, emocional",
        "visual_style": "anime visual novel",
        "content_rating": "",
        "language": language,
        "lore": (
            f"Ideia central: {prompt or 'uma historia interativa local'}.\n\n"
            "A historia deve comecar com um conflito claro, personagens com objetivos proprios "
            "e espaco para escolhas do jogador mudarem relacoes, descobertas e consequencias."
        ),
        "starting_location": "local inicial a definir",
        "starting_message": "A primeira cena deve apresentar o conflito principal e uma escolha imediata.",
        "player_character": {
            "name": "Jogador",
            "role": "protagonista",
            "species": "humano",
            "gender": "",
            "character_type": "protagonista",
            "aliases": "",
            "description": "",
            "appearance": "",
            "physical": "",
            "personality": "observador, decidido, com conflitos internos",
            "clothing": "",
            "background": "tem uma ligacao pessoal com o conflito inicial",
            "goals": "descobrir a verdade, sobreviver e decidir em quem confiar",
            "visual_prompt": "",
        },
        "characters": [],
    }


def enrich_story_creation_payload(payload):
    payload = dict(payload or {})
    payload["language"] = story_language(payload)
    language = payload["language"]
    player = dict(payload.get("player_character") or {})
    characters = [dict(character) for character in payload.get("characters") or [] if isinstance(character, dict)]
    if not needs_creation_enrichment(player) and not any(needs_creation_enrichment(character) for character in characters):
        payload["player_character"] = complete_character_record(player, payload, None, is_player=True)
        payload["characters"] = [complete_character_record(character, payload, None) for character in characters]
        apply_creation_sprite_prompts(payload, db.get_settings())
        return payload

    settings = db.get_settings()
    workbench_id = sprite_workbench_for_story_payload(payload, settings)
    prompt_profile = sprite_prompt_profile(settings, workbench_id)
    sources = [{"slot": "player_character", "index": -1, "character": player}]
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
        result = chat_json(settings.get("ollama_url"), settings.get("ollama_model"), messages, 0.4)
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
            is_player=True,
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
        apply_creation_sprite_prompts(payload, settings)
        return payload
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:creation-character-enrichment",
            {"model": settings.get("ollama_model"), "workbench": workbench_id},
            status="error",
            error=str(exc),
        )
        payload["player_character"] = complete_character_record(player, payload, None, is_player=True)
        payload["characters"] = [complete_character_record(character, payload, None) for character in characters]
        apply_creation_sprite_prompts(payload, settings)
        return payload


def needs_creation_enrichment(character):
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
        "visual_prompt",
    ]
    return any(not clean(character.get(field)) for field in required)


def sprite_prompt_profile(settings, workbench_id):
    profiles = settings.get("comfy_prompt_profiles")
    if isinstance(profiles, dict) and isinstance(profiles.get(workbench_id), dict):
        return profiles.get(workbench_id)
    return {}


def apply_creation_sprite_prompts(payload, settings):
    settings = settings or db.get_settings()
    workbench_id = sprite_workbench_for_story_payload(payload, settings)
    characters = []
    player = payload.get("player_character")
    if isinstance(player, dict):
        characters.append(player)
    characters.extend(character for character in payload.get("characters") or [] if isinstance(character, dict))
    for character in characters:
        apply_character_sprite_prompt(character, settings, workbench_id=workbench_id)


def apply_character_sprite_prompt(character, settings=None, story_id=None, expression="neutral", workbench_id=None):
    settings = settings or db.get_settings()
    workbench_id = workbench_id if workbench_id is not None else sprite_workbench_for_story_id(story_id, settings)
    prompt_profile = sprite_prompt_profile(settings, workbench_id)
    source_prompt = build_sprite_source_prompt(character, expression, "")
    fallback = build_sprite_visual_prompt(character, expression, "")
    character["visual_prompt"] = generate_workbench_visual_prompt(
        source_prompt,
        "sprite",
        workbench_id,
        prompt_profile,
        fallback,
        story_id=story_id,
    )
    return character


def sprite_workbench_for_story_payload(payload, settings):
    style = db.get_visual_style((payload or {}).get("visual_style_id"))
    return (style or {}).get("sprite_workbench") or settings.get("comfy_sprite_workbench") or ""


def sprite_workbench_for_story_id(story_id, settings):
    style = db.visual_style_for_story(story_id)
    return (style or {}).get("sprite_workbench") or settings.get("comfy_sprite_workbench") or ""


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


def local_character_enrichment(character):
    character = dict(character or {})
    if not clean(character.get("physical")) and clean(character.get("appearance")):
        character["physical"] = clean(character.get("appearance"))
    if not clean(character.get("description")) and clean(character.get("background")):
        character["description"] = clean(character.get("background"))
    if not clean(character.get("character_type")) and clean(character.get("role")):
        character["character_type"] = clean(character.get("role"))
    if not clean(character.get("species")):
        character["species"] = infer_species(character)
    if not clean(character.get("gender")):
        character["gender"] = infer_gender(character)
    if not clean(character.get("clothing")):
        character["clothing"] = infer_clothing(character)
    if not clean(character.get("visual_prompt")) or looks_portuguese_text(character.get("visual_prompt")):
        character["visual_prompt"] = build_sprite_visual_prompt(character, "neutral", "")
    return character


def complete_character_record(character, story=None, scene=None, is_player=False):
    character = dict(character or {})
    story = story or {}
    scene = scene or {}
    language = story_language(story)
    portuguese = is_portuguese(language)

    if not clean(character.get("name")):
        character["name"] = "Jogador" if is_player and portuguese else ("Player" if is_player else ("Personagem sem nome" if portuguese else "Unnamed character"))

    if not clean(character.get("physical")) and clean(character.get("appearance")):
        character["physical"] = clean(character.get("appearance"))
    if not clean(character.get("description")) and clean(character.get("background")):
        character["description"] = clean(character.get("background"))
    if not clean(character.get("character_type")) and clean(character.get("role")):
        character["character_type"] = clean(character.get("role"))

    # Preserve user-provided values, but replace blanks and weak generated placeholders.
    name = clean(character.get("name"))
    story_title = clean(story.get("title")) or ("esta historia" if portuguese else "this story")
    genre = clean(story.get("genre")) or ("drama interativo" if portuguese else "interactive drama")
    tone = clean(story.get("tone")) or ("dramatico" if portuguese else "dramatic")
    scene_title = clean(scene.get("title")) or ("a cena atual" if portuguese else "the current scene")
    scene_hint = compact_context(scene.get("scene_text"), 180) or scene_title

    defaults = pt_character_defaults(name, story_title, genre, tone, scene_hint, is_player) if portuguese else en_character_defaults(name, story_title, genre, tone, scene_hint, is_player)
    for field, value in defaults.items():
        current = clean(character.get(field))
        if not current or is_generic_introduced_text(current):
            character[field] = value

    if clean(character.get("appearance")) and not clean(character.get("physical")):
        character["physical"] = clean(character.get("appearance"))
    if not clean(character.get("visual_prompt")):
        character["visual_prompt"] = build_sprite_visual_prompt(character, "neutral", "")
    return character


def pt_character_defaults(name, story_title, genre, tone, scene_hint, is_player=False):
    if is_player:
        return {
            "species": "humano",
            "gender": "nao especificado",
            "character_type": "protagonista",
            "aliases": "nenhum alias conhecido",
            "description": f"{name} e o ponto de vista central de {story_title}, alguem cuja presenca move as escolhas, perdas e descobertas da historia.",
            "physical": "Aparencia definida de forma coerente com o mundo, com uma silhueta clara para sprite de visual novel.",
            "personality": "Observador, movido por desejo forte e por uma duvida interna que cria tensao nas escolhas.",
            "clothing": "Roupa coerente com sua origem, funcao social e com o tom da historia.",
            "role": "protagonista",
            "relationship": "E o centro das relacoes dramaticas da historia.",
            "secrets": "Carrega medos, duvidas ou uma verdade pessoal que pode ganhar importancia conforme a historia avanca.",
            "speech_style": "Fala de modo direto quando pressionado, mas deixa transparecer hesitacao nos momentos emocionais.",
        }
    return {
        "species": "humano",
        "gender": "nao especificado",
        "character_type": "personagem recorrente",
        "aliases": "nenhum alias conhecido",
        "description": (
            f"{name} pertence ao mundo de {story_title} e carrega marcas do genero {genre} e do tom {tone}. "
            f"Sua presenca sugere uma ligacao real com o conflito em torno de {scene_hint}, criando novas pressoes para o protagonista."
        ),
        "physical": "Presenca visual marcante, postura reconhecivel e detalhes fisicos coerentes com seu lugar no mundo.",
        "personality": "Age com objetivo proprio, esconde parte das intencoes e reage a pressao com uma mistura de cautela e necessidade.",
        "clothing": "Vestimenta coerente com sua funcao social, origem e atmosfera da historia.",
        "role": "personagem ligado ao conflito atual",
        "relationship": "Relacao inicial ambigua com o protagonista, atravessada por suspeita, interesse ou dependencia circunstancial.",
        "secrets": "Sabe ou deseja algo que ainda nao foi totalmente revelado.",
        "speech_style": "Fala com ritmo proprio, escolhendo palavras que sugerem subtexto e historia anterior.",
    }


def en_character_defaults(name, story_title, genre, tone, scene_hint, is_player=False):
    if is_player:
        return {
            "species": "human",
            "gender": "unspecified",
            "character_type": "protagonist",
            "aliases": "no known aliases",
            "description": f"{name} is the central point of view of {story_title}, the person whose choices, losses, and discoveries move the story.",
            "physical": "Appearance consistent with the world, with a clear silhouette for a visual novel sprite.",
            "personality": "Observant, driven by a strong desire and an inner doubt that creates tension in choices.",
            "clothing": "Clothing consistent with their origin, social role, and the tone of the story.",
            "role": "protagonist",
            "relationship": "They are the center of the story's dramatic relationships.",
            "secrets": "Carries fears, doubts, or a personal truth that may become important as the story advances.",
            "speech_style": "Speaks directly under pressure, but emotional moments reveal hesitation.",
        }
    return {
        "species": "human",
        "gender": "unspecified",
        "character_type": "recurring character",
        "aliases": "no known aliases",
        "description": (
            f"{name} belongs to the world of {story_title}, shaped by its {genre} genre and {tone} tone. "
            f"Their presence suggests a real connection to the conflict around {scene_hint}, creating new pressure for the protagonist."
        ),
        "physical": "Distinct visual presence, recognizable posture, and physical details consistent with their place in the world.",
        "personality": "Acts with a personal goal, hides part of their intent, and reacts to pressure with caution and need.",
        "clothing": "Clothing consistent with their social function, origin, and the atmosphere of the story.",
        "role": "character connected to the current conflict",
        "relationship": "An initially ambiguous relationship with the protagonist, shaped by suspicion, interest, or circumstantial dependence.",
        "secrets": "Knows or wants something that has not yet been fully revealed.",
        "speech_style": "Speaks with a distinct rhythm, choosing words that imply subtext and prior history.",
    }


def looks_portuguese_text(value):
    text = clean(value).lower()
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
    ]
    return any(marker in text for marker in markers) or any(char in text for char in "ãõçáéíóúâêô")


def enrich_introduced_character(story, scene, payload):
    candidate = introduced_candidate_from_payload(payload)
    if not clean(candidate.get("name")):
        candidate["name"] = clean(payload.get("name"))
    settings = db.get_settings()
    workbench_id = sprite_workbench_for_story_id((story or {}).get("id"), settings)
    prompt_profile = sprite_prompt_profile(settings, workbench_id)
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
        result = chat_json(settings.get("ollama_url"), settings.get("ollama_model"), messages, 0.4)
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
        character = local_character_enrichment(candidate)
    character = contextual_introduced_character_enrichment(character, story, scene)
    character = complete_character_record(character, story, scene)
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


def contextual_introduced_character_enrichment(character, story, scene):
    if not is_portuguese(story_language(story)):
        return character
    name = clean(character.get("name")) or "Este personagem"
    story_title = clean(story.get("title")) or "esta historia"
    genre = clean(story.get("genre")) or "drama interativo"
    tone = clean(story.get("tone")) or "tenso"
    scene_title = clean(scene.get("title")) or "o momento atual"
    scene_text = clean(scene.get("scene_text"))
    scene_hint = compact_context(scene_text, 180) or "a cena atual"

    if not clean(character.get("character_type")) or is_generic_introduced_text(character.get("character_type")):
        character["character_type"] = "personagem recorrente ligado ao conflito atual"
    if not clean(character.get("description")) or is_generic_introduced_text(character.get("description")):
        character["description"] = (
            f"{name} surge como uma presenca ligada ao conflito de {story_title}, "
            f"carregando sinais de uma vida moldada pelo tom {tone} da historia. "
            f"Em {scene_title}, sua chegada nao parece casual: ela pressiona a cena, "
            f"revela uma fissura no mundo de {genre} e sugere que ha interesses ocultos por tras de {scene_hint}."
        )
    physical = clean(character.get("physical"))
    description = clean(character.get("description"))
    if (
        not physical
        or is_generic_introduced_text(physical)
        or (description and physical == description)
    ):
        character["physical"] = (
            "Presenca marcante, olhar atento e postura controlada, como alguem acostumado a medir o perigo "
            "antes de revelar intencoes. A aparencia deve refletir sua funcao social no mundo e deixar uma silhueta facil de reconhecer."
        )
    if not clean(character.get("personality")) or is_generic_introduced_text(character.get("personality")):
        character["personality"] = (
            "Observa mais do que entrega, fala com cuidado e parece dividir-se entre autopreservacao e uma necessidade real de interferir. "
            "Sob pressao, tende a esconder medo atras de firmeza, o que torna dificil saber se ajuda, manipula ou testa o protagonista."
        )
    if not clean(character.get("clothing")) or is_generic_introduced_text(character.get("clothing")):
        character["clothing"] = (
            "Roupas coerentes com sua posicao no mundo da historia, com detalhes gastos ou simbolicos que indiquem origem, oficio ou lealdade."
        )
    if not clean(character.get("role")) or is_generic_introduced_text(character.get("role")):
        character["role"] = "agente de pressao narrativa, possivel aliado ambiguo ou portador de informacao importante"
    if not clean(character.get("relationship")) or is_generic_introduced_text(character.get("relationship")):
        character["relationship"] = (
            "Ainda incerta, mas nasce de uma tensao imediata com o protagonista: curiosidade, suspeita e a possibilidade de uma alianca desconfortavel."
        )
    if not clean(character.get("speech_style")) or is_generic_introduced_text(character.get("speech_style")):
        character["speech_style"] = (
            "Fala em frases medidas, com pausas que sugerem calculo; evita explicar tudo de uma vez e deixa subtexto nas escolhas de palavras."
        )
    if not clean(character.get("visual_prompt")):
        character["visual_prompt"] = build_sprite_visual_prompt(character, "neutral", "")
    return character


def infer_species(character):
    text = character_text(character)
    if any(term in text for term in ["bode", "goat"]):
        return "bode"
    if any(term in text for term in ["vampir", "elf", "fada", "demon", "anjo"]):
        return "ser fantastico"
    return "humano"


def infer_gender(character):
    text = character_text(character)
    if any(term in text for term in ["garota", "menina", "mulher", "feminina", "senhora", "1girl"]):
        return "feminino"
    if any(term in text for term in ["garoto", "menino", "homem", "masculino", "senhor", "1boy"]):
        return "masculino"
    return ""


def infer_clothing(character):
    text = character_text(character)
    if "jaqueta" in text:
        return "jaqueta e roupas casuais"
    if any(term in text for term in ["manto", "robe"]):
        return "manto de fantasia"
    if any(term in text for term in ["vestido", "dress"]):
        return "vestido"
    return "roupa coerente com o papel do personagem"


def character_text(character):
    return " ".join(
        clean(character.get(field)).lower()
        for field in ["name", "role", "description", "background", "appearance", "physical", "personality", "clothing"]
        if clean(character.get(field))
    )


def title_from_prompt(prompt):
    words = [word for word in re.findall(r"[\wÀ-ÿ]+", prompt or "") if len(word) > 2]
    if not words:
        return "Historia local"
    return " ".join(words[:5]).title()


def improve_text(payload):
    text = clean(payload.get("text"))
    if not text:
        return {"improved_text": ""}

    settings = db.get_settings()
    field_label = clean(payload.get("field_label")) or "campo"
    field_type = clean(payload.get("field_type")) or "descricao"
    story_context = payload.get("story_context") or {}
    messages = [
        {"role": "system", "content": IMPROVE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Tipo de campo: {field_type}\n"
                f"Nome do campo: {field_label}\n"
                f"Contexto da historia/personagem: {story_context}\n\n"
                f"Texto original:\n{text}\n\n"
                "Melhore o texto agora."
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
            float(settings.get("ollama_temperature") or 0.8),
            {
                "num_ctx": int(settings.get("ollama_context") or 8192),
                "num_predict": 1600,
            },
        )
        db.add_api_log(
            "ollama",
            "chat:improve",
            {"model": settings.get("ollama_model"), "messages": messages},
            result,
        )
        improved = clean(result.get("improved_text"))
        return {"improved_text": improved or text}
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:improve",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="error",
            error=str(exc),
        )
        return {
            "improved_text": (
                f"{text}\n\n"
                f"Notas para expansao futura: detalhe melhor aparencia, motivacoes, conflitos, "
                f"relacoes, atmosfera e elementos visuais quando o Ollama estiver disponivel."
            ),
            "warning": f"Ollama indisponivel: {str(exc)[:180]}",
        }


def improve_visual_prompt(text, context=None):
    text = clean(text)
    if not text:
        return ""
    settings = db.get_settings()
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
        )
        db.add_api_log(
            "ollama",
            "chat:visual-prompt",
            {"model": settings.get("ollama_model"), "messages": messages},
            result,
        )
        return sanitize_visual_prompt(extract_visual_prompt(result), text, context) or text
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:visual-prompt",
            {"model": settings.get("ollama_model"), "messages": messages},
            status="error",
            error=str(exc),
        )
        return text


def generate_workbench_visual_prompt(source_text, asset_type, workbench_id, prompt_profile, fallback_prompt="", story_id=None):
    source_text = clean(source_text)
    fallback_prompt = clean(fallback_prompt) or source_text
    prompt_profile = prompt_profile if isinstance(prompt_profile, dict) else {}
    style = clean(prompt_profile.get("style"))
    example = clean(prompt_profile.get("example"))
    if not source_text or not (style or example):
        return fallback_prompt

    settings = db.get_settings()
    system = (
        "You adapt visual generation requests for a specific ComfyUI workflow. "
        "Return only valid JSON: {\"visual_prompt\":\"...\"}. "
        "The visual_prompt must follow the workflow prompt style exactly. "
        "Preserve fixed character identity traits and requested expression. "
        "Do not add extra characters, copyrighted artist names, watermarks, UI text, or camera metadata. "
        "The visual_prompt must be entirely in English. Translate any Portuguese source fields into English."
    )
    user = (
        f"Asset type: {asset_type}\n"
        f"Workbench id: {workbench_id}\n\n"
        f"Prompt style instructions:\n{style or '(none)'}\n\n"
        f"Example prompt for this workbench:\n{example or '(none)'}\n\n"
        f"Source description to convert:\n{source_text}\n\n"
        f"Fallback prompt if useful:\n{fallback_prompt}\n\n"
        "Create one final prompt for this exact workbench. Return the visual_prompt in English only."
    )
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
        )
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "messages": messages},
            result,
            story_id=story_id,
        )
        visual_prompt = extract_visual_prompt(result)
        return clean(visual_prompt) or fallback_prompt
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:workbench-prompt",
            {"model": settings.get("ollama_model"), "workbench": workbench_id, "messages": messages},
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        return fallback_prompt


def build_sprite_visual_prompt(character, expression=None, user_prompt=""):
    character = character or {}
    source = " ".join(
        clean(part)
        for part in [
            character.get("species"),
            character.get("gender"),
            character.get("physical"),
            character.get("clothing"),
            expression,
        ]
        if clean(part)
    )
    lower = source.lower()

    tags = ["solo", "single character", "full body", "standing", "front view", "visual novel sprite"]
    tags.extend(gender_prompt_tags(lower))
    tags.extend(age_prompt_tags(lower))
    tags.extend(hair_prompt_tags(lower))
    tags.extend(eye_prompt_tags(lower))
    tags.extend(body_prompt_tags(lower))
    tags.extend(outfit_prompt_tags(lower))
    tags.extend(expression_prompt_tags(expression or lower))

    tags.extend(["clean lineart", "detailed face", "detailed eyes", "clean silhouette", "simple light gray background"])
    return dedupe_tags(tags)


def build_sprite_source_prompt(character, expression=None, user_prompt=""):
    character = character or {}
    parts = []
    for label, value in [
        ("Species", character.get("species")),
        ("Gender", character.get("gender")),
        ("Physical appearance", character.get("physical")),
        ("Clothing", character.get("clothing")),
    ]:
        value = clean(value)
        if value:
            parts.append(f"{label}: {value}")
    parts.append(
        "Create the final image prompt in English only. Sprite requirements: one character only, full body, standing, front view, visual novel sprite, simple light background."
    )
    return "\n".join(parts)


def build_background_visual_prompt(story, scene):
    story = story or {}
    scene = scene or {}
    prompt = clean(scene.get("background_prompt"))
    visual_style = clean(story.get("visual_style")) or "anime visual novel background"

    parts = [
        "empty visual novel background, no people, no characters, no faces, no silhouettes, no text, no UI",
        visual_style,
        prompt,
    ]
    if len(prompt) < 180:
        parts.extend(
            [
                "unique memorable landmark",
                "environment details tied to the current story conflict",
                "specific props and visual clues",
            ]
        )
    parts.extend(
        [
            "specific architecture and spatial layout",
            "distinct foreground, midground, and background depth",
            "environmental storytelling objects",
            "clear material textures",
            "cinematic lighting",
            "cohesive color palette",
            "wide establishing shot",
            "high detail",
            "polished anime visual novel background art",
        ]
    )
    return dedupe_tags(parts)


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
    text = clean(expression).lower()
    mapping = {
        "happy": "smile",
        "sad": "sad expression",
        "angry": "angry expression",
        "surprised": "surprised expression",
        "scared": "scared expression",
        "embarrassed": "embarrassed expression",
        "thoughtful": "thoughtful expression",
        "neutral": "neutral expression",
    }
    for key, value in mapping.items():
        if key in text:
            return [value]
    return ["neutral expression"]


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
    if any(term in source for term in ["senhor", "homem", "masculino", "luden de flama"]):
        additions.extend(["1boy", "male", "masculine", "old man"])
    if any(term in source for term in ["senhora", "mulher", "feminina", "garota"]):
        additions.extend(["1girl", "female"])
    if any(term in source for term in ["careca", "bald"]):
        additions.append("bald")
    if any(term in source for term in ["magro", "thin", "slender"]):
        additions.append("slender")
    if any(term in source for term in ["alto", "tall"]):
        additions.append("tall")
    if "flama" in source or "fogo" in source or "fire" in source:
        additions.extend(["red formal fantasy robe with gold trim"])

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


def generate_scene(story_id, user_input):
    story = db.get_story(story_id)
    if not story:
        raise ValueError("Historia nao encontrada.")

    settings = db.get_settings()
    narrative_context = build_narrative_context(story, user_input)
    user_prompt = build_narrator_user_prompt(story, user_input, narrative_context)
    messages = [
        {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    log_request = {
        "model": settings.get("ollama_model"),
        "system_chars": len(NARRATOR_SYSTEM_PROMPT),
        "user_prompt_chars": len(user_prompt),
        "context_section_chars": {key: len(str(value or "")) for key, value in narrative_context.items()},
        "user_input": user_input,
        "prompt_preview": user_prompt[:1200],
    }

    try:
        started = time.perf_counter()
        db.add_api_log(
            "ollama",
            "chat:narrator",
            log_request,
            story_id=story_id,
            status="started",
        )
        result = chat_json(
            settings.get("ollama_url"),
            settings.get("ollama_model"),
            messages,
            float(settings.get("ollama_temperature") or 0.8),
            {
                "num_ctx": int(settings.get("ollama_context") or 8192),
                "num_predict": 1800,
            },
        )
        db.add_api_log(
            "ollama",
            "chat:narrator",
            log_request,
            {"duration_seconds": round(time.perf_counter() - started, 2), "result": result},
            story_id=story_id,
        )
    except Exception as exc:
        db.add_api_log(
            "ollama",
            "chat:narrator",
            log_request,
            status="error",
            error=str(exc),
            story_id=story_id,
        )
        result = fallback_scene(story, user_input, str(exc))

    scene = normalize_scene(result)
    scene["user_input"] = user_input
    scene["raw_ai_response"] = result
    return db.add_scene(story_id, scene)


def normalize_scene(raw):
    scene_text = clean(raw.get("scene_text"))
    dialogues = normalize_dialogues(raw.get("dialogues"))
    if not dialogues and scene_text:
        dialogues = [{"character": "Narrador", "expression": "neutral", "text": scene_text}]
    return {
        "title": clean(raw.get("title")) or "Nova cena",
        "scene_text": scene_text,
        "dialogues": dialogues,
        "choices": normalize_choices(raw.get("choices")),
        "background_prompt": clean(raw.get("background_prompt")),
        "characters_on_screen": normalize_on_screen(raw.get("characters_on_screen")),
        "new_characters_detected": raw.get("new_characters_detected") if isinstance(raw.get("new_characters_detected"), list) else [],
        "memory_updates": normalize_memory(raw.get("memory_updates")),
    }


def normalize_dialogues(value):
    if not isinstance(value, list):
        return []
    dialogues = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        text = clean(item.get("text"))
        if not text:
            continue
        dialogues.append(
            {
                "character": clean(item.get("character")) or "Narrador",
                "expression": clean(item.get("expression")) or "neutral",
                "text": text,
            }
        )
    return dialogues


def normalize_choices(value):
    if not isinstance(value, list):
        return ["Continuar observando", "Agir com cautela", "Dizer algo inesperado"]
    return [clean(choice) for choice in value[:5] if clean(choice)]


def normalize_on_screen(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:4]:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "name": clean(item.get("name")),
                "position": clean(item.get("position")) or "center",
                "expression": clean(item.get("expression")) or "neutral",
            }
        )
    return [item for item in result if item["name"]]


def normalize_memory(value):
    if not isinstance(value, dict):
        return {"summary": "", "facts": []}
    facts = value.get("facts") if isinstance(value.get("facts"), list) else []
    return {"summary": clean(value.get("summary")), "facts": [clean(fact) for fact in facts if clean(fact)]}


def clean(value):
    return value.strip() if isinstance(value, str) else ""


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


def fallback_scene(story, user_input, error):
    protagonist = (story.get("player_character") or {}).get("name") or "Protagonista"
    title = story.get("title") or "Historia"
    action = user_input or "iniciar a historia"
    return {
        "title": "Cena inicial",
        "scene_text": (
            f"A historia '{title}' aguarda a IA local responder, mas o fluxo do jogo continua em modo offline. "
            f"A ultima acao registrada foi: {action}. "
            "Use esta cena para testar salvamento, escolhas e interface enquanto o Ollama fica indisponivel."
        ),
        "dialogues": [
            {
                "character": protagonist,
                "expression": "thoughtful",
                "text": "Preciso organizar meus proximos passos antes que esta historia avance de verdade.",
            }
        ],
        "choices": ["Investigar o ambiente", "Rever meus objetivos", "Esperar a IA local voltar"],
        "background_prompt": "quiet visual novel room, desk with notes, soft evening light, anime background, no people",
        "characters_on_screen": [{"name": protagonist, "position": "center", "expression": "thoughtful"}],
        "new_characters_detected": [],
        "memory_updates": {
            "summary": f"{protagonist} esta no inicio da jornada. Modo offline usado porque Ollama falhou.",
            "facts": [f"Erro Ollama registrado: {error[:180]}"],
        },
    }
