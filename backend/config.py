from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
STORIES_DIR = DATA_DIR / "stories"
STYLE_COVERS_DIR = DATA_DIR / "style_covers"
DB_PATH = DATA_DIR / "app.sqlite"

DEFAULT_SETTINGS = {
    "ai_provider": "ollama",
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "mistral-nemo",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4.1-mini",
    "openai_api_key": "",
    "openai_verify_ssl": True,
    "openai_compatible_base_url": "",
    "openai_compatible_model": "",
    "openai_compatible_api_key": "",
    "openai_compatible_verify_ssl": True,
    "openai_compatible_llama_mode": False,
    "llama_preset": "balanced",
    "llama_temperature": 0.78,
    "llama_top_p": 0.9,
    "llama_top_k": 40,
    "llama_min_p": 0.02,
    "llama_context_window": 4096,
    "llama_max_tokens": 1200,
    "llama_retry_max_tokens": 1400,
    "llama_max_attempts": 2,
    "llama_repeat_penalty": 1.12,
    "llama_repeat_last_n": 512,
    "llama_enable_thinking": False,
    "llama_cache_prompt": True,
    "llama_timings_per_token": False,
    "llama_timeout": 240,
    "llama_custom_presets": {},
    "story_ai_provider": "openai-compatible",
    "story_ai_openai_compatible_base_url": "",
    "story_ai_openai_compatible_model": "",
    "story_ai_openai_compatible_api_key": "",
    "story_ai_openai_compatible_verify_ssl": True,
    "story_ai_openai_compatible_llama_mode": True,
    "story_ai_llama_preset": "quality",
    "story_ai_llama_temperature": 0.78,
    "story_ai_llama_top_p": 0.9,
    "story_ai_llama_top_k": 40,
    "story_ai_llama_min_p": 0.03,
    "story_ai_llama_context_window": 8192,
    "story_ai_llama_max_tokens": 2400,
    "story_ai_llama_retry_max_tokens": 3200,
    "story_ai_llama_max_attempts": 2,
    "story_ai_llama_repeat_penalty": 1.12,
    "story_ai_llama_repeat_last_n": 768,
    "story_ai_llama_enable_thinking": False,
    "story_ai_llama_cache_prompt": True,
    "story_ai_llama_timings_per_token": False,
    "story_ai_llama_timeout": 420,
    "scene_ai_provider": "openai-compatible",
    "scene_ai_openai_compatible_base_url": "",
    "scene_ai_openai_compatible_model": "",
    "scene_ai_openai_compatible_api_key": "",
    "scene_ai_openai_compatible_verify_ssl": True,
    "scene_ai_openai_compatible_llama_mode": True,
    "scene_ai_llama_preset": "balanced",
    "scene_ai_llama_temperature": 0.78,
    "scene_ai_llama_top_p": 0.9,
    "scene_ai_llama_top_k": 40,
    "scene_ai_llama_min_p": 0.02,
    "scene_ai_llama_context_window": 4096,
    "scene_ai_llama_max_tokens": 1200,
    "scene_ai_llama_retry_max_tokens": 1400,
    "scene_ai_llama_max_attempts": 2,
    "scene_ai_llama_repeat_penalty": 1.12,
    "scene_ai_llama_repeat_last_n": 512,
    "scene_ai_llama_enable_thinking": False,
    "scene_ai_llama_cache_prompt": True,
    "scene_ai_llama_timings_per_token": False,
    "scene_ai_llama_timeout": 240,
    "ollama_preset": "balanced",
    "ollama_temperature": 0.8,
    "ollama_context": 6144,
    "ollama_top_p": 0.9,
    "ollama_top_k": 40,
    "ollama_min_p": 0,
    "ollama_num_predict": 1800,
    "ollama_retry_num_predict": 2200,
    "ollama_max_attempts": 2,
    "ollama_repeat_penalty": 1.12,
    "ollama_repeat_last_n": 512,
    "ollama_think": False,
    "ollama_keep_alive": "10m",
    "ollama_timeout": 240,
    "ollama_custom_presets": {},
    "comfy_url": "http://127.0.0.1:8188",
    "comfy_checkpoint": "animagine-xl-3.1.safetensors",
    "comfy_root": "N:\\SillyTavern\\ComfyUI",
    "comfy_workflows_dir": "N:\\SillyTavern\\ComfyUI\\user\\default\\workflows",
    "comfy_background_workbench": "",
    "comfy_sprite_workbench": "",
    "comfy_sprite_edit_workbench": "",
    "comfy_free_memory_between_workbench_runs": True,
    "comfy_prompt_profiles": {
        "spriteGenerator_AnimaBaseV1.json": {
            "style": (
                "Write a detailed natural-language English prompt for a visual novel character sprite. "
                "Do not use short booru tag lists as the main style. Describe anatomy, face, skin, hair, "
                "outfit, posture, expression, silhouette, and visual-novel sprite framing. "
                "One character only, full body, standing, front view, simple light background."
            ),
            "example": (
                "A tall, powerfully built man with light brown skin and a strong, athletic physique. "
                "He has broad shoulders, a muscular chest, thick arms, and a solid, imposing presence. "
                "His face is rugged and masculine, with a defined jawline, high cheekbones, and an intense, "
                "focused expression. His hair is short, gray, and slightly coarse, cut close to the head. "
                "He stands facing forward as a full-body visual novel sprite on a simple light gray background."
            ),
        },
        "spriteGenerator_Netayume.json": {
            "style": (
                "Write a detailed natural-language English prompt for a high-quality anime visual novel sprite. "
                "Use complete descriptive sentences, not only comma tags. Focus on identity consistency, clothing, "
                "body shape, face, hair, expression, pose, and clean sprite composition. One character only, full body, "
                "standing, front view, simple background."
            ),
            "example": (
                "A tall, powerfully built man with light brown skin and a commanding athletic build. "
                "He has short coarse gray hair, a rugged masculine face, a sharp jawline, high cheekbones, "
                "and a calm but intense expression. His clothing is dignified fantasy formalwear with layered fabric, "
                "subtle gold details, and a clean silhouette. Full-body visual novel character sprite, standing front view, "
                "simple light gray background."
            ),
        },
    },
    "system_language": "pt-BR",
    "default_language": "pt-BR",
    "image_width": 1536,
    "image_height": 864,
    "sprite_width": 1024,
    "sprite_height": 1536,
    "background_steps": 28,
    "background_cfg": 6.5,
    "sprite_steps": 24,
    "sprite_cfg": 5.0,
    "comfy_sampler": "dpmpp_2m_sde_gpu",
    "comfy_scheduler": "karras",
    "sprite_sampler": "euler_ancestral",
    "sprite_scheduler": "normal",
    "script_story_ai_cwd": "",
    "script_story_ai_command": "",
    "script_story_ai_start_with_app": False,
    "script_story_ai_show_window": True,
    "script_scene_ai_cwd": "",
    "script_scene_ai_command": "",
    "script_scene_ai_start_with_app": False,
    "script_scene_ai_show_window": True,
    "script_comfy_cwd": "N:\\SillyTavern\\ComfyUI",
    "script_comfy_command": "py -3.11 main.py --enable-cors-header",
    "script_comfy_start_with_app": False,
    "script_comfy_show_window": True,
}

