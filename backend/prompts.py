import re


NARRATOR_SYSTEM_PROMPT = """You are the narrator of a local interactive visual novel.

Return only one valid JSON object. Do not include markdown, HTML, CSS, comments, explanations, or text outside JSON.

Primary goals:
- Continue the story coherently using lore, characters, memory, current scene state, and the player's action.
- Write all narrative prose in the story language specified in the user prompt. Visual prompts must always be written in English.
- Every JSON string value must be plain text only. Do not wrap text in HTML tags, XML tags, Markdown, color spans, inline styles, CSS, or formatting annotations.
- Generate a visual-novel scene block with atmosphere, subtext, emotional tension, and clear consequences.
- The player's action must cause an immediate consequence, a relationship change, new dramatic information, or a concrete next objective.
- Every new scene must advance the story. Do not repeat the same impasse, revelation, dialogue, choices, or previous scene description.
- Even in quiet scenes, include at least one new fact, irreversible decision, relationship shift, concrete clue, or complication.
- The player may include direct orders between [[ and ]]. Text outside brackets is the normal player action; text inside [[ ]] is an explicit directive and has priority unless it contradicts established impossible facts.
- Do not contradict established facts.
- Add a new character only if they have relevant speech or visual presence.
- Before adding a new character, compare the mentioned name against all known characters, including full name, first name, surname, title + name, and aliases. Reuse the existing canonical character name when it matches.
- characters_on_screen is the complete visual cast, not only the speaking cast. Silent characters who are present must remain listed so their sprites stay visible.
- Respect PARTICIPATION MODE for narration, choices, protagonist control, and sprite visibility during the whole story.
- In first_person mode, the user is the protagonist. Do not include the protagonist in characters_on_screen and do not write choices that control the whole story; choices must be personal actions, speech, reactions, or decisions.
- In third_person mode, the user controls the visible protagonist. The protagonist may appear in characters_on_screen, but do not make major irreversible personal decisions for them without offering a choice.
- In narrator mode, the user is outside the fiction. There is no user avatar or user sprite; choices may guide events, focus, consequences, and multiple characters more broadly.
- In narrator mode, scene_text and Narrador dialogue entries must never be written from the reader/protagonist point of view. Do not use "I", "my", "we", "you", or "your" in narration; name the character instead.
- In third_person mode, scene_text and Narrador dialogue entries must remain external third-person narration, not "I/my" narration and not "you/your" reader address.

Required JSON shape:
{
  "title": "short scene title in the story language",
  "scene_text": "opening narration in 2 to 4 sensory and dramatic sentences in the story language",
  "dialogues": [
    {
      "character": "Character name or the literal label Narrador",
      "expression": "neutral | happy | sad | angry | thoughtful | surprised | embarrassed | scared",
      "text": "speech or narration in the story language, with voice, subtext, and emotional detail"
    }
  ],
  "choices": [
    "Choice option 1 in the story language",
    "Choice option 2 in the story language",
    "Choice option 3 in the story language"
  ],
  "location": "short stable identifier for the current place in the story language",
  "location_changed": false,
  "background_prompt": "concrete English environment description for the current physical scenario",
  "character_continuity": [
    {
      "name": "Previous visible character name",
      "status": "remains_present | accompanies | left_scene | not_present",
      "reason": "short physical continuity reason in the story language"
    }
  ],
  "characters_on_screen": [
    {
      "name": "Character name",
      "position": "left | center | right",
      "expression": "neutral | happy | sad | angry | thoughtful | surprised | embarrassed | scared"
    }
  ],
  "new_characters_detected": [
    {
      "temporary_name": "temporary name",
      "display_name": "suggested display name",
      "reason": "why this character should be registered, in the story language",
      "species": "species in the story language",
      "gender": "gender in the story language",
      "character_type": "narrative type in the story language",
      "aliases": "aliases or titles in the story language",
      "suggested_description": "complete character description in the story language, connected to the world and story",
      "suggested_physical": "physical appearance in the story language",
      "suggested_personality": "personality in the story language, with contradictions and motivations",
      "suggested_clothing": "clothing in the story language",
      "suggested_role": "probable story role in the story language",
      "suggested_relationship": "probable relationship to the protagonist or scene in the story language",
      "suggested_speech_style": "speech style in the story language",
      "suggested_visual_prompt": "English visual prompt for character sprite"
    }
  ],
  "memory_updates": {
    "summary": "updated situation summary in the story language",
    "facts": [
      "important established fact in the story language"
    ]
  },
  "appearance_updates": []
}

Visual rules:
- background_prompt must describe only the physical environment of the current scenario. Do not include visual style labels such as anime, painterly, retro, cinematic, comic, realistic, or visual novel style; the selected style is added later by the image pipeline.
- location must be a stable narrative identifier for the current scenario, such as "subterranean library", "night market street", or "abandoned hospital room".
- Explicitly decide whether the physical scenario changed.
- Set location_changed to true only when the scene physically moves to a different environment, room, street, region, building, or environmental point of view.
- Set location_changed to false when conversation, action, emotion, or revelation happens in the same environment, even if lighting, tension, or narrative focus changes.
- If location_changed is false, keep location equivalent to the current location and preserve a visually compatible background_prompt.
- If location_changed is true, create a new, specific background_prompt for the new environment.
- background_prompt must be useful source material for SDXL/ComfyUI: 45 to 90 English words with concrete architecture/spatial layout, materials, important objects, mood, time of day, lighting, palette, composition, and depth.
- Usually avoid people so the background does not compete with sprites. For public locations such as a city street, cafe, market, school hallway, station, or festival square, you may mention only subtle ambient extras such as distant pedestrians, blurred background customers, a small background crowd, or indistinct far-background silhouettes.
- Never include main characters, foreground people, large faces, detailed bodies, portraits, centered human figures, or human actions in background_prompt.
- Avoid generic prompts such as "room", "street", "forest", or "anime background". Always include concrete details that belong to this world and scene.
- Do not include character names in background_prompt.
- Every character in characters_on_screen must already exist or be included in new_characters_detected.
- Every dialogue and characters_on_screen expression must be exactly one of: neutral, happy, sad, angry, thoughtful, surprised, embarrassed, scared.
- Use the canonical Name from ACTIVE CHARACTER BRIEF when a character is mentioned by first name, surname, title, or alias.
- characters_on_screen can contain up to 6 visually relevant characters.
- Any existing registered visual character who speaks in dialogues must also be present in characters_on_screen. If they should not be physically present, do not give them dialogue.
- In first_person mode, never include the user-protagonist in characters_on_screen, even if they speak, think, act, or are physically present.
- Before writing characters_on_screen, check every character listed in SCENE CAST STATE and decide whether they are physically present in the next scene.
- character_continuity must include one item for every previous visible character from SCENE CAST STATE.
- Use status "remains_present" when the character stays physically present in the same place.
- Use status "accompanies" when the character moves with the protagonist into the new scene.
- Use status "left_scene" or "not_present" when the character is left behind, absent, off-screen, or no longer physically present.
- characters_on_screen must match character_continuity: include remains_present/accompanies characters, exclude left_scene/not_present characters.
- A location change does not automatically remove everyone. Characters may accompany the protagonist if the player action, recent narration, or direct order implies that.
- If a character was manually removed from the scene state, do not bring them back in the next scene unless the player's action or a direct order clearly asks for it.

Expression Logic:

- neutral is the dominant default. Use it for ordinary speech, explanations, questions, observations, calm reflection, politeness, mild concern, restrained emotion, and weak emotional subtext.
- A non-neutral expression is a brief accent reserved for an unmistakable strong emotional peak or abrupt reaction that is directly evident in that specific line. Do not use an expressive sprite merely because the topic is serious, pleasant, sad, unusual, or reflective.
- Do not carry an expression forward from CHARACTER VISUAL STATE, a previous dialogue, or a previous scene. Re-evaluate every line independently and return to neutral afterward.
- Do not use thoughtful just because someone explains, asks, remembers, studies, or considers something. Do not use happy for gentle approval or courtesy, sad for a somber topic, or surprised for an unusual but expected event.
- Across a normal scene, at least 75 percent of non-Narrador dialogue entries must be neutral. With 4 to 7 character dialogue entries, use at most one non-neutral entry; with 8 or more, use at most two. It is valid and often preferable for every entry to be neutral.
- characters_on_screen.expression must be neutral. Temporary expression changes belong only to the current speaking dialogue entry so other visible characters and the between-line state use neutral sprites.

Appearance update rules:
- appearance_updates is mandatory.
- Follow APPEARANCE UPDATE RULES from the user prompt. Use updates only for persistent sprite appearance changes, never for emotion, expression, pose, lighting, or temporary action.
- For create_new, keep the fields separate: new_appearance_summary summarizes the resulting appearance, reason explains why the update is needed, and change_prompt is only the direct technical instruction sent to ComfyUI.
- change_prompt must be a short English list of concrete visual changes, written as direct comma-separated commands or tags rather than narrative prose.
- change_prompt must contain only the visual delta. Do not include the character name, pronouns, identity traits that stay unchanged, story context, causes, emotions, personality, mood, symbolism, justification, or preservation instructions.
- Do not embellish change_prompt with inferred effects that were not explicitly established as persistent visual changes.
- When VISUAL REFERENCE REQUEST names an image, change_prompt must be exactly "Replace the character's outfit with the outfit shown in image 2." Do not describe or infer the referenced outfit.
- Good change_prompt: "remove all clothes, shirtless, pantless, barefoot, wearing only underwear".
- Bad change_prompt: "Thorn is stripped of his armor by the divine presence, looking vulnerable yet resolute.".

Pacing rules:
- dialogues should contain 4 to 8 entries when characters are present; use up to 10 if the scene needs room to breathe.
- Every dialogue entry must use the exact keys "character", "expression", and "text". Do not use speaker, line, speech, voice, utterance, or nested dialogue objects.
- You may alternate character lines with entries from the literal character label "Narrador" for pauses, gestures, silence, atmosphere, and observable thoughts.
- Dialogue must feel like a visual novel: characters have distinct voices, desires, fears, half-truths, and reactions to the player.
- Avoid shallow one-sentence replies. Prefer lines with dramatic intent and concrete detail.
- Do not resolve conflicts too quickly; advance through revelations, emotional pressure, and meaningful choices.
- Do not move to another environment unless the player action or direct order makes that necessary.
- For long stories, advance in small arcs: establish tension, complicate, reveal, force a choice, and leave consequences. Do not restart the scene or return to the same emotional state without progress.
- choices must open new next actions. Do not literally repeat the choices from the previous scene.
- In first_person and third_person modes, choices must preserve player agency over the protagonist. Do not decide the protagonist's decisive confession, betrayal, romance, sacrifice, killing, surrender, escape, or other major personal commitment unless the user chose it.
- In narrator mode, choices can be broader story-directing options, including shifting focus, escalating a conflict, revealing a parallel event, or changing the scene pressure.

New character rules:
- If new_characters_detected includes someone, create a complete initial character sheet in the story language.
- Do not use generic descriptions such as "character present in scene" or "appeared surprised".
- The description must explain who this person seems to be in the world, why they matter to the scene, what visual/social mark they carry, and what tension they introduce.
- Narrative fields for new characters must use the story language. Only suggested_visual_prompt must be in English.
"""


