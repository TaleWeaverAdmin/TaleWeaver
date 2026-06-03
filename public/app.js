const state = {
  route: "dashboard",
  stories: [],
  activeStory: null,
  settings: null,
  ollamaModels: [],
  checkpoints: [],
  workbenches: [],
  visualStyles: [],
  logs: [],
  drawer: "",
  busy: false,
  status: "",
  modal: null,
  activeCharacterId: "",
  characterEditId: "",
  characterPromptExpanded: false,
  spriteViewMode: localStorage.getItem("spriteViewMode") || "distant",
  dialogueSceneId: "",
  dialogueIndex: 0,
  spriteRoster: [],
  spriteExitMap: {},
  spriteExitTimer: null,
  createStep: 0,
  createDraft: defaultCreateDraft(),
  styleEditingId: "",
  styleDraft: null,
  styleAdvanced: false,
  editMode: false,
  storySort: "recent",
};

const app = document.getElementById("app");

init();

function defaultCreateDraft(language = "pt-BR") {
  return {
    story_prompt: "",
    point_of_view: "first",
    title: "",
    genre: "",
    tone: "",
    visual_style: "anime visual novel",
    visual_style_id: "",
    content_rating: "Teen",
    language,
    lore: "",
    starting_location: "",
    starting_message: "",
    player_name: "",
    player_role: "",
    player_appearance: "",
    player_personality: "",
    player_background: "",
    player_goals: "",
    characters: [emptyCharacterDraft()],
  };
}

function emptyCharacterDraft() {
  return {
    name: "",
    role: "",
    species: "",
    gender: "",
    character_type: "",
    aliases: "",
    description: "",
    physical: "",
    personality: "",
    clothing: "",
    relationship: "",
  };
}

function applyDefaultVisualStyle(draft) {
  if (!draft || draft.visual_style_id || !state.visualStyles.length) return draft;
  const style = state.visualStyles[0];
  draft.visual_style_id = style.id;
  draft.visual_style = style.name || draft.visual_style;
  return draft;
}

function initials(value) {
  const words = String(value || "TW").trim().split(/\s+/).filter(Boolean);
  return words.slice(0, 2).map(word => word[0]?.toUpperCase() || "").join("") || "TW";
}

async function init() {
  await Promise.all([loadStories(), loadSettings(), loadVisualStyles()]);
  render();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Erro inesperado.");
  return data;
}

async function loadStories() {
  const data = await api("/api/stories");
  state.stories = data.stories || [];
}

async function loadStory(id) {
  if (state.activeStory?.id && state.activeStory.id !== id) {
    state.spriteRoster = [];
    state.spriteExitMap = {};
  }
  state.activeStory = await api(`/api/stories/${id}`);
}

async function loadSettings() {
  state.settings = await api("/api/settings");
  try {
    const data = await api("/api/ollama/models");
    state.ollamaModels = (data.models || []).map(model => model.name || model.model).filter(Boolean);
  } catch {
    state.ollamaModels = [];
  }
  try {
    const data = await api("/api/comfy/checkpoints");
    state.checkpoints = data.checkpoints || [];
  } catch {
    state.checkpoints = [];
  }
  try {
    const data = await api("/api/comfy/workbenches");
    state.workbenches = data.workbenches || [];
  } catch {
    state.workbenches = [];
  }
}

async function loadVisualStyles() {
  try {
    const data = await api("/api/visual-styles");
    state.visualStyles = data.styles || [];
  } catch {
    state.visualStyles = [];
  }
}

function setBusy(value, status = "") {
  state.busy = value;
  state.status = status;
  render();
}

function render() {
  app.innerHTML = `
    <div class="app-shell">
      ${renderTopnav()}
      ${state.route === "dashboard" ? renderDashboard() : ""}
      ${state.route === "create" ? renderCreateStory() : ""}
      ${state.route === "styles" ? renderVisualStyles() : ""}
      ${state.route === "settings" ? renderSettings() : ""}
      ${state.route === "logs" ? renderLogs() : ""}
      ${state.route === "play" ? renderPlay() : ""}
      ${state.drawer ? renderDrawer() : ""}
      ${state.modal ? renderModal() : ""}
      ${state.busy ? `<div class="status">${escapeHtml(state.status || "Processando...")}</div>` : ""}
    </div>
  `;
  bindEvents();
}

function renderTopnav() {
  return `
    <header class="topnav">
      <div class="brand">
        <strong>TaleWeaver</strong>
        <span>Biblioteca local de visual novels geradas por IA</span>
      </div>
      <nav class="nav-actions">
        <button data-action="dashboard">Histórias</button>
        <button data-action="styles">Estilos</button>
        <button data-action="settings">Config</button>
        <button data-action="logs">Logs</button>
        <button class="primary" data-action="create">Nova história</button>
      </nav>
    </header>
  `;
}

function renderSettings() {
  const settings = state.settings || {};
  return `
    <main class="page">
      <section class="view-title">
        <div>
          <h1>Configurações locais</h1>
          <p>Defina conexões com Ollama e ComfyUI para geração de texto e imagens.</p>
        </div>
      </section>
      <form id="settings-form">
        <section class="panel">
          <h2>Ollama</h2>
          <div class="form-grid">
            ${valueField("ollama_url", "URL do Ollama", settings.ollama_url || "http://127.0.0.1:11434")}
            <div class="field">
              <label for="default_language">Idioma padrao de geracao</label>
              <select id="default_language" name="default_language">
                <option value="pt-BR" ${(settings.default_language || "pt-BR") === "pt-BR" ? "selected" : ""}>Portugues (pt-BR)</option>
                <option value="en-US" ${settings.default_language === "en-US" ? "selected" : ""}>English (en-US)</option>
              </select>
            </div>
            <div class="field">
              <label for="ollama_model">Modelo de texto</label>
              <select id="ollama_model" name="ollama_model">
                ${renderOllamaModelOptions(settings.ollama_model || "mistral-nemo")}
              </select>
            </div>
            ${valueField("ollama_temperature", "Temperatura", settings.ollama_temperature ?? 0.8)}
            ${valueField("ollama_context", "Contexto máximo", settings.ollama_context ?? 8192)}
          </div>
        </section>
        <div class="notice">
          Modelos Ollama detectados: ${state.ollamaModels.length ? state.ollamaModels.map(escapeHtml).join(", ") : "nenhum, verifique se o Ollama está aberto."}
        </div>
        <section class="panel">
          <h2>ComfyUI</h2>
          <div class="form-grid">
            ${valueField("comfy_url", "URL do ComfyUI", settings.comfy_url || "http://127.0.0.1:8188")}
            ${valueField("comfy_root", "Pasta do ComfyUI", settings.comfy_root || "N:\\SillyTavern\\ComfyUI")}
            ${valueField("comfy_workflows_dir", "Pasta de workbenches", settings.comfy_workflows_dir || "N:\\SillyTavern\\ComfyUI\\user\\default\\workflows")}
            <div class="field">
              <label for="comfy_checkpoint">Checkpoint padrão</label>
              <select id="comfy_checkpoint" name="comfy_checkpoint">
                ${state.checkpoints.length
                  ? state.checkpoints.map(name => `<option value="${escapeAttr(name)}" ${name === settings.comfy_checkpoint ? "selected" : ""}>${escapeHtml(name)}</option>`).join("")
                  : `<option value="${escapeAttr(settings.comfy_checkpoint || "")}">${escapeHtml(settings.comfy_checkpoint || "ComfyUI offline")}</option>`}
              </select>
            </div>
            <div class="field">
              <label for="comfy_background_workbench">Workbench de cenario</label>
              <select id="comfy_background_workbench" name="comfy_background_workbench">
                ${renderWorkbenchOptions(settings.comfy_background_workbench || "")}
              </select>
            </div>
            ${valueField("image_width", "Background largura", settings.image_width ?? 1536)}
            ${valueField("image_height", "Background altura", settings.image_height ?? 864)}
            ${valueField("background_steps", "Background steps", settings.background_steps ?? 28)}
            ${valueField("background_cfg", "Background CFG", settings.background_cfg ?? 6.5)}
            ${valueField("comfy_sampler", "Sampler", settings.comfy_sampler || "dpmpp_2m_sde_gpu")}
            ${valueField("comfy_scheduler", "Scheduler", settings.comfy_scheduler || "karras")}
          </div>
          <div class="notice">
            Checkpoints detectados: ${state.checkpoints.length ? state.checkpoints.map(escapeHtml).join(", ") : "nenhum, verifique se o ComfyUI está aberto."}
          </div>
          <div class="notice">
            Workbenches detectados: ${renderWorkbenchNotice()}
          </div>
          ${renderPromptProfiles(settings)}
        </section>
        <div class="mini-actions">
          <button type="button" data-action="test-comfy">Testar ComfyUI</button>
          <button type="button" data-action="dashboard">Voltar</button>
          <button class="primary" type="submit">Salvar configurações</button>
        </div>
      </form>
    </main>
  `;
}

function renderVisualStyles() {
  const draft = currentStyleDraft();
  return `
    <main class="page">
      <section class="view-title">
        <div>
          <h1>Estilos visuais</h1>
          <p>Defina como os sprites serao gerados em cada historia.</p>
        </div>
        <button class="primary" data-action="new-style">Novo estilo</button>
      </section>
      <section class="style-manager">
        <div class="panel style-list-panel">
          <h2>Estilos</h2>
          <div class="style-list">
            ${state.visualStyles.length ? state.visualStyles.map(style => `
              <button type="button" class="style-list-item ${style.id === state.styleEditingId ? "active" : ""}" data-action="edit-style" data-id="${escapeAttr(style.id)}">
                ${renderStyleCover(style)}
                <span>${escapeHtml(style.name || "Estilo sem nome")}</span>
                <small>${escapeHtml(style.sprite_workbench || "Workflow simples interno")}</small>
              </button>
            `).join("") : `<div class="empty-state">Nenhum estilo criado.</div>`}
          </div>
        </div>
        <form id="style-form" class="panel style-editor-panel">
          <div class="section-head">
            <h2>${state.styleEditingId ? "Editar estilo" : "Novo estilo"}</h2>
            ${state.styleEditingId ? `<button class="danger" type="button" data-action="delete-style" data-id="${escapeAttr(state.styleEditingId)}">Excluir</button>` : ""}
          </div>
          <div class="style-editor-layout">
            <div class="style-cover-picker">
              ${renderStyleCover(draft, true)}
              <label class="file-picker">
                <span>Escolher imagem</span>
                <input type="file" id="style_cover_file" name="cover_file" accept="image/png,image/jpeg,image/webp">
              </label>
              <small>A imagem sera copiada para a pasta do projeto.</small>
            </div>
            <div class="form-grid">
              ${styleField("name", "Nome do estilo", draft.name || "")}
              <div class="field">
                <label for="style_sprite_workbench">ComfyUI Workflow</label>
                <select id="style_sprite_workbench" name="sprite_workbench">
                  ${renderWorkbenchOptions(draft.sprite_workbench || "")}
                </select>
              </div>
              ${styleTextarea("prompt_prefix", "Prefixo do prompt", draft.prompt_prefix || "")}
              ${styleTextarea("prompt_suffix", "Sufixo do prompt", draft.prompt_suffix || "")}
              ${styleTextarea("negative_prompt", "Prompt negativo", draft.negative_prompt || "")}
              <label class="check-row full">
                <input type="checkbox" id="style_advanced_toggle" ${state.styleAdvanced ? "checked" : ""}>
                <span>Campos avancados</span>
              </label>
              ${state.styleAdvanced ? renderStyleAdvancedFields(draft) : ""}
            </div>
          </div>
          <div class="mini-actions">
            <button type="button" data-action="dashboard">Voltar</button>
            <button class="primary" type="submit">Salvar estilo</button>
          </div>
        </form>
      </section>
    </main>
  `;
}

function currentStyleDraft() {
  if (state.styleDraft) return state.styleDraft;
  const style = state.visualStyles.find(item => item.id === state.styleEditingId);
  if (style) return cloneStyleDraft(style);
  return emptyVisualStyleDraft();
}

function emptyVisualStyleDraft() {
  return {
    name: "",
    prompt_prefix: "",
    prompt_suffix: "",
    negative_prompt: "",
    sprite_workbench: "",
    cover_url: "",
    advanced_settings: {},
  };
}

function cloneStyleDraft(style) {
  return {
    ...emptyVisualStyleDraft(),
    ...style,
    advanced_settings: { ...(style.advanced_settings || {}) },
  };
}

function renderStyleCover(style, large = false) {
  const name = style?.name || "Estilo";
  const cover = style?.cover_url || "";
  return `
    <div class="${large ? "style-cover-large" : "style-cover-thumb"}">
      ${cover ? `<img src="${escapeAttr(cover)}" alt="${escapeAttr(name)}">` : `<strong>${escapeHtml(initials(name))}</strong>`}
    </div>
  `;
}

function styleField(name, label, value) {
  return `
    <div class="field">
      <label for="style_${name}">${label}</label>
      <input id="style_${name}" name="${name}" value="${escapeAttr(value || "")}">
    </div>
  `;
}

function styleTextarea(name, label, value) {
  return `
    <div class="field full">
      <label for="style_${name}">${label}</label>
      <textarea id="style_${name}" name="${name}" rows="4">${escapeHtml(value || "")}</textarea>
    </div>
  `;
}

