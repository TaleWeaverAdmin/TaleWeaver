# TaleWeaver - Session Memory

Last updated: 2026-06-02

## Resume Instruction

In a new Codex session, ask:

> Leia `N:\VNApp\SESSION_MEMORY.md` para entender sobre o que o projeto se trata e o que fizemos.

## User Goal

The user wants a local/self-hosted AI visual novel web platform inspired by DreamRunner.ai.

Core idea:

- Endless/dynamic visual novel generated as the player plays.
- User can create, play, continue, and store stories.
- Local IA whenever possible:
  - Ollama for text/narrative.
  - ComfyUI for backgrounds, sprites, and visual variations.
  - SillyTavern may be referenced later for character cards/prompts, but the app must work independently.

## Project Name

Application name:

- `TaleWeaver`

Previous temporary name:

- `LocalDreamVN`

## Workspace

Project root:

- `N:\VNApp`

The previous project was deleted and this one was started from an empty directory.

## Current Implementation

Implemented a first MVP base with no external package dependencies.

Backend:

- Python standard library.
- SQLite via built-in `sqlite3`.
- Static frontend served by the backend.

Frontend:

- Static `index.html`, `styles.css`, `app.js`.
- No React/Vite yet. This was a deliberate MVP choice to avoid dependency/network friction and get a local functional base quickly.
- Can be migrated to React/Vite later.

## Important Files

- `N:\VNApp\app.py`
- `N:\VNApp\README.md`
- `N:\VNApp\SESSION_MEMORY.md`
- `N:\VNApp\docs\MVP.md`
- `N:\VNApp\backend\app_server.py`
- `N:\VNApp\backend\db.py`
- `N:\VNApp\backend\narrative.py`
- `N:\VNApp\backend\prompts.py`
- `N:\VNApp\backend\ollama_client.py`
- `N:\VNApp\backend\comfy_client.py`
- `N:\VNApp\backend\config.py`
- `N:\VNApp\public\index.html`
- `N:\VNApp\public\app.js`
- `N:\VNApp\public\styles.css`
- `N:\VNApp\public\assets\placeholder-bg.svg`

## How To Run

From `N:\VNApp`:

```powershell
python app.py
```

Open:

```text
http://localhost:3000
```

ComfyUI, if needed:

```powershell
cd N:\SillyTavern\ComfyUI
py -3.11 main.py --enable-cors-header
```

Ollama should be available at:

```text
http://127.0.0.1:11434
```

ComfyUI should be available at:

```text
http://127.0.0.1:8188
```

## Data

SQLite database is created on first run:

- `N:\VNApp\data\app.sqlite`

Generated story asset folders are under:

- `N:\VNApp\data\stories`

Current tables:

- `settings`
- `stories`
- `characters`
- `scenes`
- `memory_entries`
- `lore_entries`
- `generated_assets`
- `choices`

## Implemented User Flow

1. Dashboard lists stories.
2. User creates a new story with:
   - basic metadata
   - lore/world
   - player character
   - initial characters
3. App opens visual novel screen.
4. User can generate/continue a scene.
5. Backend calls Ollama for structured JSON.
6. If Ollama fails, backend creates an offline fallback scene so UI can still be tested.
7. Scene is saved in SQLite.
8. UI displays latest dialogue, choices, characters on screen, history, characters, and memory.
9. If AI returns `new_characters_detected`, UI shows an add-character button.
10. User can review/edit/save suggested character.
11. User can queue basic background/sprite generation with ComfyUI.

## Narrative JSON Contract

Ollama is instructed to return JSON only:

```json
{
  "title": "titulo curto da cena",
  "scene_text": "narracao",
  "dialogues": [
    {
      "character": "Luna",
      "expression": "sad",
      "text": "Eu sabia que esse dia chegaria..."
    }
  ],
  "choices": [
    "Perguntar o que ela esta escondendo",
    "Conforta-la",
    "Sair em silencio"
  ],
  "background_prompt": "old library at night, rain outside, candle light, anime visual novel background, no people",
  "characters_on_screen": [
    {
      "name": "Luna",
      "position": "center",
      "expression": "sad"
    }
  ],
  "new_characters_detected": [],
  "memory_updates": {
    "summary": "Resumo atualizado",
    "facts": [
      "Fato importante"
    ]
  }
}
```

## Current Limitations

- Dashboard buttons for duplicate/archive are placeholders.
- No delete story yet.
- Settings UI exists for Ollama URL/model and ComfyUI URL/root/checkpoint/resolution.
- ComfyUI image generation now queues prompts, polls by asset id, downloads ready images, saves them into story folders, and serves them through `/api/assets/{asset_id}/file`.
- Visual novel screen now renders saved background/sprite images when available, falling back to placeholders if no asset exists.
- No IPAdapter workflow yet in this new project.
- No SillyTavern import/export yet.
- Manual editing of scenes/lore is not implemented.
- No vector database/RAG yet.

## Next Recommended Steps

1. Run syntax checks and start server.
2. Open `http://localhost:3000`.
3. Create a test story.
4. Generate a scene with Ollama online.
5. Fix any JSON edge cases from the selected Ollama model.
6. Improve image quality/workflows for background and sprites.
7. Add automatic background/sprite generation after each scene if desired.
8. Add delete/archive/duplicate story functionality.
9. Add manual scene/memory editor.

## ComfyUI Configuration Confirmed

ComfyUI path:

- `N:\SillyTavern\ComfyUI`

ComfyUI URL:

- `http://127.0.0.1:8188`

Status endpoint returned HTTP 200 and system stats.

Detected version:

- ComfyUI `0.22.0`
- Python `3.11.9`
- PyTorch `2.6.0+cu124`
- GPU: `NVIDIA GeForce RTX 3080`

Detected checkpoints:

- `illustriousXL_v01.safetensors`
- `juggernautXL_ragnarokBy.safetensors`
- `ponyDiffusionV6XL_v6StartWithThisOne.safetensors`
- `realisticVisionV51_v51VAE.safetensors`

Default app setting:

- `comfy_checkpoint = illustriousXL_v01.safetensors`
- `comfy_root = N:\SillyTavern\ComfyUI`

Confirmed IPAdapter custom nodes:

- `IPAdapterUnifiedLoader`
- `IPAdapter`

The backend now exposes:

- `GET /api/comfy/status`
- `GET /api/comfy/checkpoints`
- `GET /api/comfy/object-info/{node_name}`

The frontend now has a `Config` screen for Ollama and ComfyUI settings.

## Asset Display Fix

The app originally queued ComfyUI prompts but did not fetch or display the generated files.

Implemented:

- `GET /api/assets/{asset_id}/result`
  - Checks ComfyUI history using the saved `prompt_id`.
  - Downloads the first output image when ready.
  - Saves it under `data/stories/{story_id}/backgrounds` or `data/stories/{story_id}/characters/{character_id}`.
  - Updates `generated_assets.file_path`.
  - For backgrounds, updates `scenes.background_asset_id`.

- `GET /api/assets/{asset_id}/file`
  - Serves the saved local image file.

Frontend changes:

- After `generateBackground()` or `generateSprite()`, the UI waits for the asset result.
- Once ready, it reloads the story and renders the image.
- `renderPlay()` applies background asset URLs to `.stage`.
- `renderSprites()` renders `<img class="scene-sprite">` when a sprite asset exists for the character.
- Character drawer now shows generated sprite thumbnails for each character via `renderCharacterSpriteGallery()`.

Already resolved old queued assets for test story `story_595a74bc382b`:

- Background: `asset_8e0b167a563f`
- Sprites: `asset_584b8cf972f9`, `asset_762e712050e2`

## AI Improve Button

Added an AI text improvement feature for story/character setup.

Backend:

- `POST /api/ai/improve`
- Implemented in `backend/narrative.py` as `improve_text(payload)`.
- Uses Ollama with a JSON-only response:
  - `{ "improved_text": "..." }`
- Preserves user intent while expanding detail for lore, characters, relationships, and visual prompts.
- If Ollama is unavailable, returns a fallback expansion note instead of breaking the UI.

Frontend:

- Added `🪄 Melhorar` buttons to long-form creation fields:
  - lore/world description
  - player appearance/personality/background/goals
  - initial character physical/personality/relationship/visual prompt
  - detected/manual character modal fields
- The button updates only the target field and does not rerender the whole form, so typed content is preserved.
- Dynamically added initial-character forms attach the improve button handler after insertion.

## Automatic Backgrounds And API Logs

Added automatic background handling after each generated scene.

Backend behavior:

- After `POST /api/stories/{story_id}/generate-scene`, the server checks the latest scene's `background_prompt`.
- If the scene already has a background asset, it keeps it.
- If a similar saved background exists, it reuses that asset and updates `scenes.background_asset_id`.
- If no reusable background exists, it queues a new ComfyUI background generation automatically.
- The response includes `auto_background`:
  - `{ "mode": "reused", "asset_id": "..." }`
  - `{ "mode": "queued", "asset_id": "...", "prompt_id": "..." }`
  - `{ "mode": "existing", "asset_id": "..." }`
  - `{ "mode": "error", "error": "..." }`

Frontend behavior:

- The manual `Gerar background` button was removed from the play toolbar.
- After scene generation, if `auto_background.mode === "queued"`, the frontend waits for the asset, downloads it through the backend, then reloads the story.
- Reused backgrounds appear immediately after story reload.

Background reuse:

- Implemented with simple prompt token similarity in `backend/app_server.py`.
- Similarity threshold currently `0.62`.
- This is a pragmatic MVP solution; later it should become location IDs or embeddings.

API logs:

- Added SQLite table `api_logs`.
- Added `GET /api/logs?story_id={id}&limit=120`.
- Added top-nav `Logs` screen.
- Logs show provider, operation, status, timestamp, request JSON, response JSON, and errors.
- Currently logs:
  - Ollama narrator calls.
  - Ollama improve calls.
  - ComfyUI image prompt calls.
  - ComfyUI auto-background prompt calls.
  - ComfyUI image download/history resolution.
  - Local background reuse decisions.

