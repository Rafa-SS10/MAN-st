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
    #Manages authentication configuration and secrets retrieval
    def __init__(self) -> None:
        self.env = os.getenv("ENVIRONMENT", "dev")
        self.sso_client_id_secret = "dev/sso/id"
        self.authorize_url = f"https://man-salesfunnel-leadseek-{self.env}-userpool-domain.auth.eu-west-1.amazoncognito.com/oauth2/authorize"
        self.token_url = f"https://man-salesfunnel-leadseek-{self.env}-userpool-domain.auth.eu-west-1.amazoncognito.com/oauth2/token"
        self.callback_url = "https://sa-chatbot.salesfunnel-dev.rio.cloud"

    def get_client_secret(self, key: str) -> str:
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