DEFAULT_VISUAL_STYLES = [
    {
        "name": "Anime VN",
        "prompt_prefix": "anime visual novel character sprite,",
        "prompt_suffix": "full body, standing front view, clean silhouette, simple light gray background",
        "background_prompt_prefix": "anime visual novel background,",
        "background_prompt_suffix": "",
        "background_negative_prompt": "main character, foreground person, foreground people, close-up face, detailed face, portrait, centered human figure, character focus, action pose, text, logo, watermark",
        "background_settings": {"width": 1536, "height": 864, "steps": 28, "cfg": 6.5, "sampler_name": "dpmpp_2m_sde_gpu", "scheduler": "karras"},
    },
    {
        "name": "Fantasia painterly",
        "prompt_prefix": "painterly fantasy visual novel character sprite,",
        "prompt_suffix": "soft dramatic lighting, detailed fabric, full body, standing front view",
        "background_prompt_prefix": "painterly fantasy anime visual novel background,",
        "background_prompt_suffix": "",
        "background_negative_prompt": "main character, foreground person, foreground people, close-up face, detailed face, portrait, centered human figure, character focus, text, logo, watermark",
        "background_settings": {"width": 1536, "height": 864, "steps": 30, "cfg": 6.5, "sampler_name": "dpmpp_2m_sde_gpu", "scheduler": "karras"},
    },
    {
        "name": "Anime retro",
        "prompt_prefix": "retro anime visual novel character sprite,",
        "prompt_suffix": "clean cel shading, 1990s anime feeling, full body, standing front view",
        "background_prompt_prefix": "retro anime visual novel background,",
        "background_prompt_suffix": "",
        "background_negative_prompt": "main character, foreground person, foreground people, close-up face, detailed face, portrait, centered human figure, character focus, text, logo, watermark",
        "background_settings": {"width": 1536, "height": 864, "steps": 28, "cfg": 6.0, "sampler_name": "dpmpp_2m_sde_gpu", "scheduler": "karras"},
    },
    {
        "name": "Cinematico realista",
        "prompt_prefix": "cinematic realistic visual novel character sprite,",
        "prompt_suffix": "natural materials, film lighting, full body, standing front view",
        "background_prompt_prefix": "cinematic visual novel background,",
        "background_prompt_suffix": "",
        "background_negative_prompt": "main character, foreground person, foreground people, close-up face, detailed face, portrait, centered human figure, character focus, text, logo, watermark",
        "background_settings": {"width": 1536, "height": 864, "steps": 30, "cfg": 6.0, "sampler_name": "dpmpp_2m_sde_gpu", "scheduler": "karras"},
    },
    {
        "name": "Quadrinhos escuro",
        "prompt_prefix": "dark comic visual novel character sprite,",
        "prompt_suffix": "strong inked shadows, dramatic contrast, full body, standing front view",
        "background_prompt_prefix": "dark comic anime visual novel background,",
        "background_prompt_suffix": "",
        "background_negative_prompt": "main character, foreground person, foreground people, close-up face, detailed face, portrait, centered human figure, character focus, text, logo, watermark",
        "background_settings": {"width": 1536, "height": 864, "steps": 30, "cfg": 6.5, "sampler_name": "dpmpp_2m_sde_gpu", "scheduler": "karras"},
    },
]
