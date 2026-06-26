# TaleWeaver

**Become a Tale Weaver. Create living visual novels powered by AI.**

TaleWeaver is a free, source-available, self-hosted AI visual novel studio for creating interactive stories, characters, scenes, sprites, backgrounds, expressions, branching choices, and persistent worlds.

It is designed to be **fully customizable**. You can connect your own narrative AI, build your own ComfyUI workflows, create your own visual styles, and let each story use a completely different artistic setup.

> TaleWeaver is free for personal, educational, and non-commercial use.
> Commercial use, resale, paid redistribution, or offering TaleWeaver as part of a paid service is not allowed without permission. See `LICENSE`.

---

## What is TaleWeaver?

TaleWeaver is a local/self-hosted AI visual novel creator inspired by endless visual novel systems.

You create a story, define its lore, characters, world, visual style, and AI settings, then play through scenes where the narrative continues dynamically. Characters can speak, react, appear on screen, change expressions, change outfits, move between locations, and evolve with the story.

The goal is to make an AI-powered storytelling tool where the user is not locked into one model, one workflow, or one art style.

---

## Highlights

* Create and continue interactive visual novel stories.
* Save multiple stories and return to them later.
* Define lore, tone, world rules, protagonist, characters, and memory.
* Use local Llama/Ollama models or OpenAI-compatible APIs for narrative generation.
* Use ComfyUI for sprites, backgrounds, expressions, appearances, outfits, and visual changes.
* Create multiple visual styles and assign a different style to each story.
* Build your own ComfyUI workflows and plug them into TaleWeaver styles.
* Generate character sprites and backgrounds automatically.
* Generate expressions for each sprite.
* Detect when a character changes appearance and automatically request a new appearance through ComfyUI.
* Detect when the story moves to a new location and automatically generate or switch the scenario.
* Upload clothes, accessories, objects, or visual references to guide new character appearances.
* Manage character appearances, expressions, scenarios, references, and story state.
* Continue the story using custom actions or generated choices.
* Click characters on screen to make them speak or react next.
* Keep story memory, character continuity, and visual state across sessions.

---

## Fully Customizable Visual Styles

TaleWeaver is built around the idea of **styles**.

A style can define how the app creates:

* character sprites
* backgrounds/scenarios
* character expressions
* appearance changes
* appearance changes with references
* prompt enhancement commands
* ComfyUI workflow mappings

This means every story can have its own look.

One story can use a dark fantasy anime style.
Another can use sci-fi pixel art.
Another can use painterly backgrounds and semi-realistic sprites.

You are not limited to the workflows that come with the app. If you can build a workflow in ComfyUI, you can adapt TaleWeaver to use it.

---

## AI Compatibility

TaleWeaver supports different AI setups.

For narrative generation, it can work with:

* local Llama/Ollama models
* llama.cpp servers
* OpenAI
* OpenAI-compatible APIs
* other providers that follow the OpenAI chat/completions structure

For image generation, it integrates with:

* ComfyUI (local and could)
* custom ComfyUI workflows
* workflows for sprites, scenarios, expressions, outfits, references, and image editing

The project is meant to be flexible, experimental, and model-agnostic.

---

## Dynamic Story and Visual Awareness

TaleWeaver does more than just generate text.

It tries to keep the story and visuals connected.

Examples:

* If the AI detects that a character changed clothes, armor, hairstyle, body state, or important visual traits, TaleWeaver can trigger a new appearance generation.
* If the story moves to a new location, TaleWeaver can create or switch to the correct background.
* If a character speaks with a different emotion, the app can use the matching sprite expression.
* If a user uploads a reference outfit or accessory, that reference can be used to create a new appearance.
* If characters remain in the scene, TaleWeaver tries to preserve their visual continuity.

The goal is to make the visual novel feel alive, persistent, and reactive.

---

## Current Features

* Story dashboard with saved stories.
* Story creation with lore, genre, tone, protagonist, characters, and visual settings.
* Visual novel play screen.
* Persistent story memory.
* Character creation and management.
* Character sprites and expressions.
* Multiple appearances per character.
* Scenario/background management.
* Saved visual references per story.
* Custom visual styles.
* ComfyUI workflow integration.
* OpenAI-compatible narrative API support.
* Llama/Ollama local model support.
* SQLite persistence.
* Generated choices and manual custom actions.
* Character click-to-speak interaction.
* Automatic background and appearance generation triggers.
* Local/self-hosted backend and static frontend.

---

## Planned Future Additions

TaleWeaver is still evolving, and there are many ideas planned for future versions.

Some possible future additions include:

* **Tale Weavers**: customizable narrator profiles that guide the story in different ways, with their own tone, pacing, style, personality, and narrative behavior.
* More advanced story memory and long-term continuity.
* Better character relationship tracking.
* Improved automatic detection of visual changes.
* More flexible ComfyUI workflow support.
* Better UI customization.
* UI polish and visual refinements.
* Bug fixes and stability improvements.
* Better onboarding and setup instructions.
* More tools for managing characters, scenarios, references, appearances, and expressions.
* More ways to customize how each story feels and plays.
* Community suggestions and experimental features.

The possibilities are endless.
The sky is the limit.

---

## Start

From the project folder:

```bash
cd 'projectFolder'
python app.py
```

Open:

```text
http://localhost:3000
```
---

## Project Layout

```text
backend/
  app_server.py       HTTP API and static file server
  comfy_client.py     ComfyUI integration
  db.py               SQLite schema and queries
  narrative.py        Story engine, validation, repairs, and orchestration
  ai_client.py        OpenAI-compatible API integration
  ollama_client.py    Ollama/local model integration
  prompts.py          Prompt and context assembly

data/
  app.sqlite          Created on first run
  stories/            Generated assets per story

public/
  index.html
  app.js
  styles.css
  assets/

docs/
  MVP.md
```

---

## Philosophy

TaleWeaver is free because it was built with a lot of help from AI tools, experimentation, community knowledge, and open local AI ecosystems.

The goal is not to lock people into a paid product.
The goal is to create a flexible playground for AI-powered storytelling.

You are encouraged to:

* use it
* study it
* modify it
* suggest improvements
* build your own workflows
* create your own styles
* contribute ideas
* share what you make

Just do not resell it, repackage it as a paid product, or offer it as a paid service without permission.

---

## License

TaleWeaver is free for personal, educational, and non-commercial use.

Commercial use, resale, paid redistribution, or offering TaleWeaver as part of a paid service is not allowed without prior permission.

See `LICENSE` for details.
