NARRATOR_SYSTEM_PROMPT = """Voce e o narrador de uma visual novel interativa local.

Responda somente JSON valido, sem markdown e sem texto fora do JSON.

Objetivo:
- Continuar a historia de forma coerente com lore, personagens, memoria e acao do jogador.
- Escrever no idioma da historia informado no prompt do usuario, exceto prompts visuais, que devem ficar em ingles.
- Gerar um bloco de visual novel com atmosfera, subtexto, tensao emocional e consequencia clara.
- A acao do jogador deve produzir consequencia imediata, mudanca de relacao ou nova informacao dramatica.
- Nao contradizer fatos estabelecidos.
- So inclua personagem novo se ele tiver fala ou presenca relevante.

Formato obrigatorio:
{
  "title": "titulo curto do momento",
  "scene_text": "narracao de abertura em 2 a 4 frases sensoriais e dramaticas",
  "dialogues": [
    {
      "character": "Nome ou Narrador",
      "expression": "neutral | happy | sad | angry | surprised | scared | embarrassed | thoughtful",
      "text": "fala ou narracao com voz propria, subtexto e detalhe emocional"
    }
  ],
  "choices": [
    "Opcao de escolha 1",
    "Opcao de escolha 2",
    "Opcao de escolha 3"
  ],
  "location": "nome curto e estavel do local atual",
  "location_changed": false,
  "background_prompt": "robust English prompt for an empty visual novel background, no people",
  "characters_on_screen": [
    {
      "name": "Nome",
      "position": "left | center | right",
      "expression": "neutral | happy | sad | angry | surprised | scared | embarrassed | thoughtful"
    }
  ],
  "new_characters_detected": [
    {
      "temporary_name": "nome temporario",
      "display_name": "nome sugerido",
      "reason": "motivo para cadastro",
      "species": "especie em portugues",
      "gender": "genero em portugues",
      "character_type": "tipo narrativo em portugues",
      "aliases": "apelidos ou titulos em portugues",
      "suggested_description": "descricao completa em portugues, conectada ao mundo e a historia",
      "suggested_physical": "aparencia fisica em portugues",
      "suggested_personality": "personalidade em portugues, com contradicoes e motivacoes",
      "suggested_clothing": "vestimenta em portugues",
      "suggested_role": "papel provavel na trama em portugues",
      "suggested_relationship": "relacao provavel com o protagonista ou a cena em portugues",
      "suggested_speech_style": "estilo de fala em portugues",
      "suggested_visual_prompt": "english visual prompt for character sprite"
    }
  ],
  "memory_updates": {
    "summary": "resumo atualizado da situacao ate agora",
    "facts": [
      "fato importante estabelecido"
    ]
  }
}

Regras visuais:
- background_prompt deve descrever somente ambiente, sem pessoas.
- location deve ser um identificador narrativo estavel do cenario atual, como "biblioteca subterranea", "rua do mercado noturno" ou "quarto de hospital abandonado".
- O Ollama deve decidir explicitamente se houve mudanca fisica de cenario.
- Use location_changed true somente se a cena mudar fisicamente para outro ambiente, sala, rua, regiao, edificio ou ponto de vista ambiental.
- Use location_changed false se a conversa, acao, emocao ou revelacao acontecer no mesmo ambiente, mesmo que a iluminacao, tensao ou foco narrativo mude.
- Se location_changed false, mantenha location igual ou equivalente ao local atual e preserve um background_prompt visualmente compativel com o background atual.
- Se location_changed true, crie um background_prompt novo e especifico para o novo ambiente.
- background_prompt deve ser forte para SDXL/ComfyUI: 45 a 90 palavras em ingles, sem pessoas, sem personagens, sem texto/UI, com arquitetura/espaco, materiais, objetos importantes, clima, periodo do dia, iluminacao, paleta, composicao e profundidade.
- Evite prompts genericos como "room", "street", "forest", "anime background". Sempre inclua detalhes concretos que pertencam ao mundo e a cena.
- Nao inclua nomes de personagens no background_prompt.
- personagens em characters_on_screen devem existir ou aparecer em new_characters_detected.

Regras de ritmo:
- dialogues deve ter 4 a 8 entradas quando houver personagens na cena; pode usar ate 10 se a cena precisar respirar.
- Pode alternar falas com entradas de Narrador para pausas, gestos, silencio, atmosfera e pensamentos observaveis.
- Falas devem soar como visual novel: personagens com voz propria, desejos, receios, meias verdades e reacoes ao jogador.
- Evite respostas rasas de uma frase por personagem. Prefira linhas com intencao dramatica e detalhe concreto.
- Nao resolva conflitos rapido demais; avance por revelacoes, pressao emocional e escolhas significativas.
- Nao avance para outro ambiente sem necessidade clara da acao do jogador.

Regras para personagens novos:
- Se new_characters_detected incluir alguem, crie uma ficha inicial completa em portugues.
- Nao use descricoes genericas como "personagem presente em cena" ou "apareceu surpreso".
- A descricao deve explicar quem essa pessoa parece ser dentro daquele mundo, por que ela importa para a cena, que marca visual ou social ela carrega e que tensao ela introduz.
- Campos narrativos do personagem novo ficam em portugues brasileiro. Apenas suggested_visual_prompt fica em ingles.
"""


