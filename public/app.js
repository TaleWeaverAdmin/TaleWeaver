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
  backgroundFilterOpacity: Number(localStorage.getItem("backgroundFilterOpacity") || 50),
  dialogueSceneId: "",
  dialogueIndex: 0,
  typewriterKey: "",
  typewriterVisible: 0,
  typewriterDone: false,
  typewriterTimer: null,
  typewriterAudio: null,
  spriteRoster: [],
  spriteExpressionMap: {},
  spriteExitMap: {},
  spriteExitTimer: null,
  nextSpeakerFocus: null,
  createStep: 0,
  createDraft: defaultCreateDraft(),
  styleEditingId: "",
  styleDraft: null,
  styleTab: "sprites",
  styleSpriteAdvanced: false,
  styleBackgroundAdvanced: false,
  stylePromptCommandsVisible: false,
  stylePromptTest: { assetType: "appearance", appearance: "", clothing: "", result: "" },
  settingsAdvanced: false,
  editMode: false,
  storySort: "recent",
  playMenuOpen: false,
  redoMenuOpen: false,
  storyTopnavOpen: false,
  spriteEditMode: false,
};

const OLLAMA_PRESETS = {
  fast: {
    label: "Rapido",
    description: "Menos contexto e resposta mais curta. Bom para testar cenas e modelos pesados.",
    values: {
      ollama_temperature: 0.72,
      ollama_context: 4096,
      ollama_top_p: 0.86,
      ollama_top_k: 30,
      ollama_min_p: 0,
      ollama_num_predict: 1200,
      ollama_retry_num_predict: 1600,
      ollama_max_attempts: 2,
      ollama_repeat_penalty: 1.1,
      ollama_repeat_last_n: 384,
      ollama_think: false,
      ollama_keep_alive: "10m",
      ollama_timeout: 180,
    },
  },
  balanced: {
    label: "Balanceado",
    description: "Boa qualidade com custo controlado. Recomendado para qwen3:14b.",
    values: {
      ollama_temperature: 0.78,
      ollama_context: 6144,
      ollama_top_p: 0.9,
      ollama_top_k: 40,
      ollama_min_p: 0,
      ollama_num_predict: 1800,
      ollama_retry_num_predict: 2200,
      ollama_max_attempts: 2,
      ollama_repeat_penalty: 1.12,
      ollama_repeat_last_n: 512,
      ollama_think: false,
      ollama_keep_alive: "10m",
      ollama_timeout: 240,
    },
  },
  quality: {
    label: "Qualidade",
    description: "Mais contexto, respostas longas e uma tentativa extra. Melhor para cenas importantes.",
    values: {
      ollama_temperature: 0.84,
      ollama_context: 8192,
      ollama_top_p: 0.92,
      ollama_top_k: 50,
      ollama_min_p: 0,
      ollama_num_predict: 2600,
      ollama_retry_num_predict: 3200,
      ollama_max_attempts: 3,
      ollama_repeat_penalty: 1.12,
      ollama_repeat_last_n: 768,
      ollama_think: false,
      ollama_keep_alive: "15m",
      ollama_timeout: 420,
    },
  },
};

const OLLAMA_ADVANCED_FIELDS = [
  "ollama_temperature",
  "ollama_context",
  "ollama_top_p",
  "ollama_top_k",
  "ollama_min_p",
  "ollama_num_predict",
  "ollama_retry_num_predict",
  "ollama_max_attempts",
  "ollama_repeat_penalty",
  "ollama_repeat_last_n",
  "ollama_think",
  "ollama_keep_alive",
  "ollama_timeout",
];

const LLAMA_PRESETS = {
  fast: {
    label: "Rapido",
    description: "Menos tokens e cache de prompt ligado. Bom para testar cenas com llama.cpp local.",
    values: {
      llama_temperature: 0.72,
      llama_top_p: 0.86,
      llama_top_k: 30,
      llama_min_p: 0.02,
      llama_context_window: 4096,
      llama_max_tokens: 900,
      llama_retry_max_tokens: 1100,
      llama_max_attempts: 2,
      llama_repeat_penalty: 1.1,
      llama_repeat_last_n: 384,
      llama_enable_thinking: false,
      llama_cache_prompt: true,
      llama_timings_per_token: false,
      llama_timeout: 180,
    },
  },
  balanced: {
    label: "Balanceado",
    description: "Boa qualidade com custo controlado para llama-server em maquina local.",
    values: {
      llama_temperature: 0.78,
      llama_top_p: 0.9,
      llama_top_k: 40,
      llama_min_p: 0.02,
      llama_context_window: 4096,
      llama_max_tokens: 1200,
      llama_retry_max_tokens: 1400,
      llama_max_attempts: 2,
      llama_repeat_penalty: 1.12,
      llama_repeat_last_n: 512,
      llama_enable_thinking: false,
      llama_cache_prompt: true,
      llama_timings_per_token: false,
      llama_timeout: 240,
    },
  },
  quality: {
    label: "Qualidade",
    description: "Mais tokens e uma tentativa extra. Melhor para cenas importantes ou modelos menores.",
    values: {
      llama_temperature: 0.84,
      llama_top_p: 0.92,
      llama_top_k: 50,
      llama_min_p: 0.03,
      llama_context_window: 8192,
      llama_max_tokens: 1800,
      llama_retry_max_tokens: 2200,
      llama_max_attempts: 3,
      llama_repeat_penalty: 1.12,
      llama_repeat_last_n: 768,
      llama_enable_thinking: false,
      llama_cache_prompt: true,
      llama_timings_per_token: false,
      llama_timeout: 420,
    },
  },
};

const LLAMA_ADVANCED_FIELDS = [
  "llama_temperature",
  "llama_top_p",
  "llama_top_k",
  "llama_min_p",
  "llama_context_window",
  "llama_max_tokens",
  "llama_retry_max_tokens",
  "llama_max_attempts",
  "llama_repeat_penalty",
  "llama_repeat_last_n",
  "llama_enable_thinking",
  "llama_cache_prompt",
  "llama_timings_per_token",
  "llama_timeout",
];

const MAX_DIALOGUE_PAGE_LINES = 3;
const OFFICIAL_EXPRESSIONS = ["neutral", "happy", "sad", "angry", "thoughtful", "surprised", "embarrassed", "scared"];
const SPRITE_EXPRESSION_KEYS = ["happy", "sad", "angry", "thoughtful", "surprised", "embarrassed", "scared"];
const EXPRESSION_LABELS = {
  neutral: "Neutro",
  happy: "Feliz",
  sad: "Triste",
  angry: "Bravo",
  thoughtful: "Pensativo",
  surprised: "Surpreso",
  embarrassed: "T\u00edmido",
  scared: "Assustado",
};

const app = document.getElementById("app");

init();

function defaultCreateDraft(language = "pt-BR") {
  return {
    story_prompt: "",
    participation_mode: "first_person",
    point_of_view: "first",
    base_generated_key: "",
    title: "",
    genre: "",
    tone: "",
    visual_style: "anime visual novel",
    visual_style_id: "",
    content_rating: "",
    language,
    lore: "",
    starting_location: "",
    starting_message: "",
    player_name: "",
    player_role: "",
    player_species: "",
    player_gender: "",
    player_character_type: "",
    player_aliases: "",
    player_description: "",
    player_physical: "",
    player_appearance: "",
    player_personality: "",
    player_clothing: "",
    player_relationship: "",
    player_background: "",
    player_goals: "",
    characters: [emptyCharacterDraft()],
  };
}

const PARTICIPATION_MODES = [
  {
    value: "first_person",
    legacy: "first",
    title: "Primeira pessoa",
    short: "Você é o protagonista",
    description: "Experiência imersiva pelos olhos do personagem. O protagonista representa você, não aparece na tela e não gera sprite.",
  },
  {
    value: "third_person",
    legacy: "third",
    title: "Terceira pessoa",
    short: "Você controla um protagonista visível",
    description: "Visual novel tradicional. O protagonista representa você, aparece em cena quando fizer sentido e pode ter sprite.",
  },
  {
    value: "narrator",
    legacy: "narrator",
    title: "Narrador",
    short: "Você guia a história inteira",
    description: "Modo mais livre e cinematográfico. Você não é um personagem, pode mudar foco, eventos e rumos do elenco.",
  },
];

function normalizeParticipationMode(value) {
  const text = String(value || "").trim().toLowerCase().replace(/[-\s]+/g, "_");
  const found = PARTICIPATION_MODES.find(mode => mode.value === text || mode.legacy === text);
  return found?.value || "first_person";
}

function participationModeOption(value) {
  const mode = normalizeParticipationMode(value);
  return PARTICIPATION_MODES.find(item => item.value === mode) || PARTICIPATION_MODES[0];
}

function legacyPointOfView(mode) {
  return participationModeOption(mode).legacy;
}

function currentParticipationMode(draft) {
  return normalizeParticipationMode(draft?.participation_mode || draft?.point_of_view);
}

function createBaseKey(draft) {
  return `${currentParticipationMode(draft)}::${String(draft?.story_prompt || "").trim()}`;
}

function isCreateBaseCurrent(draft) {
  const key = createBaseKey(draft);
  return Boolean(key.split("::")[1]) && draft?.base_generated_key === key;
}

function maxCreateStep(draft) {
  if (state.createStep === 0) return 0;
  return isCreateBaseCurrent(draft) ? 3 : 0;
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
  document.addEventListener("click", handleGlobalClick);
  document.addEventListener("keydown", handleGlobalKeydown);
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
  runPostRenderEffects();
}

function renderTopnav() {
  const playMode = state.route === "play";
  const shellClass = playMode ? `story-topnav-shell ${state.storyTopnavOpen ? "open" : ""}` : "";
  return `
    <div class="${shellClass}" ${playMode ? "" : "data-topnav-shell"}>
      <header class="topnav ${playMode ? "story-topnav" : ""}">
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
      ${playMode ? `
        <button
          type="button"
          class="story-topnav-toggle"
          data-action="toggle-story-topnav"
          aria-label="${state.storyTopnavOpen ? "Esconder menu superior" : "Mostrar menu superior"}"
          aria-expanded="${state.storyTopnavOpen ? "true" : "false"}"
        >
          <img src="/icons/angulo-para-baixo.png" alt="" aria-hidden="true">
        </button>
      ` : ""}
    </div>
  `;
}

function renderSettings() {
  const settings = state.settings || {};
  const provider = settings.ai_provider || "ollama";
  return `
    <main class="page">
      <section class="view-title">
        <div>
          <h1>Configurações locais</h1>
          <p>Defina conexões com IA de texto e ComfyUI para geração de texto e imagens.</p>
        </div>
      </section>
      <form id="settings-form">
        <section class="panel">
          <h2>Configuracoes gerais</h2>
          <div class="form-grid">
            <input type="hidden" name="ai_provider" value="${escapeAttr(provider)}">
            <div class="field">
              <label for="default_language">Idioma padrao de geracao</label>
              <select id="default_language" name="default_language">
                <option value="pt-BR" ${(settings.default_language || "pt-BR") === "pt-BR" ? "selected" : ""}>Portugues (pt-BR)</option>
                <option value="en-US" ${settings.default_language === "en-US" ? "selected" : ""}>English (en-US)</option>
              </select>
            </div>
          </div>
        </section>
        ${renderTextAiRoleSettings(settings)}
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
          </div>
          <div class="notice">Configuracoes de cenario ficam em Estilos visuais. O checkpoint padrao acima e usado quando o estilo nao define um checkpoint proprio.</div>
          <div class="notice">
            Checkpoints detectados: ${state.checkpoints.length ? state.checkpoints.map(escapeHtml).join(", ") : "nenhum, verifique se o ComfyUI está aberto."}
          </div>
          <div class="notice">
            Workbenches detectados: ${renderWorkbenchNotice()}
          </div>
        </section>
        ${renderScriptSettings(settings)}
        <div class="mini-actions">
          <button type="button" data-action="test-comfy">Testar ComfyUI</button>
          <button type="button" data-action="dashboard">Voltar</button>
          <button class="primary" type="submit">Salvar configurações</button>
        </div>
      </form>
    </main>
  `;
}

function renderScriptSettings(settings) {
  return `
    <section class="panel">
      <h2>Scripts</h2>
      <div class="script-service">
        <h3>IA de geracao de historia</h3>
        <div class="form-grid">
          ${valueField("script_story_ai_cwd", "Pasta de execucao", settings.script_story_ai_cwd || "")}
          ${valueField("script_story_ai_command", "Comando de inicializacao", settings.script_story_ai_command || "")}
          ${checkboxField("script_story_ai_start_with_app", "Inicializar com o TaleWeaver", settings.script_story_ai_start_with_app === true)}
          ${checkboxField("script_story_ai_show_window", "Mostrar execucao do app", settings.script_story_ai_show_window !== false)}
        </div>
      </div>
      <div class="script-service">
        <h3>IA de narrativa</h3>
        <div class="form-grid">
          ${valueField("script_scene_ai_cwd", "Pasta de execucao", settings.script_scene_ai_cwd || settings.script_llama_cwd || "")}
          ${valueField("script_scene_ai_command", "Comando de inicializacao", settings.script_scene_ai_command || settings.script_llama_command || "")}
          ${checkboxField("script_scene_ai_start_with_app", "Inicializar com o TaleWeaver", settings.script_scene_ai_start_with_app === true || settings.script_llama_start_with_app === true)}
          ${checkboxField("script_scene_ai_show_window", "Mostrar execucao do app", settings.script_scene_ai_show_window !== false && settings.script_llama_show_window !== false)}
        </div>
      </div>
      <div class="script-service">
        <h3>Llama legado</h3>
        <div class="form-grid">
          ${valueField("script_llama_cwd", "Pasta de execucao", settings.script_llama_cwd || "")}
          ${valueField("script_llama_command", "Comando de inicializacao", settings.script_llama_command || "")}
          ${checkboxField("script_llama_start_with_app", "Inicializar com o TaleWeaver", settings.script_llama_start_with_app === true)}
          ${checkboxField("script_llama_show_window", "Mostrar execucao do app", settings.script_llama_show_window !== false)}
        </div>
      </div>
      <div class="script-service">
        <h3>ComfyUI</h3>
        <div class="form-grid">
          ${valueField("script_comfy_cwd", "Pasta de execucao", settings.script_comfy_cwd || settings.comfy_root || "N:\\SillyTavern\\ComfyUI")}
          ${valueField("script_comfy_command", "Comando de inicializacao", settings.script_comfy_command || "py -3.11 main.py --enable-cors-header")}
          ${checkboxField("script_comfy_start_with_app", "Inicializar com o TaleWeaver", settings.script_comfy_start_with_app === true)}
          ${checkboxField("script_comfy_show_window", "Mostrar execucao do app", settings.script_comfy_show_window !== false)}
        </div>
      </div>
      <div class="notice">Ao gerar historia inicial, o TaleWeaver ativa a IA de geracao de historia e pausa a IA de narrativa quando elas usam runtimes diferentes. Durante a narrativa, a IA permanece ativa entre chamadas. Durante imagens, a IA de narrativa/Llama e pausada ate o ComfyUI terminar.</div>
    </section>
  `;
}

function renderTextAiRoleSettings(settings) {
  return `
    <section class="panel">
      <h2>IA de narrativa</h2>
      ${renderTextAiRolePanel(settings, "scene_ai")}
    </section>
    <section class="panel">
      <h2>IA de geracao de historia</h2>
      ${renderTextAiRolePanel(settings, "story_ai")}
    </section>
  `;
}

function renderTextAiRolePanel(settings, prefix) {
  return `
    <div class="form-grid">
      <input type="hidden" name="${prefix}_provider" value="openai-compatible">
      ${valueField(`${prefix}_openai_compatible_base_url`, "Base URL", settings[`${prefix}_openai_compatible_base_url`] || settings.openai_compatible_base_url || "")}
      ${valueField(`${prefix}_openai_compatible_model`, "Modelo", settings[`${prefix}_openai_compatible_model`] || settings.openai_compatible_model || "")}
      ${secretField(`${prefix}_openai_compatible_api_key`, "API key", settings[`${prefix}_openai_compatible_api_key`])}
      ${checkboxField(`${prefix}_openai_compatible_verify_ssl`, "Verificar certificado SSL", settings[`${prefix}_openai_compatible_verify_ssl`] !== false)}
      ${checkboxField(`${prefix}_openai_compatible_llama_mode`, "Usar parametros llama.cpp nesta API", settings[`${prefix}_openai_compatible_llama_mode`] !== false)}
      ${renderRoleLlamaSettings(settings, prefix)}
    </div>
  `;
}

function renderRoleLlamaSettings(settings, prefix) {
  const values = currentRoleLlamaValues(settings, prefix);
  const presetName = `${prefix}_llama_preset`;
  return `
    <div class="field">
      <label for="${presetName}">Preset de performance llama.cpp</label>
      <select id="${presetName}" name="${presetName}" data-llama-role-preset="${prefix}">
        ${renderLlamaPresetOptions(values.llama_preset || "balanced")}
      </select>
    </div>
    ${numberField(`${prefix}_llama_temperature`, "Temperatura", values.llama_temperature)}
    ${numberField(`${prefix}_llama_top_p`, "Top P", values.llama_top_p)}
    ${numberField(`${prefix}_llama_top_k`, "Top K", values.llama_top_k)}
    ${numberField(`${prefix}_llama_min_p`, "Min P", values.llama_min_p)}
    ${numberField(`${prefix}_llama_context_window`, "Janela de contexto do servidor", values.llama_context_window)}
    ${numberField(`${prefix}_llama_max_tokens`, "Tokens da resposta", values.llama_max_tokens)}
    ${numberField(`${prefix}_llama_retry_max_tokens`, "Tokens em retry", values.llama_retry_max_tokens)}
    ${numberField(`${prefix}_llama_max_attempts`, "Tentativas maximas", values.llama_max_attempts)}
    ${numberField(`${prefix}_llama_repeat_penalty`, "Repeat penalty", values.llama_repeat_penalty)}
    ${numberField(`${prefix}_llama_repeat_last_n`, "Repeat last N", values.llama_repeat_last_n)}
    ${numberField(`${prefix}_llama_timeout`, "Timeout da chamada (s)", values.llama_timeout)}
    ${checkboxField(`${prefix}_llama_enable_thinking`, "Ativar thinking mode no template do llama.cpp", values.llama_enable_thinking === true)}
    ${checkboxField(`${prefix}_llama_cache_prompt`, "Reutilizar cache de prompt do llama.cpp", values.llama_cache_prompt !== false)}
    ${checkboxField(`${prefix}_llama_timings_per_token`, "Pedir diagnostico detalhado de timings", values.llama_timings_per_token === true)}
  `;
}

function renderVisualStyles() {
  const draft = currentStyleDraft();
  return `
    <main class="page">
      <section class="view-title">
        <div>
          <h1>Estilos visuais</h1>
          <p>Defina como sprites e cenarios serao gerados em cada historia.</p>
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
                <small>${escapeHtml(style.sprite_workbench || style.background_workbench || "Workflow simples interno")}</small>
              </button>
            `).join("") : `<div class="empty-state">Nenhum estilo criado.</div>`}
          </div>
        </div>
        <form id="style-form" class="panel style-editor-panel">
          <div class="section-head">
            <h2>${state.styleEditingId ? "Editar estilo" : "Novo estilo"}</h2>
            ${state.styleEditingId ? `<button class="danger" type="button" data-action="delete-style" data-id="${escapeAttr(state.styleEditingId)}">Excluir</button>` : ""}
          </div>
          <div class="style-editor-main">
            <div class="style-cover-bar">
              ${renderStyleCover(draft, true)}
              <div class="style-cover-actions">
                <label class="file-picker">
                  <span>Escolher imagem</span>
                  <input type="file" id="style_cover_file" name="cover_file" accept="image/png,image/jpeg,image/webp">
                </label>
                <small>A imagem sera copiada para a pasta do projeto.</small>
              </div>
            </div>
            <div class="form-grid style-main-grid">
              ${styleField("name", "Nome do estilo", draft.name || "")}
              ${renderStyleTabs()}
              ${renderStyleSpriteTab(draft)}
              ${renderStyleBackgroundTab(draft)}
              ${renderStyleAppearancesTab()}
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