## Ollama Model Dropdown

Settings screen now loads available Ollama models from:

- `GET /api/ollama/models`

The `ollama_model` setting is rendered as a dropdown instead of a free text field.

Detected models during implementation:

- `mistral-nemo:latest`
- `qwen2.5:7b`

If Ollama is offline, the dropdown falls back to the currently saved model value.

## Refresh Sprite

Character drawer now has an `Atualizar sprite` button per character.

Behavior:

- Finds the latest saved sprite asset for that character.
- Asks for confirmation.
- Calls `DELETE /api/assets/{asset_id}`.
- Backend tries to delete the local file under `data/` and removes the `generated_assets` row.
- Backend logs the deletion as `local / asset:delete`.
- Frontend reloads the story and immediately calls the existing sprite generation flow.

If the character has no sprite yet, `Atualizar sprite` simply generates one.

Important permission note:

- The Python server launched from Codex may fail to delete PNG files with `WinError 5`.
- The endpoint now still removes the asset from SQLite and returns `delete_error` instead of failing.
- This lets `Atualizar sprite` continue and generate a new sprite.
- Old image files may remain orphaned on disk until cleaned by a process with sufficient filesystem permissions.

## ComfyUI Image Quality Pass

Initial image quality was poor mainly because the MVP workflow was too basic:

- Fixed seed `0`.
- Only 18 steps.
- Weak negative prompt.
- Portuguese character descriptions were sent directly to ComfyUI.
- No configurable sampler/CFG/steps.

Updated:

- `backend/comfy_client.py`
  - Uses random seed per generation.
  - Uses stronger positive prompt wrappers for background/sprite.
  - Uses stronger negative prompt.
  - Supports configurable `steps`, `cfg`, `sampler_name`, `scheduler`.

- `backend/config.py`
  - Added defaults:
    - `background_steps = 28`
    - `background_cfg = 6.5`
    - `sprite_steps = 32`
    - `sprite_cfg = 6.0`
    - `comfy_sampler = dpmpp_2m_sde_gpu`
    - `comfy_scheduler = karras`

- `backend/app_server.py`
  - Passes those settings to ComfyUI.
  - Runs prompts through `narrative.improve_visual_prompt()` before sending to ComfyUI.

- `backend/narrative.py`
  - Added `improve_visual_prompt()`, which asks Ollama to convert descriptions into concise English SDXL visual prompts.

- `public/app.js`
  - Config screen now exposes background/sprite steps, CFG, sampler, and scheduler.

Existing SQLite settings were updated with the new defaults.

Validation:

- Python imports OK.
- JS syntax OK.
- Server restarted.
- Test ComfyUI prompt accepted:
  - `prompt_id = e77dd70c-6bd3-4043-bdc6-d02b370e7992`
  - `node_errors = {}`

Current installed custom nodes are still minimal:

- `ComfyUI_IPAdapter_plus`

No LoRAs or VAE files are installed yet. Consider plugins/model downloads later after evaluating improved baseline generations.

## Animagine XL 3.1 Installed

The existing `illustriousXL_v01.safetensors` produced very poor/abstract sprites even with simplified prompts.

Downloaded a better anime SDXL checkpoint from the official Hugging Face repo:

- Source: `https://huggingface.co/cagliostrolab/animagine-xl-3.1`
- File: `animagine-xl-3.1.safetensors`
- Installed at: `N:\SillyTavern\ComfyUI\models\checkpoints\animagine-xl-3.1.safetensors`
- Size: `6938325776` bytes

ComfyUI detected it immediately through `CheckpointLoaderSimple`.

Updated app settings:

- `comfy_checkpoint = animagine-xl-3.1.safetensors`
- `sprite_cfg = 5.5`
- `background_cfg = 6.0`

Updated code:

- `backend/config.py` default checkpoint is now Animagine.
- `public/app.js` waits up to 180 polling attempts for asset completion because first checkpoint load can be slow.
- `backend/narrative.py` now sanitizes visual prompts:
  - Converts bad `1old man` style tags.
  - Removes scenery/background tags from sprite prompts.
  - Forces gender tags from Portuguese cues like `senhor`, `mulher`, etc.
  - Adds plain sprite constraints.
- `backend/comfy_client.py` has stronger sprite negatives:
  - duplicate people, 2boys/2girls, split screen, frame/border, comic panel, etc.

Test result:

- `data/test_sprite_animagine.png`
- This was significantly better than the previous abstract sprite outputs and is the current quality baseline.

## Dashboard Story Management

Implemented real dashboard actions for saved stories.

Backend:

- `POST /api/stories/{story_id}/duplicate`
  - Duplicates story metadata, characters, scenes, memory entries, lore entries, choices, and generated asset records.
  - Copies local generated asset files into the new `data/stories/{new_story_id}` folder when source files exist and can be read.
  - Duplicates are created as active stories with title prefix `Copia de`.
  - Logs `local / story:duplicate`.

- `PATCH /api/stories/{story_id}`
  - Supports updating story fields, currently used by the UI for `status`.
  - Dashboard uses this for archive/restore.

- `DELETE /api/stories/{story_id}`
  - Deletes the story row and cascaded SQLite records.
  - Attempts to remove `data/stories/{story_id}`.
  - If Windows/Python filesystem permissions block folder deletion, the endpoint still deletes the DB records and returns `delete_error`.
  - Logs `local / story:delete`.

Frontend:

- Dashboard `Duplicar` now calls the duplicate endpoint and refreshes the list.
- Dashboard `Arquivar` toggles archived status.
- Archived stories show `Restaurar`.
- Dashboard `Excluir` asks for confirmation before deleting.
- If local folder removal fails, the UI alerts the user while keeping the story removed from SQLite.

Validation:

- Python syntax checked with an AST parse over `app.py` and `backend/*.py`.
- `node --check public/app.js` passed.
- HTTP smoke test passed for create, duplicate, archive, and delete using `AppHandler` on a temporary local port.
- Smoke-test stories and temporary cache folders were cleaned up.

Environment note:

- `python -m py_compile` can hit `WinError 5` when trying to write/rename `.pyc` files in this workspace. Use `python -B` plus AST parsing for syntax checks unless the cache permission issue is fixed.

## Story Folder Delete Fix

A delete attempt removed a story from SQLite but left its local folder because Python raised:

- `[WinError 5] Acesso negado`
- Example blocked file: `N:\VNApp\data\stories\story_595a74bc382b\backgrounds\asset_8e0b167a563f.png`

Fixes:

- `backend/app_server.py`
  - Replaced simple `shutil.rmtree()` with `delete_path_with_retries()`.
  - The delete helper retries, runs garbage collection between attempts, applies writable permissions with `os.chmod`, and verifies the path is actually gone before returning success.
  - On Windows, it falls back to a constrained PowerShell `Remove-Item -LiteralPath ... -Recurse -Force` call without `shell=True`.
  - Asset deletion now uses the same retry helper for individual files.
  - `DELETE /api/stories/{story_id}` now also attempts to clean orphan folders when the story row is already missing from SQLite but `data/stories/{story_id}` still exists.

Operational notes:

- There were two Python servers listening on port `3000` (`12376` old code and `10656` newer code). Both were stopped.
- A single updated server was started outside the Codex sandbox:
  - PID: `10108`
  - URL: `http://127.0.0.1:3000`
- The orphan folder `story_595a74bc382b` was removed.
- HTTP smoke test passed: create a temporary story, add a file under its story folder, call `DELETE /api/stories/{id}`, and confirm the folder is gone.

## Local-Only DreamRunner-Inspired UX Pass

User clarified the app is only for local web use and should ignore all DreamRunner community/login/credits/ranking/monetization concepts.

Reference files:

- `N:\VNApp\dreamRunner Examples`
- The folder organization is usable as-is: each saved HTML has its matching `_files` folder.
- Treat these files as UX references only. Do not copy DreamRunner branding, proprietary text, production code, or hosted/community features.

Implemented local equivalents:

Backend:

- `POST /api/ai/story-seed`
  - Uses Ollama to turn a short story idea into editable creation fields.
  - Returns title, genre, tone, visual style, lore, starting location/message, player character, and initial characters.
  - Has an offline fallback if Ollama is unavailable.
  - Logs `ollama / chat:story-seed`.

- `POST /api/stories/{story_id}/memory`
  - Adds a local memory entry from the play screen.
  - Used by the `Register` action.

- `PATCH /api/scenes/{scene_id}`
  - Edits saved scene title, narration, background prompt, and choices.
  - Used by the `Edit` action in play mode.

Frontend:

- Dashboard now focuses on local stories only:
  - no community/login/credits concepts,
  - quick story prompt,
  - `Gerar história` sends the prompt to `/api/ai/story-seed`,
  - story cards now have a visual cover area.

- Creation flow is now a 3-step wizard:
  - `Detalhes`,
  - `Personagens`,
  - `Visual`.
  - Supports point of view selection, AI-generated editable seed, player character, initial characters, and visual style presets.

- Play toolbar now has local equivalents inspired by the reference:
  - `Menu` opens lore/memory drawer,
  - `Edit` toggles scene editing,
  - `Register` opens memory registration modal,
  - `Histórico`,
  - `Personagens`,
  - `Depict` generates missing current-scene visuals,
  - `Redo` regenerates,
  - `Continue` advances.

- Custom action input now has a `5000` character limit and counter.

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check over `app.py` and `backend/*.py` passed.
- `/api/ai/story-seed` returned a valid Ollama-generated seed in testing.
- HTTP smoke test passed for story creation, memory registration, scene editing, and story deletion.
- Edge headless screenshot rendered the updated dashboard correctly after using an isolated user-data-dir.
- Server restarted with updated code:
  - PID: `18188`
  - URL: `http://127.0.0.1:3000`

