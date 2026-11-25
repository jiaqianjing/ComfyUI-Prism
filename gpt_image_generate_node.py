"""ComfyUI GPT image node: prompt/options -> IMAGE batch; calls the official image API."""
import os
import requests
import json

from .utils import init_logger
from .image_model_options import (
    GPT_DEFAULT_MODEL, GPT_MODELS, GPT_QUALITIES, GPT_SIZES, validate_gpt_options,
)
from .image_response import decode_gpt_images


class GPTImageGenerateNode:
    """ComfyUI 自定义节点：使用 OpenAI 图像模型生成图片。

    输入：
        prompt (STRING): 文本提示词，支持多行。
    输出：
        IMAGE: 生成的图片（Tensor, 0~1, BxHxWxC）。
    """

    def __init__(self):
        self.logger = init_logger()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        if not self.api_key:
            raise ValueError("Set OPENAI_API_KEY before starting ComfyUI")

    # ---------- ComfyUI 接口定义 ----------
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "model": (GPT_MODELS, {"default": GPT_DEFAULT_MODEL}),
                "n": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                "quality": (GPT_QUALITIES, {"default": "auto"}),
                "size": (GPT_SIZES, {"default": "auto"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    CATEGORY = "Prism"

    # ---------- 主功能 ----------
    def generate(self, prompt: str, model=GPT_DEFAULT_MODEL, n: int = 1, quality="auto", size="auto"):
        """根据 prompt 调用 OpenAI 图像 API 生成图片。"""
        validate_gpt_options(model, n, quality, size, editing=False)
        try:
            url = f"{self.base_url}/images/generations"
            
            # 组装调用参数 (仅使用 API 支持的参数)
            payload_data = {
                "prompt": prompt,
                "model": model,
                "n": n,
                "quality": quality,
                "size": size,
            }

            payload = json.dumps(payload_data)
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.post(url, headers=headers, data=payload, timeout=120)  # 120秒超时
            response.raise_for_status() # 检查 HTTP 错误
            
            return (decode_gpt_images(response.json()),)
        except Exception as e:
            self.logger.error(f"Error in GPTImageGenerateNode: {str(e)}")
            raise
 