function renderStyleAdvancedFields(draft) {
  const advanced = draft.advanced_settings || {};
  const fields = advancedFieldNamesForWorkbench(draft.sprite_workbench || "");
  if (!fields.length) {
    return `<div class="notice full">Nenhum campo avancado detectado para este workflow.</div>`;
  }
  return fields.map(field => renderAdvancedStyleField(field, advanced[field] ?? defaultAdvancedStyleValue(field))).join("");
}

function renderAdvancedStyleField(field, value) {
  const labels = {
    width: "Sprite largura",
    height: "Sprite altura",
    steps: "Steps",
    cfg: "CFG",
    sampler_name: "Sampler",
    scheduler: "Scheduler",
    ckpt_name: "Checkpoint",
  };
  if (field === "ckpt_name") {
    const current = value || state.settings?.comfy_checkpoint || "";
    const options = state.checkpoints.length ? state.checkpoints : [current].filter(Boolean);
    return `
      <div class="field">
        <label for="style_adv_${field}">${labels[field]}</label>
        <select id="style_adv_${field}" name="advanced_${field}">
          ${options.map(name => `<option value="${escapeAttr(name)}" ${name === current ? "selected" : ""}>${escapeHtml(name)}</option>`).join("")}
        </select>
      </div>
    `;
  }
  return `
    <div class="field">
      <label for="style_adv_${field}">${labels[field] || field}</label>
      <input id="style_adv_${field}" name="advanced_${field}" value="${escapeAttr(value || "")}">
    </div>
  `;
}

function advancedFieldNamesForWorkbench(workbenchId) {
  const allowed = ["width", "height", "steps", "cfg", "sampler_name", "scheduler", "ckpt_name"];
  if (!workbenchId) return allowed;
  const workbench = state.workbenches.find(item => item.id === workbenchId);
  const inputs = new Set(workbench?.inputs || []);
  return allowed.filter(field => inputs.has(field));
}

function defaultAdvancedStyleValue(field) {
  const settings = state.settings || {};
  const defaults = {
    width: settings.sprite_width ?? 1024,
    height: settings.sprite_height ?? 1536,
    steps: settings.sprite_steps ?? 24,
    cfg: settings.sprite_cfg ?? 5.0,
    sampler_name: settings.sprite_sampler || "euler_ancestral",
    scheduler: settings.sprite_scheduler || "normal",
    ckpt_name: settings.comfy_checkpoint || "",
  };
  return defaults[field] ?? "";
}

function renderOllamaModelOptions(currentModel) {
  const models = state.ollamaModels.length ? state.ollamaModels : [currentModel];
  const unique = [...new Set(models.filter(Boolean))];
  if (currentModel && !unique.includes(currentModel)) unique.unshift(currentModel);
  return unique.map(name => (
    `<option value="${escapeAttr(name)}" ${name === currentModel ? "selected" : ""}>${escapeHtml(name)}</option>`
  )).join("");
}

function renderWorkbenchOptions(currentWorkbench) {
  const options = [`<option value="" ${!currentWorkbench ? "selected" : ""}>Workflow simples interno</option>`];
  const workbenches = [...state.workbenches];
  if (currentWorkbench && !workbenches.some(item => item.id === currentWorkbench)) {
    workbenches.unshift({
      id: currentWorkbench,
      name: currentWorkbench,
      format: "missing",
      executable: false,
    });
  }
  return options.concat(workbenches.map(workbench => {
    const selected = workbench.id === currentWorkbench ? "selected" : "";
    const format = workbench.format || "unknown";
    const suffix = workbench.executable ? "API" : format.toUpperCase();
    return `<option value="${escapeAttr(workbench.id)}" ${selected}>${escapeHtml(workbench.name)} (${escapeHtml(suffix)})</option>`;
  })).join("");
}

function renderWorkbenchNotice() {
  if (!state.workbenches.length) return "nenhum JSON encontrado na pasta de workbenches.";
  return state.workbenches.map(workbench => {
    const status = workbench.executable ? "pronto" : `nao executavel: ${workbench.format}`;
    return `${escapeHtml(workbench.id)} [${escapeHtml(status)}]`;
  }).join(", ");
}