## Sprite Display Fix

Issue:

- The play screen showed only a translucent placeholder square.
- Current story state:
  - story: `story_74e634c90670`
  - current scene had `characters_on_screen = Lúcia / neutral`
  - saved sprite asset existed only for `João`
- Therefore `renderSprites()` could not find a matching sprite for the character actually on screen and rendered the fallback stand-in.

Fixes:

- Generated the missing Lúcia sprite:
  - asset: `asset_78fcaa7224fc`
  - file: `data/stories/story_74e634c90670/characters/char_1810fec9fbd0/neutral_asset_78fcaa7224fc.png`
  - served at `/api/assets/asset_78fcaa7224fc/file`

- `public/app.js`
  - After `generateScene()`, the frontend now calls `ensureSceneSprites()` to generate missing sprites for registered characters in `characters_on_screen`.
  - `Depict` now reuses the same sprite generation helper.
  - Added `findStoryCharacter()` helper.
  - Fallback stand-in now explicitly says `sprite pendente` instead of looking like an unexplained transparent rectangle.

- `backend/app_server.py`
  - Added optional sprite post-processing using Pillow.
  - New sprites have uniform edge-connected backgrounds removed and are saved as PNG with alpha.
  - Existing Lúcia sprite was post-processed; about 77% of pixels are transparent.

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check passed.
- Asset endpoint returned `200 image/png`.
- Server restarted:
  - PID: `19204`
  - URL: `http://127.0.0.1:3000`

## Sprite Generation Speed And Prompt Pass

User reported character sprite generation quality was still poor and slow.

Findings:

- The app was still calling Ollama to convert character descriptions into visual prompts before every sprite generation.
- For sprites, this added latency and could produce inconsistent tags.
- `backend/comfy_client.py::infer_gender_tags()` had a bug: seeing `1boy` or generic male terms could inject `old man`, which could make young male characters look old.
- The workflow used `768x1152`, `32` steps, `dpmpp_2m_sde_gpu/karras`, which is heavier than needed for MVP sprites.

Code changes:

- `backend/narrative.py`
  - Added `build_sprite_visual_prompt(character, expression, user_prompt)`.
  - Builds deterministic English sprite tags locally from character fields.
  - Avoids sending raw Portuguese character prose directly to ComfyUI.
  - Extracts gender, age, hair, eyes, body, outfit, and expression tags.

- `backend/app_server.py`
  - Sprite generation now uses `narrative.build_sprite_visual_prompt()` instead of `improve_visual_prompt()` / Ollama.
  - Sprite generation supports separate `sprite_sampler` and `sprite_scheduler` settings.

- `backend/comfy_client.py`
  - Animagine quality prefix changed to `masterpiece, best quality, very aesthetic, absurdres`.
  - Fixed gender inference so `1boy` no longer implies `old man`.
  - Sprite positive prompt now keeps the deterministic sprite tags more central.
  - Sprite negative prompt no longer bans all gray backgrounds because post-processing removes simple uniform backgrounds.

- `backend/config.py`
  - New defaults:
    - `sprite_width = 640`
    - `sprite_height = 960`
    - `sprite_steps = 24`
    - `sprite_cfg = 5.0`
    - `sprite_sampler = euler_ancestral`
    - `sprite_scheduler = normal`

- `public/app.js`
  - Config screen now exposes `sprite_sampler` and `sprite_scheduler`.

SQLite settings updated:

- `sprite_width = 640`
- `sprite_height = 960`
- `sprite_steps = 24`
- `sprite_cfg = 5.0`
- `sprite_sampler = euler_ancestral`
- `sprite_scheduler = normal`

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check passed.
- Generated a new Lúcia sprite with the new pipeline:
  - asset: `asset_bfbb6ae3bde3`
  - file: `data/stories/story_74e634c90670/characters/char_1810fec9fbd0/neutral_asset_bfbb6ae3bde3.png`
  - resolution: `640x960`
  - transparent pixels after post-processing: about `71.73%`
  - elapsed time: about `20.0s`
  - prompt:
    - `solo, single character, full body, standing, front view, visual novel sprite, 1girl, adult woman, female, feminine face, blonde hair, long hair, red eyes, tall, elegant, tailored black suit, black blazer, formal shirt, neutral expression, clean lineart, detailed face, detailed eyes, clean silhouette, simple light gray background`

Current server:

- PID: `6128`
- URL: `http://127.0.0.1:3000`

## Stories And Characters Layout Pass

User asked to make the stories and characters pages closer to the saved DreamRunner HTML examples, while keeping the app local-only and ignoring community/login/credits features.

Code changes:

- `backend/db.py`
  - `list_stories()` now returns library metadata for each story:
    - `scene_count`
    - `character_count`
    - `cover_asset_id`
    - `cover_url`

- `public/app.js`
  - Dashboard now renders as a local story library:
    - compact title area
    - library tabs
    - sort selector for recent/title/scene count
    - quick-create story card inside the grid
    - larger cover cards with status, metadata, stats, and actions
  - Create-story characters step now uses a two-column character layout:
    - player-character profile/editor card
    - initial cast panel
    - per-character draft cards with avatars and field completion counters
  - Characters drawer now uses profile-style character cards:
    - portrait/sprite area
    - role/importance header
    - relationship callout
    - sprite gallery
    - generate/refresh sprite actions

- `public/styles.css`
  - Added library grid/card styling.
  - Added quick-create card styling.
  - Added character wizard/editor card styling.
  - Added profile-card styling for the character drawer.
  - Added responsive adjustments for mobile.

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check passed.
- `/api/health` returned OK.
- `/api/stories` returned cover/story metadata for the local library.
- Headless Edge screenshot of the stories page rendered correctly.

Current server:

- PID: `5760`
- URL: `http://127.0.0.1:3000`

## Interaction Blocks And Background Reuse

User clarified that each player interaction should not produce only one short "scene" line. A single Ollama call should produce a richer interaction block with narration, the player character's implied action/dialogue, other character reactions, and a new hook/choices. User also requested that backgrounds only change when the location changes.

Code changes:

- `backend/prompts.py`
  - Narrator prompt now asks for a "bloco de interacao" instead of a single short scene.
  - Required JSON now includes:
    - `location`
    - `location_changed`
  - `dialogues` is instructed to contain 4 to 8 entries when possible.
  - Prompt tells the model to preserve `background_prompt` and set `location_changed: false` if the local/physical location did not change.
  - Narrator user prompt now sends only the last 3 moments and 12 memory entries to reduce Ollama prompt size.
  - Recent scene dialogue context is compacted instead of sending full raw dialogue arrays.

- `backend/narrative.py`
  - `normalize_dialogues()` now accepts up to 12 dialogue/narration entries.
  - Empty dialogue text is ignored.
  - If the model returns only `scene_text`, the normalizer creates a Narrador dialogue fallback.

- `backend/app_server.py`
  - Automatic background generation now carries forward the previous background asset when `location_changed` is false.
  - If the model omits `location_changed`, similar background prompts can still reuse the previous background.
  - The story is reloaded after `carried` background reuse so the UI receives the updated `background_asset_id`.
  - Automatic/manual background image queueing no longer calls Ollama just to improve the background prompt, avoiding an extra text-generation delay.

- `public/app.js`
  - Play view now renders the full interaction block instead of only the last dialogue entry.
  - History drawer now previews recent dialogue lines for each moment.
  - Busy text changed from "Gerando cena" to "Gerando resposta".

- `public/styles.css`
  - Added scrollable interaction block styling.
  - Added speaker/text rows for multi-line VN dialogue.
  - Added mobile layout for dialogue rows.

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check passed.
- `/api/health` returned OK after restart.
- `scene_location_changed()` helper validated for false/true/unknown inputs.

Current server:

- PID: `2640`
- URL: `http://127.0.0.1:3000`

## Coding Notes

- Keep backend modular.
- Avoid hard coupling UI to Ollama/ComfyUI details.
- Save prompts and generated metadata for debugging.
- Preserve structured memory and scene history.
- Prioritize working MVP over advanced image consistency initially.
- The user prefers practical step-by-step progress and wants the app built incrementally.

## Lore And Memory Editor

Continued from session memory and implemented local manual lore/memory management.

Backend:

- `backend/db.py`
  - Added `add_lore_entry()`, `update_lore_entry()`, `delete_lore_entry()`.
  - Added `update_memory_entry()`, `delete_memory_entry()`.
  - These operations update the parent story timestamp and return the refreshed story payload.

- `backend/app_server.py`
  - Added `POST /api/stories/{story_id}/lore`.
  - Added `PATCH /api/lore/{lore_id}` and `DELETE /api/lore/{lore_id}`.
  - Added `PATCH /api/memory/{memory_id}` and `DELETE /api/memory/{memory_id}`.

Frontend:

- `public/app.js`
  - The `Lore e memoria` drawer now has a base lore editor.
  - Lore entries can be created, edited, and deleted.
  - Memory entries can be edited and deleted.
  - Existing `Register` memory flow still creates new memory notes.

- `public/styles.css`
  - Added compact entry-card header styling for lore/memory rows.

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check over `app.py` and `backend/*.py` passed with `python -B`.
- HTTP smoke test passed for:
  - create temporary story,
  - create/update/delete lore entry,
  - create/update/delete memory entry,
  - delete temporary story.

Current server:

- PID: `12332`
- URL: `http://127.0.0.1:3000`

## ComfyUI Workbench Defaults

User wants the app to select ComfyUI workbenches/workflows for image generation instead of only selecting a checkpoint.

Design decision:

- Workbenches are discovered from local ComfyUI workflow JSON files.
- Default folder:
  - `N:\SillyTavern\ComfyUI\user\default\workflows`
