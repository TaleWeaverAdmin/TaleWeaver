# TaleWeaver MVP

## Goal

Build a local/self-hosted AI visual novel platform where the user can create, play, continue, and store interactive stories with dynamic AI-generated narration and visual asset prompts.

## Current MVP Features

- Dashboard listing saved stories.
- Story creation form:
  - title, genre, tone, visual style, content rating, language
  - lore/world description
  - player character
  - initial characters
- Visual novel play screen:
  - full-screen stage
  - dialogue box
  - generated choices
  - custom player action
  - history drawer
  - character drawer
  - lore/memory drawer
- SQLite persistence:
  - stories
  - scenes
  - characters
  - memory entries
  - lore entries
  - generated asset metadata
  - choices
- Ollama integration:
  - JSON-only narrator prompt
  - local model configurable in settings table
  - offline fallback scene if Ollama is unavailable
- ComfyUI integration:
  - queue basic background workflow
  - queue basic sprite workflow
  - save prompt metadata and ComfyUI prompt id
- New character detection flow:
  - AI can return `new_characters_detected`
  - UI shows add-character button
  - user can edit and save the suggested character

## Not Yet Implemented

- Delete/archive/duplicate stories.
- Manual edit scene/lore UI.
- Asset polling and automatic display of generated ComfyUI images.
- Character expression library.
- IPAdapter/ControlNet/LoRA workflows.
- SillyTavern import/export.
- Vector memory/RAG.
- Audio/TTS/music.
- Authentication or multi-user support.

## Architecture

Backend:

- Python standard library HTTP server.
- SQLite via `sqlite3`.
- Module boundaries:
  - `db.py`: persistence
  - `narrative.py`: story generation orchestration
  - `prompts.py`: prompt templates
  - `ollama_client.py`: Ollama API
  - `comfy_client.py`: ComfyUI API
  - `app_server.py`: HTTP routes and static serving

Frontend:

- Static HTML/CSS/JS.
- No build step.
- Designed to be replaceable by React/Vite later if needed.

## Next Practical Steps

1. Run the app and create a test story.
2. Generate first scene with Ollama online.
3. Improve JSON robustness based on actual model output.
4. Add story archive/delete/duplicate APIs.
5. Add settings screen for Ollama and ComfyUI URLs/model.
6. Add asset polling and save generated images into `data/stories/{story_id}`.
7. Add real sprite/background rendering once asset files are locally saved.
