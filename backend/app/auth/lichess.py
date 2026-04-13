import hashlib
import secrets
import base64

import httpx

from app.config import settings

LICHESS_AUTH_URL = "https://lichess.org/oauth"
LICHESS_TOKEN_URL = "https://lichess.org/api/token"
LICHESS_ACCOUNT_URL = "https://lichess.org/api/account"


def generate_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def get_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.lichess_client_id,
        "redirect_uri": settings.lichess_redirect_uri,
        "scope": "",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{LICHESS_AUTH_URL}?{query}"


async def exchange_code(code: str, code_verifier: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LICHESS_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.lichess_redirect_uri,
                "client_id": settings.lichess_client_id,
                "code_verifier": code_verifier,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def get_lichess_user(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            LICHESS_ACCOUNT_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()
