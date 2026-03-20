import os
import tempfile
import pytest
from unittest.mock import patch
from caption_gen import validate_inputs


def test_validate_missing_image():
    with pytest.raises(SystemExit, match="not found"):
        validate_inputs("/nonexistent.png", "/tmp/script.txt")


def test_validate_wrong_image_dimensions():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        from PIL import Image
        img = Image.new("RGB", (800, 600))
        img.save(f.name)
        with pytest.raises(SystemExit, match="1080x1920"):
            validate_inputs(f.name, "/tmp/script.txt")
        os.unlink(f.name)


def test_validate_empty_script():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")
        from PIL import Image
        Image.new("RGB", (1080, 1920)).save(img_path)
        with open(script_path, "w") as f:
            f.write("")
        with pytest.raises(SystemExit, match="empty"):
            validate_inputs(img_path, script_path)


def test_validate_missing_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")
        from PIL import Image
        Image.new("RGB", (1080, 1920)).save(img_path)
        with open(script_path, "w") as f:
            f.write("Hello world")
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="ELEVENLABS_API_KEY"):
                validate_inputs(img_path, script_path)


def test_validate_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "bg.png")
        script_path = os.path.join(tmpdir, "script.txt")
        from PIL import Image
        Image.new("RGB", (1080, 1920)).save(img_path)
        with open(script_path, "w") as f:
            f.write("Hello world")
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            text = validate_inputs(img_path, script_path)
            assert text == "Hello world"
