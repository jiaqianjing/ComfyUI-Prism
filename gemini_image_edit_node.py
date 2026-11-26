"""ComfyUI Gemini node: prompt/options -> IMAGE batch; calls the official image API."""
import torch
import base64
import numpy as np
from PIL import Image
from io import BytesIO

from .api_keys import get_api_key
from .image_model_options import (
    ASPECT_RATIOS, GEMINI_IMAGE_SIZES, GEMINI_MODELS, NANO_BANANA_2_1, validate_gemini_options,
)
from .nano_banana_client import request_nano_banana_image


class GeminiImageEditNode:
    """ComfyUI 自定义节点：使用 Google Nano Banana 模型编辑图片。

    输入：
        prompt (STRING): 文本提示词，描述要进行的编辑操作。
        image (IMAGE): 待编辑的图片。
    输出：
        IMAGE: 编辑后的图片（Tensor, 0~1, BxHxWxC）。
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
                "image": ("IMAGE",),
            },
            "optional": {
                "aspect_ratio": (ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (GEMINI_IMAGE_SIZES, {"default": "1K"}),
                "model": (GEMINI_MODELS, {"default": NANO_BANANA_2_1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "edit"
    CATEGORY = "Prism"

    # ---------- 辅助函数 ----------
    @staticmethod
    def _tensor_to_base64(tensor: torch.Tensor) -> str:
        """将 ComfyUI 的图像 Tensor 转换为 base64 编码的字符串。"""
        if tensor.ndim == 4:
            tensor = tensor[0]

        img_np = (tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
        img_pil = Image.fromarray(img_np)

        buffer = BytesIO()
        img_pil.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        # 转换为 base64
        image_bytes = buffer.read()
        base64_data = base64.b64encode(image_bytes).decode('utf-8')

        return base64_data

    # ---------- 主功能 ----------
    def edit(self, prompt: str, image: torch.Tensor, aspect_ratio: str = "1:1", image_size: str = "1K", model: str = NANO_BANANA_2_1):
        """根据 prompt 和参考图片调用 API 生成编辑后的图片。"""
        validate_gemini_options(model, aspect_ratio, image_size)
        image_base64 = self._tensor_to_base64(image)
        return (request_nano_banana_image(
            self.api_url, self.api_key, prompt, model, aspect_ratio, image_size, image_base64=image_base64
        ),)