- The app lists both visual editor workflow JSONs and API-format workflow JSONs.
- Only API-format workflows are executable through the backend.
- Visual editor workflows are shown as detected but not executable; they need to be saved/exported from ComfyUI as API format.
- Official ComfyUI docs state the API accepts workflows in API format produced by the frontend's Save/Export API Format option.

Backend:

- `backend/config.py`
  - Added settings:
    - `comfy_workflows_dir`
    - `comfy_background_workbench`
    - `comfy_sprite_workbench`
    - `comfy_sprite_edit_workbench`

- `backend/comfy_client.py`
  - Added `list_workbenches(workflows_dir)`.
  - Detects workflow format:
    - `api`
    - `ui`
    - `invalid`
    - `unknown`
  - Added `queue_workbench_image(...)`.
  - Loads only JSON files inside the configured workflows folder.
  - Rejects non-API workflows with a clear error.
  - For API workflows, fills common inputs:
    - prompt/negative prompt
    - width/height
    - seed
    - steps/CFG
    - sampler/scheduler
    - checkpoint when a `ckpt_name` input exists
    - `SaveImage.filename_prefix`

- `backend/app_server.py`
  - Added `GET /api/comfy/workbenches`.
  - Manual image generation now uses selected workbench defaults when configured.
  - Automatic background generation now uses `comfy_background_workbench` when configured.
  - Empty workbench setting keeps the old internal simple workflow.
  - Logs now include `workbench`.

Frontend:

- `public/app.js`
  - Settings now loads `/api/comfy/workbenches`.
  - ComfyUI config now includes:
    - `Pasta de workbenches`
    - `Workbench de cenario`
    - `Workbench de sprite`
    - `Workbench de edicao de sprite`
  - Selects include `Workflow simples interno` as fallback.
  - Detected workbenches are shown with format/status.

Detected current ComfyUI workflows:

- `image_anima_base_v1.json`
  - format: `ui`
  - executable: `false`
- `image_netayume_lumina_t2i.json`
  - format: `ui`
  - executable: `false`

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check over `app.py` and `backend/*.py` passed with `python -B`.
- Temporary HTTP smoke test for `/api/comfy/workbenches` passed.
- Updated server started:
  - PID: `11420`
  - URL: `http://127.0.0.1:3000`

## Workbench Prompt Profiles

User identified that each ComfyUI workbench/model needs its own prompt style.

Example:

- Sprite workbench should not receive short booru-style tags like:
  - `1boy, tall, thin, black hair`
- It should receive detailed natural-language English prose like:
  - `A tall, powerfully built man with light brown skin...`
- Sprite edit / variation workbenches will likely need different prompt instructions later.

Implementation:

- Added setting:
  - `comfy_prompt_profiles`
- It is a JSON object keyed by workbench id.
- Each profile has:
  - `style`
  - `example`

Backend:

- `backend/narrative.py`
  - Added `generate_workbench_visual_prompt(...)`.
  - Uses Ollama to convert raw story/character/cena source text into the prompt style required by the selected workbench.
  - Returns JSON-only `{ "visual_prompt": "..." }`.
  - Logs as `ollama / chat:workbench-prompt`.
  - Falls back to the existing local prompt if the profile is empty or Ollama fails.
  - Added `build_sprite_source_prompt(...)` so Ollama sees complete character fields instead of only short extracted tags.

- `backend/app_server.py`
  - `generate_image()` now determines the effective workbench before building the visual prompt.
  - If a prompt profile exists for the effective workbench, it asks Ollama to adapt the prompt.
  - Sprite prompts now use raw character/source text for Ollama, with old deterministic tag prompt as fallback.
  - Automatic background generation also supports prompt profiles if a background workbench is configured.

- `backend/config.py`
  - Added default prompt profiles for:
    - `spriteGenerator_AnimaBaseV1.json`
    - `spriteGenerator_Netayume.json`

Frontend:

- `public/app.js`
  - Config screen now renders `Perfis de prompt por workbench`.
  - Each executable workbench gets:
    - `Estilo de prompt`
    - `Exemplo de prompt`
  - Save settings collects these textareas into `comfy_prompt_profiles`.

- `public/styles.css`
  - Added compact styles for prompt profile blocks.

Validation:

- `node --check public/app.js` passed.
- Python AST syntax check over `app.py` and `backend/*.py` passed.
- Tested `generate_workbench_visual_prompt()` with Ollama and `spriteGenerator_AnimaBaseV1.json`.
- Ollama returned detailed prose:
  - `A tall, muscular man named Kael with light brown skin...`

Operational config correction:

- `spriteGenerator_Netayume.json` had been saved as `comfy_background_workbench`.
- Corrected settings:
  - `comfy_background_workbench = ""`
  - `comfy_sprite_workbench = "spriteGenerator_Netayume.json"`

Current server:

- PID: `14616`
- URL: `http://127.0.0.1:3000`

## Workbench Prompt Profile Debug Fix

User reported that sprite generation still seemed to send old short tag prompts and did not appear to call Ollama.

Diagnosis:

- API logs confirmed older requests did send old local tag prompts, e.g.:
  - `solo, single character, full body, standing...`
- There was no `ollama / chat:workbench-prompt` before those old `comfyui / prompt:image` logs.
- `netstat -ano | findstr :3000` showed three Python servers listening on `127.0.0.1:3000` simultaneously:
  - PID `6000`
  - PID `11420`
  - PID `14616`
- This meant browser/API requests could hit an older server process that did not have the new workbench prompt-profile code.

Fix:

- Stopped duplicate servers:
  - `6000`
  - `11420`
  - `14616`
- Started a single updated server.
- Added extra request log fields for `comfyui / prompt:image`:
  - `prompt_source`
    - `local`
    - `ollama:workbench-profile`
  - `source_prompt`

Validation:

- With a single updated server, a test generation produced:
  - `ollama / chat:workbench-prompt` started
  - `ollama / chat:workbench-prompt` ok
  - then `comfyui / prompt:image`
- The `prompt:image` payload contained detailed prose instead of the old short tag prompt.
- Confirmed only one listener:
  - `127.0.0.1:3000 LISTENING 2180`

Current server:

- PID: `2180`
- URL: `http://127.0.0.1:3000`

## Workbench Generation Speed Fix

User reported that manual ComfyUI workbench generation took about `27s`, while generation from the app took about `219s`.

Measured from API logs:

- `ollama / chat:workbench-prompt`
  - about `8.2s`
- `comfyui / prompt:image`
  - prompt accepted at `1780401320694`
- `comfyui / history:view-image`
  - image ready at `1780401542848`
- Difference after Comfy prompt acceptance:
  - about `222.1s`

Conclusion:

- The big delay was not the Ollama prompt-profile call.
- The app was making the workbench run differently from manual ComfyUI because `apply_workbench_inputs()` overwrote workbench generation controls:
  - width/height
  - steps
  - CFG
  - sampler
  - scheduler
- Example: `spriteGenerator_AnimaBaseV1.json` manual API workflow uses:
  - `1024x1024`
  - `30` steps
  - `cfg = 4`
  - `sampler_name = er_sde`
  - `scheduler = simple`
- The app had been overriding with app sprite settings:
  - `640x960`
  - `24` steps
  - `cfg = 5`
  - `sampler_name = euler_ancestral`
  - `scheduler = normal`

Fix:

- `backend/comfy_client.py`
  - `queue_workbench_image()` now has `preserve_generation_settings=True`.
  - For workbench JSONs, the app now preserves the workflow's own width/height/steps/CFG/sampler/scheduler by default.
  - It still randomizes seed.
  - It originally set `SaveImage.filename_prefix = LocalDreamVN`; this was later renamed to `TaleWeaver`.
  - Positive prompt is now injected as the prompt text exactly, without wrapping it in the old generic `masterpiece, best quality...` helper.

- `backend/app_server.py`
  - `comfyui / prompt:image` logs now include:
    - `workbench_generation_settings`
      - `preserved` for external workbenches
      - `app` for the internal simple workflow

Validation:

- Applied workflow test confirmed `spriteGenerator_AnimaBaseV1.json` now preserves:
  - `30 4 er_sde simple 1024 1024`
- Applied prompt test confirmed the positive prompt node receives exactly:
  - `A detailed prose prompt.`
- Python AST syntax check passed.
- Server restarted with only one listener:
  - `127.0.0.1:3000 LISTENING 2796`

Current server:

- PID: `2796`
- URL: `http://127.0.0.1:3000`

## Workbench Slow Prompt Follow-up

User reported generation got even slower: about `320s`.

Measured latest ComfyUI history for prompt:

- `9dadf1b8-ee57-44b0-9ab0-2934d5fb6832`
- `execution_start.timestamp = 1780402438579`
- `execution_success.timestamp = 1780402758717`
- ComfyUI internal execution time:
  - about `320.1s`

Findings:

- The delay was inside ComfyUI, not in the frontend wait loop.
- Queue was empty after completion.
- Current selected sprite workbench:
  - `spriteGenerator_AnimaBaseV1.json`
- This workbench uses:
  - `qwen_3_06b_base.safetensors` text encoder
  - `anima-base-v1.0.safetensors` UNET
- Older short-tag prompt runs took about `17-22s`.
- The very slow runs started when sending longer natural-language prose prompts through the AnimaBase/Qwen workflow.
- App was still overwriting the workflow's negative prompt with a long generic negative prompt, which made it less equivalent to the manual workbench.

Fixes:

- `backend/comfy_client.py`
  - External workbenches now preserve the workflow's original negative prompt when `preserve_generation_settings=True`.
  - Positive prompt is still replaced with the final app/Ollama prompt.

- Updated saved setting `comfy_prompt_profiles.spriteGenerator_AnimaBaseV1.json`:
  - Style now asks Ollama for compact natural-language prose, not long paragraphs.
  - Target length:
    - `45 to 70 words maximum`
  - Example shortened accordingly.

Validation:

