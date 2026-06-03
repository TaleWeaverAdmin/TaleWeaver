from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
STORIES_DIR = DATA_DIR / "stories"
DB_PATH = DATA_DIR / "app.sqlite"

DEFAULT_SETTINGS = {
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "mistral-nemo",
    "ollama_temperature": 0.8,
    "ollama_context": 8192,
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
                "outfit, posture, expression, silhouette, and visual-novel sprite framing. Keep it safe, "
                "non-explicit, one character only, full body, standing, front view, simple light background."
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
}