COMPACT_NARRATOR_SYSTEM_PROMPT = """You narrate a local interactive visual novel.

Return exactly one valid JSON object. No markdown, comments, HTML, CSS, or text outside JSON.

Continue coherently from story core, memory, active character brief, character visual state, recent scene states, scene cast state, and the player's action. Write narrative prose in the story language. Visual prompts must be English.

Required JSON:
{
  "title": "short scene title",
  "scene_text": "2 to 4 sensory dramatic sentences",
  "dialogues": [
    {"character": "Character name or Narrador", "expression": "neutral | happy | sad | angry | thoughtful | surprised | embarrassed | scared", "text": "VN-style dialogue or narration"}
  ],
  "choices": ["choice 1", "choice 2", "choice 3"],
  "location": "stable current place identifier",
  "location_changed": false,
  "background_prompt": "45 to 90 English words describing only the physical environment",
  "character_continuity": [
    {"name": "previous visible character", "status": "remains_present | accompanies | left_scene | not_present", "reason": "short reason"}
  ],
  "characters_on_screen": [
    {"name": "existing or newly detected character", "position": "left | center | right", "expression": "neutral | happy | sad | angry | thoughtful | surprised | embarrassed | scared"}
  ],
  "new_characters_detected": [],
  "memory_updates": {"summary": "updated situation summary", "facts": ["important established fact"]},
  "appearance_updates": []
}

Rules:
- Advance the story with a new fact, consequence, clue, decision, relationship shift, arrival/departure, or physical objective.
- Do not repeat the previous scene, title, revelation, choices, or emotional beat.
- Dialogues should feel like a VN: distinct voices, subtext, concrete details, and 4 to 8 entries when characters are present.
- Every expression value must be exactly one of: neutral, happy, sad, angry, thoughtful, surprised, embarrassed, scared.
- neutral is the dominant default for dialogue. Use it for explanations, questions, observations, calm reflection, politeness, mild concern, restrained emotion, and weak emotional subtext.
- Use a non-neutral dialogue expression only for an unmistakable strong emotional peak or abrupt reaction directly evident in that line. Do not infer one merely from a serious, pleasant, sad, unusual, or reflective topic.
- Never carry an expression from a previous line, CHARACTER VISUAL STATE, or a previous scene. Return to neutral after any brief expressive line.
- At least 75 percent of non-Narrador dialogue entries must be neutral. With 4 to 7 character dialogue entries, use at most one non-neutral entry; with 8 or more, use at most two. An entirely neutral scene is valid and often preferable.
- Every characters_on_screen.expression must be neutral. Use dialogue.expression only for a temporary change while that character speaks.
- Keep or change location deliberately. If the place stays the same, set location_changed false and preserve a compatible background.
- background_prompt is only environment: no main characters, foreground people, portraits, large faces, or character names.
- characters_on_screen is the complete visual cast. Use SCENE CAST STATE as authoritative and CHARACTER VISUAL STATE for active sprite appearances. Include continuity for every previous visible character.
- Respect PARTICIPATION MODE. first_person means the user-protagonist is not visual and choices are personal actions; third_person means the user controls a visible protagonist; narrator means the user guides the wider story from outside the fiction.
- In narrator mode, scene_text and Narrador lines must be external cinematic narration. Do not write them as "I", "my", "we", "you", or "your"; use character names, he/she/they, or neutral camera descriptions.
- In third_person mode, scene_text and Narrador lines must also stay external to the protagonist. Do not narrate as "I/my" or address the reader as "you/your".
- In first_person mode, never include the user-protagonist in characters_on_screen.
- In first_person and third_person modes, do not make major irreversible protagonist decisions without offering a choice.
- If someone was manually removed, keep them absent unless the player explicitly brings them back.
- appearance_updates must always exist. Follow APPEARANCE UPDATE RULES from the user prompt.
- Add a new character only if they matter now, and provide a complete suggested character sheet in the story language.
- Do not put someone in new_characters_detected if their display name, first name, surname, title, or alias matches an existing character.
"""