function renderStyleTabs() {
  const tabs = [
    ["sprites", "Sprites"],
    ["backgrounds", "Cenarios"],
    ["appearances", "Aparencias"],
  ];
  return `
    <div class="style-tabs full" role="tablist" aria-label="Configuracoes do estilo">
      ${tabs.map(([id, label]) => `
        <button
          type="button"
          class="${state.styleTab === id ? "active" : ""}"
          data-action="style-tab"
          data-tab="${escapeAttr(id)}"
          role="tab"
          aria-selected="${state.styleTab === id ? "true" : "false"}"
        >${escapeHtml(label)}</button>
      `).join("")}
    </div>
  `;
}

function renderStyleSpriteTab(draft) {
  const active = state.styleTab === "sprites";
  return `
    <section class="style-tab-panel full ${active ? "active" : ""}" ${active ? "" : "hidden"} role="tabpanel">
      <div class="form-grid compact-grid">
        <div class="style-workflow-row full">
          <div class="field">
            <label for="style_sprite_workbench">ComfyUI Workflow</label>
            <select id="style_sprite_workbench" name="sprite_workbench">
              ${renderWorkbenchOptions(draft.sprite_workbench || "")}
            </select>
          </div>
          <label class="check-row inline-check">
            <input type="hidden" name="expressions_enabled" value="false">
            <input type="checkbox" id="style_expressions_enabled" name="expressions_enabled" value="true" ${draft.expressions_enabled ? "checked" : ""}>
            <span>Ativar Express&otilde;es</span>
          </label>
        </div>
        ${styleTextarea("prompt_prefix", "Prefixo do prompt de sprite", draft.prompt_prefix || "")}
        ${styleTextarea("prompt_suffix", "Sufixo do prompt de sprite", draft.prompt_suffix || "")}
        ${styleTextarea("negative_prompt", "Prompt negativo de sprite", draft.negative_prompt || "")}
        ${renderExpressionWorkflowSetting(draft)}
        ${renderStylePromptCommandToggle("sprite")}
        ${state.stylePromptCommandsVisible ? renderStylePromptCommandFields(draft, "sprite") : ""}
        <label class="check-row full">
          <input type="checkbox" id="style_sprite_advanced_toggle" ${state.styleSpriteAdvanced ? "checked" : ""}>
          <span>Campos avancados de sprites</span>
        </label>
        ${state.styleSpriteAdvanced ? renderSpriteAdvancedFields(draft) : ""}
      </div>
    </section>
  `;
}

function renderStyleBackgroundTab(draft) {
  const active = state.styleTab === "backgrounds";
  return `
    <section class="style-tab-panel full ${active ? "active" : ""}" ${active ? "" : "hidden"} role="tabpanel">
      <div class="form-grid compact-grid">
        <div class="field">
          <label for="style_background_workbench">ComfyUI Workflow de cenario</label>
          <select id="style_background_workbench" name="background_workbench">
            ${renderWorkbenchOptions(draft.background_workbench || "")}
          </select>
        </div>
        ${styleTextarea("background_prompt_prefix", "Prefixo do prompt de cenario", draft.background_prompt_prefix || "")}
        ${styleTextarea("background_prompt_suffix", "Sufixo do prompt de cenario", draft.background_prompt_suffix || "")}
        ${styleTextarea("background_negative_prompt", "Prompt negativo de cenario", draft.background_negative_prompt || "")}
        ${renderStylePromptCommandToggle("background")}
        ${state.stylePromptCommandsVisible ? renderStylePromptCommandFields(draft, "background") : ""}
        <label class="check-row full">
          <input type="checkbox" id="style_background_advanced_toggle" ${state.styleBackgroundAdvanced ? "checked" : ""}>
          <span>Campos avancados de cenarios</span>
        </label>
        ${state.styleBackgroundAdvanced ? renderBackgroundAdvancedFields(draft) : ""}
      </div>
    </section>
  `;
}

