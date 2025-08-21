# spotify/services/auth.py
"""
Auth/service layer for Spotify OAuth.
- Exchanges authorization codes for tokens.
- Fetches the user's Spotify profile.
- Upserts the user + encrypted tokens into the DB.
- Provides helpers to generate/validate OAuth `state` for CSRF protection.
"""

from __future__ import annotations

import os
import base64
import secrets
from datetime import timedelta
from typing import Dict, Any

import requests
from django.utils import timezone

from ..models import SpotifyUser
from ..utils import encrypt_token
from ..clients.spotify import sp_post_form

# Environment
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# ---- OAuth state helpers (CSRF protection) ---------------------------------

_STATE_SESSION_KEY = "oauth_state"

def generate_oauth_state(length: int = 24) -> str:
    """
    Create a cryptographically-strong random state string to send to Spotify.
    """
    return secrets.token_urlsafe(length)

def save_oauth_state(session, state: str) -> None:
    """
    Persist the state in the user's session for later verification.
    """
    session[_STATE_SESSION_KEY] = state

def validate_oauth_state(session, received_state: str | None) -> bool:
    """
    Compare received state to what we saved. Pop after checking to avoid reuse.
    Returns True if valid, else False.
    """
    expected = session.get(_STATE_SESSION_KEY)
    # one-time use
    if _STATE_SESSION_KEY in session:
        try:
            del session[_STATE_SESSION_KEY]
        except Exception:
            # if session backend is immutable, ignore
            pass
    return bool(expected) and (received_state == expected)

# ---- Token exchange + profile ----------------------------------------------

def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """
    Exchange an auth code for { access_token, refresh_token, expires_in, ... }.
    Raises for non-200 responses.
    """
    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    r = sp_post_form(token_url, data=payload, headers=headers)
    r.raise_for_status()
    return r.json()

def fetch_me(access_token: str) -> Dict[str, Any]:
    """
    GET /v1/me using the provided access token. Raises on non-200.
    """
    r = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

# ---- Persistence ------------------------------------------------------------

def upsert_spotify_user(token_data: Dict[str, Any], me: Dict[str, Any]) -> SpotifyUser:
    """
    Create or update a SpotifyUser row using the token payload and profile.
    - Encrypts and stores access/refresh tokens.
    - Computes and stores expires_at.
    """
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = int(token_data.get("expires_in", 3600))

    expires_at = timezone.now() + timedelta(seconds=expires_in)

    defaults = {
        "display_name": me.get("display_name") or me.get("id"),
        "email": me.get("email"),
        "expires_at": expires_at,
        "access_token": encrypt_token(access_token),
    }
    if refresh_token:
        defaults["refresh_token"] = encrypt_token(refresh_token)

    user, _ = SpotifyUser.objects.update_or_create(
        spotify_id=me["id"],
        defaults=defaults,
    )
    return user