def build_narrative_context(story, user_input):
    characters = story.get("characters") or []
    scenes = story.get("scenes") or []
    memory = story.get("memory_entries") or []
    lore_entries = story.get("lore_entries") or []
    current_scene = scenes[-1] if scenes else {}
    current_raw = current_scene.get("raw_ai_response") or {}
    current_location = current_raw.get("location") if isinstance(current_raw, dict) else ""
    current_background = current_scene.get("background_prompt") or ""
    selected_characters = select_relevant_characters(characters, current_scene, user_input, story.get("player_character") or {})

    return {
        "story_bible": build_story_bible(story, lore_entries),
        "current_story_memory": build_current_story_memory(story, memory),
        "active_characters": build_active_characters(story, selected_characters),
        "recent_scenes": build_recent_scenes(scenes[-4:]),
        "visual_state": build_visual_state(current_location, current_background),
        "player_choice": user_input or "Comece ou continue a historia naturalmente.",
        "task": build_narrative_task(),
    }


def build_narrator_user_prompt(story, user_input, context=None):
    context = context or build_narrative_context(story, user_input)
    return f"""STORY BIBLE:
{context["story_bible"]}

CURRENT STORY MEMORY:
{context["current_story_memory"]}

ACTIVE CHARACTERS:
{context["active_characters"]}

RECENT SCENES:
{context["recent_scenes"]}

VISUAL STATE:
{context["visual_state"]}

PLAYER CHOICE:
{context["player_choice"]}

TASK:
{context["task"]}"""


def build_story_bible(story, lore_entries):
    player = story.get("player_character") or {}
    lore_lines = []
    for entry in lore_entries[:6]:
        title = compact(entry.get("title"), 80) or "Lore"
        entry_type = compact(entry.get("entry_type"), 40) or "note"
        content = compact(entry.get("content"), 260)
        if content:
            lore_lines.append(f"- [{entry_type}] {title}: {content}")

    return "\n".join(
        [
            f"Titulo: {story.get('title')}",
            f"Genero: {story.get('genre')}",
            f"Tom: {story.get('tone')}",
            f"Estilo visual: {story.get('visual_style')}",
            f"Idioma da historia: {story.get('language') or 'pt-BR'}",
            "",
            "Lore principal:",
            compact(story.get("lore") or "Nao definido.", 1200),
            "",
            "Lorebook relevante:",
            "\n".join(lore_lines) or "Sem entradas adicionais de lore.",
            "",
            "Protagonista:",
            "\n".join(
                [
                    f"Nome: {player.get('name') or 'Jogador'}",
                    f"Papel: {compact(player.get('role'), 100)}",
                    f"Personalidade: {compact(player.get('personality'), 220)}",
                    f"Objetivos: {compact(player.get('goals'), 220)}",
                    f"Historico: {compact(player.get('background'), 220)}",
                ]
            ),
        ]
    )


def build_current_story_memory(story, memory):
    selected = sorted(
        memory,
        key=lambda entry: (int(entry.get("importance") or 0), int(entry.get("created_at") or 0)),
        reverse=True,
    )[:10]
    memory_lines = []
    for entry in selected:
        entry_type = compact(entry.get("entry_type"), 40) or "note"
        importance = entry.get("importance") or 1
        content = compact(entry.get("content"), 220)
        if content:
            memory_lines.append(f"- [{entry_type}, importancia {importance}] {content}")

    return "\n".join(
        [
            "Resumo vivo:",
            compact(story.get("summary") or "A historia esta no inicio.", 950),
            "",
            "Memorias persistentes mais importantes:",
            "\n".join(memory_lines) or "Sem memoria registrada.",
        ]
    )