function renderPromptProfiles(settings) {
  const profiles = settings.comfy_prompt_profiles || {};
  const workbenches = state.workbenches.filter(workbench => workbench.executable);
  if (!workbenches.length) return "";
  return `
    <div class="prompt-profile-block">
      <h3>Perfis de prompt por workbench</h3>
      <div class="prompt-profile-grid">
        ${workbenches.map(workbench => {
          const profile = profiles[workbench.id] || {};
          return `
            <section class="prompt-profile">
              <div class="profile-head">
                <strong>${escapeHtml(workbench.name)}</strong>
                <span>${escapeHtml(workbench.id)}</span>
              </div>
              <div class="field full">
                <label for="prompt_profile_style__${escapeAttr(workbench.id)}">Estilo de prompt</label>
                <textarea id="prompt_profile_style__${escapeAttr(workbench.id)}" name="prompt_profile_style__${escapeAttr(workbench.id)}" rows="5" placeholder="${escapeAttr(defaultPromptStylePlaceholder())}">${escapeHtml(profile.style || "")}</textarea>
              </div>
              <div class="field full">
                <label for="prompt_profile_example__${escapeAttr(workbench.id)}">Exemplo de prompt</label>
                <textarea id="prompt_profile_example__${escapeAttr(workbench.id)}" name="prompt_profile_example__${escapeAttr(workbench.id)}" rows="5" placeholder="${escapeAttr(defaultPromptExamplePlaceholder())}">${escapeHtml(profile.example || "")}</textarea>
              </div>
            </section>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

function defaultPromptStylePlaceholder() {
  return "Ex.: escreva em ingles natural, detalhado, sem lista curta de tags; descreva anatomia, rosto, cabelo, roupa, expressao, pose e enquadramento de sprite.";
}

function defaultPromptExamplePlaceholder() {
  return "Ex.: A tall, powerfully built man with light brown skin, broad shoulders, short gray hair, a rugged masculine face, intense focused expression, full-body visual novel sprite, standing front view, simple light gray background.";
}

async function loadLogs() {
  const suffix = state.activeStory ? `?story_id=${encodeURIComponent(state.activeStory.id)}&limit=120` : "?limit=120";
  const data = await api(`/api/logs${suffix}`);
  state.logs = data.logs || [];
}

function renderLogs() {
  return `
    <main class="page">
      <section class="view-title">
        <div>
          <h1>Logs de API</h1>
          <p>Veja o que foi enviado para Ollama/ComfyUI e o que voltou.</p>
        </div>
        <button data-action="refresh-logs">Atualizar</button>
      </section>
      ${state.logs.length ? state.logs.map(renderLogEntry).join("") : `<div class="empty-state">Nenhum log registrado ainda.</div>`}
    </main>
  `;
}

function renderLogEntry(log) {
  return `
    <article class="log-entry">
      <div class="log-head">
        <strong>${escapeHtml(log.provider)} / ${escapeHtml(log.operation)}</strong>
        <span class="pill">${escapeHtml(log.status)}</span>
        <span class="small-text">${formatDate(log.created_at)}</span>
      </div>
      ${log.error ? `<div class="notice">${escapeHtml(log.error)}</div>` : ""}
      <details>
        <summary>Request</summary>
        <pre>${escapeHtml(JSON.stringify(log.request_payload, null, 2))}</pre>
      </details>
      <details>
        <summary>Response</summary>
        <pre>${escapeHtml(JSON.stringify(log.response_payload, null, 2))}</pre>
      </details>
    </article>
  `;
}

function renderDashboard() {
  const stories = sortedStories();
  return `
    <main class="page stories-page">
      <section class="view-title compact-title">
        <button class="danger" type="button" data-action="stop-app">Parar app</button>
        <div>
          <h1>Histórias neste dispositivo</h1>
          <p>Crie, continue e organize visual novels geradas localmente.</p>
        </div>
        <button class="primary" data-action="create">Criar história</button>
      </section>
      <section class="library-toolbar">
        <div class="library-tabs">
          <button class="active" type="button">Histórias locais</button>
          <button type="button" data-action="create">Criar</button>
        </div>
        <label class="sort-control">
          <span>Ordenar</span>
          <select id="story-sort" aria-label="Ordenar histórias">
            <option value="recent" ${state.storySort === "recent" ? "selected" : ""}>Recentes</option>
            <option value="title" ${state.storySort === "title" ? "selected" : ""}>Título</option>
            <option value="scenes" ${state.storySort === "scenes" ? "selected" : ""}>Mais cenas</option>
          </select>
        </label>
      </section>
      <section class="story-grid library-grid">
        ${renderQuickCreateCard()}
        ${stories.map(renderStoryCard).join("")}
      </section>
      ${state.stories.length ? "" : `<div class="empty-state slim-empty">Nenhuma história criada ainda.</div>`}
    </main>
  `;
}

function sortedStories() {
  const stories = [...state.stories];
  if (state.storySort === "title") {
    return stories.sort((left, right) => String(left.title || "").localeCompare(String(right.title || ""), "pt-BR"));
  }
  if (state.storySort === "scenes") {
    return stories.sort((left, right) => Number(right.scene_count || 0) - Number(left.scene_count || 0));
  }
  return stories.sort((left, right) => Number(right.updated_at || 0) - Number(left.updated_at || 0));
}

function renderQuickCreateCard() {
  return `
    <article class="story-card quick-story-card">
      <div class="quick-card-frame">
        <span class="quick-spark">✦</span>
        <span class="eyebrow">Criação rápida</span>
        <h2>Jogue sua própria história</h2>
        <p>Escreva poucas palavras. O Ollama transforma a ideia em detalhes editáveis antes de começar.</p>
      </div>
      <div class="quick-create-box">
        <textarea id="quick-story-prompt" maxlength="8000" placeholder="Ex.: um deus recém desperto precisa guiar uma tribo antiga sem revelar sua verdadeira origem"></textarea>
        <div class="quick-create-actions">
          <span class="small-text">Local neste dispositivo</span>
          <button class="primary" data-action="quick-create-story">Gerar história</button>
        </div>
      </div>
    </article>
  `;
}

function renderStoryCard(story) {
  const archived = story.status === "archived";
  return `
    <article class="story-card library-story-card">
      <div class="story-cover">
        <img src="${escapeAttr(story.cover_url || "/assets/placeholder-bg.svg")}" alt="">
        <span>${escapeHtml(story.status)}</span>
      </div>
      <div class="story-body">
        <h2>${escapeHtml(story.title)}</h2>
        <div class="meta">
          <span class="pill">${escapeHtml(story.genre || "sem gênero")}</span>
          <span class="pill">${escapeHtml(story.visual_style || "sem estilo")}</span>
        </div>
        <p class="story-description">${escapeHtml(story.summary || "A história ainda não começou.")}</p>
        <div class="story-stats">
          <span>${Number(story.scene_count || 0)} cenas</span>
          <span>${Number(story.character_count || 0)} personagens</span>
          <span>${escapeHtml(formatDate(story.updated_at))}</span>
        </div>
      </div>
      <div class="card-actions story-card-actions">
        <button class="primary" data-action="open-story" data-id="${story.id}">Continuar</button>
        <button data-action="duplicate-story" data-id="${story.id}">Duplicar</button>
        <button data-action="toggle-archive-story" data-id="${story.id}" data-status="${archived ? "active" : "archived"}">${archived ? "Restaurar" : "Arquivar"}</button>
        <button class="danger" data-action="delete-story" data-id="${story.id}" data-title="${escapeAttr(story.title)}">Excluir</button>
      </div>
    </article>
  `;
}

function renderCreateStory() {
  const draft = state.createDraft || defaultCreateDraft();
  return `
    <main class="page">
      <section class="view-title">
        <div>
          <h1>Nova história</h1>
          <p>Monte a base em três etapas. Campos vazios podem ser preenchidos depois.</p>
        </div>
      </section>
      <form id="story-form">
        ${renderCreateStepper()}
        ${state.createStep === 0 ? renderCreateStoryDetails(draft) : ""}
        ${state.createStep === 1 ? renderCreateCharacters(draft) : ""}
        ${state.createStep === 2 ? renderCreateVisualStyle(draft) : ""}
        ${renderCreateFooter()}
      </form>
    </main>
  `;
}

function renderCreateStepper() {
  const steps = [
    ["Detalhes", "document"],
    ["Personagens", "users"],
    ["Visual", "sparkles"],
  ];
  return `
    <div class="create-stepper">
      ${steps.map(([label], index) => `
        <button
          type="button"
          class="${index === state.createStep ? "active" : ""} ${index < state.createStep ? "done" : ""}"
          data-action="go-create-step"
          data-step="${index}"
        >
          <span>${index + 1}</span>
          ${label}
        </button>
      `).join("")}
    </div>
  `;
}

function renderCreateStoryDetails(draft) {
  return `
    <section class="panel wizard-panel">
      <h2>Detalhes da história</h2>
      <div class="field full">
        <label>Ponto de vista</label>
        <div class="segmented">
          ${povButton("first", "Primeira pessoa", draft.point_of_view)}
          ${povButton("third", "Terceira pessoa", draft.point_of_view)}
          ${povButton("narrator", "Narrador", draft.point_of_view)}
        </div>
      </div>
      <div class="form-grid">
        <div class="field full">
          <div class="field-head">
            <label for="story_prompt">Ideia inicial</label>
            <button type="button" class="improve-btn" data-action="generate-story-seed">Gerar base</button>
          </div>
          <textarea id="story_prompt" name="story_prompt" rows="4" maxlength="8000" placeholder="Descreva o conflito, o tipo de protagonista e o clima da história.">${escapeHtml(draft.story_prompt)}</textarea>
        </div>
        ${draftField("title", "Nome da história", "text", "Crônicas de Elaria", draft.title)}
        ${draftField("genre", "Gênero", "text", "fantasia, mistério", draft.genre)}
        ${draftField("tone", "Tom", "text", "dramático, melancólico", draft.tone)}
        ${draftField("content_rating", "Classificação", "text", "Teen", draft.content_rating)}
        ${draftField("language", "Idioma", "text", "pt-BR", draft.language)}
        ${draftField("starting_location", "Local inicial", "text", "biblioteca sob chuva", draft.starting_location)}
        ${draftTextarea("lore", "Lore e mundo", "lore", "Regras do mundo, conflitos, facções, cidades, magia, tecnologia...", draft.lore, true)}
        ${draftTextarea("starting_message", "Mensagem inicial", "lore", "Primeira situação que deve abrir a história.", draft.starting_message, true)}
      </div>
    </section>
  `;
}

function povButton(value, label, current) {
  return `<button type="button" class="${current === value ? "active" : ""}" data-action="select-pov" data-value="${value}">${label}</button>`;
}

function renderCreateCharacters(draft) {
  const playerFilled = countFilled([
    draft.player_name,
    draft.player_role,
    draft.player_appearance,
    draft.player_personality,
    draft.player_background,
    draft.player_goals,
  ]);
  return `
    <section class="characters-wizard">
      <article class="character-editor-card player-character-card">
        <div class="character-editor-head">
          <div class="character-avatar">${escapeHtml((draft.player_name || "J").slice(0, 1).toUpperCase())}</div>
          <div>
            <span class="eyebrow">Personagem principal</span>
            <h2>${escapeHtml(draft.player_name || "Jogador")}</h2>
          </div>
          <span class="field-count">${playerFilled}/6</span>
        </div>
        <div class="form-grid">
          ${draftField("player_name", "Nome", "text", "Ari", draft.player_name)}
          ${draftField("player_role", "Papel na história", "text", "aprendiz exilado", draft.player_role)}
          ${draftTextarea("player_appearance", "Aparência", "character", "", draft.player_appearance)}
          ${draftTextarea("player_personality", "Personalidade", "character", "", draft.player_personality)}
          ${draftTextarea("player_background", "História pessoal", "character", "", draft.player_background)}
          ${draftTextarea("player_goals", "Objetivos e medos", "character", "", draft.player_goals)}
        </div>
      </article>
      <section class="character-list-panel">
        <div class="section-head">
          <div>
            <span class="eyebrow">Elenco inicial</span>
            <h2>Personagens</h2>
          </div>
          <button type="button" data-action="add-initial-character">Adicionar personagem</button>
        </div>
        <div class="repeat-list character-draft-list">
          ${(draft.characters || []).map(renderInitialCharacterDraft).join("")}
        </div>
      </section>
    </section>
  `;
}

function renderInitialCharacterDraft(character, index) {
  const filled = countFilled([
    character.name,
    character.role,
    character.species,
    character.gender,
    character.character_type,
    character.aliases,
    character.description,
    character.physical,
    character.personality,
    character.clothing,
    character.relationship,
  ]);
  return `
    <div class="character-draft-card">
      <div class="character-editor-head compact">
        <div class="character-avatar secondary">${escapeHtml((character.name || String(index + 1)).slice(0, 1).toUpperCase())}</div>
        <div>
          <h3>${escapeHtml(character.name || `Personagem ${index + 1}`)}</h3>
          <span>${filled}/11 campos</span>
        </div>
        ${(state.createDraft.characters || []).length > 1 ? `<button type="button" class="danger" data-action="remove-initial-character" data-index="${index}">Remover</button>` : ""}
      </div>
      <div class="form-grid">
        ${draftField(`characters_${index}_name`, "Nome", "text", "", character.name)}
        ${draftField(`characters_${index}_role`, "Papel", "text", "", character.role)}
        ${draftField(`characters_${index}_species`, "Especie", "text", "", character.species)}
        ${draftField(`characters_${index}_gender`, "Genero", "text", "", character.gender)}
        ${draftField(`characters_${index}_character_type`, "Tipo", "text", "", character.character_type)}
        ${draftField(`characters_${index}_aliases`, "Aliases", "text", "", character.aliases)}
        ${draftTextarea(`characters_${index}_description`, "Descricao", "character", "", character.description)}
        ${draftTextarea(`characters_${index}_physical`, "Descrição física", "character", "", character.physical)}
        ${draftTextarea(`characters_${index}_personality`, "Personalidade", "character", "", character.personality)}
        ${draftTextarea(`characters_${index}_clothing`, "Vestimenta", "character", "", character.clothing)}
        ${draftTextarea(`characters_${index}_relationship`, "Relação com protagonista", "character", "", character.relationship)}
      </div>
    </div>
  `;
}

function countFilled(values) {
  return values.filter(value => String(value || "").trim()).length;
}

function renderCreateVisualStyle(draft) {
  const styles = [
    ["anime visual novel", "Anime VN", "Personagens limpos, cores vivas, composição de romance visual."],
    ["painterly fantasy visual novel", "Fantasia painterly", "Ambientes dramáticos, luz suave e textura de ilustração."],
    ["retro anime visual novel", "Anime retrô", "Contraste alto, atmosfera noventista e enquadramentos simples."],
    ["cinematic realistic visual novel", "Cinemático realista", "Iluminação de filme, materiais naturais e clima sério."],
    ["dark comic visual novel", "Quadrinhos escuro", "Sombras marcadas, contornos fortes e energia pulp."],
  ];
  return `
    <section class="panel wizard-panel">
      <h2>Estilo visual</h2>
      <div class="style-grid">
        ${styles.map(([value, title, description]) => `
          <button type="button" class="style-card ${draft.visual_style === value ? "active" : ""}" data-action="select-style" data-value="${escapeAttr(value)}">
            <span>${escapeHtml(title)}</span>
            <small>${escapeHtml(description)}</small>
          </button>
        `).join("")}
      </div>
      <div class="form-grid">
        ${draftField("visual_style", "Estilo final", "text", "anime visual novel", draft.visual_style)}
      </div>
      <div class="review-strip">
        <strong>${escapeHtml(draft.title || "História sem título")}</strong>
        <span>${escapeHtml(draft.genre || "sem gênero")}</span>
        <span>${escapeHtml((draft.characters || []).filter(item => item.name).length)} personagem(ns)</span>
      </div>
    </section>
  `;
}

function renderCreateVisualStyle(draft) {
  const styles = state.visualStyles || [];
  return `
    <section class="panel wizard-panel">
      <h2>Estilo visual</h2>
      <div class="style-grid">
        ${styles.length ? styles.map(style => `
          <button type="button" class="style-card ${draft.visual_style_id === style.id ? "active" : ""}" data-action="select-style" data-id="${escapeAttr(style.id)}" data-value="${escapeAttr(style.name || "")}">
            ${renderStyleCover(style, true)}
            <span>${escapeHtml(style.name || "Estilo")}</span>
            <small>${escapeHtml(style.sprite_workbench || "Workflow simples interno")}</small>
          </button>
        `).join("") : `<div class="empty-state">Crie um estilo no menu Estilos antes de finalizar a historia.</div>`}
      </div>
      <div class="form-grid">
        <input type="hidden" name="visual_style_id" value="${escapeAttr(draft.visual_style_id || "")}">
        ${draftField("visual_style", "Estilo final", "text", "anime visual novel", draft.visual_style)}
      </div>
      <div class="review-strip">
        <strong>${escapeHtml(draft.title || "Historia sem titulo")}</strong>
        <span>${escapeHtml(draft.genre || "sem genero")}</span>
        <span>${escapeHtml((draft.characters || []).filter(item => item.name).length)} personagem(ns)</span>
      </div>
    </section>
  `;
}

function renderCreateFooter() {
  return `
    <div class="wizard-footer">
      <button type="button" data-action="dashboard">Cancelar</button>
      <div>
        ${state.createStep > 0 ? `<button type="button" data-action="create-step-back">Voltar</button>` : ""}
        ${state.createStep < 2 ? `<button class="primary" type="button" data-action="create-step-next">Próximo</button>` : `<button class="primary" type="submit">Criar e jogar</button>`}
      </div>
    </div>
  `;
}

function renderPlay() {
  const story = state.activeStory;
  if (!story) return "";
  const scene = latestScene(story);
  syncDialogueState(scene);
  const dialogueSequence = getDialogueSequence(scene);
  const currentDialogue = dialogueSequence[state.dialogueIndex] || null;
  const dialogueComplete = !dialogueSequence.length || state.dialogueIndex >= dialogueSequence.length - 1;
  const currentSpeaker = currentDialogue && normalizeName(currentDialogue.character) !== "narrador" ? currentDialogue.character : "";
  const activeSpeaker = isCharacterOnScreen(scene, currentSpeaker) ? currentSpeaker : "";
  const background = scene ? findSceneBackground(scene) : null;
  return `
    <main class="vn-view">
      <div class="stage" ${background?.url ? `style="background-image: linear-gradient(to bottom, rgba(0,0,0,0.02), rgba(0,0,0,0.48)), url('${escapeAttr(background.url)}')"` : ""}></div>
      <div class="vn-toolbar">
        <div>
          <button data-action="dashboard">Sair</button>
          <button data-drawer="lore">Menu</button>
          <button class="${state.editMode ? "primary" : ""}" data-action="toggle-edit-mode">Edit</button>
          <button data-action="register-memory">Register</button>
          <button data-drawer="history">Histórico</button>
          <button data-drawer="characters">Personagens</button>
          <button data-action="depict-scene">Depict</button>
          <label class="sprite-view-select">
            <span>Sprites</span>
            <select id="sprite-view-mode">
              <option value="distant" ${state.spriteViewMode === "distant" ? "selected" : ""}>Distante</option>
              <option value="close" ${state.spriteViewMode === "close" ? "selected" : ""}>Aproximado</option>
            </select>
          </label>
        </div>
        <div>
          <button data-action="logs">Logs</button>
          <button data-action="regenerate-scene">Redo</button>
          <button class="primary" data-action="continue" ${state.busy || !dialogueComplete ? "disabled" : ""}>Continue</button>
        </div>
      </div>
      <div class="sprite-layer">
        ${renderSprites(scene, activeSpeaker)}
      </div>
      <section class="vn-dialogue">
        ${renderInteractionBlock(scene, currentDialogue, dialogueComplete)}
        ${state.editMode ? renderSceneEditPanel(scene) : ""}
        <div class="choices ${dialogueComplete ? "" : "hidden"}">
          ${(scene?.choices || []).map(choice => `<button data-action="choose" data-choice="${escapeAttr(choice)}">${escapeHtml(choice)}</button>`).join("")}
        </div>
        <div class="input-row ${dialogueComplete ? "" : "hidden"}">
          <div class="prompt-box">
            <textarea id="custom-action" maxlength="5000" placeholder="Escreva uma ação, fala ou direção para a IA..." ${state.busy ? "disabled" : ""}></textarea>
            <span class="input-count">0/5000</span>
          </div>
          <button data-action="continue" ${state.busy || !dialogueComplete ? "disabled" : ""}>Continuar</button>
          <button class="primary" data-action="send-custom" ${state.busy ? "disabled" : ""}>Enviar</button>
        </div>
      </section>
    </main>
  `;
}

function renderInteractionBlock(scene, currentDialogue, dialogueComplete) {
  if (!scene) {
    return `
      <div class="dialogue-box narrator">
        <div class="dialogue-content">
          <div class="scene-text">Clique em continuar para gerar a primeira resposta.</div>
        </div>
      </div>
    `;
  }
  const dialogue = currentDialogue || { character: "Narrador", text: scene.scene_text || "Aguardando a proxima resposta." };
  const isNarrator = normalizeName(dialogue.character) === "narrador";
  return `
    <div class="dialogue-box ${isNarrator ? "narrator" : "character"}">
      ${isNarrator ? "" : renderDialogueNameplate(scene, dialogue)}
      <div class="dialogue-content">
        <p class="active-dialogue-text">${escapeHtml(dialogue.text || "")}</p>
        ${dialogueComplete ? "" : `
          <button class="dialogue-next" type="button" data-action="next-dialogue" aria-label="Proxima fala">
            <span aria-hidden="true">›</span>
          </button>
        `}
      </div>
    </div>
  `;
}

function renderDialogueNameplate(scene, dialogue) {
  const name = dialogue.character || "";
  const candidate = newCharacterCandidateForName(scene, name);
  return `
    <div class="dialogue-nameplate ${candidate ? "new-speaker" : ""}">
      <span>${escapeHtml(name)}</span>
      ${candidate ? `
        <button
          class="new-character-icon"
          type="button"
          data-action="introduce-character"
          data-name="${escapeAttr(name)}"
          title="Adicionar personagem"
          aria-label="Adicionar ${escapeAttr(name)} como personagem"
          ${state.busy ? "disabled" : ""}
        >
          <span aria-hidden="true"></span>
        </button>
      ` : ""}
    </div>
  `;
}

function renderDialogueLine(dialogue) {
  return `
    <div class="dialogue-line ${normalizeName(dialogue.character) === "narrador" ? "narrator" : ""}">
      <span class="dialogue-speaker">${escapeHtml(dialogue.character || "Narrador")}</span>
      <span class="dialogue-text">${escapeHtml(dialogue.text || "")}</span>
    </div>
  `;
}

function syncDialogueState(scene) {
  const sceneId = scene?.id || "";
  if (state.dialogueSceneId !== sceneId) {
    state.dialogueSceneId = sceneId;
    state.dialogueIndex = 0;
  }
  const sequenceLength = getDialogueSequence(scene).length;
  if (!sequenceLength) {
    state.dialogueIndex = 0;
  } else if (state.dialogueIndex >= sequenceLength) {
    state.dialogueIndex = sequenceLength - 1;
  }
}

function getDialogueSequence(scene) {
  if (!scene) return [];
  const sequence = [];
  const sceneText = String(scene.scene_text || "").trim();
  const dialogues = scene.dialogues || [];
  const firstDialogueText = String(dialogues[0]?.text || "").trim();
  if (sceneText && sceneText !== firstDialogueText) {
    sequence.push({ character: "Narrador", expression: "neutral", text: sceneText });
  }
  dialogues.forEach(dialogue => {
    if (dialogue?.text) sequence.push(dialogue);
  });
  if (!sequence.length && sceneText) {
    sequence.push({ character: "Narrador", expression: "neutral", text: sceneText });
  }
  return sequence;
}

function isDialogueComplete(scene) {
  const sequence = getDialogueSequence(scene);
  return !sequence.length || state.dialogueIndex >= sequence.length - 1;
}

function isCharacterOnScreen(scene, name) {
  const key = normalizeName(name);
  if (!key) return false;
  return (scene?.characters_on_screen || []).some(character => normalizeName(character.name) === key);
}

function renderSceneEditPanel(scene) {
  if (!scene) {
    return `<div class="edit-panel"><p class="small-text">Gere uma cena antes de editar.</p></div>`;
  }
  return `
    <form class="edit-panel" id="scene-edit-form">
      <div class="form-grid">
        <div class="field">
          <label for="edit-title">Título da cena</label>
          <input id="edit-title" name="title" value="${escapeAttr(scene.title || "")}">
        </div>
        <div class="field">
          <label for="edit-background">Prompt de background</label>
          <input id="edit-background" name="background_prompt" value="${escapeAttr(scene.background_prompt || "")}">
        </div>
        <div class="field full">
          <label for="edit-scene-text">Narração</label>
          <textarea id="edit-scene-text" name="scene_text">${escapeHtml(scene.scene_text || "")}</textarea>
        </div>
        <div class="field full">
          <label for="edit-choices">Escolhas</label>
          <textarea id="edit-choices" name="choices">${escapeHtml((scene.choices || []).join("\n"))}</textarea>
        </div>
      </div>
      <div class="mini-actions">
        <button type="button" data-action="toggle-edit-mode">Cancelar</button>
        <button class="primary" type="submit">Salvar cena</button>
      </div>
    </form>
  `;
}

function renderSprites(scene, activeSpeaker = "") {
  const characters = getSpriteRenderItems(scene);
  if (!characters.length) return "";
  const viewMode = state.spriteViewMode === "close" ? "close" : "distant";
  const activeKey = normalizeName(activeSpeaker);
  return characters.map(item => {
    const character = item.character;
    const registeredCharacter = findStoryCharacter(character.name);
    if (!registeredCharacter) return "";
    const sprite = findCharacterSprite(character.name, character.expression);
    const characterKey = normalizeName(character.name);
    const focusClass = item.exiting
      ? "inactive character-inactive exiting"
      : activeKey
        ? (characterKey === activeKey ? "active character-active" : "inactive character-inactive")
        : "neutral";
    const motionClass = `${item.entering ? "entering" : ""} ${item.exiting ? "exiting" : ""}`.trim();
    const position = character.position || "center";
    if (sprite?.url) {
      return `
        <div class="scene-sprite-frame ${escapeAttr(position)} ${viewMode} ${focusClass} ${motionClass}">
          <img
            class="scene-sprite"
            src="${escapeAttr(sprite.url)}"
            alt="${escapeAttr(character.name)}"
            loading="eager"
            decoding="async"
          >
        </div>
      `;
    }
    return `
      <div class="sprite-standin ${escapeAttr(position)} ${focusClass} ${motionClass}">
        <div>
          <strong>${escapeHtml(character.name)}</strong>
          <span>${escapeHtml(character.expression || "neutral")}</span>
          <em>sprite pendente</em>
        </div>
      </div>
    `;
  }).join("");
}

function getSpriteRenderItems(scene) {
  const now = Date.now();
  const current = (scene?.characters_on_screen || []).map(character => ({
    key: normalizeName(character.name),
    character: { ...character },
  })).filter(item => item.key);
  const currentKeys = new Set(current.map(item => item.key));
  const previous = state.spriteRoster || [];

  previous.forEach(item => {
    if (!currentKeys.has(item.key) && !state.spriteExitMap[item.key]) {
      state.spriteExitMap[item.key] = {
        ...item,
        expires: now + 620,
      };
    }
  });

  const previousKeys = new Set(previous.map(item => item.key));
  const rendered = current.map(item => ({
    ...item,
    entering: !previousKeys.has(item.key) && !state.spriteExitMap[item.key],
    exiting: false,
  }));

  Object.entries(state.spriteExitMap).forEach(([key, item]) => {
    if (item.expires <= now || currentKeys.has(key)) {
      delete state.spriteExitMap[key];
      return;
    }
    rendered.push({ ...item, exiting: true, entering: false });
  });

  state.spriteRoster = current;
  scheduleSpriteExitCleanup();
  return rendered;
}

function scheduleSpriteExitCleanup() {
  if (state.spriteExitTimer || !Object.keys(state.spriteExitMap).length) return;
  state.spriteExitTimer = setTimeout(() => {
    state.spriteExitTimer = null;
    const now = Date.now();
    Object.entries(state.spriteExitMap).forEach(([key, item]) => {
      if (item.expires <= now) delete state.spriteExitMap[key];
    });
    render();
  }, 660);
}

function renderDrawer() {
  const title = {
    history: "Histórico",
    characters: "Personagens",
    lore: "Lore e memória",
  }[state.drawer] || "Painel";
  return `
    <aside class="side-drawer">
      <div class="drawer-head">
        <strong>${title}</strong>
        <button data-action="close-drawer">Fechar</button>
      </div>
      <div class="drawer-body">
        ${state.drawer === "history" ? renderHistoryDrawer() : ""}
        ${state.drawer === "characters" ? renderCharactersDrawer() : ""}
        ${state.drawer === "lore" ? renderLoreDrawer() : ""}
      </div>
    </aside>
  `;
}

function renderHistoryDrawer() {
  const scenes = state.activeStory?.scenes || [];
  if (!scenes.length) return `<div class="empty-state">Nenhuma cena ainda.</div>`;
  return scenes.slice().reverse().map(scene => `
    <article class="scene-card">
      <h3>Cena ${scene.scene_order}: ${escapeHtml(scene.title || "")}</h3>
      <p class="small-text">${escapeHtml(scene.scene_text || "")}</p>
      <div class="history-dialogues">
        ${(scene.dialogues || []).slice(0, 6).map(dialogue => `
          <p><strong>${escapeHtml(dialogue.character || "Narrador")}:</strong> ${escapeHtml(dialogue.text || "")}</p>
        `).join("")}
      </div>
      <div class="small-text">Escolhas: ${(scene.choices || []).map(escapeHtml).join(" | ")}</div>
    </article>
  `).join("");
}

function renderCharactersDrawerLegacy() {
  const characters = state.activeStory?.characters || [];
  return `
    <div class="character-drawer-toolbar">
      <div>
        <span class="eyebrow">Elenco</span>
        <strong>${characters.length} personagem(ns)</strong>
      </div>
      <button class="primary" data-action="manual-character">Adicionar personagem</button>
    </div>
    ${characters.length ? characters.map(character => `
      <article class="character-card profile-card">
        <div class="profile-media">
          ${renderCharacterPortrait(character)}
        </div>
        <div class="profile-body">
          <div class="profile-head">
            <div>
              <h3>${escapeHtml(character.name)}</h3>
              <span>${escapeHtml(character.role || "sem papel definido")}</span>
            </div>
            <span class="pill">${escapeHtml(character.importance)}</span>
          </div>
          <p class="small-text">${escapeHtml(character.physical || "Sem descrição física.")}</p>
          <p class="small-text">${escapeHtml(character.personality || "Sem personalidade.")}</p>
          ${character.relationship ? `<p class="relationship-line">${escapeHtml(character.relationship)}</p>` : ""}
          ${renderCharacterSpriteGallery(character)}
          <div class="card-actions">
            <button data-action="generate-sprite" data-character-id="${character.id}">Gerar sprite</button>
            <button data-action="refresh-sprite" data-character-id="${character.id}">Atualizar sprite</button>
          </div>
        </div>
      </article>
    `).join("") : `<div class="empty-state">Nenhum personagem cadastrado.</div>`}
  `;
}

function renderCharactersDrawer() {
  const characters = state.activeStory?.characters || [];
  if (!characters.length) {
    state.activeCharacterId = "";
    state.characterEditId = "";
  }
  if (characters.length && !characters.some(character => character.id === state.activeCharacterId)) {
    state.activeCharacterId = characters[0].id;
  }
  const active = characters.find(character => character.id === state.activeCharacterId) || characters[0];
  return `
    <div class="character-drawer-toolbar">
      <div>
        <span class="eyebrow">Elenco</span>
        <strong>${characters.length} personagem(ns)</strong>
      </div>
      <div class="character-drawer-actions">
        <button type="button" disabled>Appearance Designer</button>
        <button type="button" disabled>Add Character</button>
        <button type="button" disabled>Leave Scene</button>
      </div>
    </div>
    ${characters.length ? `
      <div class="character-workspace">
        <nav class="character-tabs" aria-label="Personagens">
          ${characters.map(character => `
            <button
              type="button"
              class="character-tab ${character.id === active?.id ? "active" : ""}"
              data-action="select-character-tab"
              data-character-id="${escapeAttr(character.id)}"
            >
              <span>${escapeHtml(character.name || "Sem nome")}</span>
              <small>${escapeHtml(character.character_type || character.role || character.importance || "personagem")}</small>
            </button>
          `).join("")}
        </nav>
        ${active ? renderCharacterDetail(active) : ""}
      </div>
    ` : `<div class="empty-state">Nenhum personagem cadastrado.</div>`}
  `;
}

function renderCharacterDetail(character) {
  if (state.characterEditId === character.id) return renderCharacterEditForm(character);
  return `
    <section class="character-detail">
      <div class="character-hero">
        <div class="profile-media character-portrait">
          ${renderCharacterPortrait(character)}
        </div>
        <div>
          <div class="profile-head">
            <div>
              <h3>${escapeHtml(character.name || "Sem nome")}</h3>
              <span>${escapeHtml(character.role || character.character_type || "sem papel definido")}</span>
            </div>
            <span class="pill">${escapeHtml(character.importance || "secondary")}</span>
          </div>
          <div class="character-action-row">
            <button data-action="edit-character" data-character-id="${escapeAttr(character.id)}">Editar</button>
            <button class="primary" data-action="refresh-sprite" data-character-id="${escapeAttr(character.id)}">Regenerate</button>
          </div>
        </div>
      </div>
      <div class="character-facts">
        ${characterFact("Especie", character.species)}
        ${characterFact("Genero", character.gender)}
        ${characterFact("Tipo", character.character_type)}
        ${characterFact("Aliases", character.aliases)}
      </div>
      ${characterSection("Descricao", character.description)}
      ${characterSection("Personalidade", character.personality)}
      ${characterSection("Aparencia fisica", character.physical)}
      ${characterSection("Vestimenta", character.clothing)}
      ${character.relationship ? characterSection("Relacao", character.relationship) : ""}
      ${renderCharacterPromptPanel(character, false)}
      ${renderCharacterSpriteGallery(character)}
    </section>
  `;
}

function renderCharacterEditForm(character) {
  return `
    <form id="character-edit-form" class="character-detail character-edit-form" data-character-id="${escapeAttr(character.id)}">
      <div class="character-edit-head">
        <div>
          <span class="eyebrow">Editar personagem</span>
          <h3>${escapeHtml(character.name || "Sem nome")}</h3>
        </div>
        <div class="character-action-row">
          <button type="button" data-action="cancel-character-edit">Cancelar</button>
          <button class="primary" type="submit">Salvar</button>
        </div>
      </div>
      <div class="character-form-grid">
        ${characterInput("name", "Nome", character.name)}
        ${characterInput("species", "Especie", character.species)}
        ${characterInput("gender", "Genero", character.gender)}
        ${characterInput("character_type", "Tipo", character.character_type)}
        ${characterInput("aliases", "Aliases", character.aliases, true)}
        ${characterInput("role", "Papel na historia", character.role, true)}
        ${characterTextarea("description", "Descricao", character.description)}
        ${characterTextarea("personality", "Personalidade", character.personality)}
        ${characterTextarea("physical", "Aparencia fisica", character.physical)}
        ${characterTextarea("clothing", "Vestimenta", character.clothing)}
        ${characterTextarea("relationship", "Relacao", character.relationship)}
      </div>
      ${renderCharacterPromptPanel(character, true)}
    </form>
  `;
}

function renderCharacterPromptPanel(character, editing) {
  const expanded = state.characterPromptExpanded;
  return `
    <section class="character-prompt-panel">
      <button type="button" class="prompt-toggle" data-action="toggle-character-prompt">
        <span>Prompt para Geracao de Imagem</span>
        <small>${expanded ? "Recolher" : "Expandir"}</small>
      </button>
      <button
        type="button"
        class="prompt-generate-btn"
        data-action="generate-character-image-prompt"
        data-character-id="${escapeAttr(character.id)}"
      >Gerar prompt</button>
      ${expanded ? `
        ${editing ? `
          <textarea name="visual_prompt" rows="8">${escapeHtml(character.visual_prompt || "")}</textarea>
        ` : `
          <pre>${escapeHtml(character.visual_prompt || "Nenhum prompt gerado.")}</pre>
        `}
      ` : editing ? `<input type="hidden" name="visual_prompt" value="${escapeAttr(character.visual_prompt || "")}">` : ""}
    </section>
  `;
}

function characterInput(name, label, value, full = false) {
  return `
    <div class="field ${full ? "full" : ""}">
      <label for="character-${name}">${label}</label>
      <input id="character-${name}" name="${name}" value="${escapeAttr(value || "")}">
    </div>
  `;
}

function characterTextarea(name, label, value) {
  return `
    <div class="field full">
      <label for="character-${name}">${label}</label>
      <textarea id="character-${name}" name="${name}" rows="4">${escapeHtml(value || "")}</textarea>
    </div>
  `;
}

function characterFact(label, value) {
  return `
    <div>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "-")}</strong>
    </div>
  `;
}

function characterSection(label, value) {
  return `
    <section class="character-info-section">
      <h4>${escapeHtml(label)}</h4>
      <p>${escapeHtml(value || "Nao informado.")}</p>
    </section>
  `;
}

function renderCharacterPortrait(character) {
  const sprite = getCharacterSprites(character.id)[0];
  if (sprite?.url) {
    return `<img src="${escapeAttr(sprite.url)}" alt="${escapeAttr(character.name)}">`;
  }
  return `<div class="profile-avatar">${escapeHtml((character.name || "?").slice(0, 1).toUpperCase())}</div>`;
}

function renderCharacterSpriteGallery(character) {
  const sprites = getCharacterSprites(character.id);
  if (!sprites.length) {
    return `<div class="sprite-empty">Nenhum sprite gerado ainda.</div>`;
  }
  return `
    <div class="character-sprites">
      ${sprites.slice(0, 8).map(sprite => `
        <figure class="sprite-thumb-card">
          <img src="${escapeAttr(sprite.url)}" alt="${escapeAttr(character.name)} ${escapeAttr(sprite.expression || "neutral")}">
          <figcaption>${escapeHtml(sprite.expression || "neutral")}</figcaption>
        </figure>
      `).join("")}
    </div>
  `;
}

function getCharacterSprites(characterId) {
  return (state.activeStory?.assets || []).filter(asset => (
    asset.asset_type === "sprite" &&
    asset.character_id === characterId &&
    asset.url
  ));
}

function renderLoreDrawer() {
  const story = state.activeStory;
  const memory = story?.memory_entries || [];
  const loreEntries = story?.lore_entries || [];
  return `
    <section class="panel lore-editor-panel">
      <div class="entry-card-head">
        <h2>Lore base</h2>
      </div>
      <form id="story-lore-form">
        <div class="field">
          <label for="story-lore">Contexto principal</label>
          <textarea id="story-lore" name="lore" rows="7">${escapeHtml(story?.lore || "")}</textarea>
        </div>
        <div class="mini-actions">
          <button class="primary" type="submit">Salvar lore</button>
        </div>
      </form>
    </section>
    <section class="panel">
      <h2>Resumo</h2>
      <p class="small-text">${escapeHtml(story?.summary || "Sem resumo.")}</p>
    </section>
    <section class="panel">
      <div class="entry-card-head">
        <h2>Entradas de lore</h2>
        <button data-action="add-lore-entry">Adicionar</button>
      </div>
      ${loreEntries.length ? loreEntries.map(entry => `
        <article class="scene-card entry-card">
          <div class="entry-card-head">
            <div>
              <h3>${escapeHtml(entry.title || "Lore")}</h3>
              <span class="small-text">${escapeHtml(entry.entry_type || "note")}</span>
            </div>
            <div class="card-actions">
              <button data-action="edit-lore" data-id="${escapeAttr(entry.id)}">Editar</button>
              <button data-action="delete-lore" data-id="${escapeAttr(entry.id)}" data-title="${escapeAttr(entry.title || "Lore")}">Excluir</button>
            </div>
          </div>
          <p class="small-text">${escapeHtml(entry.content)}</p>
        </article>
      `).join("") : `<div class="empty-state">Nenhuma entrada de lore registrada.</div>`}
    </section>
    <section class="panel">
      <div class="entry-card-head">
        <h2>Memoria</h2>
        <button data-action="register-memory">Registrar</button>
      </div>
      ${memory.length ? memory.map(entry => `
        <article class="scene-card entry-card">
          <div class="entry-card-head">
            <div>
              <h3>${escapeHtml(entry.entry_type)}</h3>
              <span class="small-text">Importancia ${escapeHtml(String(entry.importance || 1))}</span>
            </div>
            <div class="card-actions">
              <button data-action="edit-memory" data-id="${escapeAttr(entry.id)}">Editar</button>
              <button data-action="delete-memory" data-id="${escapeAttr(entry.id)}">Excluir</button>
            </div>
          </div>
          <p class="small-text">${escapeHtml(entry.content)}</p>
        </article>
      `).join("") : `<div class="empty-state">Nenhuma memoria registrada.</div>`}
    </section>
  `;
}

function renderModal() {
  if (state.modal.type === "character") {
    const c = state.modal.character || {};
    return `
      <div class="modal-backdrop">
        <form class="modal" id="character-form">
          <h2>${state.modal.generated ? "Cadastrar personagem detectado" : "Novo personagem"}</h2>
          <div class="form-grid">
            ${modalInput("name", "Nome", c.display_name || c.name || c.temporary_name || "")}
            ${modalInput("species", "Especie", c.species || "")}
            ${modalInput("gender", "Genero", c.gender || "")}
            ${modalInput("character_type", "Tipo narrativo", c.character_type || c.type || "")}
            ${modalInput("aliases", "Apelidos / titulos", c.aliases || "")}
            ${modalInput("role", "Papel", c.suggested_role || c.role || "")}
            ${modalTextarea("description", "Descricao narrativa", c.description || c.suggested_description || "")}
            ${modalTextarea("clothing", "Vestimenta", c.suggested_clothing || c.clothing || c.outfit || "")}
            ${modalTextarea("speech_style", "Estilo de fala", c.suggested_speech_style || c.speech_style || "")}
            ${modalTextarea("physical", "Aparencia fisica", c.suggested_physical || c.physical || c.appearance || "")}
            ${modalTextarea("personality", "Personalidade", c.suggested_personality || c.personality || "")}
            ${modalTextarea("relationship", "Relacao com a cena/protagonista", c.suggested_relationship || c.reason || c.relationship || "")}
            ${modalTextarea("visual_prompt", "Prompt visual", c.suggested_visual_prompt || c.visual_prompt || "")}
          </div>
          <div class="mini-actions">
            <button type="button" data-action="close-modal">Cancelar</button>
            <button class="primary" type="submit">Salvar personagem</button>
          </div>
        </form>
      </div>
    `;
  }
  if (state.modal.type === "memory") {
    return `
      <div class="modal-backdrop">
        <form class="modal" id="memory-form">
          <h2>Registrar informação</h2>
          <div class="form-grid">
            <div class="field">
              <label for="memory-entry-type">Tipo</label>
              <select id="memory-entry-type" name="entry_type">
                <option value="fact">Fato</option>
                <option value="goal">Objetivo</option>
                <option value="note">Nota</option>
              </select>
            </div>
            <div class="field">
              <label for="memory-importance">Importância</label>
              <select id="memory-importance" name="importance">
                <option value="3">Normal</option>
                <option value="5">Alta</option>
                <option value="1">Baixa</option>
              </select>
            </div>
            <div class="field full">
              <label for="memory-content">Conteúdo</label>
              <textarea id="memory-content" name="content" rows="5" placeholder="Ex.: Luna prometeu nunca abrir a porta vermelha."></textarea>
            </div>
          </div>
          <div class="mini-actions">
            <button type="button" data-action="close-modal">Cancelar</button>
            <button class="primary" type="submit">Salvar memória</button>
          </div>
        </form>
      </div>
    `;
  }
  if (state.modal.type === "memoryEdit") {
    const entry = state.modal.entry || {};
    const selectedType = entry.entry_type || "fact";
    const selectedImportance = String(entry.importance || 3);
    return `
      <div class="modal-backdrop">
        <form class="modal" id="memory-edit-form">
          <h2>Editar memoria</h2>
          <div class="form-grid">
            <div class="field">
              <label for="edit-memory-entry-type">Tipo</label>
              <select id="edit-memory-entry-type" name="entry_type">
                <option value="fact" ${selectedType === "fact" ? "selected" : ""}>Fato</option>
                <option value="goal" ${selectedType === "goal" ? "selected" : ""}>Objetivo</option>
                <option value="note" ${selectedType === "note" ? "selected" : ""}>Nota</option>
                <option value="summary" ${selectedType === "summary" ? "selected" : ""}>Resumo</option>
              </select>
            </div>
            <div class="field">
              <label for="edit-memory-importance">Importancia</label>
              <select id="edit-memory-importance" name="importance">
                <option value="3" ${selectedImportance === "3" ? "selected" : ""}>Normal</option>
                <option value="5" ${selectedImportance === "5" ? "selected" : ""}>Alta</option>
                <option value="1" ${selectedImportance === "1" ? "selected" : ""}>Baixa</option>
              </select>
            </div>
            <div class="field full">
              <label for="edit-memory-content">Conteudo</label>
              <textarea id="edit-memory-content" name="content" rows="5">${escapeHtml(entry.content || "")}</textarea>
            </div>
          </div>
          <div class="mini-actions">
            <button type="button" data-action="close-modal">Cancelar</button>
            <button class="primary" type="submit">Salvar memoria</button>
          </div>
        </form>
      </div>
    `;
  }
  if (state.modal.type === "lore") {
    const entry = state.modal.entry || {};
    const selectedType = entry.entry_type || "note";
    return `
      <div class="modal-backdrop">
        <form class="modal" id="lore-form">
          <h2>${entry.id ? "Editar lore" : "Nova entrada de lore"}</h2>
          <div class="form-grid">
            <div class="field">
              <label for="lore-title">Titulo</label>
              <input id="lore-title" name="title" value="${escapeAttr(entry.title || "")}">
            </div>
            <div class="field">
              <label for="lore-entry-type">Tipo</label>
              <select id="lore-entry-type" name="entry_type">
                <option value="world" ${selectedType === "world" ? "selected" : ""}>Mundo</option>
                <option value="location" ${selectedType === "location" ? "selected" : ""}>Local</option>
                <option value="faction" ${selectedType === "faction" ? "selected" : ""}>Faccao</option>
                <option value="rule" ${selectedType === "rule" ? "selected" : ""}>Regra</option>
                <option value="note" ${selectedType === "note" ? "selected" : ""}>Nota</option>
              </select>
            </div>
            <div class="field full">
              <label for="lore-content">Conteudo</label>
              <textarea id="lore-content" name="content" rows="7">${escapeHtml(entry.content || "")}</textarea>
            </div>
          </div>
          <div class="mini-actions">
            <button type="button" data-action="close-modal">Cancelar</button>
            <button class="primary" type="submit">Salvar lore</button>
          </div>
        </form>
      </div>
    `;
  }
  return "";
}

function bindEvents() {
  document.querySelectorAll("[data-action]").forEach(element => {
    element.addEventListener("click", handleAction);
  });
  document.querySelectorAll("[data-drawer]").forEach(element => {
    element.addEventListener("click", () => {
      state.drawer = element.dataset.drawer;
      if (state.drawer === "characters") {
        const characters = state.activeStory?.characters || [];
        state.activeCharacterId = state.activeCharacterId || characters[0]?.id || "";
        state.characterEditId = "";
      }
      render();
    });
  });
  const form = document.getElementById("story-form");
  if (form) form.addEventListener("submit", createStory);
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) settingsForm.addEventListener("submit", saveSettings);
  const styleForm = document.getElementById("style-form");
  if (styleForm) styleForm.addEventListener("submit", saveVisualStyle);
  const styleWorkbench = document.getElementById("style_sprite_workbench");
  if (styleWorkbench) {
    styleWorkbench.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      render();
    });
  }
  const styleAdvancedToggle = document.getElementById("style_advanced_toggle");
  if (styleAdvancedToggle) {
    styleAdvancedToggle.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      state.styleAdvanced = styleAdvancedToggle.checked;
      render();
    });
  }
  const characterForm = document.getElementById("character-form");
  if (characterForm) characterForm.addEventListener("submit", saveModalCharacter);
  const characterEditForm = document.getElementById("character-edit-form");
  if (characterEditForm) characterEditForm.addEventListener("submit", saveCharacterEdit);
  const memoryForm = document.getElementById("memory-form");
  if (memoryForm) memoryForm.addEventListener("submit", saveMemoryEntry);
  const memoryEditForm = document.getElementById("memory-edit-form");
  if (memoryEditForm) memoryEditForm.addEventListener("submit", saveMemoryEdit);
  const loreForm = document.getElementById("lore-form");
  if (loreForm) loreForm.addEventListener("submit", saveLoreEntry);
  const storyLoreForm = document.getElementById("story-lore-form");
  if (storyLoreForm) storyLoreForm.addEventListener("submit", saveStoryLore);
  const sceneEditForm = document.getElementById("scene-edit-form");
  if (sceneEditForm) sceneEditForm.addEventListener("submit", saveSceneEdit);
  const storySort = document.getElementById("story-sort");
  if (storySort) {
    storySort.addEventListener("change", () => {
      state.storySort = storySort.value;
      render();
    });
  }
  const spriteViewMode = document.getElementById("sprite-view-mode");
  if (spriteViewMode) {
    spriteViewMode.addEventListener("change", () => {
      state.spriteViewMode = spriteViewMode.value;
      localStorage.setItem("spriteViewMode", state.spriteViewMode);
      render();
    });
  }
  const customAction = document.getElementById("custom-action");
  if (customAction) {
    customAction.addEventListener("input", () => {
      const counter = document.querySelector(".input-count");
      if (counter) counter.textContent = `${customAction.value.length}/5000`;
    });
  }
}

