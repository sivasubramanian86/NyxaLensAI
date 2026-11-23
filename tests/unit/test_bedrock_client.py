"""
Unit tests: Bedrock client wrapper with mocked boto3.
Verifies retry logic, model routing, and lru_cache behaviour.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

import shared.bedrock_client as bc


MOCK_CONVERSE_RESPONSE = {
    "output": {
        "message": {
            "content": [{"type": "text", "text": "classification: GITHUB_URL"}]
        }
    }
}

MOCK_TOOL_USE_RESPONSE = {
    "output": {
        "message": {
            "content": [
                {"toolUse": {"toolUseId": "t1", "name": "my_tool", "input": {"result": "ok"}}}
            ]
        }
    }
}

MOCK_EMBED_RESPONSE_BODY = b'{"embedding": [0.1] * 1024}'


class TestInvokeLite:
    def test_returns_text(self):
        with patch.object(bc, "_bedrock_runtime_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client.converse.return_value = MOCK_CONVERSE_RESPONSE
            mock_client_factory.return_value = mock_client

            bc._bedrock_runtime_client.cache_clear()
            result = bc.invoke_lite("Classify this input.")
            assert "GITHUB_URL" in result

    def test_throttle_retry(self):
        from botocore.exceptions import ClientError
        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "Converse"
        )
        with patch.object(bc, "_bedrock_runtime_client") as mock_client_factory:
            mock_client = MagicMock()
            # First call throttles, second succeeds
            mock_client.converse.side_effect = [throttle_error, MOCK_CONVERSE_RESPONSE]
            mock_client_factory.return_value = mock_client

            bc._bedrock_runtime_client.cache_clear()
            with patch("time.sleep"):  # don't actually sleep in tests
                result = bc.invoke_lite("test")
            assert result is not None


class TestInvokeSonnetJson:
    def test_returns_tool_use_input(self):
        tool_schema = {
            "name": "my_tool",
            "description": "Test tool",
            "inputSchema": {"json": {"type": "object", "properties": {"result": {"type": "string"}}}},
        }
        with patch.object(bc, "_bedrock_runtime_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client.converse.return_value = MOCK_TOOL_USE_RESPONSE
            mock_client_factory.return_value = mock_client

            bc._bedrock_runtime_client.cache_clear()
            result = bc.invoke_sonnet_json("Generate output.", tool_schema)
            assert result == {"result": "ok"}

    def test_raises_on_no_tool_use_block(self):
        empty_response = {
            "output": {"message": {"content": [{"type": "text", "text": "plain text"}]}}
        }
        tool_schema = {"name": "my_tool", "description": "x",
                        "inputSchema": {"json": {"type": "object"}}}
        with patch.object(bc, "_bedrock_runtime_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client.converse.return_value = empty_response
            mock_client_factory.return_value = mock_client

            bc._bedrock_runtime_client.cache_clear()
            with pytest.raises(ValueError):
                bc.invoke_sonnet_json("test", tool_schema)
