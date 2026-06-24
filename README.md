# TaleWeaver

Become a Tale Weaver! TaleWeaver is a free AI-powered visual novel creator. Build interactive stories, characters, scenes, sprites, backgrounds, and branching narratives using local AI tools like Llama/Ollama and ComfyUI.

TaleWeaver is free for personal, educational, and non-commercial use. Commercial use, resale, or paid redistribution is not allowed without permission. See `LICENSE`.

TaleWeaver is a local/self-hosted AI visual novel studio inspired by endless visual novel systems: create a story, define lore and characters, play scenes, make choices, generate assets, and continue later.

This MVP uses only Python standard library on the backend:

- SQLite for persistence.
- Ollama for narrative generation.
- ComfyUI for background/sprite generation.
- Static frontend served by the backend.

## Start

```powershell
cd N:\VNApp
python app.py
```

Open:

```text
http://localhost:3000
```

Optional local services:

```powershell
ollama serve
```

```powershell
cd N:\SillyTavern\ComfyUI
py -3.11 main.py --enable-cors-header
```

## Project Layout

```text
backend/
  app_server.py       HTTP API and static file server
  comfy_client.py     ComfyUI integration
  db.py               SQLite schema and queries
  narrative.py        Story engine and prompt orchestration
  ollama_client.py    Ollama integration
  prompts.py          Prompt templates
data/
  app.sqlite          Created on first run
  stories/            Generated assets per story
public/
  index.html
  app.js
  styles.css
docs/
  MVP.md
SESSION_MEMORY.md
```

## MVP Scope

- Dashboard with saved stories.
- Create story with lore, player character, initial characters, and visual settings.
- Visual novel play screen.
- Ollama JSON narrative generation with offline fallback.
- SQLite persistence for stories, scenes, characters, memory, and generated assets.
- Simple new character detection flow.
- ComfyUI image generation endpoints with asset metadata saved.
- Manual continue/custom action and generated choices.
