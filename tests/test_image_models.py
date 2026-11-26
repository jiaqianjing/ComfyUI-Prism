"""Offline contracts: model options, wire requests, legacy defaults, image decoding."""
import base64
import importlib
import json
from io import BytesIO
from pathlib import Path
import sys
import types
from unittest.mock import Mock

import pytest
import torch
from PIL import Image

# Load node modules without executing ComfyUI's plugin registration entry point.
PACKAGE = 'model_test_plugin'
package = types.ModuleType(PACKAGE)
package.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[PACKAGE] = package
options = importlib.import_module(f'{PACKAGE}.image_model_options')
responses = importlib.import_module(f'{PACKAGE}.image_response')


def test_comfy_registration_stays_compatible(monkeypatch):
    from logging import getLogger

    plugin = importlib.import_module(f'{PACKAGE}.__init__')
    expected = {
        'GPTImageGenerateNode': 'GPT Image Generate',
        'GPTImageEditNode': 'GPT Image Edit',
        'GeminiImageGenerateNode': 'Nano Banana Generate',
        'GeminiImageEditNode': 'Nano Banana Edit',
    }
    assert plugin.NODE_DISPLAY_NAME_MAPPINGS == expected
    assert set(plugin.NODE_CLASS_MAPPINGS) == set(expected)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-token')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-token')
    root = getLogger()
    previous = (root.level, tuple(root.handlers))
    for node_id, cls in plugin.NODE_CLASS_MAPPINGS.items():
        assert cls.__name__ == node_id and cls.CATEGORY == 'Prism'
        cls()
        cls()
    assert (root.level, tuple(root.handlers)) == previous


def png():
    buffer = BytesIO()
    Image.new('RGB', (2, 2), (255, 0, 0)).save(buffer, format='PNG')
    return buffer.getvalue()


def test_gpt_capabilities():
    for model in options.GPT_MODELS:
        options.validate_gpt_options(model, 1, 'auto', 'auto')
        with pytest.raises(ValueError):
            options.validate_gpt_options(model, 1, 'xhigh', 'auto')
        with pytest.raises(ValueError):
            options.validate_gpt_options(model, 1, 'auto', '2048x2048')
    for n in (0, 11, True, 1.5):
        with pytest.raises(ValueError):
            options.validate_gpt_options(options.GPT_MODELS[0], n, 'auto', 'auto')


def test_gemini_capabilities():
    options.validate_gemini_options('gemini-nano-banana-2.1', '16:9', '4K')
    options.validate_gemini_options('gemini-3-pro-image', '16:9', '2K')
    options.validate_gemini_options('gemini-3.1-flash-lite-image', '16:9', '1K')
    with pytest.raises(ValueError, match='only 1K'):
        options.validate_gemini_options('gemini-3.1-flash-lite-image', '16:9', '2K')


def test_response_formats(monkeypatch):
    result = Mock(content=png())
    get = Mock(return_value=result)
    monkeypatch.setattr(responses.requests, 'get', get)
    batch = responses.decode_gpt_images({'data': [
        {'b64_json': base64.b64encode(png()).decode()},
        {'url': 'https://example.com/image.png'},
    ]})
    assert batch.shape == (2, 2, 2, 3)
    assert torch.equal(batch[0], batch[1])
    assert batch[0, 0, 0].tolist() == [1.0, 0.0, 0.0]
    get.assert_called_once_with('https://example.com/image.png', timeout=120)
    with pytest.raises(ValueError):
        responses.download_image('file:///etc/passwd')
    for data in ({}, {'data': []}, {'data': [{}]}):
        with pytest.raises(RuntimeError):
            responses.decode_gpt_images(data)


@pytest.mark.parametrize('editing', [False, True])
def test_gpt_wire_requests(monkeypatch, editing):
    module = importlib.import_module(f'{PACKAGE}.gpt_image_{"edit" if editing else "generate"}_node')
    cls = module.GPTImageEditNode if editing else module.GPTImageGenerateNode
    monkeypatch.setenv('OPENAI_API_KEY', 'test-token')
    node = cls()
    expected_model = 'gpt-image-2.6-flare'
    choices, widget = cls.INPUT_TYPES()['optional']['model']
    assert choices == [expected_model]
    assert widget['default'] == expected_model

    response = Mock()
    response.json.return_value = {'data': [{'b64_json': base64.b64encode(png()).decode()}]}
    post = Mock(return_value=response)
    monkeypatch.setattr(module.requests, 'post', post)
    method = getattr(node, cls.FUNCTION)
    image = torch.zeros(1, 2, 2, 3)
    args = {'image1': image, 'image2': image, 'mask': torch.ones(1, 2, 2)} if editing else {}
    endpoint = 'edits' if editing else 'generations'

    for model_args in ({}, {'model': expected_model}):
        result = method('test', size='1024x1024', quality='low', **args, **model_args)
        assert post.call_args.args == (f'https://api.openai.com/v1/images/{endpoint}',)
        request = post.call_args.kwargs
        assert request['headers']['Authorization'] == 'Bearer test-token'
        payload = request['data'] if editing else json.loads(request['data'])
        assert payload == {
            'model': expected_model, 'prompt': 'test', 'n': 1,
            'size': '1024x1024', 'quality': 'low',
        }
        if editing:
            assert 'Content-Type' not in request['headers']
            files = request['files']
            assert [(field, part[0], part[2]) for field, part in files] == [
                ('image[]', 'image0.png', 'image/png'),
                ('image[]', 'image1.png', 'image/png'),
                ('mask', 'mask.png', 'image/png'),
            ]
            with Image.open(files[-1][1][1]) as mask:
                assert mask.getpixel((0, 0))[3] == 0
        else:
            assert request['headers']['Content-Type'] == 'application/json'
            assert 'files' not in request
        assert result[0].shape == (1, 2, 2, 3)
    assert response.raise_for_status.call_count == 2

    before = post.call_count
    for retired in ('gpt-image-1', 'gpt-image-1.5', 'gpt-image-2-all'):
        with pytest.raises(ValueError, match='Unknown GPT image model'):
            method('test', model=retired, **args)
    with pytest.raises(ValueError, match='Unsupported image quality or size'):
        method('test', quality='max', **args)
    assert post.call_count == before


