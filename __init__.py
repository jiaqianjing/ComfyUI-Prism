from .gpt_image_generate_node import GPTImageGenerateNode
from .gpt_image_edit_node import GPTImageEditNode
from .gemini_image_generate_node import GeminiImageGenerateNode
from .gemini_image_edit_node import GeminiImageEditNode

NODE_CLASS_MAPPINGS = {
    "GPTImageGenerateNode": GPTImageGenerateNode,
    "GPTImageEditNode": GPTImageEditNode,
    "GeminiImageGenerateNode": GeminiImageGenerateNode,
    "GeminiImageEditNode": GeminiImageEditNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPTImageGenerateNode": "GPT Image Generate",
    "GPTImageEditNode": "GPT Image Edit",
    "GeminiImageGenerateNode": "Nano Banana Generate",
    "GeminiImageEditNode": "Nano Banana Edit"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