CONTEXT_STATS_KEY = "__context_stats"


def build_narrative_context(story, user_input, speaker_focus=None, appearance_reference=None):
    characters = story.get("characters") or []
    scenes = story.get("scenes") or []
    memory = story.get("memory_entries") or []
    lore_entries = story.get("lore_entries") or []
    current_scene = scenes[-1] if scenes else {}
    current_raw = current_scene.get("raw_ai_response") or {}
    current_location = current_raw.get("location") if isinstance(current_raw, dict) else ""
    current_background = current_scene.get("background_prompt") or ""
    selected_characters = select_relevant_characters(characters, current_scene, user_input, story.get("player_character") or {})

    character_visual_state, visual_stats = build_character_visual_state(story, selected_characters, current_scene)
    active_character_brief, active_character_stats = build_active_character_brief_with_stats(
        story,
        selected_characters,
        current_scene,
        speaker_focus,
        user_input,
    )
    context_stats = {**visual_stats, **active_character_stats}
    return {
        "participation_mode": build_participation_mode_context(story),
        "story_core": build_story_core(story, lore_entries),
        "current_story_memory": build_current_story_memory(story, memory),
        "story_progress": build_story_progress(story, scenes),
        "active_character_brief": active_character_brief,
        "character_visual_state": character_visual_state,
        "recent_scene_states": build_recent_scene_states(scenes[-5:]),
        "visual_state": build_visual_state(current_location, current_background),
        "saved_scenarios": build_saved_scenarios(story),
        "appearance_reference_request": build_appearance_reference_request(appearance_reference),
        "scene_cast_state": build_scene_cast_state(current_scene, memory),
        "speaker_focus": build_speaker_focus_context(story, current_scene, speaker_focus),
        "player_choice": user_input or "Start or continue the story naturally.",
        "directives": build_directives(user_input),
        "task": build_narrative_task(story, len(scenes)),
        "output_requirements": build_output_requirements(),
        CONTEXT_STATS_KEY: context_stats,
    }


def build_narrator_user_prompt(story, user_input, context=None):
    context = context or build_narrative_context(story, user_input)
    return f"""PARTICIPATION MODE:
{context["participation_mode"]}

STORY CORE:
{context["story_core"]}

CURRENT STORY MEMORY:
{context["current_story_memory"]}

STORY PROGRESS:
{context["story_progress"]}

ACTIVE CHARACTER BRIEF:
{context["active_character_brief"]}

CHARACTER VISUAL STATE:
{context["character_visual_state"]}

RECENT SCENE STATES:
{context["recent_scene_states"]}

VISUAL STATE:
{context["visual_state"]}

SAVED SCENARIOS:
{context["saved_scenarios"]}

VISUAL REFERENCE REQUEST:
{context["appearance_reference_request"]}

SCENE CAST STATE:
{context["scene_cast_state"]}

SELECTED ON-SCREEN CHARACTER:
{context["speaker_focus"]}

PLAYER CHOICE:
{context["player_choice"]}

DIRECT ORDERS:
{context["directives"]}

OUTPUT REQUIREMENTS:
{context["output_requirements"]}

TASK:
{context["task"]}"""


def build_story_bible(story, lore_entries):
    player = story.get("player_character") or {}
    participation_mode = normalize_participation_mode(story.get("participation_mode") or story.get("point_of_view"))
    lore_lines = []
    for entry in lore_entries[:6]:
        title = compact(entry.get("title"), 80) or "Lore"
        entry_type = compact(entry.get("entry_type"), 40) or "note"
        content = compact(entry.get("content"), 260)
        if content:
            lore_lines.append(f"- [{entry_type}] {title}: {content}")

    return "\n".join(
        [
            f"Title: {story.get('title')}",
            f"Genre: {story.get('genre')}",
            f"Tone: {story.get('tone')}",
            f"Visual style: {story.get('visual_style')}",
            f"Story language: {story.get('language') or 'pt-BR'}",
            f"Participation mode: {participation_mode_label(participation_mode)}",
            "",
            "Main lore:",
            compact(story.get("lore") or "Not defined.", 1200),
            "",
            "Relevant lorebook:",
            "\n".join(lore_lines) or "No additional lore entries.",
            "",
            "User/player character:" if participation_mode != "narrator" else "Narrative protagonist, if any:",
            "\n".join(
                [
                    f"Name: {player.get('name') or 'Jogador'}",
                    f"Role: {compact(player.get('role'), 100)}",
                    f"Personality: {compact(player.get('personality'), 220)}",
                    f"Goals: {compact(player.get('goals'), 220)}",
                    f"Background: {compact(player.get('background'), 220)}",
                ]
            ),
        ]
    )


def build_story_core(story, lore_entries):
    bible = build_story_bible(story, lore_entries)
    lore = compact(story.get("lore") or "Not defined.", 700)
    player = story.get("player_character") or {}
    lore_lines = []
    for entry in lore_entries[:4]:
        title = compact(entry.get("title"), 60) or "Lore"
        content = compact(entry.get("content"), 160)
        if content:
            lore_lines.append(f"- {title}: {content}")
    if len(bible) <= 1800:
        return bible
    return "\n".join(
        [
            f"Title: {story.get('title')}",
            f"Genre/tone: {story.get('genre')} / {story.get('tone')}",
            f"Story language: {story.get('language') or 'pt-BR'}",
            f"Participation mode: {participation_mode_label(normalize_participation_mode(story.get('participation_mode') or story.get('point_of_view')))}",
            f"Core lore: {lore}",
            "Relevant fixed lore:",
            "\n".join(lore_lines) or "- No additional lore entries.",
            f"Protagonist: {player.get('name') or 'Jogador'}; role: {compact(player.get('role'), 80)}; goals: {compact(player.get('goals'), 160)}",
        ]
    )


