"""One-shot Google image requests; preserve GenerateContent for older models."""
import requests

from .image_model_options import NANO_BANANA_2_1, validate_gemini_options
from .image_response import decode_gemini_images, decode_nano_banana_interaction


def request_nano_banana_image(base_url, api_key, prompt, model, aspect_ratio,
                              image_size, *, image_base64=None):
    validate_gemini_options(model, aspect_ratio, image_size)
    headers = {'x-goog-api-key': api_key, 'Content-Type': 'application/json'}
    if model == NANO_BANANA_2_1:
        url = f'{base_url}/v1beta/interactions'
        headers['Api-Revision'] = '2026-05-20'
        inputs = [{'type': 'text', 'text': prompt}]
        if image_base64 is not None:
            inputs.append({'type': 'image', 'mime_type': 'image/jpeg',
                           'data': image_base64})
        payload = {
            'model': model, 'input': inputs, 'store': False,
            'response_format': {'type': 'image', 'aspect_ratio': aspect_ratio,
                                'image_size': image_size},
        }
        decoder = decode_nano_banana_interaction
    else:
        url = f'{base_url}/v1beta/models/{model}:generateContent'
        parts = [{'text': prompt}]
        if image_base64 is not None:
            parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': image_base64}})
        payload = {
            'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {
                'responseModalities': ['TEXT', 'IMAGE'],
                'imageConfig': {'aspectRatio': aspect_ratio, 'imageSize': image_size},
            },
        }
        decoder = decode_gemini_images
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    return decoder(response.json())