def build_active_characters(story, selected_characters):
    character_lines = []
    seen = set()
    for character in selected_characters:
        key = str(character.get("name") or "").lower()
        if key in seen:
            continue
        seen.add(key)
        character_lines.append(
            "\n".join(
                [
                    f"Nome: {character.get('name', '')}",
                    f"Papel: {compact(character.get('role'), 80)}",
                    f"Tipo: {compact(character.get('character_type'), 60)}",
                    f"Descricao: {compact(character.get('description'), 180)}",
                    f"Aparencia: {compact(character.get('physical'), 160)}",
                    f"Personalidade: {compact(character.get('personality'), 180)}",
                    f"Relacao: {compact(character.get('relationship'), 140)}",
                    f"Estilo de fala: {compact(character.get('speech_style'), 100)}",
                    f"Segredos/conflitos: {compact(character.get('secrets'), 120)}",
                    f"Status: {character.get('status', '')}",
                ]
            )
        )
    return "\n\n".join(character_lines) or "Nenhum personagem conhecido."


def build_recent_scenes(recent_scenes):
    recent_lines = []
    for scene in recent_scenes:
        dialogues = scene.get("dialogues", [])
        compact_dialogues = []
        for dialogue in dialogues[-6:]:
            if isinstance(dialogue, dict):
                compact_dialogues.append(f"{dialogue.get('character', 'Narrador')}: {compact(dialogue.get('text'), 180)}")
        raw = scene.get("raw_ai_response") or {}
        location = raw.get("location") if isinstance(raw, dict) else ""
        recent_lines.append(
            f"Momento {scene.get('scene_order')} - {compact(scene.get('title'), 80)}\n"
            f"Local: {compact(location or 'desconhecido', 120)}\n"
            f"Narracao: {compact(scene.get('scene_text'), 300)}\n"
            f"Dialogos recentes: {' | '.join(compact_dialogues) or 'sem dialogos'}\n"
            f"Escolhas: {scene.get('choices', [])}"
        )
    return "\n\n".join(recent_lines) or "Nenhuma cena gerada ainda."


def build_visual_state(current_location, current_background):
    return "\n".join(
        [
            f"Local atual: {current_location or 'desconhecido'}",
            f"Background atual: {compact(current_background or 'nenhum background definido', 260)}",
        ]
    )


def build_narrative_task():
    return (
        "Gere o proximo bloco de interacao no JSON obrigatorio, com densidade de visual novel.\n"
        "Use STORY BIBLE para regras fixas do mundo e tom.\n"
        "Use CURRENT STORY MEMORY para continuidade de longo prazo e fatos persistentes.\n"
        "Use ACTIVE CHARACTERS para voz, relacoes, segredos e conflitos dos personagens presentes ou relevantes.\n"
        "Use RECENT SCENES apenas para continuidade imediata.\n"
        "Monitore o cenario atual com cuidado: se a acao acontecer no mesmo local, preserve location/background e defina location_changed como false. "
        "Se houver deslocamento fisico para outro cenario, defina location_changed como true e gere um background_prompt novo, robusto e especifico."
    )


def select_relevant_characters(characters, current_scene, user_input, player):
    wanted = set()
    text = (user_input or "").lower()
    player_name = (player.get("name") or "").lower()
    if player_name:
        wanted.add(player_name)
    for item in current_scene.get("characters_on_screen") or []:
        if isinstance(item, dict) and item.get("name"):
            wanted.add(str(item.get("name")).lower())
    for dialogue in current_scene.get("dialogues") or []:
        if isinstance(dialogue, dict) and dialogue.get("character"):
            wanted.add(str(dialogue.get("character")).lower())
    selected = []
    for character in characters:
        name = str(character.get("name") or "")
        key = name.lower()
        if key and (key in wanted or key in text):
            selected.append(character)
    if not selected:
        selected = characters[:4]
    return selected[:5]


def compact(value, limit):
    text = str(value or "").replace("\r", " ").strip()
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