- Applied workflow test confirmed:
  - Positive prompt becomes exactly the app prompt.
  - Negative prompt stays:
    - `worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, sepia`
  - Workbench generation settings remain:
    - `30 4 er_sde simple 1024 1024`

Current server:

- PID: `15876`
- URL: `http://127.0.0.1:3000`

## Repeated Workbench Runs Slow

User observed:

- First sprite generation after ComfyUI restart is fast.
- Later sprite generations become very slow.
- Same issue happened when switching to the other workbench.

Measured:

- New ComfyUI PID after user restart:
  - `15340`
- Recent ComfyUI history showed:
  - Anima runs after restart: about `26-32s`
  - Netayume runs after restart: about `35-50s`
  - Later runs degraded to about `308-319s`
- Example Netayume prompt:
  - `2a2f3e5a-cf27-413b-ab63-a874b4c1184e`
  - `execution_start.timestamp = 1780406291871`
  - `execution_success.timestamp = 1780406611387`
  - duration about `319.5s`
- Comparing app-sent workflow to saved `spriteGenerator_Netayume.json` showed only expected differences:
  - seed
  - positive prompt
  - filename_prefix
- This strongly suggests ComfyUI/VRAM/cache degradation across repeated generations, not a remaining app workflow mismatch.

Mitigation implemented:

- `backend/config.py`
  - Added setting:
    - `comfy_free_memory_between_workbench_runs = True`

- `backend/comfy_client.py`
  - Added `free_memory(base_url, unload_models=True, free_memory_flag=True)`.
  - Calls ComfyUI:
    - `POST /free`
    - payload: `{ "unload_models": true, "free_memory": true }`

- `backend/app_server.py`
  - Before queueing an external workbench image, if the setting is enabled:
    - calls `/free`
    - logs `comfyui / memory:free-before-workbench`
  - After downloading a generated workbench asset, if the setting is enabled:
    - calls `/free`
    - logs `comfyui / memory:free-after-asset`

Current settings confirmed:

- `comfy_sprite_workbench = spriteGenerator_Netayume.json`
- `comfy_free_memory_between_workbench_runs = true`

Current server:

- PID: `11340`
- URL: `http://127.0.0.1:3000`

## Character Drawer Editing Workbench

User requested character editing improvements based on DreamRunner references:

- Clicking `Personagens` now opens a wider side drawer with one tab per character.
- Each character tab shows a detail view with:
  - portrait/current sprite
  - species
  - gender
  - type
  - aliases
  - description
  - personality
  - physical appearance
  - clothing
  - relationship when present
- Temporary buttons are visible but disabled for now:
  - `Appearance Designer`
  - `Add Character`
  - `Leave Scene`
- Detail view has:
  - `Editar`
  - `Gerar prompt`
  - `Regenerate`
- `Editar` opens inline editable fields in the drawer.
- Saving character edits only saves text/data; it does not regenerate sprites.
- Added collapsible field:
  - `Prompt para Geracao de Imagem`
  - It is collapsed by default.
  - In edit mode, it can be expanded and manually edited.
- New sprite flow:
  - Ollama no longer rewrites sprite prompts inside `/generate-image`.
  - The app now has `POST /api/characters/{id}/image-prompt`.
  - That endpoint asks Ollama to generate the character image prompt using the sprite workbench prompt profile and saves it to `characters.visual_prompt`.
  - Sprite generation sends exactly `character.visual_prompt` to ComfyUI.
  - If `visual_prompt` is empty, manual sprite regeneration warns the user and automatic scene sprite generation skips that character.

Files changed:

- `backend/db.py`
  - Added character columns with migration:
    - `species`
    - `gender`
    - `character_type`
    - `aliases`
    - `description`
    - `clothing`
  - Updated character insert/update/duplicate paths.
- `backend/app_server.py`
  - Added character image prompt endpoint.
  - Stopped workbench-profile Ollama conversion for sprite image generation.
- `backend/narrative.py`
  - Character prompt source now includes the new detailed fields.
- `public/app.js`
  - Added character drawer state, tabs, detail/edit views, prompt generation, and exact-prompt sprite generation.
- `public/styles.css`
  - Added wider character drawer, tab layout, detail sections, edit form, and prompt panel styles.

Validation:

- `node --check public/app.js` passed.
- Python AST parse passed for:
  - `backend/db.py`
  - `backend/app_server.py`
  - `backend/narrative.py`
- `python -c "from backend import db; db.init_db(); print('ok')"` passed and applied DB migration.
- `python -m py_compile ...` was attempted but failed because Windows denied writing to `backend/__pycache__`, not because of syntax.
- `curl http://127.0.0.1:3000/api/settings` passed.
- `curl http://127.0.0.1:3000/api/stories` passed.
- Edge headless rendered the dashboard DOM.

Current server:

- PID: `8284`
- URL: `http://127.0.0.1:3000`

## Faster Story Scene Generation

User reported each new story scene felt very slow, close to 2 minutes.

Main findings:

- `public/app.js` was not only waiting for Ollama text.
- After `/generate-scene`, the frontend also waited for:
  - queued background generation in ComfyUI
  - scene sprite generation
- So "continue story" was mixing text generation with image generation.
- `backend/prompts.py` also sent a relatively large narrator prompt:
  - previous example: system about `2851` chars, user prompt about `6664` chars
  - total about `9515` chars before response generation

Changes implemented:

- `backend/prompts.py`
  - Shortened narrator system prompt.
  - Reduced expected scene response size:
    - dialogues now targets `2 to 4` entries instead of `4 to 8`.
  - `build_narrator_user_prompt` now sends selective context:
    - essential lore truncated
    - current summary truncated
    - current player personality/goals
    - only relevant/current characters, not every known character
    - no visual prompt in narrative context
    - only 2 recent scenes
    - fewer memory entries
  - Added helpers:
    - `select_relevant_characters`
    - `compact`

- `backend/narrative.py`
  - Narrator API logs now store prompt sizes and a preview instead of the full prompt payload.
  - Logs include `duration_seconds` for successful narrator calls.

- `backend/app_server.py`
  - `/api/stories/{id}/generate-scene` now respects payload:
    - `generate_images: false`
  - When false, it skips auto background queuing and returns:
    - `auto_background: { "mode": "skipped" }`

- `public/app.js`
  - `generateScene` now sends:
    - `{ user_input, generate_images: false }`
  - Removed automatic sprite generation after text scene generation.
  - Existing `depictCurrentScene()` still generates background/sprites when user explicitly asks for images.

Measured prompt size after change on current story:

- system prompt: about `2444` chars
- user prompt: about `3945` chars
- total before response: about `6389` chars

Validation:

- `node --check public/app.js` passed.
- Python AST parse passed for:
  - `backend/prompts.py`
  - `backend/narrative.py`
  - `backend/app_server.py`
- `curl http://127.0.0.1:3000/api/stories` passed.
- `curl http://127.0.0.1:3000/` returned HTML.

Current server:

- PID: `11084`
- URL: `http://127.0.0.1:3000`

## Story Creation Uses Initial Scene And Character Image Prompts

User requested changes to story creation:

1. Initial characters must populate new detailed fields:
   - species
   - gender
   - character_type
   - aliases
   - description
   - clothing
   - visual_prompt / Prompt para Geracao de Imagem
2. Character image prompts must consider all descriptive character fields.
3. `Mensagem inicial` must become the first scene, not just text inside lore.
4. First background and initial sprites should be generated automatically on first story creation.

Changes implemented:

- `backend/narrative.py`
  - Expanded `STORY_SEED_SYSTEM_PROMPT` schema for player and initial characters.
  - `normalize_story_seed` and `normalize_seed_character` now preserve new fields.
  - Added `enrich_story_creation_payload(payload)`.
    - Called during `/api/stories` creation.
    - Uses Ollama to fill missing species/gender/type/aliases/description/physical/personality/clothing/relationship/visual_prompt.
    - Includes sprite workbench prompt profile style/example when available.
    - Falls back to local inference if Ollama fails.
  - `build_sprite_visual_prompt` now includes:
    - species
    - gender
    - character_type
    - description
    - physical
    - clothing
    - personality
    - visual_prompt

- `backend/app_server.py`
  - `/api/stories` now calls:
    - `narrative.enrich_story_creation_payload(payload)`
    - then `db.create_story(...)`

- `backend/db.py`
  - `create_story` now reads `starting_message`.
  - If `starting_message` exists, it creates the first scene immediately via `build_initial_scene`.
  - Initial scene includes:
    - title from `starting_location`
    - scene_text from `starting_message`
    - narrator dialogue with the starting message
    - default first choices
    - detected `characters_on_screen` by matching character names/aliases in the starting message
    - initial background prompt based on location/message/style
    - memory summary from the starting message

- `public/app.js`
  - Initial character draft now carries new fields:
    - species
    - gender
    - character_type
    - aliases
    - description
    - clothing
  - Creation form now shows these fields for initial characters.
  - `saveCreateDraft` preserves these fields instead of discarding them.
  - Create story payload now sends:
    - `starting_location`
    - `starting_message`
    - `story_prompt`
  - After creating a story, frontend automatically runs `generateInitialStoryAssets()`.
    - Generates first background from first scene.
    - Generates sprites for all initial characters with `visual_prompt`, not only those detected on screen.
    - Uses scene expression if present, otherwise `neutral`.

Validation:

- `node --check public/app.js` passed.
- Python AST parse passed for:
  - `backend/db.py`
  - `backend/narrative.py`
  - `backend/app_server.py`
- Tested `db.build_initial_scene(...)` in memory:
  - detected Garret and Tum from starting message
  - produced background prompt
- `curl http://127.0.0.1:3000/api/stories` passed.
- `curl http://127.0.0.1:3000/` returned HTML.

Current server:

- PID: `21924`
- URL: `http://127.0.0.1:3000`

## Character Prompt Button Placement And Replacement

User requested:

