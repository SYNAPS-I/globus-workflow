"""Globus authentication helpers."""

import os

import globus_sdk
from dotenv import load_dotenv

load_dotenv()


def get_confidential_client():
    """Create a Globus confidential application client."""
    client_id = os.environ["GLOBUS_CLIENT_ID"]
    client_secret = os.environ["GLOBUS_CLIENT_SECRET"]

    client = globus_sdk.ConfidentialAppAuthClient(client_id, client_secret)
    return client


def get_transfer_client():
    """Create an authorized Globus TransferClient."""
    client = get_confidential_client()

    token_response = client.oauth2_client_credentials_tokens()
    transfer_data = token_response.by_resource_server["transfer.api.globus.org"]

    authorizer = globus_sdk.AccessTokenAuthorizer(transfer_data["access_token"])
    return globus_sdk.TransferClient(authorizer=authorizer)
