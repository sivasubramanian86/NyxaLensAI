"""
Unit tests: GitHub client — Secrets Manager token caching.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

import shared.github_client as gc


class TestGetToken:
    def test_returns_empty_string_when_no_arn(self):
        gc._get_token.cache_clear()
        with patch.dict("os.environ", {"GITHUB_SECRET_ARN": ""}):
            token = gc._get_token()
        assert token == ""

    def test_fetches_from_secrets_manager(self):
        gc._get_token.cache_clear()
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {"SecretString": "ghp_test_token"}
        with patch("shared.github_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            with patch.dict("os.environ", {"GITHUB_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123:secret:test"}):
                token = gc._get_token()
        assert token == "ghp_test_token"

    def test_returns_empty_on_secrets_manager_error(self):
        from botocore.exceptions import ClientError
        gc._get_token.cache_clear()
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "GetSecretValue"
        )
        with patch("shared.github_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            with patch.dict("os.environ", {"GITHUB_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123:secret:missing"}):
                token = gc._get_token()
        assert token == ""