- Move `Gerar prompt` from the top character action row to the `Prompt para Geracao de Imagem` panel.
- Clicking `Gerar prompt` should replace an existing prompt instead of only producing a new one when the field is empty.

Changes implemented:

- `public/app.js`
  - Removed `Gerar prompt` from the top character action row.
  - Added `Gerar prompt` beside the prompt panel header/toggle.

- `public/styles.css`
  - `character-prompt-panel` now uses a two-column grid:
    - left: prompt tab/toggle
    - right: `Gerar prompt`
  - textarea/pre content spans both columns.

- `backend/app_server.py`
  - `generate_character_image_prompt` no longer uses existing `character.visual_prompt` as the primary fallback.
  - It now generates fallback from the current character descriptive fields via `narrative.build_sprite_visual_prompt(...)`, so regeneration replaces the saved prompt.

Validation:

- `node --check public/app.js` passed.
- Python AST parse passed for `backend/app_server.py`.
- `curl http://127.0.0.1:3000/api/stories` passed.
- `curl http://127.0.0.1:3000/` returned HTML.

Current server:

- PID: `19140`
- URL: `http://127.0.0.1:3000`

## Character Image Prompt Source Limited To Visual Fields

User requested:

- Improve `Prompt para Geracao de Imagem` generation.
- Character image prompt generation must use only:
  - `Especie`
  - `Genero`
  - `Aparencia Fisica`
  - `Vestimenta`
- Continue using `Perfis de prompt por workbench`.
- The generated image prompt must be entirely in English.
- Other app fields remain in pt-BR.

Changes implemented:

- `backend/narrative.py`
  - `build_sprite_source_prompt(...)` now includes only:
    - species
    - gender
    - physical
    - clothing
  - It no longer includes:
    - name
    - role/type
    - aliases
    - description
    - personality
    - relationship
    - previous fixed visual prompt
    - arbitrary user visual request
  - Source prompt now explicitly says:
    - final image prompt must be English only
    - one character only
    - full-body, standing, front-view visual novel sprite
  - `generate_workbench_visual_prompt(...)` now explicitly instructs Ollama to translate any Portuguese source fields and return `visual_prompt` in English only.
  - `build_sprite_visual_prompt(...)` fallback now also uses only species/gender/physical/clothing, not prior visual prompt or narrative/personality fields.
  - Creation enrichment instructions now say generated `visual_prompt` must be based only on species/gender/physical/clothing.
  - Fixed local fallback false positive:
    - `jaqueta jeans velha` no longer causes `elderly`
    - denim jacket is recognized as clothing.

Validation:

- Python AST parse passed for `backend/narrative.py`.
- Local test confirmed source prompt contains only:
  - Species
  - Gender
  - Physical appearance
  - Clothing
- Local fallback output stayed in English.
- `curl http://127.0.0.1:3000/api/stories` passed.
- `curl http://127.0.0.1:3000/` returned HTML.

Current server:

- PID: `16696`
- URL: `http://127.0.0.1:3000`

## Sprite View Mode: Distant And Close

User requested:

- Sprites are generated full-body and should continue that way.
- On screen, add two display modes:
  - `Distante`: current full-body view.
  - `Aproximado`: larger waist-up/upper-half style view by cropping the same sprite.
- Switching modes should not require waiting for generation/load each time.

Changes implemented:

- `public/app.js`
  - Added state:
    - `spriteViewMode`
    - persisted in `localStorage`
  - Added toolbar select:
    - `Sprites: Distante | Aproximado`
  - `renderSprites(...)` now wraps sprite images in `.scene-sprite-frame`.
  - Images use:
    - `loading="eager"`
    - `decoding="async"`
  - Same sprite image URL is reused for both display modes.

- `public/styles.css`
  - Added `.scene-sprite-frame.distant`.
  - Added `.scene-sprite-frame.close`.
  - Close mode enlarges the same full-body image and crops inside the frame, emphasizing the upper body.
  - Mobile rules adjusted for both modes.

Important behavior:

- No second sprite asset is generated.
- No additional ComfyUI call is needed.
- Switching mode reuses the same loaded/cached image and changes only CSS layout/crop.

Validation:

- `node --check public/app.js` passed.
- `curl http://127.0.0.1:3000/` returned HTML.
- `curl http://127.0.0.1:3000/api/stories` passed.

Current server:

- PID: `20836`
- URL: `http://127.0.0.1:3000`

## Sprite View Mode Crop Fix

User reported:

- `Distante` became even more distant than before.
- `Aproximado` cropped the sprite so badly that almost nothing was visible.

Fix implemented:

- `public/styles.css`
  - Restored distant mode behavior to match the old image sizing:
    - image again uses `max-height: 100%`
    - image again uses `max-width: 32vw`
    - distant frame no longer restricts width/height or clips overflow
  - Reworked close mode:
    - smaller crop frame
    - less aggressive image scaling
    - top-aligned image with no upward translation
    - mobile close mode also reduced from previous excessive crop

Validation:

- `node --check public/app.js` passed.
- `curl http://127.0.0.1:3000/` returned HTML.
- `curl http://127.0.0.1:3000/api/stories` passed.

Current server:

- PID: `7668`
- URL: `http://127.0.0.1:3000`

## Sprite Close Mode Horizontal Crop Fix

User reported:

- `Distante` is now OK.
- `Aproximado` still showed only a piece of the left side of the sprite.
- It looked like the sprite was shifted to the right and outside the div.

Fix implemented:

- `public/styles.css`
  - Close mode no longer scales by image height.
  - Close mode now scales by width:
    - `.scene-sprite-frame.close .scene-sprite { width: 100%; height: auto; }`
  - Close frame is wider:
    - desktop: `min(56vw, 640px)`
    - mobile: `76vw`
  - The frame still clips vertically, but should no longer clip horizontally.

Reason:

- Height-based scaling made wide/transparent sprite canvases overflow horizontally.
- Width-based scaling keeps the whole canvas inside the frame and crops mostly the lower part.

Validation:

- `node --check public/app.js` passed.
- `curl http://127.0.0.1:3000/` returned HTML.
- `curl http://127.0.0.1:3000/api/stories` passed.

Current server:

- PID: `16432`
- URL: `http://127.0.0.1:3000`

## Sprite Close Mode Size Fix

User reported:

- `Distante` is OK.
- `Aproximado` became smaller than `Distante`.

Fix implemented:

- `public/styles.css`
  - Close mode now uses the same base sizing as distant mode:
    - `max-height: 100%`
    - `max-width: 32vw`
  - Then applies visual zoom:
    - desktop: `transform: scale(1.65)`
    - mobile: `transform: scale(1.55)`
  - Close frame remains wide enough to avoid horizontal clipping:
    - desktop: `min(56vw, 640px)`
    - mobile: `76vw`

Validation:

- `node --check public/app.js` passed.
- `curl http://127.0.0.1:3000/` returned HTML.
- `curl http://127.0.0.1:3000/api/stories` passed.

Current server:

- PID: `6012`
- URL: `http://127.0.0.1:3000`

## DreamRunner-Style VN Screen Redesign

User requested major Visual Novel screen redesign based on:

- `N:\VNApp\dreamRunner Examples\Dialog\GenlarSpeaking.html`
- `N:\VNApp\dreamRunner Examples\Dialog\NarratorSpeaking.html`
- other files in `N:\VNApp\dreamRunner Examples\Dialog\`

Requested changes:

1. Improve sprite/background quality, likely via resolution.
2. Make sprites larger, closer to DreamRunner.
3. Active speaking character:
   - stays in same position
   - moves visually to front layer
   - gets subtle highlight/shadow
   - non-speaking characters become slightly darker and behind
4. Improve sprite cutout/fringe cleanup.
5. Show one dialogue/narration entry at a time.
   - User advances with arrow beside dialogue.
   - Narrator should not show name; text should be italic and lower opacity.
6. Restyle the VN UI to look closer to DreamRunner:
   - black translucent blurred dialogue box
   - nameplate for character names
   - video-game style next arrow

Changes implemented:

- `public/app.js`
  - Added state:
    - `dialogueSceneId`
    - `dialogueIndex`
  - Added dialogue sequencing:
    - `syncDialogueState(scene)`
    - `getDialogueSequence(scene)`
    - `isDialogueComplete(scene)`
    - `isCharacterOnScreen(scene, name)`
  - `renderPlay()` now:
    - shows only current dialogue/narration item
    - disables Continue until the dialogue sequence is complete
    - hides choices/custom input until the dialogue sequence is complete
    - determines active speaker from current dialogue
  - Added `next-dialogue` action.
  - `renderSprites(scene, activeSpeaker)` now gives sprites:
    - `active`
    - `inactive`
    - `neutral`
  - If current speaker is not on screen, no sprite is dimmed.
  - `renderInteractionBlock(...)` now renders a DreamRunner-like dialogue box:
    - character nameplate for non-narrator
    - no narrator nameplate
    - narrator text italic/lower opacity
    - arrow button to advance one line at a time

- `public/styles.css`
  - Restyled VN stage/dialogue heavily.
  - Sprites are larger:
    - `.sprite-layer` bottom moved lower and height increased.
    - sprite max width increased.
  - Added active/inactive sprite focus:
    - active: brighter, front z-index, stronger shadow
    - inactive: dimmer, lower z-index
  - Dialogue box now uses black translucent blurred background.
  - Added DreamRunner-style nameplate.
  - Added circular next arrow.
  - Mobile layout adjusted for new dialogue box/sprite positions.

- `backend/app_server.py`
  - Improved sprite background cleanup after download:
    - threshold increased slightly
    - added `soften_sprite_edge(...)`
    - edge pixels near the removed uniform background are made transparent or decontaminated to reduce white fringe/rebarba.
  - This affects newly downloaded/generated sprite assets. Existing saved sprite files are not automatically reprocessed.

- `backend/config.py`
  - Increased default simple-generation resolution:
    - background: `1536 x 864`
    - sprite: `1024 x 1536`

- Current DB settings were also updated:
  - `image_width = 1536`
  - `image_height = 864`
  - `sprite_width = 1024`
  - `sprite_height = 1536`

Important note:

- External ComfyUI workbenches may preserve their own workflow resolution because the app currently preserves workbench generation settings. For workbench-based generation, resolution may still need to be changed inside the ComfyUI workflow unless we later add a setting to override workbench width/height.

Validation:

- `node --check public/app.js` passed.
- Python AST parse passed for:
  - `backend/app_server.py`
  - `backend/config.py`
- `curl http://127.0.0.1:3000/` returned HTML.
- `curl http://127.0.0.1:3000/api/settings` confirmed new resolution settings.
- Server process responding.

