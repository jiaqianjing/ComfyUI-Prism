"""ComfyUI Gemini node: prompt/options -> IMAGE batch; calls the official image API."""

from .api_keys import get_api_key
from .image_model_options import (
    ASPECT_RATIOS, GEMINI_IMAGE_SIZES, GEMINI_MODELS, NANO_BANANA_2_1,
)
from .nano_banana_client import request_nano_banana_image

class GeminiImageGenerateNode:
    """ComfyUI 自定义节点：使用 Google Nano Banana 模型生成图片。

    输入：
        prompt (STRING): 文本提示词，支持多行。
    输出：
        IMAGE: 生成的图片（Tensor, 0~1, BxHxWxC）。
    """

    def __init__(self):
        self.api_key = get_api_key("GEMINI_API_KEY")
        self.api_url = "https://generativelanguage.googleapis.com"

    # ---------- ComfyUI 接口定义 ----------
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "aspect_ratio": (ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (GEMINI_IMAGE_SIZES, {"default": "1K"}),
                "model": (GEMINI_MODELS, {"default": NANO_BANANA_2_1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    CATEGORY = "Prism"

    # ---------- 主功能 ----------
    def generate(self, prompt: str, aspect_ratio: str = "1:1", image_size: str = "1K", model: str = NANO_BANANA_2_1):
        """根据 prompt 调用选定的 Nano Banana 模型生成图片。"""
        return (request_nano_banana_image(
            self.api_url, self.api_key, prompt, model, aspect_ratio, image_size
        ),)