async function handleAction(event) {
  const action = event.currentTarget.dataset.action;
  if (action === "dashboard") {
    state.route = "dashboard";
    state.drawer = "";
    await loadStories();
    render();
  }
  if (action === "create") {
    await loadVisualStyles();
    state.createDraft = defaultCreateDraft(state.settings?.default_language || "pt-BR");
    applyDefaultVisualStyle(state.createDraft);
    state.createStep = 0;
    state.route = "create";
    render();
  }
  if (action === "quick-create-story") {
    const prompt = document.getElementById("quick-story-prompt")?.value || "";
    state.createDraft = defaultCreateDraft(state.settings?.default_language || "pt-BR");
    applyDefaultVisualStyle(state.createDraft);
    state.createDraft.story_prompt = prompt.trim();
    state.createStep = 0;
    state.route = "create";
    render();
    if (prompt.trim()) await generateStorySeed();
  }
  if (action === "stop-app") stopApp();
  if (action === "settings") {
    await loadSettings();
    state.route = "settings";
    render();
  }
  if (action === "styles") {
    await Promise.all([loadVisualStyles(), loadSettings()]);
    state.route = "styles";
    state.styleEditingId = state.styleEditingId || state.visualStyles[0]?.id || "";
    state.styleDraft = null;
    render();
  }
  if (action === "new-style") {
    state.styleEditingId = "";
    state.styleDraft = emptyVisualStyleDraft();
    state.styleAdvanced = false;
    render();
  }
  if (action === "edit-style") {
    state.styleEditingId = event.currentTarget.dataset.id || "";
    const style = state.visualStyles.find(item => item.id === state.styleEditingId);
    state.styleDraft = style ? cloneStyleDraft(style) : emptyVisualStyleDraft();
    state.styleAdvanced = false;
    render();
  }
  if (action === "delete-style") deleteVisualStyle(event.currentTarget.dataset.id);
  if (action === "logs") {
    await loadLogs();
    state.route = "logs";
    state.drawer = "";
    render();
  }
  if (action === "refresh-logs") {
    await loadLogs();
    render();
  }
  if (action === "test-comfy") testComfy();
  if (action === "improve-field") improveField(event.currentTarget);
  if (action === "open-story") {
    await loadStory(event.currentTarget.dataset.id);
    state.route = "play";
    state.editMode = false;
    state.dialogueSceneId = "";
    state.dialogueIndex = 0;
    render();
  }
  if (action === "go-create-step") goCreateStep(Number(event.currentTarget.dataset.step));
  if (action === "create-step-next") goCreateStep(state.createStep + 1);
  if (action === "create-step-back") goCreateStep(state.createStep - 1);
  if (action === "select-pov") {
    saveCreateDraft();
    state.createDraft.point_of_view = event.currentTarget.dataset.value;
    render();
  }
  if (action === "select-style") {
    saveCreateDraft();
    const styleId = event.currentTarget.dataset.id || "";
    const style = state.visualStyles.find(item => item.id === styleId);
    state.createDraft.visual_style_id = styleId;
    state.createDraft.visual_style = style?.name || event.currentTarget.dataset.value || state.createDraft.visual_style;
    render();
  }
  if (action === "generate-story-seed") generateStorySeed();
  if (action === "add-initial-character") addInitialCharacterForm();
  if (action === "remove-initial-character") removeInitialCharacterForm(Number(event.currentTarget.dataset.index));
  if (action === "close-drawer") {
    state.drawer = "";
    render();
  }
  if (action === "toggle-edit-mode") {
    state.editMode = !state.editMode;
    render();
  }
  if (action === "register-memory") {
    state.modal = { type: "memory" };
    render();
  }
  if (action === "edit-memory") {
    const entry = findMemoryEntry(event.currentTarget.dataset.id);
    if (entry) {
      state.modal = { type: "memoryEdit", entry };
      render();
    }
  }
  if (action === "delete-memory") deleteMemoryEntry(event.currentTarget.dataset.id);
  if (action === "add-lore-entry") {
    state.modal = { type: "lore", entry: {} };
    render();
  }
  if (action === "edit-lore") {
    const entry = findLoreEntry(event.currentTarget.dataset.id);
    if (entry) {
      state.modal = { type: "lore", entry };
      render();
    }
  }
  if (action === "delete-lore") {
    deleteLoreEntry(event.currentTarget.dataset.id, event.currentTarget.dataset.title);
  }
  if (action === "depict-scene") depictCurrentScene();
  if (action === "next-dialogue") {
    const sequence = getDialogueSequence(latestScene(state.activeStory));
    state.dialogueIndex = Math.min(state.dialogueIndex + 1, Math.max(0, sequence.length - 1));
    render();
  }
  if (action === "continue") generateScene("");
  if (action === "send-custom") generateScene(document.getElementById("custom-action")?.value || "");
  if (action === "choose") generateScene(event.currentTarget.dataset.choice || "");
  if (action === "regenerate-scene") generateScene("Regenerar a cena mantendo a continuidade, mas melhorando ritmo e clareza.");
  if (action === "open-new-character") openDetectedCharacter(Number(event.currentTarget.dataset.index));
  if (action === "introduce-character") introduceNewCharacter(event.currentTarget.dataset.name);
  if (action === "select-character-tab") {
    state.activeCharacterId = event.currentTarget.dataset.characterId || "";
    state.characterEditId = "";
    state.characterPromptExpanded = false;
    render();
  }
  if (action === "edit-character") {
    state.characterEditId = event.currentTarget.dataset.characterId || "";
    render();
  }
  if (action === "cancel-character-edit") {
    state.characterEditId = "";
    render();
  }
  if (action === "toggle-character-prompt") {
    state.characterPromptExpanded = !state.characterPromptExpanded;
    render();
  }
  if (action === "generate-character-image-prompt") {
    generateCharacterImagePrompt(event.currentTarget.dataset.characterId);
  }
  if (action === "manual-character") {
    state.modal = { type: "character", character: {}, generated: false };
    render();
  }
  if (action === "close-modal") {
    state.modal = null;
    render();
  }
  if (action === "generate-bg") generateBackground();
  if (action === "generate-sprite") generateSprite(event.currentTarget.dataset.characterId);
  if (action === "refresh-sprite") refreshSprite(event.currentTarget.dataset.characterId);
  if (action === "duplicate-story") duplicateStory(event.currentTarget.dataset.id);
  if (action === "toggle-archive-story") {
    updateStoryStatus(event.currentTarget.dataset.id, event.currentTarget.dataset.status);
  }
  if (action === "delete-story") {
    deleteStory(event.currentTarget.dataset.id, event.currentTarget.dataset.title);
  }
}