def normalize_participation_mode(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "first": "first_person",
        "first_person": "first_person",
        "primeira": "first_person",
        "primeira_pessoa": "first_person",
        "third": "third_person",
        "third_person": "third_person",
        "terceira": "third_person",
        "terceira_pessoa": "third_person",
        "narrator": "narrator",
        "narrador": "narrator",
    }
    return aliases.get(text, "first_person")


def participation_mode_label(mode):
    if mode == "third_person":
        return "third_person - user controls a visible protagonist"
    if mode == "narrator":
        return "narrator - user guides the whole story from outside the fiction"
    return "first_person - user is the invisible point-of-view protagonist"


def build_participation_mode_context(story):
    mode = normalize_participation_mode(story.get("participation_mode") or story.get("point_of_view"))
    player = story.get("player_character") or {}
    name = player.get("name") or "the protagonist"
    if mode == "third_person":
        return "\n".join(
            [
                "Mode: third_person.",
                f"The user controls only {name}, the visible protagonist.",
                "Narrate from outside the protagonist: show their actions, expressions, posture, and reactions as a character in the scene.",
                "The protagonist may appear in characters_on_screen when physically present and should have a sprite like other visible characters.",
                "Choices must be things the protagonist can do, say, hide, confront, or decide.",
                "Do not make large, irreversible, intimate, or identity-defining decisions for the protagonist without offering the user a choice first.",
            ]
        )
    if mode == "narrator":
        return "\n".join(
            [
                "Mode: narrator.",
                "The user is outside the fiction and has no avatar, no sprite, and no personal character in the scene.",
                "The user guides the broader story direction rather than controlling one person.",
                "You may shift focus between characters, show scenes where the protagonist is absent, reveal parallel events, and develop the world cinematically.",
                "Choices may direct events, focus, consequences, conflicts, and narrative pressure across the cast.",
            ]
        )
    return "\n".join(
        [
            "Mode: first_person.",
            f"The user is {name}, the point-of-view protagonist.",
            "Write as a direct, immersive experience through the protagonist's perceptions, sensations, thoughts, and immediate reactions.",
            "The protagonist must not appear in characters_on_screen, must not occupy a sprite slot, and should not need a generated sprite.",
            "Other characters appear normally with sprites when present.",
            "Choices must be actions, speech, reactions, or decisions the protagonist can personally take.",
            "Do not make large, irreversible, intimate, or identity-defining decisions for the protagonist without offering the user a choice first.",
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
            "Living summary:",
            compact(story.get("summary") or "The story is at the beginning.", 950),
            "",
            "Most important persistent memories:",
            "\n".join(memory_lines) or "No registered memory.",
        ]
    )


def build_story_progress(story, scenes):
    scene_count = len(scenes or [])
    next_scene = scene_count + 1
    if scene_count < 8:
        phase = "beginning: establish conflict, world rules, character desires, and first consequences"
    elif scene_count < 25:
        phase = "development: deepen relationships, complicate objectives, reveal partial clues, and create costs"
    elif scene_count < 60:
        phase = "long arc: alternate investigation, emotional pressure, consequences, and location changes without resolving everything too early"
    else:
        phase = "long campaign: preserve continuity, gradually pay off old promises, and open coherent new sub-arcs"

    previous_user_inputs = []
    previous_choices = []
    for scene in (scenes or [])[-8:]:
        user_input = compact(scene.get("user_input"), 160)
        if user_input:
            previous_user_inputs.append(f"- Scene {scene.get('scene_order')}: {user_input}")
        choices = scene.get("choices") or []
        if choices:
            previous_choices.append(f"- Scene {scene.get('scene_order')}: {choices}")

    return "\n".join(
        [
            f"Next scene to generate: {next_scene}",
            f"Total saved scenes: {scene_count}",
            f"Suggested narrative phase: {phase}",
            "",
            "Recent player actions:",
            "\n".join(previous_user_inputs) or "- No recent player action registered.",
            "",
            "Recent offered choices:",
            "\n".join(previous_choices[-4:]) or "- No recent choices registered.",
            "",
            "Anti-repetition contract:",
            "- The next scene must change the story state compared with RECENT SCENE STATES.",
            "- Do not rewrite the previous scene with different words.",
            "- If the player chose to continue, advance to the nearest logical consequence.",
        ]
    )


def build_active_characters(story, selected_characters):
    return build_active_character_brief(story, selected_characters, {}, None)


def build_active_character_brief(story, selected_characters, current_scene=None, speaker_focus=None, user_input=""):
    brief, _stats = build_active_character_brief_with_stats(
        story,
        selected_characters,
        current_scene,
        speaker_focus,
        user_input,
    )
    return brief