@pytest.mark.parametrize('editing', [False, True])
def test_nano_banana_and_legacy_wire_requests(monkeypatch, editing):
    module = importlib.import_module(f'{PACKAGE}.gemini_image_{"edit" if editing else "generate"}_node')
    client = importlib.import_module(f'{PACKAGE}.nano_banana_client')
    cls = module.GeminiImageEditNode if editing else module.GeminiImageGenerateNode
    monkeypatch.setenv('GEMINI_API_KEY', 'test-token')
    node = cls()
    expected_model = 'gemini-nano-banana-2.1'
    choices, widget = cls.INPUT_TYPES()['optional']['model']
    assert choices == [expected_model, 'gemini-3-pro-image', 'gemini-3.1-flash-lite-image']
    assert widget['default'] == expected_model
    assert cls.INPUT_TYPES()['optional']['image_size'][0] == ['1K', '2K', '4K']
    image_data = base64.b64encode(png()).decode()
    response = Mock()
    post = Mock(return_value=response)
    monkeypatch.setattr(client.requests, 'post', post)
    method = getattr(node, cls.FUNCTION)
    args = {'image': torch.zeros(1, 2, 2, 3)} if editing else {}

    for optional_model in ({}, {'model': expected_model}):
        response.json.return_value = {
            'status': 'completed',
            'steps': [
                {'type': 'thought', 'content': [{'type': 'image', 'data': 'not-output'}]},
                {'type': 'model_output', 'content': [
                    {'type': 'text', 'text': 'Ignored'},
                    {'type': 'image', 'mime_type': 'image/png', 'data': image_data},
                ]},
            ],
        }
        assert method('test', aspect_ratio='16:9', image_size='4K', **args, **optional_model)[0].shape == (1, 2, 2, 3)
        assert post.call_args.args == ('https://generativelanguage.googleapis.com/v1beta/interactions',)
        request = post.call_args.kwargs
        assert request['headers']['Api-Revision'] == '2026-05-20'
        assert request['headers']['x-goog-api-key'] == 'test-token'
        payload = request['json']
        assert payload['model'] == expected_model
        assert payload['store'] is False
        assert payload['response_format'] == {'type': 'image', 'aspect_ratio': '16:9', 'image_size': '4K'}
        assert payload['input'][0] == {'type': 'text', 'text': 'test'}
        assert len(payload['input']) == (2 if editing else 1)
        if editing:
            part = payload['input'][1]
            assert (part['type'], part['mime_type']) == ('image', 'image/jpeg')
            with Image.open(BytesIO(base64.b64decode(part['data']))) as reference:
                assert reference.format == 'JPEG' and reference.size == (2, 2)

    response.json.return_value = {'candidates': [{'content': {'parts': [
        {'inlineData': {'data': image_data}}
    ]}}]}
    for legacy in choices[1:]:
        assert method('test', model=legacy, **args)[0].shape == (1, 2, 2, 3)
        assert post.call_args.args == (f'https://generativelanguage.googleapis.com/v1beta/models/{legacy}:generateContent',)
        request = post.call_args.kwargs
        assert 'Api-Revision' not in request['headers']
        assert request['headers']['x-goog-api-key'] == 'test-token'
        assert request['timeout'] == 180
        parts = request['json']['contents'][0]['parts']
        assert parts[0] == {'text': 'test'}
        if editing:
            assert parts[1]['inline_data']['mime_type'] == 'image/jpeg'
    before = post.call_count
    with pytest.raises(ValueError, match='only 1K'):
        method('test', model='gemini-3.1-flash-lite-image', image_size='4K', **args)
    assert post.call_count == before


def test_nano_banana_rejects_incomplete_or_missing_image():
    with pytest.raises(RuntimeError, match='did not complete'):
        responses.decode_nano_banana_interaction({'status': 'incomplete'})
    with pytest.raises(RuntimeError, match='No image data'):
        responses.decode_nano_banana_interaction({'status': 'completed', 'steps': []})


@pytest.mark.parametrize('key', ['inlineData', 'inline_data'])
def test_gemini_response_formats(key):
    result = responses.decode_gemini_images({'candidates': [{'content': {'parts': [
        {'text': 'description'}, {key: {'data': base64.b64encode(png()).decode()}}
    ]}}]})
    assert result.shape == (1, 2, 2, 3)
    for data in ({}, {'candidates': []}, {'candidates': [{'content': {'parts': []}}]}):
        with pytest.raises(RuntimeError):
            responses.decode_gemini_images(data)