Current server:

- PID: `15712`
- URL: `http://127.0.0.1:3000`

## Sprite Background Removal Moved To ComfyUI

User decided to handle sprite background removal inside the ComfyUI sprite workbench, likely with a dedicated RMBG/background-removal node.

Change implemented:

- `backend/app_server.py`
  - Removed the app-side Pillow sprite cutout step.
  - Asset downloads now save the image exactly as ComfyUI returns it.
  - Removed old helper functions:
    - `prepare_asset_image(...)`
    - `remove_uniform_sprite_background(...)`
    - `soften_sprite_edge(...)`
    - `color_distance(...)`
  - Removed the now-unused `io` import.

Important behavior:

- New sprite quality/cutout depends on the selected ComfyUI workbench output.
- Existing saved sprite files are not changed.
- If the ComfyUI workbench outputs PNG with alpha, the app will preserve that transparency.

Validation:

- Confirmed no remaining references to old background-removal helpers in `backend/app_server.py`.
- Python AST parse passed for `backend/app_server.py`.
- `py_compile` was not usable because Windows denied writing to `backend/__pycache__`.
- Server restarted:
  - PID: `7656`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## Stop App Button

User requested a button on the initial menu to stop the app.

Changes implemented:

- `backend/app_server.py`
  - Added `POST /api/app/shutdown`.
  - The endpoint logs `local / app:shutdown`, responds with JSON first, then shuts down the local `ThreadingHTTPServer` on a short delayed thread.

- `public/app.js`
  - Added `Parar app` button to the dashboard initial screen.
  - Added `stopApp()` with confirmation dialog.
  - Calls `/api/app/shutdown` and shows `App parado. Pode fechar esta aba.` after confirmation.

- `public/styles.css`
  - Adjusted dashboard title ordering so the stop button stays aligned with the title actions.

Validation:

- `node --check public/app.js` passed.
- Python AST parse passed for `backend/app_server.py`.
- Server restarted:
  - PID: `21732`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## Root Startup Batch File

User requested a `.bat` in the project root to start the app.

Added:

- `iniciar_app.bat`

Behavior:

- Changes directory to the batch file location.
- Stops any existing process listening on local port `3000` before starting.
- Runs:
  - `"C:\Python314\python.exe" -B app.py`
- Prints the app URL:
  - `http://127.0.0.1:3000`
- Keeps the console open after the server exits with `pause`, so errors remain visible.

## Richer Visual Novel Text And Introduced Character Quality

User requested:

- Generated scenes should stop feeling simplistic or shallow.
- Visual novel text should be more detailed, a little more poetic, and structurally richer.
- The narrator may return more than one narrator line and one line per character.
- Characters introduced mid-scene should not be saved with weak/generic fields like:
  - `Personagem presente em cena com expressão de surpresa.`
- Newly introduced characters must feel like complete characters who belong to the world and story.
- Narrative character fields should remain in pt-BR; only image prompts should be in English.

Changes implemented:

- `backend/prompts.py`
  - Reworked narrator instructions away from "short/direct" output.
  - Scene text now asks for 2 to 4 atmospheric/dramatic sentences.
  - Dialogues now target 4 to 8 entries, with up to 10 when the scene needs room.
  - Narrator may insert atmosphere, pauses, gestures, silence, and observable thoughts.
  - Added explicit rules for visual novel voice, subtext, emotional tension, meaningful choices, and slower conflict resolution.
  - Expanded `new_characters_detected` schema with species, gender, character type, aliases, physical appearance, clothing, relationship, speech style, and stronger description requirements.
  - Narrator context now includes more useful character data:
    - description
    - secrets/conflicts
    - 3 recent scenes instead of 2
    - up to 6 recent dialogue lines per scene instead of 4
    - slightly larger lore and summary context

- `backend/ollama_client.py`
  - `chat_json(...)` now accepts optional Ollama generation options.

- `backend/narrative.py`
  - Narrator calls now pass:
    - `num_ctx` from `ollama_context`
    - `num_predict = 1800`
  - Story seed / improve calls may also use larger generation options.
  - Introduced-character enrichment prompt is stricter:
    - all narrative fields must be Brazilian Portuguese
    - visual prompt remains English only
    - weak placeholders must be ignored
    - the character must be tied to the world, current conflict, scene, and protagonist
  - Added contextual fallback enrichment for introduced characters.
    - Replaces generic text like "personagem presente em cena".
    - Fills description, physical, personality, clothing, role, relationship, and speech style with pt-BR contextual defaults when Ollama gives weak/missing data or is unavailable.
    - Prevents a narrative description from being reused as physical appearance.

- `public/app.js`
  - Character-detected modal now exposes more fields:
    - species
    - gender
    - character type
    - aliases
    - narrative description
    - clothing
    - speech style
    - physical appearance
  - Saving a detected/generated character now uses `/api/stories/{story_id}/characters/introduce`, so the backend can enrich it with story and scene context before saving.
  - Frontend fallback candidates no longer generate weak `suggested_description` values such as "Personagem presente em cena...".
  - Frontend candidate fallbacks now send only a `reason` and a broader role hint, letting backend enrichment create the actual character sheet.

Validation:

- Python AST syntax check passed for:
  - `backend/prompts.py`
  - `backend/narrative.py`
  - `backend/ollama_client.py`
  - `backend/app_server.py`
- `node --check public/app.js` passed.
- Local fallback test confirmed a weak introduced character description is replaced by a contextual pt-BR character description, physical description, and role.

Server:

- Server was started after this change:
  - PID: `18268`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## Complete Character Records And Language Preparation

User requested:

- Whenever a character is generated, either at story creation or mid-story, all character fields must be filled.
- Fields like `Genero` must not remain blank.
- Narrative fields must be in pt-BR by default.
- Only image generation prompts should be in English.
- Existing stories/characters do not need migration.
- Future language switching should be prepared so the app can later generate/interface in English if desired.

Changes implemented:

- `backend/narrative.py`
  - Added central character completion helper:
    - `complete_character_record(...)`
  - It fills all main character fields when missing or weak:
    - name
    - species
    - gender
    - character_type
    - aliases
    - description
    - physical
    - personality
    - clothing
    - role
    - relationship
    - secrets
    - speech_style
    - visual_prompt
  - pt-BR remains the default for narrative fields.
  - `visual_prompt` is kept/generated in English.
  - If a visual prompt is empty or clearly Portuguese, it is rebuilt from species/gender/physical/clothing using the English sprite prompt fallback.
  - Story creation enrichment now always runs final completion for player and initial characters, even when Ollama already returned data.
  - Introduced characters now run final completion after contextual enrichment.
  - Added language helpers:
    - `normalize_language(...)`
    - `story_language(...)`
    - `is_portuguese(...)`
    - `language_instruction(...)`
  - Supports `pt-BR` now and prepares `en-US` for future generated content.
  - Fixed prompt gender detection false positive where `man` matched inside unrelated words such as `marcante`.

- `backend/app_server.py`
  - Manual character creation endpoint now loads story context and calls `narrative.complete_character_record(...)` before saving.
  - Added `latest_scene(...)` helper for manual character context.

- `backend/prompts.py`
  - Narrator prompt no longer hardcodes Portuguese; it now says to write in the story language from the user prompt.
  - User prompt now includes `Idioma da historia`.

- `public/app.js`
  - Settings screen now exposes `Idioma padrao de geracao` with:
    - `pt-BR`
    - `en-US`
  - New story drafts use `settings.default_language` as the initial story language.

Validation:

- Python AST syntax check passed for:
  - `backend/prompts.py`
  - `backend/narrative.py`
  - `backend/ollama_client.py`
  - `backend/app_server.py`
  - `backend/db.py`
- `node --check public/app.js` passed.
- Direct local tests confirmed:
  - pt-BR character completion leaves no empty required fields.
  - en-US character completion leaves no empty required fields.
  - visual prompt fallback stays English.

Server:

- Previous server PID `18268` was stopped.
- Server restarted:
  - PID: `3156`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## Ollama-Driven Scenario Change And Stronger Background Prompts

User requested:

- The app must identify when the scenario/background changes.
- Scenario change should be decided by Ollama per scene, not hardcoded rules.
- Each scene should track what scenario/location it is in.
- If Ollama identifies a scenario change, the app should automatically generate a new background.
- Background descriptions sent to ComfyUI should be more robust and less generic.

Changes implemented:

- `backend/prompts.py`
  - Strengthened the narrator contract for `location`, `location_changed`, and `background_prompt`.
  - `location` is now described as a stable narrative identifier for the current scenario.
  - `location_changed` is explicitly Ollama's decision:
    - true only for a physical move to a different environment/room/street/region/building/environmental point of view.
    - false for dialogue, emotional shifts, revelations, or action that remains in the same environment.
  - `background_prompt` must now be robust English for SDXL/ComfyUI:
    - 45 to 90 words
    - no people/characters/text/UI
    - architecture/spatial layout
    - materials
    - important objects
    - mood/time of day
    - lighting
    - palette
    - composition/depth
  - Explicitly tells Ollama to avoid generic prompts like just `room`, `street`, `forest`, or `anime background`.

