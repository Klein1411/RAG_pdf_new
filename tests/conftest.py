"""
Pytest configuration and fixtures
"""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_dotenv():
    """Auto-mock dotenv.load_dotenv() cho tất cả tests"""
    with patch('src.gemini_client.dotenv.load_dotenv'):
        yield