function renderStyleAppearancesTab() {
  const active = state.styleTab === "appearances";
  const draft = currentStyleDraft();
  return `
    <section class="style-tab-panel full ${active ? "active" : ""}" ${active ? "" : "hidden"} role="tabpanel">
      <div class="form-grid compact-grid">
        <div class="field full">
          <label for="style_appearance_workbench">Workflow de Alterar Aparência</label>
          <select id="style_appearance_workbench" name="appearance_workbench">
            ${renderWorkbenchOptions(draft.appearance_workbench || "")}
          </select>
        </div>
        ${renderStylePromptCommandToggle("appearance")}
        ${state.stylePromptCommandsVisible ? renderStylePromptCommandFields(draft, "appearance") : ""}
      </div>
    </section>
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
    background_workbench: "",
    appearance_workbench: "",
    background_prompt_prefix: "",
    background_prompt_suffix: "",
    background_negative_prompt: "",
    sprite_prompt_command: "",
    sprite_prompt_example: "",
    background_prompt_command: "",
    background_prompt_example: "",
    appearance_prompt_command: "",
    appearance_prompt_example: "",
    expressions_enabled: false,
    expression_workbench: "",
    cover_url: "",
    advanced_settings: {},
    background_settings: {},
  };
}

function cloneStyleDraft(style) {
  return {
    ...emptyVisualStyleDraft(),
    ...style,
    advanced_settings: { ...(style.advanced_settings || {}) },
    background_settings: { ...(style.background_settings || {}) },
    expressions_enabled: styleBoolValue(style.expressions_enabled),
  };
}

function emptyCharacterExpressionPrompts() {
  return SPRITE_EXPRESSION_KEYS.reduce((acc, expression) => {
    acc[expression] = "";
    return acc;
  }, {});
}

function normalizeCharacterExpressionPrompts(value) {
  const parsed = parseJsonValue(value, {});
  const source = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  const result = emptyCharacterExpressionPrompts();
  SPRITE_EXPRESSION_KEYS.forEach(expression => {
    result[expression] = String(source[expression] || "").trim();
  });
  return result;
}

function styleBoolValue(value) {
  if (value === true || value === 1) return true;
  const text = String(value ?? "").trim().toLowerCase();
  return ["true", "1", "yes", "sim"].includes(text);
}

function parseJsonValue(value, fallback) {
  if (typeof value !== "string") return value ?? fallback;
  try {
    return JSON.parse(value);
  } catch (_) {
    return fallback;
  }
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

function renderStylePromptCommandToggle(assetType) {
  const id = `style_prompt_commands_toggle_${normalizeStylePromptAssetType(assetType)}`;
  return `
    <label class="check-row full">
      <input type="checkbox" id="${escapeAttr(id)}" class="style-prompt-commands-toggle" ${state.stylePromptCommandsVisible ? "checked" : ""}>
      <span>Mostrar comandos de geracao de prompt</span>
    </label>
  `;
}

function renderStylePromptCommandFields(draft, assetType) {
  const config = stylePromptConfig(assetType);
  const test = state.stylePromptTest || {};
  const result = test.assetType === config.assetType ? test.result || "" : "";
  const appearanceId = `style_prompt_test_appearance_${config.assetType}`;
  const clothingId = `style_prompt_test_clothing_${config.assetType}`;
  const resultId = `style_prompt_test_result_${config.assetType}`;
  return `
    <section class="prompt-command-panel full">
      ${styleTextarea(config.commandField, config.commandLabel, draft[config.commandField] || "")}
      ${styleTextarea(config.exampleField, "Exemplo de prompt", draft[config.exampleField] || "")}
      <div class="prompt-test full">
        <div class="form-grid compact-grid">
          <div class="field full">
            <label for="${escapeAttr(appearanceId)}">Aparencia / descricao base</label>
            <textarea id="${escapeAttr(appearanceId)}" rows="4">${escapeHtml(test.assetType === config.assetType ? test.appearance || "" : "")}</textarea>
          </div>
          <div class="field full">
            <label for="${escapeAttr(clothingId)}">Vestimenta</label>
            <textarea id="${escapeAttr(clothingId)}" rows="3">${escapeHtml(test.assetType === config.assetType ? test.clothing || "" : "")}</textarea>
          </div>
          <div class="mini-actions full">
            <button type="button" data-action="test-style-prompt" data-asset-type="${escapeAttr(config.assetType)}">Criar prompt de imagem</button>
          </div>
          <div class="field full">
            <label for="${escapeAttr(resultId)}">Resultado</label>
            <textarea id="${escapeAttr(resultId)}" rows="6" readonly>${escapeHtml(result)}</textarea>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderExpressionWorkflowSetting(draft) {
  return `
    <section class="expression-prompt-panel full">
      <div class="field full">
        <label for="style_expression_workbench">Workflow de Alterar Express&otilde;es</label>
        <select id="style_expression_workbench" name="expression_workbench">
          ${renderWorkbenchOptions(draft.expression_workbench || "")}
        </select>
      </div>
    </section>
  `;
}

function stylePromptConfig(assetType) {
  const type = normalizeStylePromptAssetType(assetType);
  const configs = {
    sprite: {
      assetType: "sprite",
      commandField: "sprite_prompt_command",
      exampleField: "sprite_prompt_example",
      commandLabel: "Comando de geracao de prompt para sprites",
    },
    background: {
      assetType: "background",
      commandField: "background_prompt_command",
      exampleField: "background_prompt_example",
      commandLabel: "Comando de geracao de prompt para cenarios",
    },
    appearance: {
      assetType: "appearance",
      commandField: "appearance_prompt_command",
      exampleField: "appearance_prompt_example",
      commandLabel: "Comando de geracao de prompt para aparencias",
    },
  };
  return configs[type] || configs.sprite;
}

function normalizeStylePromptAssetType(assetType) {
  if (assetType === "background" || assetType === "backgrounds") return "background";
  if (assetType === "appearance" || assetType === "appearances") return "appearance";
  return "sprite";
}

function renderSpriteAdvancedFields(draft) {
  const advanced = draft.advanced_settings || {};
  const spriteFields = advancedFieldNamesForWorkbench(draft.sprite_workbench || "");
  return spriteFields.length
    ? spriteFields.map(field => renderAdvancedStyleField(field, advanced[field] ?? "", defaultAdvancedStyleValue(field))).join("")
    : `<div class="notice full">Nenhum campo avancado detectado para este workflow.</div>`;
}

function renderBackgroundAdvancedFields(draft) {
  const background = draft.background_settings || {};
  const fields = advancedBackgroundFieldNames();
  return fields.map(field => renderAdvancedBackgroundField(field, background[field] ?? "", defaultAdvancedBackgroundValue(field))).join("");
}

function renderAdvancedStyleField(field, value, defaultValue = "") {
  const labels = {
    width: "Sprite largura",
    height: "Sprite altura",
    seed: "Seed",
    steps: "Steps",
    cfg: "CFG",
    sampler_name: "Sampler",
    scheduler: "Scheduler",
    ckpt_name: "Checkpoint",
  };
  if (field === "ckpt_name") {
    const current = value || "";
    const options = state.checkpoints.length ? state.checkpoints : [defaultValue].filter(Boolean);
    return `
      <div class="field">
        <label for="style_adv_${field}">${labels[field]}</label>
        <select id="style_adv_${field}" name="advanced_${field}">
          <option value="" ${!current ? "selected" : ""}>Usar default do workbench</option>
          ${options.map(name => `<option value="${escapeAttr(name)}" ${name === current ? "selected" : ""}>${escapeHtml(name)}</option>`).join("")}
        </select>
      </div>
    `;
  }
  return `
    <div class="field">
      <label for="style_adv_${field}">${labels[field] || field}</label>
      <input id="style_adv_${field}" name="advanced_${field}" value="${escapeAttr(value || "")}" placeholder="${escapeAttr(defaultValue || "default do workbench")}">
    </div>
  `;
}

function advancedFieldNamesForWorkbench(workbenchId) {
  const allowed = ["width", "height", "seed", "steps", "cfg", "sampler_name", "scheduler", "ckpt_name"];
  if (!workbenchId) return allowed;
  const workbench = state.workbenches.find(item => item.id === workbenchId);
  const inputs = new Set(workbench?.inputs || []);
  return allowed.filter(field => field === "seed" ? inputs.has("seed") || inputs.has("noise_seed") : inputs.has(field));
}

function advancedBackgroundFieldNames(workbenchId = currentStyleDraft()?.background_workbench || "") {
  const allowed = ["width", "height", "seed", "steps", "cfg", "sampler_name", "scheduler", "ckpt_name"];
  if (!workbenchId) return allowed;
  const workbench = state.workbenches.find(item => item.id === workbenchId);
  const inputs = new Set(workbench?.inputs || []);
  return allowed.filter(field => field === "seed" ? inputs.has("seed") || inputs.has("noise_seed") : inputs.has(field));
}

function filterStyleSettingsForFields(settings, fields) {
  const allowed = new Set(fields || []);
  const output = {};
  Object.entries(settings || {}).forEach(([key, value]) => {
    if (!allowed.has(key) || value === null || value === undefined || String(value).trim() === "") return;
    output[key] = value;
  });
  return output;
}

function defaultAdvancedStyleValue(field) {
  const settings = state.settings || {};
  const defaults = {
    width: settings.sprite_width ?? 1024,
    height: settings.sprite_height ?? 1536,
    seed: "",
    steps: settings.sprite_steps ?? 24,
    cfg: settings.sprite_cfg ?? 5.0,
    sampler_name: settings.sprite_sampler || "euler_ancestral",
    scheduler: settings.sprite_scheduler || "normal",
    ckpt_name: settings.comfy_checkpoint || "",
  };
  return defaults[field] ?? "";
}

function renderAdvancedBackgroundField(field, value, defaultValue = "") {
  const labels = {
    width: "Cenario largura",
    height: "Cenario altura",
    seed: "Cenario seed",
    steps: "Cenario steps",
    cfg: "Cenario CFG",
    sampler_name: "Cenario sampler",
    scheduler: "Cenario scheduler",
    ckpt_name: "Cenario checkpoint",
  };
  if (field === "ckpt_name") {
    const current = value || "";
    const options = state.checkpoints.length ? state.checkpoints : [defaultValue].filter(Boolean);
    return `
      <div class="field">
        <label for="style_bg_${field}">${labels[field]}</label>
        <select id="style_bg_${field}" name="background_${field}">
          <option value="">Usar default do workbench</option>
          ${options.map(name => `<option value="${escapeAttr(name)}" ${name === current ? "selected" : ""}>${escapeHtml(name)}</option>`).join("")}
        </select>
      </div>
    `;
  }
  return `
    <div class="field">
      <label for="style_bg_${field}">${labels[field] || field}</label>
      <input id="style_bg_${field}" name="background_${field}" value="${escapeAttr(value || "")}" placeholder="${escapeAttr(defaultValue || "default do workbench")}">
    </div>
  `;
}

function defaultAdvancedBackgroundValue(field) {
  const settings = state.settings || {};
  const defaults = {
    width: settings.image_width ?? 1536,
    height: settings.image_height ?? 864,
    seed: "",
    steps: settings.background_steps ?? 28,
    cfg: settings.background_cfg ?? 6.5,
    sampler_name: settings.comfy_sampler || "dpmpp_2m_sde_gpu",
    scheduler: settings.comfy_scheduler || "karras",
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

function renderAiProviderFields(settings, provider) {
  if (provider === "openai") {
    return `
      ${valueField("openai_base_url", "OpenAI Base URL", settings.openai_base_url || "https://api.openai.com/v1")}
      ${valueField("openai_model", "OpenAI modelo", settings.openai_model || "gpt-4.1-mini")}
      ${secretField("openai_api_key", "OpenAI API key", settings.openai_api_key)}
      ${checkboxField("openai_verify_ssl", "Verificar certificado SSL", settings.openai_verify_ssl !== false)}
    `;
  }
  if (provider === "openai-compatible") {
    return `
      ${valueField("openai_compatible_base_url", "OpenAI-compatible Base URL", settings.openai_compatible_base_url || "")}
      ${valueField("openai_compatible_model", "OpenAI-compatible modelo", settings.openai_compatible_model || "")}
      ${secretField("openai_compatible_api_key", "OpenAI-compatible API key", settings.openai_compatible_api_key)}
      ${checkboxField("openai_compatible_verify_ssl", "Verificar certificado SSL", settings.openai_compatible_verify_ssl !== false)}
      ${checkboxField("openai_compatible_llama_mode", "Usar parametros llama.cpp nesta API", settings.openai_compatible_llama_mode === true)}
      ${settings.openai_compatible_llama_mode === true ? renderLlamaSettings(settings) : ""}
    `;
  }
  return `
    ${valueField("ollama_url", "URL do Ollama", settings.ollama_url || "http://127.0.0.1:11434")}
    <div class="field">
      <label for="ollama_model">Modelo de texto</label>
      <select id="ollama_model" name="ollama_model">
        ${renderOllamaModelOptions(settings.ollama_model || "mistral-nemo")}
      </select>
    </div>
    <div class="field">
      <label for="ollama_preset">Preset de performance</label>
      <select id="ollama_preset" name="ollama_preset">
        ${renderOllamaPresetOptions(settings.ollama_preset || "balanced")}
      </select>
    </div>
    <div class="field">
      <label for="ollama_custom_preset_name">Nome para preset custom</label>
      <input id="ollama_custom_preset_name" placeholder="rapido_custom">
    </div>
    <div class="settings-preset-actions full">
      <button type="button" data-action="apply-ollama-preset">Aplicar preset</button>
      <button type="button" data-action="save-ollama-preset">Salvar como preset</button>
      <button type="button" data-action="delete-ollama-preset">Excluir preset custom</button>
    </div>
    <label class="check-row full">
      <input type="checkbox" id="settings_advanced_toggle" ${state.settingsAdvanced ? "checked" : ""}>
      <span>Configurações avançadas do modelo</span>
    </label>
    ${state.settingsAdvanced ? renderOllamaAdvancedSettings(settings) : renderOllamaHiddenAdvancedSettings(settings)}
  `;
}

function renderLlamaSettings(settings) {
  return `
    <div class="field">
      <label for="llama_preset">Preset de performance llama.cpp</label>
      <select id="llama_preset" name="llama_preset">
        ${renderLlamaPresetOptions(settings.llama_preset || "balanced")}
      </select>
    </div>
    <div class="field">
      <label for="llama_custom_preset_name">Nome para preset custom</label>
      <input id="llama_custom_preset_name" placeholder="llama_rapido_custom">
    </div>
    <div class="settings-preset-actions full">
      <button type="button" data-action="apply-llama-preset">Aplicar preset</button>
      <button type="button" data-action="save-llama-preset">Salvar como preset</button>
      <button type="button" data-action="delete-llama-preset">Excluir preset custom</button>
    </div>
    <label class="check-row full">
      <input type="checkbox" id="settings_advanced_toggle" ${state.settingsAdvanced ? "checked" : ""}>
      <span>Configuracoes avancadas do llama.cpp</span>
    </label>
    ${state.settingsAdvanced ? renderLlamaAdvancedSettings(settings) : renderLlamaHiddenAdvancedSettings(settings)}
  `;
}

function renderAiProviderNotice(settings, provider) {
  if (provider === "ollama") {
    const models = state.ollamaModels.length ? state.ollamaModels.map(escapeHtml).join(", ") : "nenhum, verifique se o Ollama esta aberto.";
    return `<div class="notice">Modelos Ollama detectados: ${models}</div>`;
  }
  const model = provider === "openai" ? settings.openai_model : settings.openai_compatible_model;
  const baseUrl = provider === "openai" ? settings.openai_base_url : settings.openai_compatible_base_url;
  return `<div class="notice">Provider ativo: ${escapeHtml(aiProviderLabel(provider))}. Modelo: ${escapeHtml(model || "nao configurado")}. Base URL: ${escapeHtml(baseUrl || "nao configurada")}.</div>`;
}

function aiProviderLabel(provider) {
  if (provider === "openai") return "OpenAI API";
  if (provider === "openai-compatible") return "OpenAI-compatible";
  return "Ollama local";
}

function renderOllamaPresetOptions(currentPreset) {
  const presets = ollamaPresetDefinitions();
  return Object.entries(presets).map(([id, preset]) => (
    `<option value="${escapeAttr(id)}" ${id === currentPreset ? "selected" : ""}>${escapeHtml(preset.label || id)}</option>`
  )).join("");
}

function renderLlamaPresetOptions(currentPreset) {
  const presets = llamaPresetDefinitions();
  return Object.entries(presets).map(([id, preset]) => (
    `<option value="${escapeAttr(id)}" ${id === currentPreset ? "selected" : ""}>${escapeHtml(preset.label || id)}</option>`
  )).join("");
}

function renderOllamaAdvancedSettings(settings) {
  const values = currentOllamaValues(settings);
  return `
    <div class="notice full">${escapeHtml(ollamaPresetDescription(settings.ollama_preset || "balanced"))}</div>
    ${numberField("ollama_temperature", "Temperatura", values.ollama_temperature)}
    ${numberField("ollama_context", "Contexto maximo", values.ollama_context)}
    ${numberField("ollama_top_p", "Top P", values.ollama_top_p)}
    ${numberField("ollama_top_k", "Top K", values.ollama_top_k)}
    ${numberField("ollama_min_p", "Min P", values.ollama_min_p)}
    ${numberField("ollama_num_predict", "Tokens da cena", values.ollama_num_predict)}
    ${numberField("ollama_retry_num_predict", "Tokens em retry", values.ollama_retry_num_predict)}
    ${numberField("ollama_max_attempts", "Tentativas maximas", values.ollama_max_attempts)}
    ${numberField("ollama_repeat_penalty", "Repeat penalty", values.ollama_repeat_penalty)}
    ${numberField("ollama_repeat_last_n", "Repeat last N", values.ollama_repeat_last_n)}
    ${valueField("ollama_keep_alive", "Keep alive", values.ollama_keep_alive)}
    ${numberField("ollama_timeout", "Timeout da chamada (s)", values.ollama_timeout)}
    <label class="check-row full">
      <input type="hidden" name="ollama_think" value="false">
      <input type="checkbox" id="ollama_think" name="ollama_think" value="true" ${values.ollama_think ? "checked" : ""}>
      <span>Ativar thinking do modelo quando suportado</span>
    </label>
  `;
}

function renderLlamaAdvancedSettings(settings) {
  const values = currentLlamaValues(settings);
  return `
    <div class="notice full">${escapeHtml(llamaPresetDescription(settings.llama_preset || "balanced"))}</div>
    ${numberField("llama_temperature", "Temperatura", values.llama_temperature)}
    ${numberField("llama_top_p", "Top P", values.llama_top_p)}
    ${numberField("llama_top_k", "Top K", values.llama_top_k)}
    ${numberField("llama_min_p", "Min P", values.llama_min_p)}
    ${numberField("llama_context_window", "Janela de contexto do servidor", values.llama_context_window)}
    ${numberField("llama_max_tokens", "Tokens da cena", values.llama_max_tokens)}
    ${numberField("llama_retry_max_tokens", "Tokens em retry", values.llama_retry_max_tokens)}
    ${numberField("llama_max_attempts", "Tentativas maximas", values.llama_max_attempts)}
    ${numberField("llama_repeat_penalty", "Repeat penalty", values.llama_repeat_penalty)}
    ${numberField("llama_repeat_last_n", "Repeat last N", values.llama_repeat_last_n)}
    ${numberField("llama_timeout", "Timeout da chamada (s)", values.llama_timeout)}
    <label class="check-row full">
      <input type="hidden" name="llama_enable_thinking" value="false">
      <input type="checkbox" id="llama_enable_thinking" name="llama_enable_thinking" value="true" ${values.llama_enable_thinking ? "checked" : ""}>
      <span>Ativar thinking mode no template do llama.cpp</span>
    </label>
    <label class="check-row full">
      <input type="hidden" name="llama_cache_prompt" value="false">
      <input type="checkbox" id="llama_cache_prompt" name="llama_cache_prompt" value="true" ${values.llama_cache_prompt ? "checked" : ""}>
      <span>Reutilizar cache de prompt do llama.cpp</span>
    </label>
    <label class="check-row full">
      <input type="hidden" name="llama_timings_per_token" value="false">
      <input type="checkbox" id="llama_timings_per_token" name="llama_timings_per_token" value="true" ${values.llama_timings_per_token ? "checked" : ""}>
      <span>Pedir diagnostico detalhado de timings</span>
    </label>
    <div class="notice full">A janela de contexto deve bater com o llama-server. Com 4096, o app usa prompt narrativo compacto automaticamente. Para usar prompt completo, inicie o servidor com 8192 ou mais e salve esse valor aqui.</div>
  `;
}

function renderOllamaHiddenAdvancedSettings(settings) {
  const values = currentOllamaValues(settings);
  return OLLAMA_ADVANCED_FIELDS.map(field => (
    `<input type="hidden" id="${escapeAttr(field)}" name="${escapeAttr(field)}" value="${escapeAttr(field === "ollama_think" ? String(Boolean(values[field])) : values[field] ?? "")}">`
  )).join("");
}

function renderLlamaHiddenAdvancedSettings(settings) {
  const values = currentLlamaValues(settings);
  return LLAMA_ADVANCED_FIELDS.map(field => (
    `<input type="hidden" id="${escapeAttr(field)}" name="${escapeAttr(field)}" value="${escapeAttr(["llama_enable_thinking", "llama_cache_prompt", "llama_timings_per_token"].includes(field) ? String(Boolean(values[field])) : values[field] ?? "")}">`
  )).join("");
}

function currentOllamaValues(settings = {}) {
  const preset = ollamaPresetDefinitions()[settings.ollama_preset || "balanced"] || OLLAMA_PRESETS.balanced;
  return {
    ...(OLLAMA_PRESETS.balanced.values || {}),
    ...((preset && preset.values) || {}),
    ...OLLAMA_ADVANCED_FIELDS.reduce((acc, field) => {
      if (settings[field] !== undefined && settings[field] !== null && settings[field] !== "") acc[field] = settings[field];
      return acc;
    }, {}),
  };
}

function currentLlamaValues(settings = {}) {
  const preset = llamaPresetDefinitions()[settings.llama_preset || "balanced"] || LLAMA_PRESETS.balanced;
  return {
    ...(LLAMA_PRESETS.balanced.values || {}),
    ...((preset && preset.values) || {}),
    ...LLAMA_ADVANCED_FIELDS.reduce((acc, field) => {
      if (settings[field] !== undefined && settings[field] !== null && settings[field] !== "") acc[field] = settings[field];
      return acc;
    }, {}),
  };
}

function currentRoleLlamaValues(settings = {}, prefix = "scene_ai") {
  const presetId = settings[`${prefix}_llama_preset`] || settings.llama_preset || "balanced";
  const preset = llamaPresetDefinitions()[presetId] || LLAMA_PRESETS.balanced;
  const values = {
    ...(LLAMA_PRESETS.balanced.values || {}),
    ...((preset && preset.values) || {}),
    llama_preset: presetId,
  };
  LLAMA_ADVANCED_FIELDS.forEach(field => {
    const roleField = `${prefix}_${field}`;
    if (settings[roleField] !== undefined && settings[roleField] !== null && settings[roleField] !== "") {
      values[field] = settings[roleField];
    } else if (settings[field] !== undefined && settings[field] !== null && settings[field] !== "") {
      values[field] = settings[field];
    }
  });
  return values;
}

function ollamaPresetDefinitions() {
  const custom = state.settings?.ollama_custom_presets || {};
  const normalized = {};
  Object.entries(custom).forEach(([id, preset]) => {
    if (!preset) return;
    normalized[id] = {
      label: preset.label || id,
      description: preset.description || "Preset customizado salvo localmente.",
      custom: true,
      values: preset.values || preset,
    };
  });
  return { ...OLLAMA_PRESETS, ...normalized };
}

function llamaPresetDefinitions() {
  const custom = state.settings?.llama_custom_presets || {};
  const normalized = {};
  Object.entries(custom).forEach(([id, preset]) => {
    if (!preset) return;
    normalized[id] = {
      label: preset.label || id,
      description: preset.description || "Preset customizado salvo localmente.",
      custom: true,
      values: preset.values || preset,
    };
  });
  return { ...LLAMA_PRESETS, ...normalized };
}

function ollamaPresetDescription(presetId) {
  const preset = ollamaPresetDefinitions()[presetId] || OLLAMA_PRESETS.balanced;
  return preset.description || "";
}

function llamaPresetDescription(presetId) {
  const preset = llamaPresetDefinitions()[presetId] || LLAMA_PRESETS.balanced;
  return preset.description || "";
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
          <p>Veja o que foi enviado para IA/ComfyUI e o que voltou.</p>
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
        <p>Escreva poucas palavras, escolha como você participa e então deixe a IA montar a base editável.</p>
      </div>
      <div class="quick-create-box">
        <textarea id="quick-story-prompt" maxlength="8000" placeholder="Ex.: um deus recém desperto precisa guiar uma tribo antiga sem revelar sua verdadeira origem"></textarea>
        <div class="quick-create-actions">
          <span class="small-text">Local neste dispositivo</span>
          <button class="primary" data-action="quick-create-story">Configurar história</button>
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
          <p>Escolha como você participa antes da IA gerar a base da história.</p>
        </div>
      </section>
      <form id="story-form">
        ${renderCreateStepper(draft)}
        ${state.createStep === 0 ? renderCreateParticipation(draft) : ""}
        ${state.createStep === 1 ? renderCreateStoryDetails(draft) : ""}
        ${state.createStep === 2 ? renderCreateCharacters(draft) : ""}
        ${state.createStep === 3 ? renderCreateVisualStyle(draft) : ""}
        ${renderCreateFooter()}
      </form>
    </main>
  `;
}

function renderCreateStepper(draft) {
  const steps = [
    ["Participação", "user"],
    ["Detalhes", "document"],
    ["Personagens", "users"],
    ["Visual", "sparkles"],
  ];
  const maxStep = maxCreateStep(draft);
  return `
    <div class="create-stepper">
      ${steps.map(([label], index) => `
        <button
          type="button"
          class="${index === state.createStep ? "active" : ""} ${index < state.createStep ? "done" : ""}"
          data-action="go-create-step"
          data-step="${index}"
          ${index > maxStep ? "disabled" : ""}
        >
          <span>${index + 1}</span>
          ${label}
        </button>
      `).join("")}
    </div>
  `;
}

function renderCreateParticipation(draft) {
  const participationMode = currentParticipationMode(draft);
  return `
    <section class="panel wizard-panel">
      <h2>Como você participa</h2>
      <div class="participation-grid">
        ${PARTICIPATION_MODES.map(mode => participationButton(mode, participationMode)).join("")}
      </div>
      <p class="small-text">Essa escolha define como a IA cria o protagonista, as escolhas e os sprites antes de gerar a base da história.</p>
      <div class="form-grid">
        <div class="field full">
          <label for="story_prompt">Ideia inicial</label>
          <textarea id="story_prompt" name="story_prompt" rows="4" maxlength="8000" placeholder="Descreva o conflito, o tipo de protagonista e o clima da história.">${escapeHtml(draft.story_prompt)}</textarea>
        </div>
      </div>
    </section>
  `;
}

function renderCreateStoryDetails(draft) {
  return `
    <section class="panel wizard-panel">
      <h2>Detalhes da história</h2>
      <div class="form-grid">
        ${draftField("title", "Nome da história", "text", "Crônicas de Elaria", draft.title)}
        ${draftField("genre", "Gênero", "text", "fantasia, mistério", draft.genre)}
        ${draftField("tone", "Tom", "text", "dramático, melancólico", draft.tone)}
        ${draftField("content_rating", "Classificação", "text", "definida pelo usuário", draft.content_rating)}
        ${draftField("language", "Idioma", "text", "pt-BR", draft.language)}
        ${draftField("starting_location", "Local inicial", "text", "biblioteca sob chuva", draft.starting_location)}
        ${draftTextarea("lore", "Lore e mundo", "lore", "Regras do mundo, conflitos, facções, cidades, magia, tecnologia...", draft.lore, true)}
        ${draftTextarea("starting_message", "Mensagem inicial", "lore", "Primeira situação que deve abrir a história.", draft.starting_message, true)}
      </div>
    </section>
  `;
}

function participationButton(mode, current) {
  return `
    <button type="button" class="participation-card ${current === mode.value ? "active" : ""}" data-action="select-pov" data-value="${mode.value}">
      <span>${escapeHtml(mode.title)}</span>
      <strong>${escapeHtml(mode.short)}</strong>
      <small>${escapeHtml(mode.description)}</small>
    </button>
  `;
}

function renderCreateCharacters(draft) {
  const participationMode = currentParticipationMode(draft);
  const playerCopy = createPlayerCopy(participationMode);
  const playerFilled = countFilled([
    draft.player_name,
    draft.player_role,
    draft.player_species,
    draft.player_gender,
    draft.player_character_type,
    draft.player_aliases,
    draft.player_description,
    draft.player_physical,
    draft.player_personality,
    draft.player_clothing,
    draft.player_relationship,
  ]);
  return `
    <section class="characters-wizard">
      <article class="character-editor-card player-character-card">
        <div class="character-editor-head">
          <div class="character-avatar">${escapeHtml((draft.player_name || "J").slice(0, 1).toUpperCase())}</div>
          <div>
            <span class="eyebrow">${escapeHtml(playerCopy.eyebrow)}</span>
            <h2>${escapeHtml(draft.player_name || playerCopy.fallbackName)}</h2>
          </div>
          <span class="field-count">${playerFilled}/11 campos</span>
        </div>
        <p class="small-text participation-note">${escapeHtml(playerCopy.note)}</p>
        <div class="form-grid">
          ${draftField("player_name", "Nome", "text", "Ari", draft.player_name)}
          ${draftField("player_role", "Papel na história", "text", "aprendiz exilado", draft.player_role)}
          ${draftField("player_species", "Especie", "text", "", draft.player_species)}
          ${draftField("player_gender", "Genero", "text", "", draft.player_gender)}
          ${draftField("player_character_type", "Tipo", "text", "", draft.player_character_type)}
          ${draftField("player_aliases", "Aliases", "text", "", draft.player_aliases)}
          ${draftTextarea("player_description", "Descricao", "character", "", draft.player_description)}
          ${draftTextarea("player_physical", "Descrição física", "character", "", draft.player_physical)}
          ${draftTextarea("player_personality", "Personalidade", "character", "", draft.player_personality)}
          ${draftTextarea("player_clothing", "Vestimenta", "character", "", draft.player_clothing)}
          ${draftTextarea("player_relationship", "Relação com protagonista", "character", "", draft.player_relationship)}
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

function createPlayerCopy(mode) {
  if (mode === "narrator") {
    return {
      eyebrow: "Protagonista narrativo opcional",
      fallbackName: "Protagonista",
      note: "No modo narrador, você não é esse personagem. Preencha apenas se a história tiver um protagonista central; ele será tratado como parte do elenco.",
    };
  }
  if (mode === "third_person") {
    return {
      eyebrow: "Protagonista controlado",
      fallbackName: "Jogador",
      note: "Na terceira pessoa, você controla esse protagonista e ele pode aparecer na tela com sprite quando estiver em cena.",
    };
  }
  return {
    eyebrow: "Seu personagem",
    fallbackName: "Jogador",
    note: "Na primeira pessoa, esse personagem representa você, mas não aparece na tela e não gera sprite.",
  };
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
  const nextLabel = state.createStep === 0 ? "Gerar base e avançar" : "Próximo";
  return `
    <div class="wizard-footer">
      <button type="button" data-action="dashboard">Cancelar</button>
      <div>
        ${state.createStep > 0 ? `<button type="button" data-action="create-step-back">Voltar</button>` : ""}
        ${state.createStep < 3 ? `<button class="primary" type="button" data-action="create-step-next">${nextLabel}</button>` : `<button class="primary" type="submit">Criar e jogar</button>`}
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
  syncTypewriterState(scene, currentDialogue);
  const currentLineComplete = isTypewriterComplete(scene, currentDialogue);
  const dialogueComplete = !dialogueSequence.length || (state.dialogueIndex >= dialogueSequence.length - 1 && currentLineComplete);
  const currentSpeaker = currentDialogue && normalizeName(currentDialogue.character) !== "narrador" ? currentDialogue.character : "";
  const activeSpeaker = isCharacterOnScreen(scene, currentSpeaker) ? currentSpeaker : "";
  const background = scene ? findSceneBackground(scene) : null;
  const backgroundFilterOpacity = boundedBackgroundFilterOpacity(state.backgroundFilterOpacity);
  const focusedSpeaker = selectedNextSpeakerName(scene);
  return `
    <main class="vn-view" style="--background-filter-opacity: ${backgroundFilterOpacity / 100}">
      <div class="stage" ${background?.url ? `style="background-image: url('${escapeAttr(background.url)}')"` : ""}></div>
      <div class="vn-toolbar">
        <div class="vn-display-controls">
          <label class="sprite-view-select">
            <span>Sprites</span>
            <select id="sprite-view-mode">
              <option value="distant" ${state.spriteViewMode === "distant" ? "selected" : ""}>Distante</option>
              <option value="close" ${state.spriteViewMode === "close" ? "selected" : ""}>Aproximado</option>
            </select>
          </label>
          <label class="background-filter-control" title="Filtro de Opacidade do Cenario">
            <span>Filtro de Opacidade do Cenario</span>
            <input id="background-filter-opacity" type="range" min="0" max="100" step="1" value="${backgroundFilterOpacity}">
            <output>${backgroundFilterOpacity}%</output>
          </label>
        </div>
      </div>
      <div class="vn-action-menu ${state.playMenuOpen ? "open" : ""}">
        <button
          class="vn-menu-toggle"
          type="button"
          data-action="toggle-play-menu"
          aria-label="Menu da historia"
          aria-expanded="${state.playMenuOpen ? "true" : "false"}"
          title="Menu"
        >
          <img src="/icons/cardapio-hamburguer.png" alt="" aria-hidden="true">
          <span class="sr-only">Menu</span>
        </button>
        <div class="vn-menu-items" role="menu" aria-label="Acoes da historia">
          <button type="button" data-action="dashboard" role="menuitem">Sair</button>
          <button type="button" data-drawer="lore" role="menuitem">Menu</button>
          <button type="button" class="${state.editMode ? "primary" : ""}" data-action="toggle-edit-mode" role="menuitem">Editar</button>
          <button type="button" data-action="register-memory" role="menuitem">Register</button>
          <button type="button" data-drawer="scene" role="menuitem">Cena</button>
          <button type="button" data-drawer="history" role="menuitem">Historico</button>
          <button type="button" data-drawer="characters" role="menuitem">Personagens</button>
          <button type="button" data-action="logs" role="menuitem">Logs</button>
          <button type="button" data-action="depict-scene" role="menuitem">Depict</button>
        </div>
      </div>
      <div class="sprite-layer ${state.spriteEditMode ? "sprite-editing" : ""}">
        ${renderSprites(scene, activeSpeaker, dialogueComplete, currentDialogue)}
      </div>
      <section class="vn-dialogue">
        ${renderInteractionBlock(scene, currentDialogue, dialogueComplete, currentLineComplete)}
        ${state.editMode ? renderSceneEditPanel(scene) : ""}
        ${focusedSpeaker ? `<div class="next-speaker-focus ${dialogueComplete ? "" : "hidden"}">Proxima fala: ${escapeHtml(focusedSpeaker)}</div>` : ""}
        <div class="choices ${dialogueComplete ? "" : "hidden"}">
          ${(scene?.choices || []).map(choice => `<button data-action="choose" data-choice="${escapeAttr(choice)}">${escapeHtml(choice)}</button>`).join("")}
        </div>
        <div class="input-row ${dialogueComplete ? "" : "hidden"}">
          <div class="prompt-box">
            <textarea id="custom-action" maxlength="5000" placeholder="Escreva uma acao, fala ou direcao para a IA. Use [[ordem direta]] para instrucoes explicitas, ex.: [[Nao troque de cenario]]" ${state.busy ? "disabled" : ""}></textarea>
            <span class="input-count">0/5000</span>
          </div>
          <div class="input-actions-row">
            <button type="button" class="sprite-edit-toggle ${state.spriteEditMode ? "active" : ""}" data-action="toggle-sprite-edit-mode">Editar</button>
            <div class="redo-menu-wrap input-redo-menu ${state.redoMenuOpen ? "open" : ""}">
              <button
                type="button"
                class="redo-action"
                data-action="toggle-redo-menu"
                aria-haspopup="menu"
                aria-expanded="${state.redoMenuOpen ? "true" : "false"}"
                ${state.busy ? "disabled" : ""}
              >Refazer</button>
              <div class="redo-submenu" role="menu" aria-label="Opcoes de Refazer">
                <button type="button" data-action="regenerate-current-scene" role="menuitem">Regerar cena</button>
                <button type="button" data-action="open-redo-new-input" role="menuitem">Regerar cena com novo input</button>
              </div>
            </div>
            <button class="primary continue-action" data-action="send-custom" ${state.busy ? "disabled" : ""}>Continuar</button>
          </div>
        </div>
      </section>
    </main>
  `;
}

function boundedBackgroundFilterOpacity(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 50;
  return Math.max(0, Math.min(100, Math.round(number)));
}

function renderInteractionBlock(scene, currentDialogue, dialogueComplete, currentLineComplete = true) {
  if (!scene) {
    return `
      <div class="dialogue-box narrator">
        <div class="dialogue-content">
          <div class="scene-text">Clique em continuar para gerar a primeira resposta.</div>
        </div>
      </div>
    `;
  }
  const dialogue = currentDialogue || (scene.scene_text ? { character: "Narrador", text: scene.scene_text } : null);
  if (!dialogue) {
    return `
      <div class="dialogue-box narrator">
        <div class="dialogue-content">
          <div class="scene-text error-text">Cena invalida: a IA nao retornou texto de cena ou dialogo.</div>
        </div>
      </div>
    `;
  }
  const isNarrator = normalizeName(dialogue.character) === "narrador";
  const visibleText = currentLineComplete ? (dialogue.text || "") : getTypewriterVisibleText(dialogue);
  return `
    <div class="dialogue-box ${isNarrator ? "narrator" : "character"}">
      ${isNarrator ? "" : renderDialogueNameplate(scene, dialogue)}
      <div class="dialogue-content">
        <p class="active-dialogue-text" data-typewriter-text="true">${escapeHtml(visibleText)}${currentLineComplete ? "" : `<span class="typewriter-caret"></span>`}</p>
        ${dialogueComplete ? "" : `
          <button class="dialogue-next" type="button" data-action="next-dialogue" aria-label="Proxima fala">
            <img src="/icons/angulo-duplo-pequeno-direito.png" alt="" aria-hidden="true">
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
    resetTypewriter();
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
    sequence.push(...paginateDialogue({ character: "Narrador", expression: "neutral", text: sceneText }));
  }
  dialogues.forEach(dialogue => {
    if (dialogue?.text) sequence.push(...paginateDialogue(dialogue));
  });
  if (!sequence.length && sceneText) {
    sequence.push(...paginateDialogue({ character: "Narrador", expression: "neutral", text: sceneText }));
  }
  return sequence;
}

function paginateDialogue(dialogue) {
  const text = String(dialogue?.text || "").trim();
  if (!text) return [];
  const pages = splitDialogueTextIntoPages(text, dialoguePageCharLimit());
  return pages.map((page, index) => ({
    ...dialogue,
    text: page,
    source_text: text,
    page_index: index,
    page_count: pages.length,
  }));
}

function dialoguePageCharLimit() {
  const viewport = Math.max(320, window.innerWidth || 1024);
  const horizontalInsets = viewport <= 760 ? 10 * 2 + 18 + 64 : 24 * 2 + 30 + 84;
  const availableWidth = Math.max(220, viewport - horizontalInsets);
  const fontSize = viewport <= 760 ? 19 : Math.min(25, Math.max(19, viewport * 0.0205));
  const averageCharacterWidth = fontSize * 0.52;
  const charsPerLine = Math.max(28, Math.min(110, Math.floor(availableWidth / averageCharacterWidth)));
  return Math.max(70, Math.floor(charsPerLine * MAX_DIALOGUE_PAGE_LINES * 0.82));
}

function splitDialogueTextIntoPages(text, maxChars) {
  const normalized = String(text || "").replace(/\r/g, "").trim();
  if (!normalized) return [];
  const paragraphs = normalized.split(/\n+/).map(part => part.trim()).filter(Boolean);
  const pages = [];
  let current = "";
  paragraphs.forEach(paragraph => {
    const chunks = splitParagraphIntoReadableChunks(paragraph, maxChars);
    chunks.forEach(chunk => {
      const candidate = current ? `${current}\n${chunk}` : chunk;
      if (current && candidate.length > maxChars) {
        pages.push(current);
        current = chunk;
      } else {
        current = candidate;
      }
    });
  });
  if (current) pages.push(current);
  return pages.length ? pages : [normalized];
}

function splitParagraphIntoReadableChunks(paragraph, maxChars) {
  const sentences = String(paragraph || "").match(/[^.!?…]+[.!?…]+["')\]]*|[^.!?…]+$/g) || [paragraph];
  const chunks = [];
  let current = "";
  sentences.map(item => item.trim()).filter(Boolean).forEach(sentence => {
    if (sentence.length > maxChars) {
      if (current) {
        chunks.push(current);
        current = "";
      }
      chunks.push(...splitLongTextByWords(sentence, maxChars));
      return;
    }
    const candidate = current ? `${current} ${sentence}` : sentence;
    if (current && candidate.length > maxChars) {
      chunks.push(current);
      current = sentence;
    } else {
      current = candidate;
    }
  });
  if (current) chunks.push(current);
  return chunks;
}

function splitLongTextByWords(text, maxChars) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const chunks = [];
  let current = "";
  words.forEach(word => {
    const candidate = current ? `${current} ${word}` : word;
    if (current && candidate.length > maxChars) {
      chunks.push(current);
      current = word;
    } else {
      current = candidate;
    }
  });
  if (current) chunks.push(current);
  return chunks;
}

function isDialogueComplete(scene) {
  const sequence = getDialogueSequence(scene);
  return !sequence.length || state.dialogueIndex >= sequence.length - 1;
}

function dialogueLineKey(scene, dialogue) {
  if (!scene || !dialogue) return "";
  return `${scene.id || "scene"}:${state.dialogueIndex}:${normalizeName(dialogue.character)}:${dialogue.page_index ?? 0}:${String(dialogue.text || "").length}`;
}

function syncTypewriterState(scene, dialogue) {
  const key = dialogueLineKey(scene, dialogue);
  if (!key) {
    resetTypewriter();
    return;
  }
  if (state.typewriterKey !== key) {
    stopTypewriterTimer();
    state.typewriterKey = key;
    state.typewriterVisible = 0;
    state.typewriterDone = !String(dialogue.text || "").length;
  }
}

function getTypewriterVisibleText(dialogue) {
  const text = String(dialogue?.text || "");
  return text.slice(0, Math.min(text.length, state.typewriterVisible));
}

function isTypewriterComplete(scene, dialogue) {
  if (!dialogue) return true;
  const key = dialogueLineKey(scene, dialogue);
  return state.typewriterKey === key && (state.typewriterDone || state.typewriterVisible >= String(dialogue.text || "").length);
}

function runPostRenderEffects() {
  if (state.route !== "play") {
    stopTypewriterTimer();
    return;
  }
  const scene = latestScene(state.activeStory);
  const dialogue = getDialogueSequence(scene)[state.dialogueIndex] || null;
  startTypewriter(scene, dialogue);
}

function startTypewriter(scene, dialogue) {
  if (!dialogue || state.typewriterDone || state.typewriterTimer) return;
  const key = dialogueLineKey(scene, dialogue);
  const text = String(dialogue.text || "");
  if (!key || state.typewriterKey !== key || state.typewriterVisible >= text.length) {
    completeTypewriterLine(false);
    return;
  }
  state.typewriterTimer = setInterval(() => {
    if (state.typewriterKey !== key) {
      stopTypewriterTimer();
      return;
    }
    const step = text[state.typewriterVisible] === " " ? 2 : 1;
    state.typewriterVisible = Math.min(text.length, state.typewriterVisible + step);
    const target = document.querySelector("[data-typewriter-text='true']");
    if (target) {
      target.textContent = text.slice(0, state.typewriterVisible);
      if (state.typewriterVisible < text.length) {
        const caret = document.createElement("span");
        caret.className = "typewriter-caret";
        target.appendChild(caret);
      }
    }
    if (state.typewriterVisible % 3 === 0) playTypewriterTick(text[state.typewriterVisible - 1]);
    if (state.typewriterVisible >= text.length) completeTypewriterLine(true);
  }, 18);
}

function completeTypewriterLine(rerender = true) {
  stopTypewriterTimer();
  state.typewriterDone = true;
  const scene = latestScene(state.activeStory);
  const dialogue = getDialogueSequence(scene)[state.dialogueIndex] || null;
  const target = document.querySelector("[data-typewriter-text='true']");
  if (target && dialogue) target.textContent = dialogue.text || "";
  if (rerender) render();
}

function resetTypewriter() {
  stopTypewriterTimer();
  state.typewriterKey = "";
  state.typewriterVisible = 0;
  state.typewriterDone = false;
}

function stopTypewriterTimer() {
  if (state.typewriterTimer) {
    clearInterval(state.typewriterTimer);
    state.typewriterTimer = null;
  }
}

function playTypewriterTick(character) {
  if (!character || /\s/.test(character)) return;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    state.typewriterAudio = state.typewriterAudio || new AudioContextClass();
    const context = state.typewriterAudio;
    if (context.state === "suspended") context.resume().catch(() => {});
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = 820 + Math.random() * 140;
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.018, context.currentTime + 0.004);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.026);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.03);
  } catch {
    // Browser audio can be blocked until the first user gesture.
  }
}

function isCharacterOnScreen(scene, name) {
  const key = normalizeName(name);
  if (!key) return false;
  return getVisualSceneCharacters(scene).some(character => normalizeName(character.name) === key);
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

function renderSprites(scene, activeSpeaker = "", interactionReady = false, currentDialogue = null) {
  const characters = getSpriteRenderItems(scene);
  if (!characters.length) {
    state.spriteExpressionMap = {};
    return "";
  }
  const viewMode = state.spriteViewMode === "close" ? "close" : "distant";
  const activeKey = normalizeName(activeSpeaker);
  const selectedKey = normalizeName(selectedNextSpeakerName(scene));
  const clickable = interactionReady && !state.busy;
  const nextExpressionMap = {};
  const editPanels = [];
  const markup = characters.map((item, index) => {
    const character = item.character;
    const registeredCharacter = findStoryCharacter(character.name);
    if (!registeredCharacter) return "";
    const effectiveExpression = effectiveSpriteExpression(character, currentDialogue);
    const sprite = findCharacterSprite(character.name, effectiveExpression);
    const characterKey = normalizeName(character.name);
    const spriteKey = sprite?.url || "";
    const previousSpriteKey = state.spriteExpressionMap?.[characterKey] || "";
    const expressionChanged = Boolean(spriteKey && previousSpriteKey && previousSpriteKey !== spriteKey && !item.entering && !item.exiting);
    if (spriteKey && !item.exiting) nextExpressionMap[characterKey] = spriteKey;
    const focusClass = item.exiting
      ? "inactive character-inactive exiting"
      : activeKey
        ? (characterKey === activeKey ? "active character-active" : "inactive character-inactive")
        : "neutral";
    const motionClass = `${item.entering ? "entering" : ""} ${item.exiting ? "exiting" : ""}`.trim();
    const interactionClass = `${clickable && !item.exiting ? "sprite-clickable" : ""} ${selectedKey && characterKey === selectedKey ? "speaker-selected" : ""} ${expressionChanged ? "expression-swapping" : ""}`.trim();
    const clickAttrs = clickable && !item.exiting
      ? `data-action="select-sprite-speaker" data-name="${escapeAttr(character.name)}" title="Ouvir ${escapeAttr(character.name)} agora" role="button" tabindex="0"`
      : "";
    const slot = spriteSlotLayout(index, characters.length, character.position || "center");
    if (sprite?.url) {
      if (state.spriteEditMode && !item.exiting) {
        editPanels.push(renderSpriteEditPanel(registeredCharacter, character, slot, viewMode));
      }
      return `
        <div class="scene-sprite-frame ${escapeAttr(slot.className)} ${viewMode} ${focusClass} ${motionClass} ${interactionClass}" ${slot.left ? `style="left: ${slot.left}%"` : ""}>
          ${expressionChanged ? `
            <img
              class="scene-sprite expression-old"
              src="${escapeAttr(previousSpriteKey)}"
              alt=""
              aria-hidden="true"
              loading="eager"
              decoding="async"
            >
          ` : ""}
          <img
            class="scene-sprite ${expressionChanged ? "expression-new" : ""}"
            src="${escapeAttr(sprite.url)}"
            alt="${escapeAttr(character.name)}"
            ${clickAttrs}
            loading="eager"
            decoding="async"
          >
        </div>
      `;
    }
    return `
      <div class="sprite-standin ${escapeAttr(slot.className)} ${focusClass} ${motionClass} ${interactionClass}" ${clickAttrs} ${slot.left ? `style="left: ${slot.left}%"` : ""}>
        <div>
          <strong>${escapeHtml(character.name)}</strong>
          <span>${escapeHtml(effectiveExpression || "neutral")}</span>
          <em>sprite pendente</em>
        </div>
      </div>
    `;
  }).join("");
  state.spriteExpressionMap = nextExpressionMap;
  return `${markup}${editPanels.join("")}`;
}

function effectiveSpriteExpression(sceneCharacter, currentDialogue) {
  if (!styleExpressionsEnabled()) return sceneCharacter.expression || "neutral";
  if (currentDialogue && dialogueTargetsCharacter(currentDialogue, sceneCharacter)) {
    return normalizeExpression(currentDialogue.expression || "neutral");
  }
  return normalizeExpression(sceneCharacter.expression || "neutral");
}

function dialogueTargetsCharacter(dialogue, sceneCharacter) {
  const speakerKey = normalizeName(dialogue?.character);
  const sceneName = sceneCharacter?.name || "";
  if (!speakerKey || !sceneName || speakerKey === "narrador") return false;
  if (speakerKey === normalizeName(sceneName)) return true;
  const registered = findStoryCharacter(sceneName);
  const names = [
    registered?.name,
    sceneName,
    ...String(registered?.aliases || "").split(",").map(alias => alias.trim()),
  ];
  return names.some(value => normalizeName(value) === speakerKey);
}

function selectedNextSpeakerName(scene = latestScene(state.activeStory)) {
  const focus = state.nextSpeakerFocus;
  if (!focus?.name || !scene) return "";
  const selectedKey = normalizeName(focus.name);
  const visible = getVisualSceneCharacters(scene).find(character => normalizeName(character.name) === selectedKey);
  return visible?.name || "";
}

function getSpriteRenderItems(scene) {
  const now = Date.now();
  const current = getVisualSceneCharacters(scene).map(character => ({
    key: normalizeName(character.name),
    character: { ...character },
  })).filter(item => item.key);
  const currentKeys = new Set(current.map(item => item.key));
  const previous = (state.spriteRoster || []).filter(item => isRegisteredVisualCharacter(item.character?.name));

  previous.forEach(item => {
    if (!currentKeys.has(item.key) && !state.spriteExitMap[item.key]) {
      state.spriteExitMap[item.key] = {
        ...item,
        expires: now + 1240,
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

function renderSpriteEditPanel(character, sceneCharacter, slot = {}, viewMode = "distant") {
  if (!character?.id) return "";
  const name = character.name || sceneCharacter?.name || "Personagem";
  return `
    <div class="sprite-edit-anchor ${escapeAttr(slot.className || "")} ${escapeAttr(viewMode)}" ${slot.left ? `style="left: ${slot.left}%"` : ""}>
      <div class="sprite-edit-panel">
        <strong title="${escapeAttr(name)}">${escapeHtml(name)}</strong>
        <div class="sprite-edit-actions">
          <button type="button" data-action="open-character-profile" data-character-id="${escapeAttr(character.id)}" title="Ficha do Personagem" aria-label="Ficha do Personagem">
            <img src="/icons/cartao-de-identificacao.png" alt="" aria-hidden="true">
          </button>
          <button type="button" data-action="character-appearance-placeholder" data-character-id="${escapeAttr(character.id)}" title="Aparência" aria-label="Aparência">
            <img src="/icons/camiseta.png" alt="" aria-hidden="true">
          </button>
          <button type="button" data-action="refresh-sprite" data-character-id="${escapeAttr(character.id)}" title="Regenerar Sprite" aria-label="Regenerar Sprite">
            <img src="/icons/retuite-de-flechas.png" alt="" aria-hidden="true">
          </button>
          <button type="button" data-action="remove-character-from-scene" data-name="${escapeAttr(name)}" title="Remover personagem da cena" aria-label="Remover personagem da cena">
            <img src="/icons/sair-do-usuario.png" alt="" aria-hidden="true">
          </button>
          <button type="button" class="danger" data-action="delete-character" data-character-id="${escapeAttr(character.id)}" data-character-name="${escapeAttr(name)}" title="Deletar Personagem" aria-label="Deletar Personagem">
            <img src="/icons/deletar-usuario.png" alt="" aria-hidden="true">
          </button>
        </div>
      </div>
    </div>
  `;
}

function getVisualSceneCharacters(scene) {
  const seen = new Set();
  return (scene?.characters_on_screen || []).filter(character => {
    const key = normalizeName(character?.name);
    if (!key || seen.has(key) || !isRegisteredVisualCharacter(character.name)) return false;
    seen.add(key);
    return true;
  });
}

function isRegisteredVisualCharacter(name) {
  const character = findStoryCharacter(name);
  return !!character && isVisualCharacter(character);
}

function storyParticipationMode(story = state.activeStory) {
  return normalizeParticipationMode(story?.participation_mode || story?.point_of_view);
}

function isVisualCharacter(character, story = state.activeStory) {
  if (!character) return false;
  return !(storyParticipationMode(story) === "first_person" && Number(character.is_player || 0) === 1);
}

function spriteSlotLayout(index, total, preferredPosition = "center") {
  const classic = ["left", "center", "right"];
  if (total <= 1) return { className: "center", left: "" };
  if (total === 2) return { className: index === 0 ? "left" : "right", left: "" };
  if (total === 3) return { className: classic[index] || preferredPosition, left: "" };
  const positionsByTotal = {
    4: [32, 44, 56, 68],
    5: [28, 39, 50, 61, 72],
    6: [24, 34, 44, 56, 66, 76],
  };
  const positions = positionsByTotal[Math.min(Math.max(total, 4), 6)];
  return {
    className: "slot-dynamic",
    left: positions[Math.min(index, positions.length - 1)],
  };
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
  }, 1320);
}

function renderDrawer() {
  const title = {
    history: "Histórico",
    characters: "Personagens",
    appearanceDesigner: "Design de Aparências",
    lore: "Lore e memória",
    scene: "Cena",
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
        ${state.drawer === "appearanceDesigner" ? renderAppearanceDesignerDrawer() : ""}
        ${state.drawer === "lore" ? renderLoreDrawer() : ""}
        ${state.drawer === "scene" ? renderSceneDrawer() : ""}
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

function renderSceneDrawer() {
  const story = state.activeStory;
  const scene = latestScene(story);
  if (!story || !scene) return `<div class="empty-state">Nenhuma cena ativa.</div>`;
  const background = findSceneBackground(scene);
  const onScreen = scene.characters_on_screen || [];
  const onScreenKeys = new Set(onScreen.map(item => normalizeName(item.name)));
  const available = (story.characters || []).filter(character => !onScreenKeys.has(normalizeName(character.name)));
  return `
    <section class="scene-drawer-section">
      <div class="scene-drawer-head">
        <h3>Background atual</h3>
        <button type="button" class="icon-button" title="Regenerar cenário" aria-label="Regenerar cenário" data-action="open-regenerate-background">&#8635;</button>
      </div>
      ${background?.url ? `
        <figure class="scene-background-preview">
          <img src="${escapeAttr(background.url)}" alt="">
          <figcaption>${escapeHtml(scene.background_prompt || background.prompt || "Background da cena")}</figcaption>
        </figure>
      ` : `
        <p class="small-text">${escapeHtml(scene.background_prompt || "Nenhum background gerado para esta cena.")}</p>
      `}
    </section>

    <section class="scene-drawer-section">
      <div class="scene-drawer-head">
        <h3>Personagens em cena</h3>
        <span>${onScreen.length}/6</span>
      </div>
      ${onScreen.length ? `
        <div class="scene-character-list">
          ${onScreen.map(character => `
            <div class="scene-character-row">
              <div>
                <strong>${escapeHtml(character.name || "Sem nome")}</strong>
                <span>${escapeHtml(character.expression || "neutral")} · ${escapeHtml(character.position || "center")}</span>
              </div>
              <button type="button" data-action="remove-character-from-scene" data-name="${escapeAttr(character.name || "")}">Remover</button>
            </div>
          `).join("")}
        </div>
      ` : `<p class="small-text">Nenhum personagem marcado como visivel nesta cena.</p>`}

      <div class="scene-add-character">
        <select id="scene-add-character-select" ${available.length && onScreen.length < 6 ? "" : "disabled"}>
          ${available.length ? available.map(character => `<option value="${escapeAttr(character.id)}">${escapeHtml(character.name || "Sem nome")}</option>`).join("") : `<option value="">Todos os personagens ja estao em cena</option>`}
        </select>
        <button type="button" data-action="add-character-to-scene" ${available.length && onScreen.length < 6 ? "" : "disabled"}>Incluir personagem na cena</button>
      </div>
    </section>

    <section class="scene-drawer-section">
      <h3>Informacoes da cena atual</h3>
      <article class="scene-card current-scene-card">
        <h3>Cena ${scene.scene_order}: ${escapeHtml(scene.title || "")}</h3>
        <p class="small-text">${escapeHtml(scene.scene_text || "")}</p>
        <div class="history-dialogues">
          ${(scene.dialogues || []).slice(0, 10).map(dialogue => `
            <p><strong>${escapeHtml(dialogue.character || "Narrador")}:</strong> ${escapeHtml(dialogue.text || "")}</p>
          `).join("") || `<p>Sem dialogos nesta cena.</p>`}
        </div>
        <div class="small-text">Escolhas: ${(scene.choices || []).map(escapeHtml).join(" | ") || "Nenhuma escolha registrada."}</div>
      </article>
    </section>
  `;
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
        <button type="button" data-action="open-appearance-designer" data-character-id="${escapeAttr(active?.id || "")}" ${active && isVisualCharacter(active) ? "" : "disabled"}>Appearance Designer</button>
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

function renderAppearanceDesignerDrawer() {
  const characters = (state.activeStory?.characters || []).filter(character => isVisualCharacter(character));
  if (characters.length && !characters.some(character => character.id === state.activeCharacterId)) {
    state.activeCharacterId = characters[0].id;
  }
  const character = characters.find(item => item.id === state.activeCharacterId) || characters[0];
  if (!character) return `<div class="empty-state">Nenhum personagem visual disponivel.</div>`;
  const appearances = getCharacterAppearances(character.id);
  const activeAppearance = getActiveAppearance(character);
  const referenceSprite = getAppearanceSprite(activeAppearance, "neutral");
  const scene = latestScene(state.activeStory);
  const background = scene ? findSceneBackground(scene) : null;
  const style = state.activeStory?.visual_style_record || {};
  return `
    <div class="appearance-designer">
      <div class="character-drawer-toolbar">
        <div>
          <span class="eyebrow">Design de Aparências</span>
          <strong>${escapeHtml(character.name || "Personagem")}</strong>
        </div>
        <select data-action="select-appearance-character">
          ${characters.map(item => `<option value="${escapeAttr(item.id)}" ${item.id === character.id ? "selected" : ""}>${escapeHtml(item.name || "Sem nome")}</option>`).join("")}
        </select>
      </div>
      <section class="appearance-preview" ${background?.url ? `style="background-image: url('${escapeAttr(background.url)}')"` : ""}>
        ${referenceSprite?.url ? `<img src="${escapeAttr(referenceSprite.url)}" alt="${escapeAttr(character.name)}">` : `<div class="sprite-empty">Nenhuma imagem valida para preview.</div>`}
      </section>
      <section class="appearance-section">
        <h3>Sprites de Aparências</h3>
        ${appearances.length ? `
          <div class="appearance-card-grid">
            ${appearances.map(appearance => renderAppearanceCard(character, appearance, { showRegenerate: true })).join("")}
            ${false ? appearances.map(appearance => {
              const sprite = getAppearanceSprite(appearance, "neutral");
              if (!sprite?.url) return "";
              const active = isAppearanceActive(character, appearance);
              const initial = isInitialAppearance(character.id, appearance);
              return `
                <button
                  type="button"
                  class="appearance-card ${active ? "active" : ""}"
                  data-action="set-active-appearance"
                  data-character-id="${escapeAttr(character.id)}"
                  data-appearance-id="${escapeAttr(appearance.id)}"
                >
                  <img src="${escapeAttr(sprite.url)}" alt="${escapeAttr(appearance.label || "Aparência")}">
                  <span>${escapeHtml(appearance.label || "Aparência")}</span>
                  ${active ? `<small>Ativa</small>` : ""}
                </button>
              `;
            }).join("") : ""}
          </div>
        ` : `<div class="sprite-empty">Nenhuma aparência gerada ainda.</div>`}
      </section>
      <form id="appearance-designer-form" class="appearance-section appearance-change-form" data-character-id="${escapeAttr(character.id)}" data-reference-asset-id="${escapeAttr(referenceSprite?.id || "")}">
        <h3>O que mudar</h3>
        ${style.appearance_workbench ? "" : `<p class="small-text">Configure o Workflow de Alterar Aparência no estilo atual antes de gerar.</p>`}
        <label for="appearance-change-prompt">Prompt do usuário</label>
        <textarea id="appearance-change-prompt" name="prompt" rows="5" placeholder="Ex: trocar a roupa por uma armadura escura"></textarea>
        <label class="check-row">
          <input type="checkbox" name="improve_prompt" value="true" checked>
          <span>Melhorar prompt antes de enviar</span>
        </label>
        <div class="mini-actions">
          <button type="submit" class="primary" ${style.appearance_workbench && referenceSprite?.id ? "" : "disabled"}>Gerar</button>
        </div>
      </form>
    </div>
  `;
}

function renderAppearanceCard(character, appearance, options = {}) {
  const sprite = getAppearanceSprite(appearance, "neutral");
  if (!sprite?.url) return "";
  const active = isAppearanceActive(character, appearance);
  const selected = options.selectedAppearanceId === appearance.id;
  const initial = isInitialAppearance(character.id, appearance);
  const selectAction = options.selectAction || "set-active-appearance";
  return `
    <figure class="appearance-card ${active ? "active" : ""} ${selected ? "selected" : ""}">
      ${options.showRegenerate && !initial ? `
        <button
          type="button"
          class="appearance-regenerate-button"
          data-action="open-appearance-regenerate"
          data-character-id="${escapeAttr(character.id)}"
          data-appearance-id="${escapeAttr(appearance.id)}"
          title="Regerar aparência"
          aria-label="Regerar aparência"
        >
          <img src="/icons/retuite-de-flechas.png" alt="" aria-hidden="true">
        </button>
      ` : ""}
      <button
        type="button"
        class="appearance-card-select"
        data-action="${escapeAttr(selectAction)}"
        data-character-id="${escapeAttr(character.id)}"
        data-appearance-id="${escapeAttr(appearance.id)}"
      >
        <img src="${escapeAttr(sprite.url)}" alt="${escapeAttr(appearance.label || "Aparencia")}">
        <span>${escapeHtml(appearance.label || "Aparencia")}</span>
        ${active ? `<small>Ativa</small>` : ""}
        ${selected ? `<small>Referencia</small>` : ""}
      </button>
    </figure>
  `;
}

function renderCharacterDetail(character) {
  if (state.characterEditId === character.id) return renderCharacterEditForm(character);
  const visualCharacter = isVisualCharacter(character);
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
            ${visualCharacter ? `<button class="primary" data-action="refresh-sprite" data-character-id="${escapeAttr(character.id)}">Regenerate</button>` : ""}
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
      ${visualCharacter ? renderCharacterPromptPanel(character, false) : `<div class="sprite-empty">Este personagem nao usa sprite neste modo.</div>`}
      ${visualCharacter ? renderCharacterSpriteGallery(character) : ""}
    </section>
  `;
}

function renderCharacterEditForm(character) {
  const visualCharacter = isVisualCharacter(character);
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
      ${visualCharacter ? renderCharacterPromptPanel(character, true) : `<input type="hidden" name="visual_prompt" value="">`}
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
  if (!isVisualCharacter(character)) {
    return `<div class="profile-avatar">${escapeHtml((character.name || "?").slice(0, 1).toUpperCase())}</div>`;
  }
  const sprite = getActiveAppearanceSprite(character);
  if (sprite?.url) {
    return `<img src="${escapeAttr(sprite.url)}" alt="${escapeAttr(character.name)}">`;
  }
  return `<div class="profile-avatar">${escapeHtml((character.name || "?").slice(0, 1).toUpperCase())}</div>`;
}

function renderCharacterSpriteGallery(character) {
  if (!isVisualCharacter(character)) {
    return "";
  }
  const appearances = getCharacterAppearances(character.id);
  if (!appearances.length) {
    return `<div class="sprite-empty">Nenhum sprite gerado ainda.</div>`;
  }
  return `
    <h4 class="character-sprites-title">Sprites de Aparências</h4>
    <div class="character-sprites">
      ${appearances.map(appearance => {
        const sprite = getAppearanceSprite(appearance);
        if (!sprite?.url) return "";
        const active = isAppearanceActive(character, appearance);
        return `
        <figure class="sprite-thumb-card ${active ? "active" : ""}">
          <button
            type="button"
            class="sprite-select-button"
            data-action="set-active-appearance"
            data-character-id="${escapeAttr(character.id)}"
            data-appearance-id="${escapeAttr(appearance.id)}"
            title="Usar como sprite ativo"
            aria-label="Usar ${escapeAttr(appearance.label || "aparência")} como sprite ativo"
          >${active ? "Ativa" : "Usar"}</button>
          <button
            type="button"
            class="sprite-expression-button"
            data-action="open-expression-modal"
            data-character-id="${escapeAttr(character.id)}"
            data-sprite-id="${escapeAttr(sprite.id)}"
            title="Express&otilde;es"
            aria-label="Express&otilde;es de ${escapeAttr(character.name)}"
          >
            <img src="/icons/sorriso.png" alt="" aria-hidden="true">
          </button>
          <button
            type="button"
            class="sprite-preview-button"
            data-action="open-sprite-preview"
            data-character-id="${escapeAttr(character.id)}"
            data-sprite-id="${escapeAttr(sprite.id)}"
            title="Visualizar sprite"
            aria-label="Visualizar sprite de ${escapeAttr(character.name)}"
          >
            <img src="/icons/ampliar.png" alt="" aria-hidden="true">
          </button>
          <img src="${escapeAttr(sprite.url)}" alt="${escapeAttr(character.name)} ${escapeAttr(sprite.expression || "neutral")}">
          <figcaption>${escapeHtml(appearance.label || "Aparência")}</figcaption>
        </figure>
      `; }).join("")}
    </div>
  `;
}

function getCharacterSprites(characterId) {
  return (state.activeStory?.assets || []).filter(asset => (
    asset.asset_type === "sprite" &&
    asset.character_id === characterId &&
    asset.url &&
    (normalizeExpression(asset.expression) === "neutral" || !asset.base_asset_id || asset.base_asset_id === asset.id)
  ));
}

function getCharacterAppearances(characterId) {
  const appearances = (state.activeStory?.appearances || [])
    .filter(appearance => appearance.character_id === characterId)
    .sort((a, b) => Number(b.is_active || 0) - Number(a.is_active || 0) || Number(b.created_at || 0) - Number(a.created_at || 0));
  if (appearances.length) return appearances;
  return getCharacterSprites(characterId).map((sprite, index) => ({
    id: sprite.appearance_id || sprite.id,
    character_id: characterId,
    label: index === 0 ? "Inicial" : `Aparência ${index + 1}`,
    primary_asset_id: sprite.id,
    neutral_asset_id: sprite.id,
    is_active: index === 0,
    created_at: sprite.created_at || 0,
  }));
}

function isAppearanceActive(character, appearance) {
  if (!character || !appearance) return false;
  return character.active_appearance_id
    ? character.active_appearance_id === appearance.id
    : appearance.is_active === true;
}

function isInitialAppearance(characterId, appearance) {
  if (!characterId || !appearance) return false;
  const appearances = (state.activeStory?.appearances || [])
    .filter(item => item.character_id === characterId)
    .sort((a, b) => Number(a.created_at || 0) - Number(b.created_at || 0));
  return appearances.length ? appearances[0].id === appearance.id : false;
}

function getActiveAppearance(character) {
  if (!character) return null;
  const appearances = getCharacterAppearances(character.id);
  return appearances.find(appearance => isAppearanceActive(character, appearance)) || appearances[0] || null;
}

function getAppearanceSprite(appearance, expression = "neutral") {
  if (!appearance) return null;
  const assets = state.activeStory?.assets || [];
  const normalized = normalizeExpression(expression);
  const byId = id => assets.find(asset => asset.id === id && asset.url);
  if (normalized !== "neutral") {
    const baseId = appearance.neutral_asset_id || appearance.primary_asset_id;
    const expressionAsset = assets.find(asset => (
      asset.asset_type === "sprite" &&
      asset.url &&
      asset.appearance_id === appearance.id &&
      normalizeExpression(asset.expression) === normalized
    )) || assets.find(asset => (
      asset.asset_type === "sprite" &&
      asset.url &&
      baseId &&
      (asset.base_asset_id === baseId || asset.base_asset_id === byId(baseId)?.base_asset_id) &&
      normalizeExpression(asset.expression) === normalized
    ));
    if (expressionAsset) return expressionAsset;
  }
  return byId(appearance.neutral_asset_id) ||
    byId(appearance.primary_asset_id) ||
    assets.find(asset => asset.asset_type === "sprite" && asset.url && asset.appearance_id === appearance.id && normalizeExpression(asset.expression) === "neutral") ||
    assets.find(asset => asset.asset_type === "sprite" && asset.url && asset.appearance_id === appearance.id) ||
    null;
}

function getActiveAppearanceSprite(character, expression = "neutral") {
  const appearance = getActiveAppearance(character);
  return getAppearanceSprite(appearance, expression) || getCharacterSprites(character?.id)[0] || null;
}

function renderExpressionsModal() {
  const character = (state.activeStory?.characters || []).find(item => item.id === state.modal.characterId);
  const baseSprite = (state.activeStory?.assets || []).find(item => item.id === state.modal.baseSpriteId && item.url);
  if (!character || !baseSprite) return "";
  const prompts = normalizeCharacterExpressionPrompts(character.expression_prompts || {});
  const selected = new Set(state.modal.selectedExpressions || []);
  const editingExpression = state.modal.editingExpression || "";
  const selectedCount = selected.size;
  return `
    <div class="modal-backdrop">
      <div class="modal expression-modal" role="dialog" aria-modal="true" aria-label="Express&otilde;es">
        <div class="sprite-preview-head">
          <div>
            <h2>Express&otilde;es</h2>
            <span>${escapeHtml(character.name || "Personagem")}</span>
          </div>
          <button type="button" data-action="close-modal">Fechar</button>
        </div>
        <div class="expression-grid">
          ${SPRITE_EXPRESSION_KEYS.map(expression => {
            const asset = getSpriteExpressionAsset(baseSprite, expression) || baseSprite;
            const label = EXPRESSION_LABELS[expression] || expression;
            return `
              <figure class="expression-card">
                <label class="expression-select-checkbox" title="Selecionar ${escapeAttr(label)}">
                  <input
                    type="checkbox"
                    data-action="toggle-expression-selection"
                    data-expression="${escapeAttr(expression)}"
                    ${selected.has(expression) ? "checked" : ""}
                  >
                </label>
                <button
                  type="button"
                  class="expression-preview-button"
                  title="Visualizar"
                  aria-label="Visualizar ${escapeAttr(label)}"
                  data-action="open-expression-preview"
                  data-character-id="${escapeAttr(character.id)}"
                  data-sprite-id="${escapeAttr(baseSprite.id)}"
                  data-expression="${escapeAttr(expression)}"
                >
                  <img src="/icons/ampliar.png" alt="" aria-hidden="true">
                </button>
                <img src="${escapeAttr(asset.url || baseSprite.url || "")}" alt="${escapeAttr(character.name)} ${escapeAttr(label)}">
                <figcaption>${escapeHtml(label)}</figcaption>
                <div class="expression-prompt-field">
                  <textarea
                    id="expression-prompt-${escapeAttr(expression)}"
                    rows="5"
                    ${editingExpression === expression ? "" : "readonly"}
                  >${escapeHtml(prompts[expression] || "")}</textarea>
                  <button
                    type="button"
                    class="expression-prompt-edit-button"
                    data-action="${editingExpression === expression ? "save-character-expression-prompt" : "edit-character-expression-prompt"}"
                    data-expression="${escapeAttr(expression)}"
                    title="${editingExpression === expression ? "Salvar prompt" : "Editar prompt"}"
                    aria-label="${editingExpression === expression ? "Salvar prompt" : "Editar prompt"} de ${escapeAttr(label)}"
                  >
                    <img src="/icons/${editingExpression === expression ? "save.webp" : "edit.webp"}" alt="" aria-hidden="true">
                  </button>
                </div>
              </figure>
            `;
          }).join("")}
        </div>
        <div class="expression-modal-actions">
          <button
            type="button"
            class="primary"
            data-action="regenerate-selected-expressions"
            ${selectedCount ? "" : "disabled"}
          >${selectedCount > 1 ? "Regerar Express&otilde;es" : "Regerar Express&atilde;o"}</button>
        </div>
      </div>
    </div>
  `;
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

function renderAppearanceRegenerateModal() {
  const modal = state.modal || {};
  const character = (state.activeStory?.characters || []).find(item => item.id === modal.characterId);
  if (!character) return "";
  const appearances = getCharacterAppearances(character.id);
  const target = appearances.find(item => item.id === modal.targetAppearanceId);
  const style = state.activeStory?.visual_style_record || {};
  const selectedReferenceId = modal.referenceAppearanceId || modal.targetAppearanceId;
  return `
    <div class="modal-backdrop">
      <form class="modal appearance-regenerate-modal" id="appearance-regenerate-form">
        <div class="sprite-preview-head">
          <div>
            <h2>Regerar aparência</h2>
            <span>${escapeHtml(character.name || "Personagem")} - ${escapeHtml(target?.label || "Aparencia")}</span>
          </div>
          <button type="button" data-action="close-modal">Fechar</button>
        </div>
        ${style.appearance_workbench ? "" : `<p class="field-error">Configure o Workflow de Alterar Aparencia no estilo atual antes de regenerar.</p>`}
        <section class="appearance-section">
          <h3>Selecionar sprite de referência</h3>
          <div class="appearance-card-grid">
            ${appearances.map(appearance => renderAppearanceCard(character, appearance, {
              selectAction: "select-regenerate-reference",
              selectedAppearanceId: selectedReferenceId,
            })).join("")}
          </div>
        </section>
        <section class="appearance-section">
          <h3>O que mudar</h3>
          <div class="field">
            <label for="appearance-regenerate-prompt">Prompt do usuário</label>
            <textarea id="appearance-regenerate-prompt" name="prompt" rows="6">${escapeHtml(modal.value || "")}</textarea>
            ${modal.error ? `<small class="field-error">${escapeHtml(modal.error)}</small>` : ""}
          </div>
          <label class="check-row">
            <input type="checkbox" name="improve_prompt" value="true" ${modal.improvePrompt === false ? "" : "checked"}>
            <span>Melhorar prompt antes de enviar</span>
          </label>
          <div class="mini-actions">
            <button type="button" data-action="close-modal">Cancelar</button>
            <button class="primary" type="submit" ${style.appearance_workbench ? "" : "disabled"}>${state.busy ? "Enviando..." : "Enviar"}</button>
          </div>
        </section>
      </form>
    </div>
  `;
}

function renderModal() {
  if (state.modal.type === "spritePreview") {
    const sprite = state.modal.sprite || {};
    return `
      <div class="modal-backdrop">
        <div class="modal sprite-preview-modal" role="dialog" aria-modal="true" aria-label="Visualizar sprite">
          <div class="sprite-preview-head">
            <div>
              <h2>${escapeHtml(state.modal.characterName || "Sprite")}</h2>
              <span>${escapeHtml(sprite.expression || "neutral")}</span>
            </div>
            <button type="button" data-action="close-modal">Fechar</button>
          </div>
          <div class="sprite-preview-stage">
            <img src="${escapeAttr(sprite.url || "")}" alt="${escapeAttr(state.modal.characterName || "Sprite")}">
          </div>
        </div>
      </div>
    `;
  }
  if (state.modal.type === "expressions") {
    return renderExpressionsModal();
  }
  if (state.modal.type === "appearanceRegenerate") {
    return renderAppearanceRegenerateModal();
  }
  if (state.modal.type === "backgroundRegenerate") {
    const scene = latestScene(state.activeStory);
    const background = findSceneBackground(scene);
    const prompt = state.modal.prompt ?? editableBackgroundPrompt(scene, background);
    return `
      <div class="modal-backdrop">
        <form class="modal" id="background-regenerate-form">
          <h2>Regenerar cenario</h2>
          <div class="form-grid">
            <div class="field full">
              <label for="background-regenerate-prompt">Prompt do cenario</label>
              <textarea id="background-regenerate-prompt" name="prompt" rows="8">${escapeHtml(prompt || "")}</textarea>
            </div>
          </div>
          <div class="mini-actions">
            <button type="button" data-action="close-modal">Cancelar</button>
            <button class="primary" type="submit">Regenerar cenario</button>
          </div>
        </form>
      </div>
    `;
  }
  if (state.modal.type === "redoNewInput") {
    return `
      <div class="modal-backdrop">
        <form class="modal redo-input-modal" id="redo-new-input-form">
          <h2>Regerar cena com novo input</h2>
          <div class="field">
            <label for="redo-new-input-text">Novo comando</label>
            <textarea id="redo-new-input-text" name="user_input" rows="6">${escapeHtml(state.modal.value || "")}</textarea>
            ${state.modal.error ? `<small class="field-error">${escapeHtml(state.modal.error)}</small>` : ""}
          </div>
          <div class="mini-actions">
            <button type="button" data-action="close-modal">Cancelar</button>
            <button class="primary" type="submit">Regerar</button>
          </div>
        </form>
      </div>
    `;
  }
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
      state.playMenuOpen = false;
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
  const aiProvider = document.getElementById("ai_provider");
  if (aiProvider) {
    aiProvider.addEventListener("change", () => {
      state.settings = { ...(state.settings || {}), ...collectSettingsDraft(settingsForm), ai_provider: aiProvider.value };
      render();
    });
  }
  const settingsAdvancedToggle = document.getElementById("settings_advanced_toggle");
  if (settingsAdvancedToggle) {
    settingsAdvancedToggle.addEventListener("change", () => {
      state.settings = {
        ...(state.settings || {}),
        ...(currentSettingsProvider() === "openai-compatible" ? collectLlamaFormValues(settingsForm) : collectOllamaFormValues(settingsForm)),
      };
      state.settingsAdvanced = settingsAdvancedToggle.checked;
      render();
    });
  }
  const llamaMode = document.getElementById("openai_compatible_llama_mode");
  if (llamaMode) {
    llamaMode.addEventListener("change", () => {
      state.settings = { ...(state.settings || {}), ...collectSettingsDraft(settingsForm), openai_compatible_llama_mode: llamaMode.checked };
      render();
    });
  }
  const ollamaPreset = document.getElementById("ollama_preset");
  if (ollamaPreset) {
    ollamaPreset.addEventListener("change", () => applyOllamaPresetToForm(ollamaPreset.value));
  }
  const llamaPreset = document.getElementById("llama_preset");
  if (llamaPreset) {
    llamaPreset.addEventListener("change", () => applyLlamaPresetToForm(llamaPreset.value));
  }
  document.querySelectorAll("[data-llama-role-preset]").forEach(select => {
    select.addEventListener("change", () => applyRoleLlamaPresetToForm(select.dataset.llamaRolePreset, select.value));
  });
  const styleForm = document.getElementById("style-form");
  if (styleForm) styleForm.addEventListener("submit", saveVisualStyle);
  const styleWorkbench = document.getElementById("style_sprite_workbench");
  if (styleWorkbench) {
    styleWorkbench.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      render();
    });
  }
  const styleBackgroundWorkbench = document.getElementById("style_background_workbench");
  if (styleBackgroundWorkbench) {
    styleBackgroundWorkbench.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      render();
    });
  }
  const styleAppearanceWorkbench = document.getElementById("style_appearance_workbench");
  if (styleAppearanceWorkbench) {
    styleAppearanceWorkbench.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      render();
    });
  }
  const styleExpressionWorkbench = document.getElementById("style_expression_workbench");
  if (styleExpressionWorkbench) {
    styleExpressionWorkbench.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      render();
    });
  }
  const styleExpressionsEnabled = document.getElementById("style_expressions_enabled");
  if (styleExpressionsEnabled) {
    styleExpressionsEnabled.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      render();
    });
  }
  const styleSpriteAdvancedToggle = document.getElementById("style_sprite_advanced_toggle");
  if (styleSpriteAdvancedToggle) {
    styleSpriteAdvancedToggle.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      state.styleSpriteAdvanced = styleSpriteAdvancedToggle.checked;
      render();
    });
  }
  const styleBackgroundAdvancedToggle = document.getElementById("style_background_advanced_toggle");
  if (styleBackgroundAdvancedToggle) {
    styleBackgroundAdvancedToggle.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      state.styleBackgroundAdvanced = styleBackgroundAdvancedToggle.checked;
      render();
    });
  }
  document.querySelectorAll(".style-prompt-commands-toggle").forEach(toggle => {
    toggle.addEventListener("change", () => {
      state.styleDraft = collectStyleDraft(styleForm);
      state.stylePromptCommandsVisible = toggle.checked;
      render();
    });
  });
  const characterForm = document.getElementById("character-form");
  if (characterForm) characterForm.addEventListener("submit", saveModalCharacter);
  const backgroundRegenerateForm = document.getElementById("background-regenerate-form");
  if (backgroundRegenerateForm) backgroundRegenerateForm.addEventListener("submit", regenerateCurrentBackground);
  const redoNewInputForm = document.getElementById("redo-new-input-form");
  if (redoNewInputForm) redoNewInputForm.addEventListener("submit", regenerateCurrentSceneWithInput);
  const characterEditForm = document.getElementById("character-edit-form");
  if (characterEditForm) characterEditForm.addEventListener("submit", saveCharacterEdit);
  const appearanceDesignerForm = document.getElementById("appearance-designer-form");
  if (appearanceDesignerForm) appearanceDesignerForm.addEventListener("submit", generateCharacterAppearance);
  const appearanceRegenerateForm = document.getElementById("appearance-regenerate-form");
  if (appearanceRegenerateForm) appearanceRegenerateForm.addEventListener("submit", regenerateExistingAppearance);
  const appearanceCharacterSelect = document.querySelector('[data-action="select-appearance-character"]');
  if (appearanceCharacterSelect) {
    appearanceCharacterSelect.addEventListener("change", () => {
      state.activeCharacterId = appearanceCharacterSelect.value || "";
      render();
    });
  }
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
  const backgroundFilterOpacity = document.getElementById("background-filter-opacity");
  if (backgroundFilterOpacity) {
    backgroundFilterOpacity.addEventListener("input", () => {
      const value = boundedBackgroundFilterOpacity(backgroundFilterOpacity.value);
      state.backgroundFilterOpacity = value;
      localStorage.setItem("backgroundFilterOpacity", String(value));
      const vnView = document.querySelector(".vn-view");
      if (vnView) vnView.style.setProperty("--background-filter-opacity", String(value / 100));
      const output = backgroundFilterOpacity.closest(".background-filter-control")?.querySelector("output");
      if (output) output.textContent = `${value}%`;
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

function handleGlobalClick(event) {
  if (!state.redoMenuOpen) return;
  if (event.target.closest(".redo-menu-wrap")) return;
  state.redoMenuOpen = false;
  render();
}

function handleGlobalKeydown(event) {
  if (event.key !== "Escape") return;
  if (state.redoMenuOpen) {
    state.redoMenuOpen = false;
    render();
    return;
  }
  if (state.modal?.type === "redoNewInput") {
    state.modal = null;
    render();
  }
}

async function handleAction(event) {
  const action = event.currentTarget.dataset.action;
  if (event.currentTarget.closest(".sprite-edit-panel")) {
    event.stopPropagation();
  }
  if (action === "toggle-story-topnav") {
    state.storyTopnavOpen = !state.storyTopnavOpen;
    const shell = document.querySelector(".story-topnav-shell");
    const toggle = event.currentTarget;
    if (shell) shell.classList.toggle("open", state.storyTopnavOpen);
    toggle.setAttribute("aria-expanded", state.storyTopnavOpen ? "true" : "false");
    toggle.setAttribute("aria-label", state.storyTopnavOpen ? "Esconder menu superior" : "Mostrar menu superior");
    return;
  }
  if (action === "toggle-play-menu") {
    state.playMenuOpen = !state.playMenuOpen;
    state.redoMenuOpen = false;
    render();
    return;
  }
  if (action === "toggle-redo-menu") {
    event.stopPropagation();
    state.redoMenuOpen = !state.redoMenuOpen;
    render();
    return;
  }
  state.playMenuOpen = false;
  state.redoMenuOpen = false;
  state.storyTopnavOpen = false;
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
    state.styleTab = "sprites";
    state.styleSpriteAdvanced = false;
    state.styleBackgroundAdvanced = false;
    state.stylePromptCommandsVisible = false;
    state.stylePromptTest = { assetType: "appearance", appearance: "", clothing: "", result: "" };
    render();
  }
  if (action === "edit-style") {
    state.styleEditingId = event.currentTarget.dataset.id || "";
    const style = state.visualStyles.find(item => item.id === state.styleEditingId);
    state.styleDraft = style ? cloneStyleDraft(style) : emptyVisualStyleDraft();
    state.styleTab = "sprites";
    state.styleSpriteAdvanced = false;
    state.styleBackgroundAdvanced = false;
    state.stylePromptCommandsVisible = false;
    state.stylePromptTest = { assetType: "appearance", appearance: "", clothing: "", result: "" };
    render();
  }
  if (action === "style-tab") {
    const styleForm = document.getElementById("style-form");
    state.styleDraft = collectStyleDraft(styleForm);
    state.styleTab = event.currentTarget.dataset.tab || "sprites";
    render();
  }
  if (action === "delete-style") deleteVisualStyle(event.currentTarget.dataset.id);
  if (action === "test-style-prompt") testStylePrompt(event.currentTarget.dataset.assetType || "appearance");
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
  if (action === "apply-ollama-preset") applySelectedOllamaPreset();
  if (action === "save-ollama-preset") saveOllamaPreset();
  if (action === "delete-ollama-preset") deleteOllamaPreset();
  if (action === "apply-llama-preset") applySelectedLlamaPreset();
  if (action === "save-llama-preset") saveLlamaPreset();
  if (action === "delete-llama-preset") deleteLlamaPreset();
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
  if (action === "create-step-next") await advanceCreateStep();
  if (action === "create-step-back") goCreateStep(state.createStep - 1);
  if (action === "select-pov") {
    saveCreateDraft();
    const mode = normalizeParticipationMode(event.currentTarget.dataset.value);
    const previousMode = currentParticipationMode(state.createDraft);
    state.createDraft.participation_mode = mode;
    state.createDraft.point_of_view = legacyPointOfView(mode);
    if (mode !== previousMode) {
      state.createDraft.base_generated_key = "";
    }
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
  if (action === "toggle-sprite-edit-mode") {
    state.spriteEditMode = !state.spriteEditMode;
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
  if (action === "open-regenerate-background") openRegenerateBackgroundModal();
  if (action === "open-expression-modal") openExpressionModal(event.currentTarget.dataset.characterId || "", event.currentTarget.dataset.spriteId || "");
  if (action === "open-expression-preview") openExpressionPreview(event.currentTarget.dataset.characterId || "", event.currentTarget.dataset.spriteId || "", event.currentTarget.dataset.expression || "");
  if (action === "toggle-expression-selection") toggleExpressionSelection(event.currentTarget.dataset.expression || "", event.currentTarget.checked);
  if (action === "edit-character-expression-prompt") editCharacterExpressionPrompt(event.currentTarget.dataset.expression || "");
  if (action === "save-character-expression-prompt") saveCharacterExpressionPrompt(event.currentTarget.dataset.expression || "");
  if (action === "regenerate-selected-expressions") regenerateSelectedExpressions();
  if (action === "open-appearance-designer") openAppearanceDesigner(event.currentTarget.dataset.characterId || "");
  if (action === "open-appearance-regenerate") {
    event.stopPropagation();
    openAppearanceRegenerateModal(event.currentTarget.dataset.characterId || "", event.currentTarget.dataset.appearanceId || "");
  }
  if (action === "select-regenerate-reference") {
    event.stopPropagation();
    selectRegenerateReference(event.currentTarget.dataset.appearanceId || "");
  }
  if (action === "set-active-appearance") setActiveAppearance(event.currentTarget.dataset.characterId || "", event.currentTarget.dataset.appearanceId || "");
  if (action === "add-character-to-scene") addCharacterToCurrentScene();
  if (action === "remove-character-from-scene") removeCharacterFromCurrentScene(event.currentTarget.dataset.name || "");
  if (action === "open-character-profile") openCharacterProfile(event.currentTarget.dataset.characterId || "");
  if (action === "character-appearance-placeholder") {
    openAppearanceDesigner(event.currentTarget.dataset.characterId || "");
  }
  if (action === "delete-character") deleteCharacter(event.currentTarget.dataset.characterId || "", event.currentTarget.dataset.characterName || "");
  if (action === "next-dialogue") {
    const scene = latestScene(state.activeStory);
    const currentDialogue = getDialogueSequence(scene)[state.dialogueIndex] || null;
    if (!isTypewriterComplete(scene, currentDialogue)) {
      completeTypewriterLine(true);
      return;
    }
    const sequence = getDialogueSequence(latestScene(state.activeStory));
    state.dialogueIndex = Math.min(state.dialogueIndex + 1, Math.max(0, sequence.length - 1));
    resetTypewriter();
    render();
  }
  if (action === "continue") generateScene("");
  if (action === "send-custom") generateScene(document.getElementById("custom-action")?.value || "");
  if (action === "choose") generateScene(event.currentTarget.dataset.choice || "");
  if (action === "select-sprite-speaker") selectSpriteSpeaker(event.currentTarget.dataset.name || "");
  if (action === "regenerate-current-scene") regenerateCurrentScene();
  if (action === "open-redo-new-input") openRedoWithNewInputModal();
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
  if (action === "open-sprite-preview") openSpritePreview(event.currentTarget.dataset.characterId, event.currentTarget.dataset.spriteId);
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
  const payload = collectSettingsPayload(event.currentTarget);
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

function collectSettingsPayload(formElement) {
  const form = new FormData(formElement);
  const numeric = new Set([
    "ollama_temperature",
    "ollama_context",
    "ollama_top_p",
    "ollama_top_k",
    "ollama_min_p",
    "ollama_num_predict",
    "ollama_retry_num_predict",
    "ollama_max_attempts",
    "ollama_repeat_penalty",
    "ollama_repeat_last_n",
    "ollama_timeout",
    "llama_temperature",
    "llama_top_p",
    "llama_top_k",
    "llama_min_p",
    "llama_context_window",
    "llama_max_tokens",
    "llama_retry_max_tokens",
    "llama_max_attempts",
    "llama_repeat_penalty",
    "llama_repeat_last_n",
    "llama_timeout",
    "image_width",
    "image_height",
    "sprite_width",
    "sprite_height",
    "background_steps",
    "background_cfg",
    "sprite_steps",
    "sprite_cfg",
    ...roleLlamaNumericFields("story_ai"),
    ...roleLlamaNumericFields("scene_ai"),
  ]);
  const booleans = new Set([
    "ollama_think",
    "openai_verify_ssl",
    "openai_compatible_verify_ssl",
    "openai_compatible_llama_mode",
    "story_ai_openai_compatible_verify_ssl",
    "story_ai_openai_compatible_llama_mode",
    "scene_ai_openai_compatible_verify_ssl",
    "scene_ai_openai_compatible_llama_mode",
    "llama_enable_thinking",
    "llama_cache_prompt",
    "llama_timings_per_token",
    "script_story_ai_start_with_app",
    "script_story_ai_show_window",
    "script_scene_ai_start_with_app",
    "script_scene_ai_show_window",
    "script_llama_start_with_app",
    "script_llama_show_window",
    "script_comfy_start_with_app",
    "script_comfy_show_window",
    ...roleLlamaBooleanFields("story_ai"),
    ...roleLlamaBooleanFields("scene_ai"),
  ]);
  const payload = {};
  for (const [key, value] of form.entries()) {
    if (numeric.has(key)) {
      payload[key] = value === "" ? "" : Number(value);
    } else if (booleans.has(key)) {
      payload[key] = value === "true";
    } else {
      payload[key] = value;
    }
  }
  if (form.has("ollama_think")) payload.ollama_think = payload.ollama_think === true;
  if (form.has("llama_enable_thinking")) payload.llama_enable_thinking = payload.llama_enable_thinking === true;
  if (form.has("llama_cache_prompt")) payload.llama_cache_prompt = payload.llama_cache_prompt === true;
  if (form.has("llama_timings_per_token")) payload.llama_timings_per_token = payload.llama_timings_per_token === true;
  if (form.has("openai_compatible_llama_mode")) payload.openai_compatible_llama_mode = payload.openai_compatible_llama_mode === true;
  if (form.has("story_ai_openai_compatible_verify_ssl")) payload.story_ai_openai_compatible_verify_ssl = payload.story_ai_openai_compatible_verify_ssl === true;
  if (form.has("story_ai_openai_compatible_llama_mode")) payload.story_ai_openai_compatible_llama_mode = payload.story_ai_openai_compatible_llama_mode === true;
  if (form.has("scene_ai_openai_compatible_verify_ssl")) payload.scene_ai_openai_compatible_verify_ssl = payload.scene_ai_openai_compatible_verify_ssl === true;
  if (form.has("scene_ai_openai_compatible_llama_mode")) payload.scene_ai_openai_compatible_llama_mode = payload.scene_ai_openai_compatible_llama_mode === true;
  if (form.has("script_story_ai_start_with_app")) payload.script_story_ai_start_with_app = payload.script_story_ai_start_with_app === true;
  if (form.has("script_story_ai_show_window")) payload.script_story_ai_show_window = payload.script_story_ai_show_window === true;
  if (form.has("script_scene_ai_start_with_app")) payload.script_scene_ai_start_with_app = payload.script_scene_ai_start_with_app === true;
  if (form.has("script_scene_ai_show_window")) payload.script_scene_ai_show_window = payload.script_scene_ai_show_window === true;
  if (form.has("script_llama_start_with_app")) payload.script_llama_start_with_app = payload.script_llama_start_with_app === true;
  if (form.has("script_llama_show_window")) payload.script_llama_show_window = payload.script_llama_show_window === true;
  if (form.has("script_comfy_start_with_app")) payload.script_comfy_start_with_app = payload.script_comfy_start_with_app === true;
  if (form.has("script_comfy_show_window")) payload.script_comfy_show_window = payload.script_comfy_show_window === true;
  payload.ollama_custom_presets = state.settings?.ollama_custom_presets || {};
  payload.llama_custom_presets = state.settings?.llama_custom_presets || {};
  return payload;
}

function roleLlamaNumericFields(prefix) {
  return LLAMA_ADVANCED_FIELDS
    .filter(field => !["llama_enable_thinking", "llama_cache_prompt", "llama_timings_per_token"].includes(field))
    .map(field => `${prefix}_${field}`);
}

function roleLlamaBooleanFields(prefix) {
  return ["llama_enable_thinking", "llama_cache_prompt", "llama_timings_per_token"].map(field => `${prefix}_${field}`);
}

function collectSettingsDraft(formElement) {
  const payload = collectSettingsPayload(formElement);
  ["openai_api_key", "openai_compatible_api_key", "story_ai_openai_compatible_api_key", "scene_ai_openai_compatible_api_key"].forEach(key => {
    if (payload[key] === "") delete payload[key];
  });
  return payload;
}

function collectOllamaFormValues(formElement) {
  if (!formElement) return {};
  const form = new FormData(formElement);
  return OLLAMA_ADVANCED_FIELDS.reduce((acc, field) => {
    if (field === "ollama_think") {
      acc[field] = form.get(field) === "true";
      return acc;
    }
    if (form.has(field)) acc[field] = form.get(field);
    return acc;
  }, { ollama_preset: form.get("ollama_preset") || "balanced" });
}

function collectLlamaFormValues(formElement) {
  if (!formElement) return {};
  const form = new FormData(formElement);
  return LLAMA_ADVANCED_FIELDS.reduce((acc, field) => {
    if (field === "llama_enable_thinking" || field === "llama_cache_prompt" || field === "llama_timings_per_token") {
      acc[field] = form.get(field) === "true";
      return acc;
    }
    if (form.has(field)) acc[field] = form.get(field);
    return acc;
  }, { llama_preset: form.get("llama_preset") || "balanced" });
}

function currentSettingsProvider() {
  return document.getElementById("ai_provider")?.value || state.settings?.ai_provider || "ollama";
}

function applySelectedOllamaPreset() {
  const presetId = document.getElementById("ollama_preset")?.value || "balanced";
  applyOllamaPresetToForm(presetId);
}

function applySelectedLlamaPreset() {
  const presetId = document.getElementById("llama_preset")?.value || "balanced";
  applyLlamaPresetToForm(presetId);
}

function applyOllamaPresetToForm(presetId) {
  const preset = ollamaPresetDefinitions()[presetId];
  if (!preset) return;
  const form = document.getElementById("settings-form");
  if (!form) return;
  const values = preset.values || {};
  Object.entries(values).forEach(([field, value]) => setFormFieldValue(form, field, value));
  const select = document.getElementById("ollama_preset");
  if (select) select.value = presetId;
}

function applyLlamaPresetToForm(presetId) {
  const preset = llamaPresetDefinitions()[presetId];
  if (!preset) return;
  const form = document.getElementById("settings-form");
  if (!form) return;
  const values = preset.values || {};
  Object.entries(values).forEach(([field, value]) => setFormFieldValue(form, field, value));
  const select = document.getElementById("llama_preset");
  if (select) select.value = presetId;
}

function applyRoleLlamaPresetToForm(prefix, presetId) {
  const preset = llamaPresetDefinitions()[presetId];
  if (!prefix || !preset) return;
  const form = document.getElementById("settings-form");
  if (!form) return;
  const values = preset.values || {};
  Object.entries(values).forEach(([field, value]) => {
    setFormFieldValue(form, `${prefix}_${field}`, value);
  });
  const select = document.getElementById(`${prefix}_llama_preset`);
  if (select) select.value = presetId;
}

async function saveOllamaPreset() {
  const form = document.getElementById("settings-form");
  const nameInput = document.getElementById("ollama_custom_preset_name");
  const rawName = (nameInput?.value || "").trim();
  if (!form || !rawName) {
    alert("Informe um nome para o preset custom.");
    return;
  }
  const presetId = sanitizePresetId(rawName);
  if (!presetId) {
    alert("Use letras, numeros, espaco, hifen ou underline no nome do preset.");
    return;
  }
  const payload = collectSettingsPayload(form);
  const values = {};
  OLLAMA_ADVANCED_FIELDS.forEach(field => {
    values[field] = payload[field];
  });
  payload.ollama_preset = presetId;
  payload.ollama_custom_presets = {
    ...(state.settings?.ollama_custom_presets || {}),
    [presetId]: {
      label: rawName,
      description: "Preset customizado salvo localmente.",
      values,
    },
  };
  setBusy(true, "Salvando preset...");
  try {
    state.settings = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
    await loadSettings();
    state.settingsAdvanced = true;
    render();
    alert("Preset salvo.");
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveLlamaPreset() {
  const form = document.getElementById("settings-form");
  const nameInput = document.getElementById("llama_custom_preset_name");
  const rawName = (nameInput?.value || "").trim();
  if (!form || !rawName) {
    alert("Informe um nome para o preset custom.");
    return;
  }
  const presetId = sanitizePresetId(rawName);
  if (!presetId) {
    alert("Use letras, numeros, espaco, hifen ou underline no nome do preset.");
    return;
  }
  const payload = collectSettingsPayload(form);
  const values = {};
  LLAMA_ADVANCED_FIELDS.forEach(field => {
    values[field] = payload[field];
  });
  payload.llama_preset = presetId;
  payload.llama_custom_presets = {
    ...(state.settings?.llama_custom_presets || {}),
    [presetId]: {
      label: rawName,
      description: "Preset customizado salvo localmente.",
      values,
    },
  };
  setBusy(true, "Salvando preset...");
  try {
    state.settings = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
    await loadSettings();
    state.settingsAdvanced = true;
    render();
    alert("Preset salvo.");
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function deleteOllamaPreset() {
  const presetId = document.getElementById("ollama_preset")?.value || "";
  const presets = state.settings?.ollama_custom_presets || {};
  if (!presetId || OLLAMA_PRESETS[presetId] || !presets[presetId]) {
    alert("Selecione um preset customizado para excluir.");
    return;
  }
  const form = document.getElementById("settings-form");
  const payload = collectSettingsPayload(form);
  const nextPresets = { ...presets };
  delete nextPresets[presetId];
  payload.ollama_preset = "balanced";
  payload.ollama_custom_presets = nextPresets;
  setBusy(true, "Excluindo preset...");
  try {
    state.settings = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
    await loadSettings();
    render();
    alert("Preset excluido.");
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function deleteLlamaPreset() {
  const presetId = document.getElementById("llama_preset")?.value || "";
  const presets = state.settings?.llama_custom_presets || {};
  if (!presetId || LLAMA_PRESETS[presetId] || !presets[presetId]) {
    alert("Selecione um preset customizado para excluir.");
    return;
  }
  const form = document.getElementById("settings-form");
  const payload = collectSettingsPayload(form);
  const nextPresets = { ...presets };
  delete nextPresets[presetId];
  payload.llama_preset = "balanced";
  payload.llama_custom_presets = nextPresets;
  setBusy(true, "Excluindo preset...");
  try {
    state.settings = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
    await loadSettings();
    render();
    alert("Preset excluido.");
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function setFormFieldValue(form, field, value) {
  const elements = form.querySelectorAll(`[name="${CSS.escape(field)}"]`);
  if (!elements.length) return;
  elements.forEach(element => {
    if (element.type === "checkbox") {
      element.checked = Boolean(value);
    } else {
      element.value = value ?? "";
    }
  });
}

function sanitizePresetId(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 48);
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
  const { expression_prompts: _legacyExpressionPrompts, expression_prompts_visible: _legacyExpressionPromptsVisible, ...styleBase } = current;
  const selectedSpriteWorkbench = styleFormValue(data, "sprite_workbench", current.sprite_workbench);
  const selectedBackgroundWorkbench = styleFormValue(data, "background_workbench", current.background_workbench);
  const spriteAdvancedFields = new Set(advancedFieldNamesForWorkbench(selectedSpriteWorkbench));
  const backgroundAdvancedFields = new Set(advancedBackgroundFieldNames(selectedBackgroundWorkbench));
  const advanced = filterStyleSettingsForFields(current.advanced_settings || {}, spriteAdvancedFields);
  const backgroundSettings = filterStyleSettingsForFields(current.background_settings || {}, backgroundAdvancedFields);
  for (const [key, value] of data.entries()) {
    if (state.styleSpriteAdvanced) {
      if (key.startsWith("advanced_")) {
        const field = key.replace("advanced_", "");
        if (!spriteAdvancedFields.has(field)) continue;
        if (String(value || "").trim()) {
          advanced[field] = ["width", "height", "steps"].includes(field) ? Number(value) : (field === "cfg" ? Number(value) : String(value).trim());
        } else {
          delete advanced[field];
        }
      }
    }
    if (state.styleBackgroundAdvanced) {
      if (!key.startsWith("background_")) continue;
      const field = key.replace("background_", "");
      if (!backgroundAdvancedFields.has(field)) continue;
      if (String(value || "").trim()) {
        backgroundSettings[field] = ["width", "height", "steps"].includes(field) ? Number(value) : (field === "cfg" ? Number(value) : String(value).trim());
      } else {
        delete backgroundSettings[field];
      }
    }
  }
  return {
    ...styleBase,
    name: styleFormValue(data, "name", current.name),
    prompt_prefix: styleFormValue(data, "prompt_prefix", current.prompt_prefix),
    prompt_suffix: styleFormValue(data, "prompt_suffix", current.prompt_suffix),
    negative_prompt: styleFormValue(data, "negative_prompt", current.negative_prompt),
    sprite_workbench: styleFormValue(data, "sprite_workbench", current.sprite_workbench),
    background_workbench: styleFormValue(data, "background_workbench", current.background_workbench),
    appearance_workbench: styleFormValue(data, "appearance_workbench", current.appearance_workbench),
    background_prompt_prefix: styleFormValue(data, "background_prompt_prefix", current.background_prompt_prefix),
    background_prompt_suffix: styleFormValue(data, "background_prompt_suffix", current.background_prompt_suffix),
    background_negative_prompt: styleFormValue(data, "background_negative_prompt", current.background_negative_prompt),
    sprite_prompt_command: styleFormValue(data, "sprite_prompt_command", current.sprite_prompt_command),
    sprite_prompt_example: styleFormValue(data, "sprite_prompt_example", current.sprite_prompt_example),
    background_prompt_command: styleFormValue(data, "background_prompt_command", current.background_prompt_command),
    background_prompt_example: styleFormValue(data, "background_prompt_example", current.background_prompt_example),
    appearance_prompt_command: styleFormValue(data, "appearance_prompt_command", current.appearance_prompt_command),
    appearance_prompt_example: styleFormValue(data, "appearance_prompt_example", current.appearance_prompt_example),
    expressions_enabled: styleFormBool(data, "expressions_enabled", current.expressions_enabled === true),
    expression_workbench: styleFormValue(data, "expression_workbench", current.expression_workbench),
    advanced_settings: advanced,
    background_settings: backgroundSettings,
  };
}

function styleFormValue(data, key, fallback = "") {
  if (!data || !data.has(key)) return String(fallback || "").trim();
  return String(data.get(key) || "").trim();
}

function styleFormBool(data, key, fallback = false) {
  if (!data || !data.has(key)) return Boolean(fallback);
  return data.getAll(key).some(value => value === "true");
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

async function testStylePrompt(assetType) {
  const styleForm = document.getElementById("style-form");
  const normalizedType = normalizeStylePromptAssetType(assetType);
  const appearance = document.getElementById(`style_prompt_test_appearance_${normalizedType}`)?.value || "";
  const clothing = document.getElementById(`style_prompt_test_clothing_${normalizedType}`)?.value || "";
  state.styleDraft = collectStyleDraft(styleForm);
  state.stylePromptTest = {
    assetType: normalizedType,
    appearance,
    clothing,
    result: "",
  };
  setBusy(true, "Gerando teste de prompt...");
  try {
    const result = await api("/api/visual-styles/prompt-test", {
      method: "POST",
      body: JSON.stringify({
        asset_type: normalizedType,
        style: state.styleDraft,
        appearance,
        clothing,
      }),
    });
    state.stylePromptTest = {
      assetType: normalizedType,
      appearance,
      clothing,
      result: result.visual_prompt || "",
    };
    render();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
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
  const target = Math.max(0, Math.min(3, step));
  if (target > maxCreateStep(state.createDraft)) return;
  state.createStep = target;
  render();
}

async function advanceCreateStep() {
  saveCreateDraft();
  if (state.createStep === 0) {
    if (!isCreateBaseCurrent(state.createDraft)) {
      const generated = await generateStorySeed({ advanceToStep: 1 });
      if (!generated) return;
      return;
    }
    state.createStep = 1;
    render();
    return;
  }
  goCreateStep(state.createStep + 1);
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
    "player_species",
    "player_gender",
    "player_character_type",
    "player_aliases",
    "player_description",
    "player_physical",
    "player_appearance",
    "player_personality",
    "player_clothing",
    "player_relationship",
    "player_background",
    "player_goals",
  ];
  fields.forEach(fieldName => {
    if (data.has(fieldName)) draft[fieldName] = data.get(fieldName) || "";
  });
  draft.participation_mode = currentParticipationMode(draft);
  draft.point_of_view = legacyPointOfView(draft.participation_mode);
  if (state.createStep === 2) {
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

async function generateStorySeed(options = {}) {
  saveCreateDraft();
  const prompt = (state.createDraft.story_prompt || "").trim();
  const participationMode = currentParticipationMode(state.createDraft);
  if (!prompt) {
    alert("Escreva uma ideia antes de gerar a base da história.");
    return false;
  }
  setBusy(true, "Gerando base da história com IA...");
  try {
    const seed = await api("/api/ai/story-seed", {
      method: "POST",
      body: JSON.stringify({ prompt, participation_mode: participationMode }),
    });
    state.createDraft = {
      ...state.createDraft,
      story_prompt: prompt,
      participation_mode: normalizeParticipationMode(seed.participation_mode || participationMode),
      point_of_view: legacyPointOfView(seed.participation_mode || participationMode),
      base_generated_key: `${normalizeParticipationMode(seed.participation_mode || participationMode)}::${prompt}`,
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
      player_species: seed.player_character?.species || state.createDraft.player_species,
      player_gender: seed.player_character?.gender || state.createDraft.player_gender,
      player_character_type: seed.player_character?.character_type || seed.player_character?.type || state.createDraft.player_character_type,
      player_aliases: seed.player_character?.aliases || state.createDraft.player_aliases,
      player_description: seed.player_character?.description || seed.player_character?.background || state.createDraft.player_description,
      player_physical: seed.player_character?.physical || seed.player_character?.appearance || state.createDraft.player_physical,
      player_appearance: seed.player_character?.appearance || state.createDraft.player_appearance,
      player_personality: seed.player_character?.personality || state.createDraft.player_personality,
      player_clothing: seed.player_character?.clothing || state.createDraft.player_clothing,
      player_relationship: seed.player_character?.relationship || state.createDraft.player_relationship,
      player_background: seed.player_character?.background || state.createDraft.player_background,
      player_goals: seed.player_character?.goals || state.createDraft.player_goals,
      characters: seed.characters?.length ? seed.characters : state.createDraft.characters,
    };
    if (typeof options.advanceToStep === "number") {
      state.createStep = Math.max(0, Math.min(3, options.advanceToStep));
    }
    if (seed.warning) console.warn(seed.warning);
    return true;
  } catch (error) {
    alert(error.message);
    return false;
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
  const participationMode = currentParticipationMode(draft);
  const participation = participationModeOption(participationMode);
  const characters = (draft.characters || [])
    .filter(character => character.name)
    .map(({ visual_prompt, ...character }) => character);
  const loreParts = [
    draft.lore,
    `Modo de participação: ${participation.title}. ${participation.description}`,
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
    participation_mode: participationMode,
    point_of_view: legacyPointOfView(participationMode),
    content_rating: draft.content_rating,
    language: draft.language || "pt-BR",
    starting_location: draft.starting_location,
    starting_message: draft.starting_message,
    story_prompt: draft.story_prompt,
    lore: loreParts.join("\n\n"),
    player_character: {
      name: draft.player_name,
      role: draft.player_role,
      species: draft.player_species,
      gender: draft.player_gender,
      character_type: draft.player_character_type,
      aliases: draft.player_aliases,
      description: draft.player_description || draft.player_background,
      physical: draft.player_physical || draft.player_appearance,
      appearance: draft.player_physical || draft.player_appearance,
      personality: draft.player_personality,
      clothing: draft.player_clothing,
      relationship: draft.player_relationship,
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

async function selectSpriteSpeaker(name) {
  const scene = latestScene(state.activeStory);
  const character = getVisualSceneCharacters(scene).find(item => normalizeName(item.name) === normalizeName(name));
  if (!character || state.busy) return;
  state.nextSpeakerFocus = { name: character.name };
  render();
  await generateScene("", { speakerFocus: character.name, clearFocusOnError: true });
}

async function generateScene(userInput, options = {}) {
  if (!state.activeStory) return;
  const speakerFocus = options.speakerFocus || selectedNextSpeakerName();
  setBusy(true, "Gerando resposta com IA...");
  try {
    state.activeStory = await api(`/api/stories/${state.activeStory.id}/generate-scene`, {
      method: "POST",
      body: JSON.stringify({ user_input: userInput, speaker_focus: speakerFocus, generate_images: true }),
    });
    state.nextSpeakerFocus = null;
    const autoBackground = state.activeStory.auto_background;
    await waitForAppearanceUpdateAssets(state.activeStory);
    if (autoBackground?.mode === "queued") {
      await waitForAsset(autoBackground.asset_id, "Gerando cenário no ComfyUI...");
      await loadStory(state.activeStory.id);
    }
  } catch (error) {
    if (options.clearFocusOnError) state.nextSpeakerFocus = null;
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function canRegenerateCurrentScene() {
  const scenes = state.activeStory?.scenes || [];
  return scenes.length > 1;
}

function openRedoWithNewInputModal() {
  state.playMenuOpen = false;
  state.redoMenuOpen = false;
  if (!canRegenerateCurrentScene()) {
    alert("Nao ha cena anterior para regerar a cena atual.");
    render();
    return;
  }
  const scene = latestScene(state.activeStory);
  state.modal = {
    type: "redoNewInput",
    value: scene?.user_input || "",
    error: "",
  };
  render();
}

async function regenerateCurrentScene() {
  if (!state.activeStory) return;
  if (!canRegenerateCurrentScene()) {
    alert("Nao ha cena anterior para regerar a cena atual.");
    return;
  }
  await regenerateCurrentSceneRequest({});
}

async function regenerateCurrentSceneWithInput(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const userInput = String(new FormData(form).get("user_input") || "").trim();
  if (!userInput) {
    state.modal = {
      ...(state.modal || {}),
      type: "redoNewInput",
      value: "",
      error: "Digite um input antes de regerar.",
    };
    render();
    return;
  }
  state.modal = null;
  await regenerateCurrentSceneRequest({ user_input: userInput });
}

async function regenerateCurrentSceneRequest(payload = {}) {
  const story = state.activeStory;
  if (!story) return;
  setBusy(true, "Regerando cena com IA...");
  try {
    state.activeStory = await api(`/api/stories/${story.id}/regenerate-scene`, {
      method: "POST",
      body: JSON.stringify({ ...payload, generate_images: true }),
    });
    resetScenePlayback();
    state.nextSpeakerFocus = null;
    const autoBackground = state.activeStory.auto_background;
    await waitForAppearanceUpdateAssets(state.activeStory);
    if (autoBackground?.mode === "queued") {
      await waitForAsset(autoBackground.asset_id, "Gerando cenario no ComfyUI...");
      await loadStory(state.activeStory.id);
      resetScenePlayback();
    }
    render();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function resetScenePlayback() {
  state.dialogueSceneId = "";
  state.dialogueIndex = 0;
  resetTypewriter();
  state.spriteRoster = [];
  state.spriteExitMap = {};
}

function openDetectedCharacter(index) {
  const scene = latestScene(state.activeStory);
  const detected = getNewCharacterCandidates(scene);
  state.modal = { type: "character", character: detected[index] || {}, generated: true };
  render();
}

function openSpritePreview(characterId, spriteId) {
  const character = (state.activeStory?.characters || []).find(item => item.id === characterId);
  const sprite = (state.activeStory?.assets || []).find(item => item.id === spriteId && item.url);
  if (!character || !sprite) return;
  state.modal = {
    type: "spritePreview",
    characterName: character.name,
    sprite,
  };
  render();
}

async function openExpressionModal(characterId, spriteId) {
  let character = (state.activeStory?.characters || []).find(item => item.id === characterId);
  let sprite = (state.activeStory?.assets || []).find(item => item.id === spriteId && item.url);
  if (!character || !sprite) return;
  if (!characterExpressionPromptsComplete(character)) {
    setBusy(true, `Gerando prompts de expressao de ${character.name}...`);
    try {
      await api(`/api/characters/${characterId}/expression-prompts`, { method: "POST", body: JSON.stringify({}) });
      await loadStory(state.activeStory.id);
      character = (state.activeStory?.characters || []).find(item => item.id === characterId);
      sprite = (state.activeStory?.assets || []).find(item => item.id === spriteId && item.url) || sprite;
    } catch (error) {
      alert(error.message);
      return;
    } finally {
      setBusy(false);
    }
  }
  state.modal = { type: "expressions", characterId, baseSpriteId: sprite.id, selectedExpressions: [], editingExpression: "" };
  render();
}

function characterExpressionPromptsComplete(character) {
  const prompts = normalizeCharacterExpressionPrompts(character?.expression_prompts || {});
  return SPRITE_EXPRESSION_KEYS.every(expression => expressionPromptIsEditOnly(prompts[expression]));
}

function expressionPromptIsEditOnly(prompt) {
  const text = String(prompt || "").trim().toLowerCase();
  if (!text) return false;
  const forbidden = [
    "masterpiece", "best quality", "score_", "year 20", "visual novel sprite",
    "single character", "realistic anime", "watercolor", "cinematic lighting",
    "detailed iris", "highly detailed", "wearing ", "waist-up", "full body",
    "half body", "from head to",
  ];
  const preservation = "keep the same character, same face, same hairstyle, same outfit, same body, same proportions, same visual style, same framing";
  const content = text.split("keep the same character", 1)[0];
  return !forbidden.some(marker => text.includes(marker)) && text.includes(preservation) && (content.match(/\b[\w'-]+\b/g) || []).length <= 45;
}

async function ensureStoryExpressionPrompts() {
  const story = state.activeStory;
  if (!story || story.visual_style_record?.expressions_enabled !== true) return story;
  const missing = (story.characters || []).filter(character => isVisualCharacter(character, story) && !characterExpressionPromptsComplete(character));
  if (!missing.length) return story;
  state.status = "Gerando prompts de expressao dos personagens...";
  render();
  await api(`/api/stories/${story.id}/expression-prompts`, { method: "POST", body: JSON.stringify({}) });
  await loadStory(story.id);
  return state.activeStory;
}

function openExpressionPreview(characterId, spriteId, expression) {
  const character = (state.activeStory?.characters || []).find(item => item.id === characterId);
  const baseSprite = (state.activeStory?.assets || []).find(item => item.id === spriteId && item.url);
  if (!character || !baseSprite) return;
  const normalized = normalizeExpression(expression);
  const asset = getSpriteExpressionAsset(baseSprite, normalized) || baseSprite;
  state.modal = {
    type: "spritePreview",
    characterName: character.name,
    sprite: {
      ...asset,
      expression: normalized,
    },
  };
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
  const character = (state.activeStory.characters || []).find(item => item.id === characterId);
  if (!isVisualCharacter(character)) {
    alert("Este personagem nao usa prompt de imagem neste modo de participacao.");
    return;
  }
  setBusy(true, "Gerando prompt de imagem com IA...");
  try {
    const scene = latestScene(state.activeStory);
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

async function addCharacterToCurrentScene() {
  const story = state.activeStory;
  const scene = latestScene(story);
  const characterId = document.getElementById("scene-add-character-select")?.value || "";
  const character = (story?.characters || []).find(item => item.id === characterId);
  if (!story || !scene || !character) return;
  const charactersOnScreen = [...(scene.characters_on_screen || [])];
  if (charactersOnScreen.length >= 6) {
    alert("A cena ja tem 6 personagens em tela.");
    return;
  }
  if (charactersOnScreen.some(item => normalizeName(item.name) === normalizeName(character.name))) return;
  charactersOnScreen.push({
    name: character.name,
    position: "center",
    expression: "neutral",
  });
  await updateCurrentSceneCast({
    characters_on_screen: charactersOnScreen,
    memory: `${character.name} foi incluido manualmente na cena ${scene.scene_order} e deve ser tratado como presente na proxima continuacao.`,
    status: `Incluindo ${character.name} na cena...`,
  });
}

async function removeCharacterFromCurrentScene(name) {
  const story = state.activeStory;
  const scene = latestScene(story);
  const key = normalizeName(name);
  if (!story || !scene || !key) return;
  const charactersOnScreen = (scene.characters_on_screen || []).filter(item => normalizeName(item.name) !== key);
  const dialogues = (scene.dialogues || []).filter(dialogue => normalizeName(dialogue.character) !== key);
  await updateCurrentSceneCast({
    characters_on_screen: charactersOnScreen,
    dialogues,
    memory: `${name} saiu manualmente da cena ${scene.scene_order}; nao deve ser tratado como presente na proxima continuacao, a menos que a narrativa o traga de volta.`,
    status: `Removendo ${name} da cena...`,
  });
}

async function updateCurrentSceneCast({ characters_on_screen, dialogues, memory, status }) {
  const story = state.activeStory;
  const scene = latestScene(story);
  if (!story || !scene) return;
  setBusy(true, status || "Atualizando cena...");
  try {
    state.activeStory = await api(`/api/scenes/${scene.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        characters_on_screen,
        ...(dialogues ? { dialogues } : {}),
      }),
    });
    if (memory) {
      state.activeStory = await api(`/api/stories/${story.id}/memory`, {
        method: "POST",
        body: JSON.stringify({
          entry_type: "scene-state",
          importance: 4,
          content: memory,
        }),
      });
    }
    state.drawer = "scene";
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function openCharacterProfile(characterId) {
  const character = (state.activeStory?.characters || []).find(item => item.id === characterId);
  if (!character) return;
  state.drawer = "characters";
  state.activeCharacterId = character.id;
  state.characterEditId = "";
  render();
}

function openAppearanceDesigner(characterId) {
  const character = (state.activeStory?.characters || []).find(item => item.id === characterId);
  if (character) state.activeCharacterId = character.id;
  state.drawer = "appearanceDesigner";
  state.characterEditId = "";
  render();
}

async function setActiveAppearance(characterId, appearanceId) {
  if (!characterId || !appearanceId) return;
  setBusy(true, "Selecionando aparência...");
  try {
    state.activeStory = await api(`/api/characters/${characterId}/appearances/${appearanceId}/activate`, { method: "PATCH" });
    state.activeCharacterId = characterId;
    render();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function generateCharacterAppearance(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const characterId = form.dataset.characterId || "";
  const referenceAssetId = form.dataset.referenceAssetId || "";
  const data = new FormData(form);
  const promptText = String(data.get("prompt") || "").trim();
  if (!promptText) {
    alert("Descreva o que deseja mudar na aparência.");
    return;
  }
  if (!referenceAssetId) {
    alert("Selecione uma aparência de referência antes de gerar.");
    return;
  }
  const scene = latestScene(state.activeStory);
  setBusy(true, "Enviando nova aparência para o ComfyUI...");
  try {
    const result = await api(`/api/characters/${characterId}/appearances`, {
      method: "POST",
      body: JSON.stringify({
        prompt: promptText,
        reference_asset_id: referenceAssetId,
        improve_prompt: data.getAll("improve_prompt").includes("true"),
        scene_id: scene?.id || null,
      }),
    });
    await waitForAsset(result.asset_id, "Gerando nova aparência no ComfyUI...");
    await loadStory(state.activeStory.id);
    state.activeCharacterId = characterId;
    state.drawer = "appearanceDesigner";
    render();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function openAppearanceRegenerateModal(characterId, appearanceId) {
  const character = (state.activeStory?.characters || []).find(item => item.id === characterId);
  const appearance = getCharacterAppearances(characterId).find(item => item.id === appearanceId);
  if (!character || !appearance || isInitialAppearance(characterId, appearance)) return;
  state.modal = {
    type: "appearanceRegenerate",
    characterId,
    targetAppearanceId: appearanceId,
    referenceAppearanceId: appearanceId,
    value: "",
    error: "",
    improvePrompt: true,
  };
  render();
}

function selectRegenerateReference(appearanceId) {
  if (!state.modal || state.modal.type !== "appearanceRegenerate") return;
  state.modal.referenceAppearanceId = appearanceId;
  state.modal.error = "";
  render();
}

async function regenerateExistingAppearance(event) {
  event.preventDefault();
  if (!state.activeStory || !state.modal || state.modal.type !== "appearanceRegenerate") return;
  const form = event.currentTarget;
  const data = new FormData(form);
  const promptText = String(data.get("prompt") || "").trim();
  const improvePrompt = data.getAll("improve_prompt").includes("true");
  if (!promptText) {
    state.modal = { ...state.modal, value: promptText, improvePrompt, error: "Descreva o que deseja mudar na aparência." };
    render();
    return;
  }
  const characterId = state.modal.characterId;
  const targetAppearanceId = state.modal.targetAppearanceId;
  const referenceAppearanceId = state.modal.referenceAppearanceId || targetAppearanceId;
  const character = (state.activeStory.characters || []).find(item => item.id === characterId);
  const reference = getCharacterAppearances(characterId).find(item => item.id === referenceAppearanceId);
  const referenceSprite = getAppearanceSprite(reference, "neutral");
  if (!character || !referenceSprite?.id) {
    state.modal = { ...state.modal, value: promptText, improvePrompt, error: "Selecione uma aparência de referência válida." };
    render();
    return;
  }
  const ok = confirm("Esta ação substituirá a aparência selecionada. A imagem anterior será perdida. Deseja continuar?");
  if (!ok) return;
  const scene = latestScene(state.activeStory);
  setBusy(true, "Enviando regeneração de aparência para o ComfyUI...");
  try {
    const result = await api(`/api/characters/${characterId}/appearances/${targetAppearanceId}/regenerate`, {
      method: "POST",
      body: JSON.stringify({
        prompt: promptText,
        reference_appearance_id: referenceAppearanceId,
        improve_prompt: improvePrompt,
        scene_id: scene?.id || null,
      }),
    });
    await waitForAsset(result.asset_id, "Regenerando aparência no ComfyUI...");
    state.activeStory = await api(`/api/characters/${characterId}/appearances/${targetAppearanceId}/replace`, {
      method: "POST",
      body: JSON.stringify({ asset_id: result.asset_id }),
    });
    state.activeCharacterId = characterId;
    state.drawer = "appearanceDesigner";
    state.modal = null;
    render();
  } catch (error) {
    state.modal = { ...state.modal, value: promptText, improvePrompt, error: error.message };
    render();
  } finally {
    setBusy(false);
  }
}

async function deleteCharacter(characterId, characterName = "") {
  const character = (state.activeStory?.characters || []).find(item => item.id === characterId);
  if (!character) return;
  const name = characterName || character.name || "este personagem";
  const ok = confirm(
    `Deletar ${name} da historia?\n\n` +
    "O personagem sera removido da historia e nao sera mais enviado para a IA como personagem ativo/relevante.\n" +
    "Os dados do personagem e sprites associados serao deletados.\n" +
    "Ele tambem sera removido da cena atual, se estiver presente.\n\n" +
    "Falas antigas no historico nao precisam ser apagadas e serao preservadas."
  );
  if (!ok) return;
  setBusy(true, `Deletando ${name}...`);
  try {
    const result = await api(`/api/characters/${characterId}`, { method: "DELETE" });
    state.activeStory = result.story || result;
    if (state.activeCharacterId === characterId) {
      state.activeCharacterId = state.activeStory?.characters?.[0]?.id || "";
    }
    state.characterEditId = "";
    state.spriteEditMode = false;
    render();
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
  await ensureStoryExpressionPrompts();
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
    if (!isVisualCharacter(character, story)) continue;
    if (!(character.visual_prompt || "").trim() || getCharacterAppearances(character.id).length) continue;
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
  await ensureStoryExpressionPrompts();
  const story = state.activeStory;
  const scene = latestScene(story);
  if (!story || !scene) return [];

  const generated = [];
  for (const item of scene.characters_on_screen || []) {
    const character = findStoryCharacter(item.name);
    if (!character || !isVisualCharacter(character, story) || findCharacterSprite(item.name, item.expression)?.url) continue;
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

function openRegenerateBackgroundModal() {
  const scene = latestScene(state.activeStory);
  if (!scene) return;
  const background = findSceneBackground(scene);
  state.modal = {
    type: "backgroundRegenerate",
    prompt: editableBackgroundPrompt(scene, background),
  };
  render();
}

async function regenerateCurrentBackground(event) {
  event.preventDefault();
  const scene = latestScene(state.activeStory);
  if (!state.activeStory || !scene) return;
  const form = new FormData(event.currentTarget);
  const prompt = String(form.get("prompt") || "").trim();
  if (!prompt) {
    alert("Informe o prompt do cenario.");
    return;
  }
  setBusy(true, "Enviando novo cenario para ComfyUI...");
  try {
    const result = await api(`/api/stories/${state.activeStory.id}/generate-image`, {
      method: "POST",
      body: JSON.stringify({
        asset_type: "background",
        scene_id: scene.id,
        prompt,
        prompt_is_visual: true,
      }),
    });
    state.modal = null;
    await waitForAsset(result.asset_id, "Regenerando cenario no ComfyUI...");
    await loadStory(state.activeStory.id);
    state.drawer = "scene";
    render();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function toggleExpressionSelection(expression, checked) {
  if (!state.modal || state.modal.type !== "expressions" || !SPRITE_EXPRESSION_KEYS.includes(expression)) return;
  const selected = new Set(state.modal.selectedExpressions || []);
  if (checked) selected.add(expression);
  else selected.delete(expression);
  state.modal.selectedExpressions = SPRITE_EXPRESSION_KEYS.filter(item => selected.has(item));
  render();
}

function editCharacterExpressionPrompt(expression) {
  if (!state.modal || state.modal.type !== "expressions" || !SPRITE_EXPRESSION_KEYS.includes(expression)) return;
  state.modal.editingExpression = expression;
  render();
  document.getElementById(`expression-prompt-${expression}`)?.focus();
}

async function saveCharacterExpressionPrompt(expression) {
  if (!state.activeStory || !state.modal || state.modal.type !== "expressions" || !SPRITE_EXPRESSION_KEYS.includes(expression)) return;
  const characterId = state.modal.characterId;
  const character = (state.activeStory.characters || []).find(item => item.id === characterId);
  const text = String(document.getElementById(`expression-prompt-${expression}`)?.value || "").trim();
  if (!character || !text) {
    alert("O prompt de expressao nao pode ficar vazio.");
    return;
  }
  const prompts = normalizeCharacterExpressionPrompts(character.expression_prompts || {});
  prompts[expression] = text;
  setBusy(true, "Salvando prompt de expressao...");
  try {
    await api(`/api/characters/${characterId}`, {
      method: "PATCH",
      body: JSON.stringify({ expression_prompts: prompts }),
    });
    await loadStory(state.activeStory.id);
    state.modal.editingExpression = "";
    render();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function regenerateSelectedExpressions() {
  if (!state.activeStory || !state.modal || state.modal.type !== "expressions") return;
  const selected = SPRITE_EXPRESSION_KEYS.filter(expression => (state.modal.selectedExpressions || []).includes(expression));
  if (!selected.length) return;
  const style = state.activeStory.visual_style_record || {};
  if (!style.expression_workbench) {
    alert("Configure o Workflow de Alterar Expressoes no estilo atual antes de regenerar.");
    return;
  }
  const characterId = state.modal.characterId;
  const baseSpriteId = state.modal.baseSpriteId;
  const actionLabel = selected.length > 1 ? "as expressoes selecionadas" : `a expressao ${EXPRESSION_LABELS[selected[0]] || selected[0]}`;
  if (!confirm(`Regenerar ${actionLabel}? As imagens atuais serao substituidas nesta aparencia.`)) return;

  const failures = [];
  setBusy(true, selected.length > 1 ? "Regenerando expressoes..." : "Regenerando expressao...");
  for (let index = 0; index < selected.length; index += 1) {
    const expression = selected[index];
    const label = EXPRESSION_LABELS[expression] || expression;
    try {
      const referenceAsset = (state.activeStory.assets || []).find(item => (
        item.id === baseSpriteId &&
        item.url &&
        normalizeExpression(item.expression) === "neutral"
      ));
      if (!referenceAsset) throw new Error(`Imagem de referencia ausente para ${label}.`);
      state.status = `Regenerando ${label} (${index + 1}/${selected.length})...`;
      render();
      const result = await api(`/api/assets/${referenceAsset.id}/expressions/${expression}/regenerate`, {
        method: "POST",
        body: JSON.stringify({
          workbench: style.expression_workbench,
          selected_count: selected.length,
          sequence_index: index,
        }),
      });
      await waitForAsset(result.asset_id, `Gerando expressao ${label} no ComfyUI...`);
      await loadStory(state.activeStory.id);
      render();
    } catch (error) {
      failures.push(`${label}: ${error.message}`);
    }
  }
  state.modal = { type: "expressions", characterId, baseSpriteId, selectedExpressions: [], editingExpression: "" };
  setBusy(false);
  render();
  if (failures.length) alert(`Algumas expressoes falharam:\n${failures.join("\n")}`);
}

async function generateSprite(characterId) {
  await ensureStoryExpressionPrompts();
  const character = (state.activeStory.characters || []).find(item => item.id === characterId);
  if (!character) return;
  if (!isVisualCharacter(character)) {
    alert("Este personagem nao usa sprite neste modo de participacao.");
    return;
  }
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
  if (!isVisualCharacter(character)) {
    alert("Este personagem nao usa sprite neste modo de participacao.");
    return;
  }
  if (!(character.visual_prompt || "").trim()) {
    alert("Gere ou preencha o Prompt para Geracao de Imagem antes de regenerar o sprite.");
    state.characterPromptExpanded = true;
    render();
    return;
  }
  const latestSprite = getActiveAppearanceSprite(character, "neutral");
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
  const pollIntervalMs = 1500;
  const startedAt = Date.now();
  while (true) {
    const elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000);
    state.status = `${label} ${elapsedSeconds}s`;
    render();
    await sleep(pollIntervalMs);
    const result = await api(`/api/assets/${assetId}/result`);
    if (result.ready) return result.asset;
  }
}

async function waitForAppearanceUpdateAssets(story) {
  const results = story?.appearance_update_results?.results || [];
  const queuedAssets = results.filter(item => item?.mode === "create_new" && item.asset_id);
  if (!queuedAssets.length) return [];
  const resolved = [];
  for (const item of queuedAssets) {
    resolved.push(await waitForAsset(item.asset_id, "Gerando nova aparencia no ComfyUI..."));
  }
  await loadStory(story.id);
  return resolved;
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

function editableBackgroundPrompt(scene, background) {
  return (
    background?.metadata?.source_prompt ||
    scene?.background_prompt ||
    background?.prompt ||
    ""
  );
}

function findCharacterSprite(name, expression) {
  const character = findStoryCharacter(name);
  if (!character) return null;
  const base = getActiveAppearanceSprite(character, "neutral");
  if (!base) return null;
  if (!styleExpressionsEnabled()) return base;
  const appearance = getActiveAppearance(character);
  return getAppearanceSprite(appearance, expression) || getAppearanceSprite(appearance, "neutral") || base;
}

function styleExpressionsEnabled() {
  return state.activeStory?.visual_style_record?.expressions_enabled === true;
}

function normalizeExpression(value) {
  const text = String(value || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  return OFFICIAL_EXPRESSIONS.includes(text) ? text : "neutral";
}

function getSpriteExpressionAsset(baseSprite, expression) {
  if (!baseSprite) return null;
  const normalized = normalizeExpression(expression);
  if (normalized === "neutral") return baseSprite;
  const baseId = baseSprite.base_asset_id || baseSprite.id;
  const assets = (state.activeStory?.assets || []).filter(asset => (
    asset.asset_type === "sprite" &&
    asset.character_id === baseSprite.character_id &&
    asset.url &&
    (!baseSprite.appearance_id || !asset.appearance_id || asset.appearance_id === baseSprite.appearance_id) &&
    (asset.base_asset_id === baseId || asset.base_asset_id === baseSprite.id) &&
    normalizeExpression(asset.expression) === normalized
  ));
  return assets[0] || baseSprite;
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

function secretField(name, label, value) {
  const configured = value === "********" || Boolean(value);
  return `
    <div class="field">
      <label for="${name}">${label}</label>
      <input id="${name}" name="${name}" type="password" autocomplete="off" value="" placeholder="${configured ? "Configurada - deixe em branco para manter" : "Cole a chave aqui"}">
    </div>
  `;
}

function checkboxField(name, label, checked) {
  return `
    <label class="check-row full">
      <input type="hidden" name="${name}" value="false">
      <input type="checkbox" id="${name}" name="${name}" value="true" ${checked ? "checked" : ""}>
      <span>${label}</span>
    </label>
  `;
}

function numberField(name, label, value) {
  return `
    <div class="field">
      <label for="${name}">${label}</label>
      <input id="${name}" name="${name}" type="number" step="any" value="${escapeAttr(value)}">
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