def build_active_character_brief_with_stats(story, selected_characters, current_scene=None, speaker_focus=None, user_input=""):
    current_scene = current_scene or {}
    selected_characters = selected_characters or []
    all_characters = []
    seen = set()
    for character in list(selected_characters) + list((story or {}).get("characters") or []):
        key = normalize_prompt_name((character or {}).get("name"))
        if not key or key in seen:
            continue
        seen.add(key)
        all_characters.append(character)

    focus_key = normalize_prompt_name((speaker_focus or {}).get("name") if isinstance(speaker_focus, dict) else speaker_focus)
    visible_names = [
        str(item.get("name") or "").strip()
        for item in (current_scene or {}).get("characters_on_screen") or []
        if isinstance(item, dict) and item.get("name")
    ]
    visible_keys = [normalize_prompt_name(name) for name in visible_names]
    visible_keys = [key for key in visible_keys if key]
    dialogue_keys = []
    dialogue_names = []
    for dialogue in current_scene.get("dialogues") or []:
        if not isinstance(dialogue, dict):
            continue
        dialogue_name = str(dialogue.get("character") or "").strip()
        name_key = normalize_prompt_name(dialogue_name)
        if name_key and name_key != normalize_prompt_name("Narrador") and name_key not in dialogue_keys:
            dialogue_keys.append(name_key)
            dialogue_names.append(dialogue_name)

    known_alias_keys = {
        normalize_prompt_name(alias)
        for character in all_characters
        for alias in character_alias_candidates(character)
        if normalize_prompt_name(alias)
    }
    for name in visible_names + dialogue_names:
        key = normalize_prompt_name(name)
        if key and key not in seen and key not in known_alias_keys:
            seen.add(key)
            all_characters.append(
                {
                    "name": name,
                    "role": "personagem presente na cena",
                    "personality": "usar o estado da cena e as falas recentes",
                    "speech_style": "consistente com a cena atual",
                }
            )

    user_text = normalize_prompt_name(user_input)
    player_key = normalize_prompt_name(((story or {}).get("player_character") or {}).get("name"))

    scored = []
    for index, character in enumerate(all_characters):
        name_key = normalize_prompt_name(character.get("name"))
        if not name_key:
            continue
        aliases = [normalize_prompt_name(alias) for alias in character_alias_candidates(character)]
        aliases = [alias for alias in aliases if alias]
        mentioned = any(alias and alias in user_text for alias in aliases) if user_text else False
        score = 0
        visible_matches = [visible_keys.index(alias) for alias in aliases if alias in visible_keys]
        dialogue_matches = [dialogue_keys.index(alias) for alias in aliases if alias in dialogue_keys]
        if visible_matches:
            score = max(score, 1000 - min(visible_matches))
        if dialogue_matches:
            score = max(score, 900 - min(dialogue_matches))
        if focus_key and focus_key in aliases:
            score = max(score, 850)
        if mentioned:
            score = max(score, 800)
        if player_key and name_key == player_key:
            score = max(score, 700)
        if not visible_keys and not dialogue_keys and not user_text and index < 6:
            score = max(score, 500 - index)
        if score:
            scored.append((score, index, character))

    scored.sort(key=lambda item: (-item[0], item[1]))
    included = [item[2] for item in scored]
    included_keys = {normalize_prompt_name(character.get("name")) for character in included}
    omitted = [
        character.get("name") or ""
        for character in all_characters
        if normalize_prompt_name(character.get("name")) not in included_keys
    ]
    was_compressed = False

    if not included:
        stats = {
            "active_character_brief_character_count": 0,
            "active_character_brief_included_characters": [],
            "active_character_brief_omitted_characters": [],
            "active_character_brief_used_saved_ai_summary": 0,
            "active_character_brief_generated_missing_summary": 0,
            "active_character_brief_was_compressed": False,
        }
        return "No known active characters.", stats

    lines = [render_active_character_brief_line(character, "normal") for character in included]
    text = "\n".join(lines)
    target_limit = 1800
    used_saved_ai_summary = sum(1 for character in included if clean_ai_summary_text(character.get("ai_prompt_brief")))
    generated_missing_summary = len(included) - used_saved_ai_summary
    if len(text) > target_limit:
        was_compressed = True
        lines = [render_active_character_brief_line(character, "short") for character in included]
        text = "\n".join(lines)
    if len(text) > target_limit:
        lines = [render_active_character_brief_line(character, "tiny") for character in included]
        text = "\n".join(lines)
    if len(text) > target_limit:
        line_limit = max(48, int((target_limit - max(0, len(lines) - 1)) / max(1, len(lines))))
        lines = [hard_compact_line(line, line_limit) for line in lines]
        text = "\n".join(lines)

    stats = {
        "active_character_brief_character_count": len(included),
        "active_character_brief_included_characters": [character.get("name") or "" for character in included],
        "active_character_brief_omitted_characters": [name for name in omitted if name],
        "active_character_brief_used_saved_ai_summary": used_saved_ai_summary,
        "active_character_brief_generated_missing_summary": generated_missing_summary,
        "active_character_brief_was_compressed": was_compressed,
    }
    return text or "No known active characters.", stats


def character_alias_candidates(character):
    character = character or {}
    name = str(character.get("name") or "").strip()
    aliases = str(character.get("aliases") or "").strip()
    parts = []
    if name:
        name_parts = name.split()
        parts.extend([name, name_parts[0], name_parts[-1]])
    if aliases:
        parts.extend([item.strip() for item in re.split(r"[,;/|]", aliases) if item.strip()])
    seen = set()
    unique = []
    for part in parts:
        key = normalize_prompt_name(part)
        if key and key not in seen:
            seen.add(key)
            unique.append(part)
    return unique


def render_active_character_brief_line(character, detail="normal"):
    saved = normalize_saved_ai_prompt_brief(character)
    if saved:
        return saved
    if detail == "tiny":
        role_limit, personality_limit, speech_limit, line_limit = 30, 38, 30, 170
    elif detail == "short":
        role_limit, personality_limit, speech_limit, line_limit = 46, 60, 46, 235
    else:
        role_limit, personality_limit, speech_limit, line_limit = 64, 82, 64, 320
    name = compact_name_without_ellipsis(character.get("name") or "Unnamed character", 46)
    role = compact_without_ellipsis(character.get("ai_role_summary") or character.get("role") or character.get("character_type") or character.get("description") or "personagem ativo na cena", role_limit)
    personality = compact_without_ellipsis(character.get("ai_personality_summary") or character.get("personality") or character.get("description") or "sem personalidade registrada", personality_limit)
    speech = compact_without_ellipsis(character.get("ai_voice_summary") or character.get("speech_style") or "sem padrao de fala registrado", speech_limit)
    line = f"{name} | Role: {role} Personality: {personality} Voice: {speech}"
    return hard_compact_line(line, line_limit)


def normalize_saved_ai_prompt_brief(character):
    character = character or {}
    brief = clean_ai_summary_text(character.get("ai_prompt_brief"))
    if not brief:
        return ""
    name = clean_ai_summary_text(character.get("name") or "")
    if " | Role: " in brief and " Personality: " in brief and " Voice: " in brief:
        return brief
    role = clean_ai_summary_text(character.get("ai_role_summary") or character.get("role") or "")
    personality = clean_ai_summary_text(character.get("ai_personality_summary") or character.get("personality") or "")
    voice = clean_ai_summary_text(character.get("ai_voice_summary") or character.get("speech_style") or "")
    if name and role and personality and voice:
        return f"{name} | Role: {ensure_period(role)} Personality: {ensure_period(personality)} Voice: {ensure_period(voice)}"
    return brief


def clean_ai_summary_text(value):
    text = str(value or "").replace("\r", " ").strip()
    text = " ".join(text.split())
    return text.replace("...", "").strip()


def compact_name_without_ellipsis(value, limit):
    text = clean_ai_summary_text(value)
    if len(text) <= limit:
        return text
    words = text.split()
    chosen = []
    current = 0
    for word in words:
        extra = len(word) + (1 if chosen else 0)
        if chosen and current + extra > limit:
            break
        if not chosen and extra > limit:
            chosen.append(word[:limit].rstrip(" ,.;:"))
            break
        chosen.append(word)
        current += extra
    return " ".join(chosen).strip()


def ensure_period(value):
    text = clean_ai_summary_text(value).rstrip(" ,;:")
    if not text:
        return ""
    return text if text[-1] in ".!?" else f"{text}."


