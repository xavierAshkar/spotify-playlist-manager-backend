'''
spotify/services/auth.py

This file is used to handle Spotify authentication and user data management.
 - Exchanges authorization codes for access and refresh tokens.
 - Fetches user profile information from Spotify.
 - Upserts user data into the database.
'''

import base64, os
from datetime import timedelta
from django.utils import timezone
from ..models import SpotifyUser
from ..utils import encrypt_token
from ..clients.spotify import sp_post_form
import requests

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

def exchange_code_for_tokens(code: str):
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
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = sp_post_form(token_url, data=payload, headers=headers)
    r.raise_for_status()
    return r.json()

def fetch_me(access_token: str):
    r = requests.get("https://api.spotify.com/v1/me",
                     headers={"Authorization": f"Bearer {access_token}"})
    r.raise_for_status()
    return r.json()

def upsert_spotify_user(token_data: dict, me: dict):
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in   = token_data["expires_in"]
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