async function stopApp() {
  if (!confirm("Parar o servidor local do app?")) return;
  setBusy(true, "Parando app...");
  try {
    await api("/api/app/shutdown", { method: "POST", body: JSON.stringify({}) });
    state.status = "App parado. Pode fechar esta aba.";
    render();
  } catch (error) {
    alert(error.message);
    setBusy(false);
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const numeric = new Set([
    "ollama_temperature",
    "ollama_context",
    "image_width",
    "image_height",
    "sprite_width",
    "sprite_height",
    "background_steps",
    "background_cfg",
    "sprite_steps",
    "sprite_cfg",
  ]);
  const payload = {};
  for (const [key, value] of form.entries()) {
    if (key.startsWith("prompt_profile_style__") || key.startsWith("prompt_profile_example__")) continue;
    payload[key] = numeric.has(key) ? Number(value) : value;
  }
  payload.comfy_prompt_profiles = collectPromptProfiles(form);
  setBusy(true, "Salvando configurações...");
  try {
    state.settings = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
    await loadSettings();
    alert("Configurações salvas.");
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveVisualStyle(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = collectStyleDraft(form);
  const coverFile = document.getElementById("style_cover_file")?.files?.[0] || null;
  if (!payload.name.trim()) {
    alert("Informe o nome do estilo.");
    return;
  }
  setBusy(true, "Salvando estilo...");
  try {
    const saved = state.styleEditingId
      ? await api(`/api/visual-styles/${state.styleEditingId}`, { method: "PATCH", body: JSON.stringify(payload) })
      : await api("/api/visual-styles", { method: "POST", body: JSON.stringify(payload) });
    let finalStyle = saved;
    if (coverFile) {
      const upload = new FormData();
      upload.append("image", coverFile);
      finalStyle = await uploadStyleCover(saved.id, upload);
    }
    await loadVisualStyles();
    state.styleEditingId = finalStyle.id;
    state.styleDraft = cloneStyleDraft(finalStyle);
    alert("Estilo salvo.");
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function uploadStyleCover(styleId, formData) {
  const response = await fetch(`/api/visual-styles/${encodeURIComponent(styleId)}/cover`, {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Erro ao enviar imagem.");
  return data;
}

function collectStyleDraft(form) {
  const data = form ? new FormData(form) : new FormData();
  const current = currentStyleDraft();
  const advanced = state.styleAdvanced ? {} : { ...(current.advanced_settings || {}) };
  if (state.styleAdvanced) {
    for (const [key, value] of data.entries()) {
      if (!key.startsWith("advanced_")) continue;
      const field = key.replace("advanced_", "");
      if (String(value || "").trim()) {
        advanced[field] = ["width", "height", "steps"].includes(field) ? Number(value) : (field === "cfg" ? Number(value) : value);
      }
    }
  }
  return {
    ...current,
    name: String(data.get("name") || "").trim(),
    prompt_prefix: String(data.get("prompt_prefix") || "").trim(),
    prompt_suffix: String(data.get("prompt_suffix") || "").trim(),
    negative_prompt: String(data.get("negative_prompt") || "").trim(),
    sprite_workbench: String(data.get("sprite_workbench") || "").trim(),
    advanced_settings: advanced,
  };
}

async function deleteVisualStyle(styleId) {
  if (!styleId) return;
  const style = state.visualStyles.find(item => item.id === styleId);
  if (!confirm(`Excluir o estilo "${style?.name || styleId}"? Historias existentes manterao apenas o nome do estilo.`)) return;
  setBusy(true, "Excluindo estilo...");
  try {
    await api(`/api/visual-styles/${styleId}`, { method: "DELETE" });
    await loadVisualStyles();
    state.styleEditingId = state.visualStyles[0]?.id || "";
    state.styleDraft = null;
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function testComfy() {
  setBusy(true, "Testando ComfyUI...");
  try {
    const status = await api("/api/comfy/status");
    const gpu = status.devices?.[0]?.name || "dispositivo não informado";
    alert(`ComfyUI online. GPU: ${gpu}`);
  } catch (error) {
    alert(`ComfyUI não respondeu: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function collectPromptProfiles(form) {
  const profiles = {};
  for (const workbench of state.workbenches.filter(item => item.executable)) {
    const style = (form.get(`prompt_profile_style__${workbench.id}`) || "").trim();
    const example = (form.get(`prompt_profile_example__${workbench.id}`) || "").trim();
    if (style || example) {
      profiles[workbench.id] = { style, example };
    }
  }
  return profiles;
}

function addInitialCharacterForm() {
  saveCreateDraft();
  state.createDraft.characters.push(emptyCharacterDraft());
  render();
}

function removeInitialCharacterForm(index) {
  saveCreateDraft();
  state.createDraft.characters.splice(index, 1);
  if (!state.createDraft.characters.length) state.createDraft.characters.push(emptyCharacterDraft());
  render();
}

function goCreateStep(step) {
  saveCreateDraft();
  state.createStep = Math.max(0, Math.min(2, step));
  render();
}

function saveCreateDraft() {
  const form = document.getElementById("story-form");
  if (!form) return;
  const data = new FormData(form);
  const draft = state.createDraft || defaultCreateDraft();
  const fields = [
    "story_prompt",
    "title",
    "genre",
    "tone",
    "visual_style_id",
    "visual_style",
    "content_rating",
    "language",
    "lore",
    "starting_location",
    "starting_message",
    "player_name",
    "player_role",
    "player_appearance",
    "player_personality",
    "player_background",
    "player_goals",
  ];
  fields.forEach(fieldName => {
    if (data.has(fieldName)) draft[fieldName] = data.get(fieldName) || "";
  });
  if (state.createStep === 1) {
    draft.characters = (draft.characters || []).map((character, index) => ({
      ...character,
      name: data.has(`characters_${index}_name`) ? data.get(`characters_${index}_name`) : character.name,
      role: data.has(`characters_${index}_role`) ? data.get(`characters_${index}_role`) : character.role,
      species: data.has(`characters_${index}_species`) ? data.get(`characters_${index}_species`) : character.species,
      gender: data.has(`characters_${index}_gender`) ? data.get(`characters_${index}_gender`) : character.gender,
      character_type: data.has(`characters_${index}_character_type`) ? data.get(`characters_${index}_character_type`) : character.character_type,
      aliases: data.has(`characters_${index}_aliases`) ? data.get(`characters_${index}_aliases`) : character.aliases,
      description: data.has(`characters_${index}_description`) ? data.get(`characters_${index}_description`) : character.description,
      physical: data.has(`characters_${index}_physical`) ? data.get(`characters_${index}_physical`) : character.physical,
      personality: data.has(`characters_${index}_personality`) ? data.get(`characters_${index}_personality`) : character.personality,
      clothing: data.has(`characters_${index}_clothing`) ? data.get(`characters_${index}_clothing`) : character.clothing,
      relationship: data.has(`characters_${index}_relationship`) ? data.get(`characters_${index}_relationship`) : character.relationship,
    }));
  }
  state.createDraft = draft;
}

async function generateStorySeed() {
  saveCreateDraft();
  const prompt = (state.createDraft.story_prompt || "").trim();
  if (!prompt) {
    alert("Escreva uma ideia antes de gerar a base da história.");
    return;
  }
  setBusy(true, "Gerando base da história com Ollama...");
  try {
    const seed = await api("/api/ai/story-seed", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    });
    state.createDraft = {
      ...state.createDraft,
      story_prompt: prompt,
      title: seed.title || state.createDraft.title,
      genre: seed.genre || state.createDraft.genre,
      tone: seed.tone || state.createDraft.tone,
      visual_style: seed.visual_style || state.createDraft.visual_style,
      content_rating: seed.content_rating || state.createDraft.content_rating,
      language: seed.language || state.createDraft.language,
      lore: seed.lore || state.createDraft.lore,
      starting_location: seed.starting_location || state.createDraft.starting_location,
      starting_message: seed.starting_message || state.createDraft.starting_message,
      player_name: seed.player_character?.name || state.createDraft.player_name,
      player_role: seed.player_character?.role || state.createDraft.player_role,
      player_appearance: seed.player_character?.appearance || state.createDraft.player_appearance,
      player_personality: seed.player_character?.personality || state.createDraft.player_personality,
      player_background: seed.player_character?.background || state.createDraft.player_background,
      player_goals: seed.player_character?.goals || state.createDraft.player_goals,
      characters: seed.characters?.length ? seed.characters : state.createDraft.characters,
    };
    if (seed.warning) console.warn(seed.warning);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function improveField(button) {
  const targetId = button.dataset.target;
  const target = document.getElementById(targetId);
  if (!target) return;

  const original = target.value.trim();
  if (!original) {
    alert("Escreva algo no campo antes de pedir para melhorar.");
    target.focus();
    return;
  }

  const previousLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Melhorando...";
  try {
    const result = await api("/api/ai/improve", {
      method: "POST",
      body: JSON.stringify({
        text: original,
        field_type: button.dataset.fieldType || "descricao",
        field_label: button.dataset.label || target.name || target.id,
        story_context: collectFormContext(target.closest("form")),
      }),
    });
    const currentTarget = document.getElementById(targetId);
    if (currentTarget) {
      currentTarget.value = result.improved_text || original;
      currentTarget.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (result.warning) console.warn(result.warning);
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = previousLabel;
  }
}

function collectFormContext(form) {
  if (!form) return {};
  const data = new FormData(form);
  const keys = ["title", "genre", "tone", "visual_style", "lore", "player_name", "player_role", "name", "role"];
  const context = {};
  keys.forEach(key => {
    const value = data.get(key);
    if (value) context[key] = value;
  });
  return context;
}

async function createStory(event) {
  event.preventDefault();
  saveCreateDraft();
  const draft = state.createDraft || defaultCreateDraft();
  const characters = (draft.characters || [])
    .filter(character => character.name)
    .map(({ visual_prompt, ...character }) => character);
  const loreParts = [
    draft.lore,
    draft.point_of_view ? `Ponto de vista: ${draft.point_of_view}` : "",
    draft.starting_location ? `Local inicial: ${draft.starting_location}` : "",
    draft.starting_message ? `Mensagem inicial: ${draft.starting_message}` : "",
    draft.story_prompt ? `Ideia original: ${draft.story_prompt}` : "",
  ].filter(Boolean);
  const payload = {
    title: draft.title || "História sem título",
    genre: draft.genre,
    tone: draft.tone,
    visual_style: draft.visual_style,
    visual_style_id: draft.visual_style_id,
    content_rating: draft.content_rating,
    language: draft.language || "pt-BR",
    starting_location: draft.starting_location,
    starting_message: draft.starting_message,
    story_prompt: draft.story_prompt,
    lore: loreParts.join("\n\n"),
    player_character: {
      name: draft.player_name,
      role: draft.player_role,
      appearance: draft.player_appearance,
      personality: draft.player_personality,
      background: draft.player_background,
      goals: draft.player_goals,
    },
    characters,
  };
  setBusy(true, "Criando história...");
  try {
    state.spriteRoster = [];
    state.spriteExitMap = {};
    state.activeStory = await api("/api/stories", { method: "POST", body: JSON.stringify(payload) });
    state.route = "play";
    render();
    await generateInitialStoryAssets();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function duplicateStory(storyId) {
  if (!storyId) return;
  setBusy(true, "Duplicando historia...");
  try {
    await api(`/api/stories/${storyId}/duplicate`, { method: "POST", body: JSON.stringify({}) });
    await loadStories();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function updateStoryStatus(storyId, status) {
  if (!storyId || !status) return;
  setBusy(true, status === "archived" ? "Arquivando historia..." : "Restaurando historia...");
  try {
    await api(`/api/stories/${storyId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await loadStories();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function deleteStory(storyId, title) {
  if (!storyId) return;
  const ok = confirm(`Excluir "${title || "esta historia"}"? Esta acao remove cenas, personagens, memoria e assets salvos.`);
  if (!ok) return;

  setBusy(true, "Excluindo historia...");
  try {
    const result = await api(`/api/stories/${storyId}`, { method: "DELETE" });
    if (result.delete_error) {
      alert(`Historia excluida, mas a pasta local nao foi removida: ${result.delete_error}`);
    }
    if (state.activeStory?.id === storyId) {
      state.activeStory = null;
      state.drawer = "";
      state.route = "dashboard";
    }
    await loadStories();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function generateScene(userInput) {
  if (!state.activeStory) return;
  setBusy(true, "Gerando resposta com Ollama...");
  try {
    state.activeStory = await api(`/api/stories/${state.activeStory.id}/generate-scene`, {
      method: "POST",
      body: JSON.stringify({ user_input: userInput, generate_images: true }),
    });
    if (state.activeStory.auto_background?.mode === "queued") {
      await waitForAsset(state.activeStory.auto_background.asset_id, "Gerando cenário no ComfyUI...");
      await loadStory(state.activeStory.id);
    }
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function openDetectedCharacter(index) {
  const scene = latestScene(state.activeStory);
  const detected = getNewCharacterCandidates(scene);
  state.modal = { type: "character", character: detected[index] || {}, generated: true };
  render();
}

async function introduceNewCharacter(name) {
  const story = state.activeStory;
  const scene = latestScene(story);
  const candidate = newCharacterCandidateForName(scene, name);
  if (!story || !scene || !candidate) return;

  setBusy(true, `Criando ficha de ${name}...`);
  try {
    const result = await api(`/api/stories/${story.id}/characters/introduce`, {
      method: "POST",
      body: JSON.stringify({
        scene_id: scene.id,
        name,
        candidate,
      }),
    });
    state.activeStory = result.story || await api(`/api/stories/${story.id}`);
    render();

    const created = result.character || findStoryCharacter(name);
    if (created?.id && (created.visual_prompt || "").trim()) {
      await generateSprite(created.id);
    } else if (created?.id) {
      state.characterPromptExpanded = true;
      alert(`Personagem ${created.name || name} criado, mas sem prompt de imagem.`);
      setBusy(false);
    } else {
      setBusy(false);
    }
  } catch (error) {
    alert(error.message);
    setBusy(false);
  }
}

async function saveModalCharacter(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  setBusy(true, "Salvando personagem...");
  try {
    if (state.modal?.generated) {
      const scene = latestScene(state.activeStory);
      await api(`/api/stories/${state.activeStory.id}/characters/introduce`, {
        method: "POST",
        body: JSON.stringify({
          ...payload,
          scene_id: scene?.id || "",
          candidate: {
            ...(state.modal.character || {}),
            ...payload,
          },
        }),
      });
    } else {
      await api(`/api/stories/${state.activeStory.id}/characters`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }
    state.modal = null;
    await loadStory(state.activeStory.id);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveCharacterEdit(event) {
  event.preventDefault();
  if (!state.activeStory) return;
  const characterId = event.currentTarget.dataset.characterId;
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  setBusy(true, "Salvando personagem...");
  try {
    await api(`/api/characters/${characterId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    state.characterEditId = "";
    state.activeCharacterId = characterId;
    await loadStory(state.activeStory.id);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function generateCharacterImagePrompt(characterId) {
  if (!state.activeStory || !characterId) return;
  setBusy(true, "Gerando prompt de imagem com Ollama...");
  try {
    const scene = latestScene(state.activeStory);
    const character = (state.activeStory.characters || []).find(item => item.id === characterId);
    const onScreen = (scene?.characters_on_screen || []).find(item => normalizeName(item.name) === normalizeName(character?.name));
    await api(`/api/characters/${characterId}/image-prompt`, {
      method: "POST",
      body: JSON.stringify({
        expression: onScreen?.expression || "neutral",
      }),
    });
    state.activeCharacterId = characterId;
    state.characterPromptExpanded = true;
    await loadStory(state.activeStory.id);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveMemoryEntry(event) {
  event.preventDefault();
  if (!state.activeStory) return;
  const form = new FormData(event.currentTarget);
  const content = (form.get("content") || "").trim();
  if (!content) {
    alert("Escreva a informação antes de registrar.");
    return;
  }
  setBusy(true, "Registrando memória...");
  try {
    state.activeStory = await api(`/api/stories/${state.activeStory.id}/memory`, {
      method: "POST",
      body: JSON.stringify({
        entry_type: form.get("entry_type") || "note",
        importance: Number(form.get("importance") || 3),
        content,
      }),
    });
    state.modal = null;
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveMemoryEdit(event) {
  event.preventDefault();
  if (!state.activeStory || !state.modal?.entry?.id) return;
  const form = new FormData(event.currentTarget);
  const content = (form.get("content") || "").trim();
  if (!content) {
    alert("Escreva a memoria antes de salvar.");
    return;
  }
  setBusy(true, "Salvando memoria...");
  try {
    state.activeStory = await api(`/api/memory/${state.modal.entry.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        entry_type: form.get("entry_type") || "note",
        importance: Number(form.get("importance") || 3),
        content,
      }),
    });
    state.modal = null;
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveStoryLore(event) {
  event.preventDefault();
  if (!state.activeStory) return;
  const form = new FormData(event.currentTarget);
  setBusy(true, "Salvando lore...");
  try {
    state.activeStory = await api(`/api/stories/${state.activeStory.id}`, {
      method: "PATCH",
      body: JSON.stringify({ lore: form.get("lore") || "" }),
    });
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveLoreEntry(event) {
  event.preventDefault();
  if (!state.activeStory) return;
  const form = new FormData(event.currentTarget);
  const content = (form.get("content") || "").trim();
  if (!content) {
    alert("Escreva o conteudo de lore antes de salvar.");
    return;
  }
  const payload = {
    title: form.get("title") || "Entrada de lore",
    entry_type: form.get("entry_type") || "note",
    content,
  };
  const entryId = state.modal?.entry?.id;
  setBusy(true, "Salvando lore...");
  try {
    state.activeStory = await api(entryId ? `/api/lore/${entryId}` : `/api/stories/${state.activeStory.id}/lore`, {
      method: entryId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    state.modal = null;
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function deleteMemoryEntry(memoryId) {
  if (!memoryId || !confirm("Excluir esta memoria?")) return;
  setBusy(true, "Excluindo memoria...");
  try {
    state.activeStory = await api(`/api/memory/${memoryId}`, { method: "DELETE" });
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function deleteLoreEntry(loreId, title) {
  if (!loreId || !confirm(`Excluir "${title || "esta entrada de lore"}"?`)) return;
  setBusy(true, "Excluindo lore...");
  try {
    state.activeStory = await api(`/api/lore/${loreId}`, { method: "DELETE" });
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function findMemoryEntry(memoryId) {
  return (state.activeStory?.memory_entries || []).find(entry => entry.id === memoryId);
}

function findLoreEntry(loreId) {
  return (state.activeStory?.lore_entries || []).find(entry => entry.id === loreId);
}

async function saveSceneEdit(event) {
  event.preventDefault();
  const scene = latestScene(state.activeStory);
  if (!scene) return;
  const form = new FormData(event.currentTarget);
  const choices = String(form.get("choices") || "")
    .split("\n")
    .map(item => item.trim())
    .filter(Boolean);
  setBusy(true, "Salvando cena...");
  try {
    state.activeStory = await api(`/api/scenes/${scene.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: form.get("title") || "",
        scene_text: form.get("scene_text") || "",
        background_prompt: form.get("background_prompt") || "",
        choices,
      }),
    });
    state.editMode = false;
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function depictCurrentScene() {
  const story = state.activeStory;
  const scene = latestScene(story);
  if (!story || !scene) {
    alert("Gere uma cena antes de pedir imagens.");
    return;
  }

  setBusy(true, "Preparando imagens da cena...");
  try {
    const background = findSceneBackground(scene);
    if (!background?.url && scene.background_prompt) {
      const result = await api(`/api/stories/${story.id}/generate-image`, {
        method: "POST",
        body: JSON.stringify({
          asset_type: "background",
          scene_id: scene.id,
          prompt: scene.background_prompt,
        }),
      });
      await waitForAsset(result.asset_id, "Gerando cenário no ComfyUI...");
      await loadStory(story.id);
    }

    await ensureSceneSprites("Gerando sprites da cena...");
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function generateInitialStoryAssets() {
  const story = state.activeStory;
  const scene = latestScene(story);
  if (!story || !scene) return;

  state.status = "Gerando imagens iniciais...";
  render();
  const background = findSceneBackground(scene);
  if (!background?.url && scene.background_prompt) {
    const result = await api(`/api/stories/${story.id}/generate-image`, {
      method: "POST",
      body: JSON.stringify({
        asset_type: "background",
        scene_id: scene.id,
        prompt: scene.background_prompt,
      }),
    });
    await waitForAsset(result.asset_id, "Gerando background inicial no ComfyUI...");
    await loadStory(story.id);
  }

  await ensureInitialCharacterSprites("Gerando sprites iniciais...");
}

async function ensureInitialCharacterSprites(label = "Gerando sprites iniciais...") {
  const story = state.activeStory;
  const scene = latestScene(story);
  if (!story) return [];

  const generated = [];
  for (const character of story.characters || []) {
    if (!(character.visual_prompt || "").trim() || getCharacterSprites(character.id).length) continue;
    const onScreen = (scene?.characters_on_screen || []).find(item => normalizeName(item.name) === normalizeName(character.name));
    state.status = `${label} ${character.name}`;
    render();
    const result = await api(`/api/stories/${story.id}/generate-image`, {
      method: "POST",
      body: JSON.stringify({
        asset_type: "sprite",
        character_id: character.id,
        scene_id: scene?.id || null,
        expression: onScreen?.expression || "neutral",
        prompt: character.visual_prompt,
      }),
    });
    generated.push(result.asset_id);
    await waitForAsset(result.asset_id, `Gerando sprite inicial de ${character.name}...`);
    await loadStory(story.id);
  }
  return generated;
}

async function ensureSceneSprites(label = "Gerando sprites da cena...") {
  const story = state.activeStory;
  const scene = latestScene(story);
  if (!story || !scene) return [];

  const generated = [];
  for (const item of scene.characters_on_screen || []) {
    const character = findStoryCharacter(item.name);
    if (!character || findCharacterSprite(item.name, item.expression)?.url) continue;
    if (!(character.visual_prompt || "").trim()) continue;

    state.status = `${label} ${character.name}`;
    render();
    const result = await api(`/api/stories/${story.id}/generate-image`, {
      method: "POST",
      body: JSON.stringify({
        asset_type: "sprite",
        character_id: character.id,
        scene_id: scene.id,
        expression: item.expression || "neutral",
        prompt: character.visual_prompt,
      }),
    });
    generated.push(result.asset_id);
    await waitForAsset(result.asset_id, `Gerando sprite de ${character.name}...`);
    await loadStory(story.id);
  }
  return generated;
}

async function generateBackground() {
  const scene = latestScene(state.activeStory);
  if (!scene?.background_prompt) {
    alert("A cena atual ainda nao tem prompt de background.");
    return;
  }
  setBusy(true, "Enviando background para ComfyUI...");
  try {
    const result = await api(`/api/stories/${state.activeStory.id}/generate-image`, {
      method: "POST",
      body: JSON.stringify({
        asset_type: "background",
        scene_id: scene.id,
        prompt: scene.background_prompt,
      }),
    });
    await waitForAsset(result.asset_id, "Gerando background no ComfyUI...");
    await loadStory(state.activeStory.id);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function generateSprite(characterId) {
  const character = (state.activeStory.characters || []).find(item => item.id === characterId);
  if (!character) return;
  if (!(character.visual_prompt || "").trim()) {
    alert("Gere ou preencha o Prompt para Geracao de Imagem antes de gerar o sprite.");
    state.characterPromptExpanded = true;
    render();
    return;
  }
  setBusy(true, "Enviando sprite para ComfyUI...");
  try {
    const scene = latestScene(state.activeStory);
    const onScreen = (scene?.characters_on_screen || []).find(item => normalizeName(item.name) === normalizeName(character.name));
    const result = await api(`/api/stories/${state.activeStory.id}/generate-image`, {
      method: "POST",
      body: JSON.stringify({
        asset_type: "sprite",
        character_id: character.id,
        scene_id: scene?.id || null,
        expression: onScreen?.expression || "neutral",
        prompt: character.visual_prompt,
      }),
    });
    await waitForAsset(result.asset_id, "Gerando sprite no ComfyUI...");
    await loadStory(state.activeStory.id);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function refreshSprite(characterId) {
  const character = (state.activeStory.characters || []).find(item => item.id === characterId);
  if (!character) return;
  if (!(character.visual_prompt || "").trim()) {
    alert("Gere ou preencha o Prompt para Geracao de Imagem antes de regenerar o sprite.");
    state.characterPromptExpanded = true;
    render();
    return;
  }
  const latestSprite = getCharacterSprites(characterId)[0];
  if (!latestSprite) {
    await generateSprite(characterId);
    return;
  }

  const ok = confirm(`Excluir o sprite atual de ${character.name} e gerar um novo?`);
  if (!ok) return;

  setBusy(true, "Excluindo sprite atual...");
  try {
    await api(`/api/assets/${latestSprite.id}`, { method: "DELETE" });
    await loadStory(state.activeStory.id);
  } catch (error) {
    alert(error.message);
    setBusy(false);
    return;
  }

  await generateSprite(characterId);
}

async function waitForAsset(assetId, label) {
  if (!assetId) throw new Error("Asset sem ID.");
  for (let attempt = 0; attempt < 180; attempt += 1) {
    state.status = `${label} ${attempt + 1}/180`;
    render();
    await sleep(1500);
    const result = await api(`/api/assets/${assetId}/result`);
    if (result.ready) return result.asset;
  }
  throw new Error("A imagem ainda nao ficou pronta no ComfyUI.");
}

function findSceneBackground(scene) {
  const assets = state.activeStory?.assets || [];
  if (scene.background_asset_id) {
    return assets.find(asset => asset.id === scene.background_asset_id && asset.url);
  }
  return (
    assets.find(asset => asset.asset_type === "background" && asset.scene_id === scene.id && asset.url) ||
    assets.find(asset => asset.asset_type === "background" && asset.url)
  );
}

function findCharacterSprite(name, expression) {
  const character = findStoryCharacter(name);
  if (!character) return null;
  const assets = (state.activeStory?.assets || []).filter(asset => (
    asset.asset_type === "sprite" &&
    asset.character_id === character.id &&
    asset.url
  ));
  if (!assets.length) return null;
  return assets.find(asset => normalizeName(asset.expression) === normalizeName(expression)) || assets[0];
}

function findStoryCharacter(name) {
  const key = normalizeName(name);
  if (!key) return null;
  return (state.activeStory?.characters || []).find(item => {
    const names = [
      item.name,
      ...String(item.aliases || "").split(",").map(alias => alias.trim()),
    ];
    return names.some(value => normalizeName(value) === key);
  });
}

function newCharacterCandidateForName(scene, name) {
  const key = normalizeName(name);
  if (!key || key === "narrador" || findStoryCharacter(name)) return null;
  return getNewCharacterCandidates(scene).find(candidate => {
    const names = [
      candidate.display_name,
      candidate.temporary_name,
      candidate.name,
    ];
    return names.some(value => normalizeName(value) === key);
  }) || null;
}

function getNewCharacterCandidates(scene) {
  if (!scene) return [];
  const candidates = new Map();
  const addCandidate = item => {
    if (!item || typeof item !== "object") return;
    const displayName = item.display_name || item.name || item.temporary_name;
    const temporaryName = item.temporary_name || item.name || item.display_name;
    const key = normalizeName(displayName || temporaryName);
    if (!key || key === "narrador" || findStoryCharacter(displayName || temporaryName)) return;
    candidates.set(key, {
      ...item,
      display_name: displayName || temporaryName,
      temporary_name: temporaryName || displayName,
    });
  };

  (scene.raw_ai_response?.new_characters_detected || []).forEach(addCandidate);
  (scene.dialogues || []).forEach(dialogue => {
    const name = dialogue?.character || "";
    if (!name || normalizeName(name) === "narrador" || findStoryCharacter(name)) return;
    addCandidate({
      temporary_name: name,
      display_name: name,
      reason: dialogue.text ? `Foi introduzido por uma fala na cena: ${dialogue.text}` : "Foi introduzido por uma fala na cena atual.",
      suggested_role: "personagem ligado ao conflito atual",
    });
  });
  (scene.characters_on_screen || []).forEach(character => {
    const name = character?.name || "";
    if (!name || normalizeName(name) === "narrador" || findStoryCharacter(name)) return;
    addCandidate({
      temporary_name: name,
      display_name: name,
      reason: `Foi mostrado em cena com expressao ${character.expression || "neutral"} e precisa de uma ficha coerente com o mundo.`,
      suggested_role: "presenca importante na cena atual",
    });
  });
  return [...candidates.values()];
}

function latestScene(story) {
  const scenes = story?.scenes || [];
  return scenes[scenes.length - 1] || null;
}

function latestDialogue(scene) {
  const dialogues = scene?.dialogues || [];
  return dialogues[dialogues.length - 1] || { character: "Narrador", text: scene?.scene_text || "" };
}

function normalizeName(value) {
  return String(value || "").trim().toLowerCase();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function field(name, label, type, placeholder) {
  return `
    <div class="field">
      <label for="${name}">${label}</label>
      <input id="${name}" name="${name}" type="${type}" placeholder="${escapeAttr(placeholder || "")}">
    </div>
  `;
}

function draftField(name, label, type, placeholder, value) {
  return `
    <div class="field">
      <label for="${name}">${label}</label>
      <input id="${name}" name="${name}" type="${type}" placeholder="${escapeAttr(placeholder || "")}" value="${escapeAttr(value || "")}">
    </div>
  `;
}

function draftTextarea(name, label, fieldType, placeholder, value, full = false) {
  return `
    <div class="field ${full ? "full" : ""}">
      <div class="field-head">
        <label for="${name}">${label}</label>
        ${improveButton(name, fieldType || "description", label)}
      </div>
      <textarea id="${name}" name="${name}" placeholder="${escapeAttr(placeholder || "")}">${escapeHtml(value || "")}</textarea>
    </div>
  `;
}

function valueField(name, label, value) {
  return `
    <div class="field">
      <label for="${name}">${label}</label>
      <input id="${name}" name="${name}" value="${escapeAttr(value)}">
    </div>
  `;
}

function textareaField(name, label, fieldType = "description") {
  return `
    <div class="field">
      <div class="field-head">
        <label for="${name}">${label}</label>
        ${improveButton(name, fieldType, label)}
      </div>
      <textarea id="${name}" name="${name}"></textarea>
    </div>
  `;
}

function modalInput(name, label, value) {
  return `
    <div class="field">
      <label for="modal-${name}">${label}</label>
      <input id="modal-${name}" name="${name}" value="${escapeAttr(value)}">
    </div>
  `;
}

function modalTextarea(name, label, value) {
  return `
    <div class="field">
      <div class="field-head">
        <label for="modal-${name}">${label}</label>
        ${improveButton(`modal-${name}`, name === "visual_prompt" ? "visual_prompt" : "character", label)}
      </div>
      <textarea id="modal-${name}" name="${name}">${escapeHtml(value)}</textarea>
    </div>
  `;
}

function improveButton(target, fieldType, label) {
  return `
    <button
      type="button"
      class="improve-btn"
      title="Melhorar com IA"
      data-action="improve-field"
      data-target="${escapeAttr(target)}"
      data-field-type="${escapeAttr(fieldType)}"
      data-label="${escapeAttr(label)}"
    >🪄 Melhorar</button>
  `;
}

function formatDate(value) {
  if (!value) return "";
  return new Date(Number(value)).toLocaleString("pt-BR");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