def compact_without_ellipsis(value, limit):
    text = clean_ai_summary_text(value)
    if len(text) <= limit:
        return ensure_period(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected = []
    current = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        extra = len(sentence) + (1 if selected else 0)
        if selected and current + extra > limit:
            break
        if not selected and len(sentence) > limit:
            break
        selected.append(sentence)
        current += extra
    if selected:
        return ensure_period(" ".join(selected))
    words = text.split()
    chosen = []
    current = 0
    for word in words:
        extra = len(word) + (1 if chosen else 0)
        if chosen and current + extra > limit:
            break
        if not chosen and extra > limit:
            chosen.append(word[:limit].rstrip(" ,.;:"))
            break
        chosen.append(word)
        current += extra
    return ensure_period(" ".join(chosen))


def hard_compact_line(value, limit):
    text = str(value or "").replace("\r", " ").strip()
    text = " ".join(text.split())
    limit = int(limit or 0)
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[:limit].rstrip(" ,.;:")


def build_character_visual_state(story, selected_characters, current_scene):
    appearances = story.get("appearances") or []
    assets = story.get("assets") or []
    appearance_by_character = {}
    for appearance in appearances:
        appearance_by_character.setdefault(appearance.get("character_id"), []).append(appearance)
    assets_by_id = {asset.get("id"): asset for asset in assets}
    on_screen = {
        normalize_prompt_name(item.get("name")): item
        for item in (current_scene or {}).get("characters_on_screen") or []
        if isinstance(item, dict) and item.get("name")
    }
    lines = []
    stats = {"appearance_count_sent": 0, "omitted_appearances_count": 0}
    seen = set()
    for character in selected_characters[:10]:
        character_id = character.get("id")
        name = character.get("name") or ""
        key = normalize_prompt_name(name)
        if not character_id or not name or key in seen:
            continue
        seen.add(key)
        character_appearances = prioritized_character_appearances(character, appearance_by_character.get(character_id) or [], assets_by_id)
        active = active_character_appearance(character, character_appearances)
        visible = on_screen.get(key) or {}
        entry_lines = [
            f"{name}:",
            f"Active appearance: {(active or {}).get('id') or character.get('active_appearance_id') or 'none'}",
            "Available appearances:",
        ]
        if not character_appearances:
            entry_lines.append("* none registered")
            lines.append("\n".join(entry_lines))
            continue
        sent = 0
        for appearance in character_appearances[:4]:
            summary = summarize_appearance_for_prompt(character, appearance, assets_by_id)
            if not summary:
                continue
            entry_lines.append(f"* {appearance.get('id')}: {summary}")
            if appearance.get("id") == (active or {}).get("id"):
                entry_lines.append(f"  Current expression: {visible.get('expression') or 'neutral'}")
                entry_lines.append(f"  On screen: {visible.get('position') or 'off-screen'}")
            sent += 1
        omitted = max(0, len(character_appearances) - sent)
        if omitted:
            entry_lines.append(f"* {omitted} other appearance(s) omitted.")
        stats["appearance_count_sent"] += sent
        stats["omitted_appearances_count"] += omitted
        lines.append("\n".join(entry_lines))
    return "\n\n".join(lines) or "No character appearances are registered yet.", stats


def prioritized_character_appearances(character, appearances, assets_by_id):
    active_id = character.get("active_appearance_id") or ""
    def score(item):
        label = str(item.get("label") or "").lower()
        base_asset = assets_by_id.get(item.get("neutral_asset_id") or item.get("primary_asset_id") or "") or {}
        created = int(item.get("updated_at") or item.get("created_at") or base_asset.get("created_at") or 0)
        priority = 0
        if item.get("id") == active_id or item.get("is_active"):
            priority += 1000000000000
        if any(term in label for term in ("default", "inicial", "initial")):
            priority += 1000000000
        return priority + created
    return sorted(appearances or [], key=score, reverse=True)


def active_character_appearance(character, appearances):
    active_id = character.get("active_appearance_id") or ""
    for appearance in appearances or []:
        if appearance.get("id") == active_id or appearance.get("is_active"):
            return appearance
    return (appearances or [None])[0]


def summarize_appearance_for_prompt(character, appearance, assets_by_id):
    asset = assets_by_id.get(appearance.get("neutral_asset_id") or appearance.get("primary_asset_id") or "") or {}
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    generated_summary = appearance_summary_text(metadata.get("new_appearance_summary"))
    if generated_summary:
        return compact(generated_summary, 140)

    label = meaningful_appearance_label(appearance.get("label"))
    identity = character_identity_summary(character)
    clothing = appearance_summary_text(character.get("clothing"))
    if label:
        parts = [label]
        if identity and normalize_prompt_name(identity) not in normalize_prompt_name(label):
            parts.append(identity)
        return compact(", ".join(parts), 140)
    if clothing:
        parts = [f"usando {clothing}"]
        if identity:
            parts.append(identity)
        return compact(", ".join(parts), 140)

    technical_source = metadata.get("source_prompt") or asset.get("prompt") or character.get("visual_prompt") or character.get("physical") or ""
    return compact(clean_technical_appearance_summary(technical_source), 140)


def meaningful_appearance_label(value):
    text = appearance_summary_text(value)
    if not text:
        return ""
    normalized = normalize_prompt_name(text)
    generic = {
        "aparencia",
        "aparência",
        "appearance",
        "inicial",
        "initial",
        "default",
        "sprite",
        "neutral",
    }
    if normalized in generic or re.fullmatch(r"(aparencia|aparência|appearance)\s*\d*", normalized):
        return ""
    return compact(text, 80)


def appearance_summary_text(value):
    text = str(value or "").replace("\r", " ").strip()
    text = " ".join(text.split())
    text = re.sub(r"\b(full\s*body|front[- ]view|sprite|single character|single human|visual novel style|anime visual novel style|centered composition|clean character design|sharp lineart|polished cel shading)\b", "", text, flags=re.I)
    text = re.sub(r"\b(keep the same|do not change|change only)\b.*", "", text, flags=re.I)
    text = re.sub(r",?\s*\b(mantendo|while keeping|keeping)\b.*", "", text, flags=re.I)
    text = re.sub(r"\s+([,.;])", r"\1", text)
    text = re.sub(r"([,;]\s*){2,}", ", ", text)
    return text.strip(" ,.;")


def character_identity_summary(character):
    physical = appearance_summary_text((character or {}).get("physical"))
    if not physical:
        return ""
    hair = concise_hair_summary(physical)
    if hair:
        return hair
    sentences = re.split(r"(?<=[.!?])\s+", physical)
    useful = []
    for sentence in sentences:
        low = sentence.lower()
        if any(term in low for term in ("cabelo", "cabelos", "hair", "olhos", "eyes", "corpo", "porte", "body")):
            useful.append(sentence.strip(" ."))
        if len(" ".join(useful)) >= 70:
            break
    return compact(", ".join(useful) or physical, 80)


def concise_hair_summary(text):
    match = re.search(r"\b(cabelo|cabelos|hair)\b[^.]*", text, flags=re.I)
    if not match:
        return ""
    source = match.group(0).lower()
    parts = []
    if any(term in source for term in ("loiro", "loira", "blonde", "dourado", "golden")):
        parts.append("loiro")
    if any(term in source for term in ("ondul", "ondas", "wavy")):
        parts.append("ondulado")
    if any(term in source for term in ("curto", "short")):
        parts.append("curto")
    if any(term in source for term in ("longo", "long")):
        parts.append("longo")
    if any(term in source for term in ("preto", "black")):
        parts.append("preto")
    if any(term in source for term in ("castanho", "brown")):
        parts.append("castanho")
    if any(term in source for term in ("ruivo", "red hair", "redhead")):
        parts.append("ruivo")
    if not parts:
        return compact(match.group(0).strip(" ."), 60)
    return "cabelo " + " ".join(parts[:3])


def clean_technical_appearance_summary(value):
    text = appearance_summary_text(value)
    if not text:
        return ""
    clothing_match = re.search(r"\bwearing\s+([^.;]+)", text, flags=re.I)
    body_match = re.search(r"\b(without clothes|shirtless|only underwear|wearing only [^.;,]+|no clothes|nude|armou?r|uniform|disguise|towel|swimsuit)\b[^.;]*", text, flags=re.I)
    parts = []
    if clothing_match:
        parts.append(f"wearing {clothing_match.group(1).strip(' ,')}")
    if body_match:
        parts.append(body_match.group(0).strip(" ,"))
    if not parts:
        parts = [item.strip() for item in re.split(r"[,.;]", text) if item.strip()][:3]
    return ", ".join(parts)


def build_character_alias_line(character):
    name = str((character or {}).get("name") or "").strip()
    aliases = str((character or {}).get("aliases") or "").strip()
    parts = []
    if name:
        name_parts = name.split()
        parts.extend([name, name_parts[0], name_parts[-1]])
        if len(name_parts) >= 2:
            for title in ["Professor", "Professora", "Dr.", "Dra.", "Senhor", "Senhora", "Mr.", "Ms."]:
                parts.append(f"{title} {name_parts[0]}")
    if aliases:
        parts.extend([item.strip() for item in re.split(r"[,;/|]", aliases) if item.strip()])
    seen = set()
    unique = []
    for part in parts:
        key = part.lower()
        if part and key not in seen:
            seen.add(key)
            unique.append(part)
    return ", ".join(unique)


def build_recent_scenes(recent_scenes):
    return build_recent_scene_states(recent_scenes)


def build_recent_scene_states(recent_scenes):
    recent_lines = []
    for scene in recent_scenes:
        dialogues = scene.get("dialogues", [])
        compact_dialogues = []
        for dialogue in dialogues[-3:]:
            if isinstance(dialogue, dict):
                compact_dialogues.append(f"{dialogue.get('character', 'Narrador')}: {compact(dialogue.get('text'), 120)}")
        raw = scene.get("raw_ai_response") or {}
        location = raw.get("location") if isinstance(raw, dict) else ""
        memory = scene.get("memory_updates") or {}
        facts = memory.get("facts") if isinstance(memory, dict) else []
        cast = [
            item.get("name")
            for item in scene.get("characters_on_screen") or []
            if isinstance(item, dict) and item.get("name")
        ]
        recent_lines.append(
            f"Scene {scene.get('scene_order')} - {compact(scene.get('title'), 80)}\n"
            f"* Location: {compact(location or 'unknown', 90)}\n"
            f"* State change: {compact((memory or {}).get('summary') or scene.get('scene_text'), 220)}\n"
            f"* Characters: {', '.join(cast) or 'none visible'}\n"
            f"* Key dialogue: {' | '.join(compact_dialogues) or 'no key dialogue'}\n"
            f"* Choices offered: {compact('; '.join(str(choice) for choice in scene.get('choices', [])[:4]), 220)}\n"
            f"* New clue/fact: {compact('; '.join(str(fact) for fact in (facts or [])[:3]), 220)}"
        )
    return "\n\n".join(recent_lines) or "No generated scenes yet."


def build_visual_state(current_location, current_background):
    return "\n".join(
        [
            f"Current location: {current_location or 'unknown'}",
            f"Current background: {compact(current_background or 'no background defined', 260)}",
        ]
    )


def build_saved_scenarios(story):
    scenarios = (story or {}).get("scenarios") or []
    if not scenarios:
        return "No saved scenarios."
    lines = []
    for scenario in scenarios:
        name = compact(scenario.get("name") or "Unnamed scenario", 80)
        description = compact(scenario.get("description") or "", 140)
        active = " | ACTIVE" if scenario.get("is_active") else ""
        lines.append(f"- {name}{active}: {description or 'no short description'}")
    return "\n".join(lines)


def build_appearance_reference_request(reference):
    if not isinstance(reference, dict) or not reference.get("name"):
        return "No visual reference selected by the player."
    name = compact(reference.get("name"), 80)
    return (
        f'The player selected the saved visual reference "{name}" for the persistent appearance change in PLAYER_CHOICE. '
        f'For the create_new appearance_update that corresponds to that change, include "reference_name": "{name}" exactly. '
        'Set change_prompt exactly to "Replace the character\'s outfit with the outfit shown in image 2." Do not describe, infer, or summarize the referenced outfit. '
        "This request requires create_new; do not replace it with switch_existing or revert_existing. "
        "Do not mention the reference marker or its name in scene_text or dialogues. "
        "If more than one character receives a new appearance, attach reference_name only to the character whose change is described by PLAYER_CHOICE."
    )


def build_scene_cast_state(current_scene, memory):
    current_scene = current_scene or {}
    on_screen = []
    for item in current_scene.get("characters_on_screen") or []:
        if isinstance(item, dict) and item.get("name"):
            on_screen.append(
                f"- {item.get('name')} | position: {item.get('position') or 'center'} | expression: {item.get('expression') or 'neutral'}"
            )
    speakers = []
    seen = set()
    for dialogue in current_scene.get("dialogues") or []:
        if not isinstance(dialogue, dict):
            continue
        name = str(dialogue.get("character") or "").strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            speakers.append(name)
    manual_entries = []
    for entry in sorted(memory or [], key=lambda item: int(item.get("created_at") or 0), reverse=True):
        if (entry.get("entry_type") or "") == "scene-state":
            content = compact(entry.get("content"), 260)
            if content:
                manual_entries.append(f"- {content}")
        if len(manual_entries) >= 5:
            break

    return "\n".join(
        [
            "Current visual cast, authoritative for sprites:",
            "\n".join(on_screen) or "- No character is currently marked as visible.",
            "",
            "Characters who spoke in the current scene:",
            ", ".join(speakers) or "No character has spoken yet.",
            "",
            "Required continuity decision:",
            "- For each current visual cast member, decide their physical status in character_continuity before writing characters_on_screen.",
            "- Valid statuses: remains_present, accompanies, left_scene, not_present.",
            "- If the next scene remains in the same physical place, a silent character can remain visible with status remains_present.",
            "- If the next scene changes place, include a previous character only with status accompanies or if they are explicitly present in the new place.",
            "- If the player action means the protagonist leaves someone behind, mark that character left_scene or not_present.",
            "- If multiple characters travel together, mark all of them accompanies and include them in characters_on_screen.",
            "- If someone was manually added, find a natural way to acknowledge their presence in the next scene; this can be a brief arrival, a silent reaction, or simply visual presence.",
            "- If someone was manually removed, do not include them in characters_on_screen or dialogues in the next scene unless a direct order says otherwise.",
            "",
            "Recent manual scene-state changes:",
            "\n".join(manual_entries) or "- No recent manual scene-state changes.",
        ]
    )


def build_speaker_focus_context(story, current_scene, speaker_focus=None):
    focus_name = ""
    if isinstance(speaker_focus, dict):
        focus_name = str(speaker_focus.get("name") or speaker_focus.get("character") or "").strip()
    else:
        focus_name = str(speaker_focus or "").strip()
    if not focus_name:
        return "No on-screen character was selected by the user for the next interaction."

    visible = None
    focus_key = normalize_prompt_name(focus_name)
    for item in (current_scene or {}).get("characters_on_screen") or []:
        if isinstance(item, dict) and normalize_prompt_name(item.get("name")) == focus_key:
            visible = item
            break
    if not visible:
        return "No valid on-screen character was selected by the user for the next interaction."

    character_record = None
    visible_key = normalize_prompt_name(visible.get("name"))
    for character in (story or {}).get("characters") or []:
        if isinstance(character, dict) and normalize_prompt_name(character.get("name")) == visible_key:
            character_record = character
            break

    name = visible.get("name") or focus_name
    details = []
    if character_record:
        details = [
            f"Role: {compact(character_record.get('role'), 90)}",
            f"Personality: {compact(character_record.get('personality'), 180)}",
            f"Relationship: {compact(character_record.get('relationship'), 150)}",
            f"Speech style: {compact(character_record.get('speech_style'), 130)}",
            f"Current visible expression: {visible.get('expression') or 'neutral'}",
        ]
    else:
        details = [f"Current visible expression: {visible.get('expression') or 'neutral'}"]

    return "\n".join(
        [
            f"The user selected {name} on screen.",
            f"In the next scene, {name} must continue the interaction and should speak, react, or take initiative first.",
            f"The opening beat must center {name}: either the first sentence of scene_text shows {name}'s reaction/action, or the first non-narrator dialogue line belongs to {name}.",
            f"Keep {name} present and relevant at the beginning of the scene; do not switch the opening beat to another character.",
            f"Do not invent that {name} left the scene unless the story consequence is explicit and unavoidable.",
            f"Respect {name}'s personality, memory, emotional state, relationship, and current context.",
            *[line for line in details if line and not line.endswith(": ")],
        ]
    )


def normalize_prompt_name(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^\wÀ-ÿ\s'-]", " ", text)
    return " ".join(text.split())


def build_directives(user_input):
    directives = []
    for item in re.findall(r"\[\[(.*?)\]\]", str(user_input or ""), flags=re.S):
        text = compact(item, 260)
        if text:
            directives.append(f"- {text}")
    if not directives:
        return "No direct orders."
    return "\n".join(
        [
            "Explicit orders extracted from [[...]]:",
            *directives,
            "",
            "Follow these orders while continuing the narrative. Example: if an order says not to change scenario/location, keep location_changed false and preserve the current location even if the action contains internal movement.",
        ]
    )


def build_output_requirements():
    return "\n".join(
        [
            "Return only valid JSON.",
            "Required keys: title, scene_text, dialogues, choices, location, location_changed, background_prompt, character_continuity, characters_on_screen, new_characters_detected, memory_updates, appearance_updates.",
            "",
            "APPEARANCE UPDATE RULES:",
            "appearance_updates is mandatory.",
            "Before final JSON, inspect PLAYER_CHOICE, DIRECT ORDERS, scene_text, dialogues, and memory_updates.",
            "PLAYER_CHOICE has highest priority.",
            "If any source mentions persistent clothing change/removal, armor, disguise, transformation, major injury, or skin/hair/eye/body change for an existing character, appearance_updates must not be empty.",
            "Use create_new if the new visual state is not listed in CHARACTER VISUAL STATE.",
            "Use switch_existing/revert_existing only if an existing appearance already visually matches the new state.",
            "Never switch to the same active appearance unless that active appearance already describes the new state.",
            "Do not use appearance_updates for expressions, emotions, poses, gestures, lighting, speaking, walking, holding temporary objects, or temporary dirt/wetness.",
            "Any registered visual character who speaks in dialogues must also appear in characters_on_screen. If a character is absent or off-screen, they must not speak as a normal dialogue entry.",
            "If the scene or memory says the character is visually different from the active appearance, appearance_updates must describe that change.",
            "create_new requires: character, action, based_on_appearance_id, new_appearance_name, new_appearance_summary, change_prompt, reason, activate_after_generation.",
            "When VISUAL REFERENCE REQUEST names a saved reference, the corresponding create_new update also requires reference_name with that exact logical name.",
            'For that referenced update, change_prompt must be exactly "Replace the character\'s outfit with the outfit shown in image 2." Never describe the clothing from the story text.',
            "For create_new, new_appearance_summary describes the resulting appearance and reason explains the narrative decision; do not put those explanations in change_prompt.",
            "change_prompt is sent to ComfyUI. Write it in English as a short comma-separated list of direct, concrete visual changes only.",
            "change_prompt must not contain the character name or pronouns. Do not write a sentence about what happened to the character.",
            "Exclude unchanged identity traits, story context, causes, emotions, personality, mood, symbolism, justification, and instructions to preserve the rest of the image.",
            "Include only explicitly established persistent visual changes; do not invent extra marks, glow, damage, accessories, or other effects for dramatic flavor.",
            'Correct change_prompt for removing a character\'s clothes: "remove all clothes, shirtless, pantless, barefoot, wearing only underwear".',
            'Incorrect change_prompt: "Thorn is now stripped of his heavy armor by the divine presence, looking vulnerable yet resolute.".',
            "switch_existing/revert_existing require: character, action, target_appearance_id, reason, activate_after_generation.",
            "Valid actions: create_new, switch_existing, revert_existing.",
            'Example: if PLAYER_CHOICE says "remove Mike\'s hoodie" and no existing appearance matches that state, return create_new based on Michael\'s active appearance.',
        ]
    )


def build_narrative_task(story=None, scene_count=0):
    next_scene = int(scene_count or 0) + 1
    return (
        f"Generate scene {next_scene} as valid JSON. Continue from recent scene state, advance the plot, "
        "respect cast continuity, character voices, visual state, participation mode, output schema, and APPEARANCE UPDATE RULES."
    )


def select_relevant_characters(characters, current_scene, user_input, player):
    wanted = set()
    text = normalize_prompt_name(user_input)
    player_name = normalize_prompt_name(player.get("name"))
    if player_name:
        wanted.add(player_name)
    for item in current_scene.get("characters_on_screen") or []:
        if isinstance(item, dict) and item.get("name"):
            wanted.add(normalize_prompt_name(item.get("name")))
    for dialogue in current_scene.get("dialogues") or []:
        if isinstance(dialogue, dict) and dialogue.get("character"):
            wanted.add(normalize_prompt_name(dialogue.get("character")))
    selected = []
    for character in characters:
        aliases = [normalize_prompt_name(alias) for alias in character_alias_candidates(character)]
        aliases = [alias for alias in aliases if alias]
        if any(alias in wanted or (text and alias in text) for alias in aliases):
            selected.append(character)
    if not selected:
        selected = characters[:]
    extras = [character for character in characters if character not in selected]
    return (selected + extras)[: max(12, len(selected))]


def compact(value, limit):
    text = str(value or "").replace("\r", " ").strip()
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
