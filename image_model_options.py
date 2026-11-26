"""Supported official image models and node options."""
GPT_DEFAULT_MODEL = 'gpt-image-2.6-flare'
GPT_MODELS = [GPT_DEFAULT_MODEL]
GPT_QUALITIES = ['auto', 'high', 'medium', 'low']
GPT_SIZES = ['auto', '1024x1024', '1536x1024', '1024x1536']
NANO_BANANA_2_1 = 'gemini-nano-banana-2.1'
GEMINI_MODELS = [NANO_BANANA_2_1, 'gemini-3-pro-image', 'gemini-3.1-flash-lite-image']
GEMINI_IMAGE_SIZES = ['1K', '2K', '4K']
GEMINI_SIZES = {
    NANO_BANANA_2_1: tuple(GEMINI_IMAGE_SIZES),
    'gemini-3-pro-image': ('1K', '2K'),
    'gemini-3.1-flash-lite-image': ('1K',),
}
ASPECT_RATIOS = ['1:1', '9:16', '16:9', '4:3', '3:4']


def validate_gpt_options(model, n, quality, size, *, editing=False):
    """Validate options before network I/O."""
    if model not in GPT_MODELS:
        raise ValueError(f'Unknown GPT image model: {model}')
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 10:
        raise ValueError('n must be an integer from 1 to 10')
    if quality not in GPT_QUALITIES or size not in GPT_SIZES:
        raise ValueError('Unsupported image quality or size')


def validate_gemini_options(model, aspect_ratio, image_size):
    """Reject unknown models and resolutions unsupported by the selected model."""
    if model not in GEMINI_SIZES:
        raise ValueError(f'Unknown Gemini image model: {model}')
    if aspect_ratio not in ASPECT_RATIOS:
        raise ValueError('Unsupported aspect ratio')
    if image_size not in GEMINI_SIZES[model]:
        raise ValueError(f'{model} supports only {", ".join(GEMINI_SIZES[model])}')
