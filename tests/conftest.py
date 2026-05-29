import pytest
import os


@pytest.fixture(autouse=True)
def set_env():
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    yield