- `backend/narrative.py`
  - Added `build_background_visual_prompt(story, scene)`.
  - It converts the scene's Ollama-produced `background_prompt` into a stronger final ComfyUI prompt with:
    - empty VN background / no people constraints
    - visual style
    - unique landmark / story-conflict environment details when prompt is short
    - foreground/midground/background depth
    - environmental storytelling objects
    - material texture
    - cinematic lighting
    - cohesive palette
    - wide establishing shot
  - The final prompt avoids appending pt-BR scene text/location so the ComfyUI prompt stays English.

- `backend/app_server.py`
  - Automatic background generation now sends the robust final background prompt to ComfyUI.
  - Logs now include:
    - original scene `source_prompt`
    - final prompt sent to ComfyUI
    - `location`
    - `location_changed`
  - Manual/Depict/initial `/generate-image` background requests also use the robust background prompt builder when a scene is available.
  - Added `scene_location(scene)` helper.

- `backend/db.py`
  - Initial scene background prompt is now more detailed:
    - no people/characters/UI constraints
    - architecture/spatial layout
    - environmental storytelling objects
    - material textures
    - depth layers
    - cinematic lighting
    - cohesive palette

- `public/app.js`
  - Scene generation now sends `generate_images: true` again.
  - Since sprite auto-generation remains removed, this only re-enables automatic background handling.
  - Backend will carry forward/reuse existing background when Ollama says `location_changed: false`; it will queue a new background when the location changes and no reusable background exists.

Validation:

- Python AST syntax check passed for:
  - `backend/prompts.py`
  - `backend/narrative.py`
  - `backend/app_server.py`
  - `backend/db.py`
- `node --check public/app.js` passed.
- Direct local prompt test confirmed robust background prompt output remains English and includes no-people constraints.

Server:

- Previous server PID `3156` was stopped.
- Server restarted:
  - PID: `3544`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## Create Story NameError Fix

User reported:

- Creating a story failed with:
  - `name 'story' is not defined`

Cause:

- `backend/narrative.py`
  - In `enrich_story_creation_payload(...)`, a leftover line called:
    - `story_language(story)`
  - That function has only `payload`, not a `story` variable.
  - This happened in the enrichment path used when initial character fields were missing.

Fix:

- Removed the invalid `story_language(story)` call.
- The function now uses the already normalized `payload["language"]` / payload context.

Validation:

- Python AST syntax check passed for:
  - `backend/narrative.py`
  - `backend/app_server.py`
  - `backend/prompts.py`
  - `backend/db.py`
- `node --check public/app.js` passed.
- Direct function test no longer raises `NameError`.
- Real HTTP smoke test passed:
  - `POST /api/stories` with minimal player/character data created a test story.
  - Result had 2 characters and 1 initial scene.
  - Test story `story_f7664729b6aa` was deleted afterward.

Server:

- Previous server PID `3544` was stopped.
- Server restarted:
  - PID: `7988`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## Initial Character Prompt Generation And Sprite Stage Motion

User requested:

1. In story creation, remove the visible `Prompt visual` field from initial characters.
   - The user should not see or edit it during creation.
   - It should stay empty in the wizard and be generated only when the story is actually created.
   - Initial prompt generation must use `Perfis de prompt por workbench`, matching the later `Gerar prompt` behavior.
2. Character entry/removal on the VN stage should be smoother.
   - Characters should slide in from the side according to their final position and fade in.
   - Characters leaving the scene should fade out and slide away.
3. Sprites should be horizontally closer to each other.
   - Later characters should not sit too far in the screen corners.
   - Slight overlap is acceptable because active speaker layering handles focus.
4. Active speaker should move visually forward.
   - Inspired by DreamRunner's `character-active` / `character-inactive` behavior.
   - Active character should become slightly larger and receive a soft shadow/highlight.

Changes implemented:

- `public/app.js`
  - Removed `Prompt visual` from the initial character creation cards.
  - `emptyCharacterDraft()` no longer includes `visual_prompt`.
  - `saveCreateDraft()` no longer reads `characters_{index}_visual_prompt`.
  - `createStory()` strips any stale `visual_prompt` from initial characters before sending payload.
  - Added sprite transition state:
    - `spriteRoster`
    - `spriteExitMap`
    - `spriteExitTimer`
  - `renderSprites(...)` now renders current and temporarily exiting sprites.
  - Added classes:
    - `character-active`
    - `character-inactive`
    - `entering`
    - `exiting`
  - Sprite state is cleared when switching stories or creating a new story.

- `backend/narrative.py`
  - Added `apply_creation_sprite_prompts(payload, settings)`.
  - Added `apply_character_sprite_prompt(character, settings, story_id=None, expression="neutral")`.
  - Initial story creation now generates final `visual_prompt` for player and initial characters after completion/enrichment.
  - This uses the same workbench profile flow as `Gerar prompt`:
    - `build_sprite_source_prompt(...)`
    - `generate_workbench_visual_prompt(...)`
    - fallback via `build_sprite_visual_prompt(...)`
  - Introduced characters also receive a final workbench-profile sprite prompt before being saved.

- `backend/app_server.py`
  - Manual character creation now also applies `apply_character_sprite_prompt(...)` before saving.

- `public/styles.css`
  - Sprite layer changed from flex distribution to absolute positioning.
  - Horizontal positions are closer to center:
    - left around 39%
    - center 50%
    - right around 61%
  - Active speaker:
    - z-index front layer
    - slight scale up
    - slight upward/forward movement
    - stronger drop shadow and subtle highlight
  - Inactive characters:
    - behind active speaker
    - dimmer and slightly smaller
  - Added enter/exit animations:
    - left enters/exits from the left
    - right enters/exits from the right
    - center fades/slides vertically
  - Mobile positions adjusted to keep sprites closer while avoiding extreme corners.

Validation:

- Python AST syntax check passed for:
  - `backend/narrative.py`
  - `backend/app_server.py`
  - `backend/db.py`
  - `backend/prompts.py`
- `node --check public/app.js` passed.
- Direct local prompt fallback test passed.
- Real HTTP story creation smoke test passed:
  - Created test story `story_6f074764eba8`.
  - Returned 2 characters and 1 initial scene.
  - Both characters received generated `visual_prompt` values.
  - Test story was deleted afterward.

Server:

- Previous server PID `7988` was stopped.
- Server restarted:
  - PID: `4180`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## Introduced Character Language Fix And Sprite Motion Tuning

User reported:

1. Adding a new character mid-story failed with:
   - `name 'language' is not defined`
2. Active speaker scale effect was too strong and abrupt.
3. Sprites were closer in a good way, but should be about 20% less close.
4. In `Aproximado` sprite view, sprites should sit about 15% higher.

Fixes:

- `backend/narrative.py`
  - In `enrich_introduced_character(...)`, added:
    - `language = story_language(story)`
  - This fixes the undefined `language` variable used by introduced-character prompt instructions.

- `public/styles.css`
  - Reduced active speaker scale:
    - from `1.045` to `1.022`
  - Reduced active upward movement:
    - from `-10px` to `-6px`
  - Softened active highlight/shadow slightly.
  - Made transform/filter transitions slower and smoother:
    - transform now `460ms cubic-bezier(0.16, 0.84, 0.24, 1)`
    - filter now `420ms cubic-bezier(0.16, 0.84, 0.24, 1)`
  - Opened sprite spacing about 20% from the previous closer layout:
    - desktop left/right from `39% / 61%` to `37% / 63%`
    - mobile left/right from `35% / 65%` to `32% / 68%`
  - Added `--sprite-close-lift` so `Aproximado` mode lifts sprites about `15%` without fighting the active-speaker forward movement.
  - Updated sprite enter/exit keyframes to include the close-mode lift variable.

Validation:

- Python AST syntax check passed for:
  - `backend/narrative.py`
  - `backend/app_server.py`
  - `backend/db.py`
  - `backend/prompts.py`
- `node --check public/app.js` passed.
- Direct introduced-character enrichment test passed without `NameError`.

Server:

- Previous server PID `4180` was stopped.
- Server restarted:
  - PID: `20396`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.

## App Renamed To TaleWeaver

User requested:

- Rename the application from the temporary `LocalDreamVN` name to:
  - `TaleWeaver`

Scope:

- The workspace folder remains `N:\VNApp` for now to avoid breaking local scripts, paths, and existing session references.
- The app/product name shown to users and used by runtime logs/assets is now `TaleWeaver`.

Changes implemented:

- `README.md`
  - Title and description now use `TaleWeaver`.
- `docs/MVP.md`
  - Title now uses `TaleWeaver MVP`.
- `public/index.html`
  - Browser title is now `TaleWeaver`.
- `public/app.js`
  - Top navigation brand is now `TaleWeaver`.
- `backend/app_server.py`
  - HTTP `server_version` is now `TaleWeaver/0.1`.
  - Console log prefix is now `[TaleWeaver]`.
  - Startup message is now `TaleWeaver running at ...`.
- `backend/comfy_client.py`
  - ComfyUI `SaveImage.filename_prefix` now uses `TaleWeaver`.
- `backend/__init__.py`
  - Package docstring now says `TaleWeaver backend package`.
- `iniciar_app.bat`
  - Startup message now says `Iniciando TaleWeaver...`.
- `SESSION_MEMORY.md`
  - Header and project name updated.
  - Previous temporary name preserved as historical context.

Validation:

- Python AST syntax check passed for:
  - `app.py`
  - `backend/app_server.py`
  - `backend/comfy_client.py`
- `node --check public/app.js` passed.
- Search confirmed no remaining `LocalDreamVN` occurrences in app code/docs except historical notes inside `SESSION_MEMORY.md`.
- `GET /` returns `<title>TaleWeaver</title>`.

Server:

- Previous server PID `20396` was stopped.
- Server restarted:
  - PID: `16468`
  - URL: `http://127.0.0.1:3000`
- `GET /api/health` returned `{ "ok": true }`.
