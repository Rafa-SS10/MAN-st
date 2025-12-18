"""
Authentication Configuration Module

This module handles the configuration and retrieval of authentication secrets
from AWS Secrets Manager. It manages environment-specific URLs for Cognito
and retrieves client secrets required for the OAuth flow.
"""

import boto3
import json
import os


class AuthConfig:
    """
    Manages authentication configuration and secrets retrieval.

    Attributes:
        env (str): Deployment environment name, read from ENVIRONMENT env var (default "dev").
        sso_client_id_secret (str): Secrets Manager key path for the SSO client secret.
        authorize_url (str): Cognito authorize endpoint for the configured environment.
        token_url (str): Cognito token endpoint for the configured environment.
        callback_url (str): OAuth callback URL used by the application.

    Example:
        >>> cfg = AuthConfig()
        >>> cfg.env
        'dev'
    """
    def __init__(self) -> None:
        """
        Initialize the AuthConfig with environment-specific defaults.

        Reads the ENVIRONMENT environment variable to determine which environment
        to target and builds the Cognito authorize and token URLs accordingly.

        Args:
            None

        Returns:
            None

        Example:
            >>> cfg = AuthConfig()
            >>> isinstance(cfg, AuthConfig)
            True
        """
        self.env = os.getenv("ENVIRONMENT", "dev")
        self.sso_client_id_secret = "dev/sso/id"
        self.authorize_url = f"https://man-salesfunnel-leadseek-{self.env}-userpool-domain.auth.eu-west-1.amazoncognito.com/oauth2/authorize"
        self.token_url = f"https://man-salesfunnel-leadseek-{self.env}-userpool-domain.auth.eu-west-1.amazoncognito.com/oauth2/token"
        self.callback_url = "https://sa-chatbot.salesfunnel-dev.rio.cloud"

    def get_client_secret(self, key: str) -> str:
        """
        Retrieve a client secret from AWS Secrets Manager.

        Determines which secret id to request based on the provided key, calls
        AWS Secrets Manager, and returns the parsed secret string as a Python object.

        Args:
            key (str): Identifier for which secret to retrieve. Supported values:
                - "CLIENT_SECRET": uses self.secret_name (must be set elsewhere).
                - "B2C_CLIENT_SECRET": uses self.sso_client_id_secret.

        Returns:
            str: Parsed secret content retrieved from Secrets Manager. Typically a dict
            when the secret string contains JSON.

        Raises:
            Exception: If the secret is not present in the Secrets Manager response.
            botocore.exceptions.ClientError: If the AWS Secrets Manager call fails.

        Example:
            >>> cfg = AuthConfig()
            >>> cfg.get_client_secret("B2C_CLIENT_SECRET")
            {'client_secret': '...'}
        """
        #Retrieve client secret from AWS Secrets Manager
        if key == "CLIENT_SECRET":
            secretid = self.secret_name
        elif key == "B2C_CLIENT_SECRET":
            secretid = self.sso_client_id_secret
        client = boto3.client("secretsmanager", region_name="eu-west-1")
        response = client.get_secret_value(SecretId=secretid)
        if "SecretString" in response:
            secret_string = response["SecretString"]
            secret = json.loads(secret_string)
            return secret
        else:
            raise Exception("Secret not found in response.")