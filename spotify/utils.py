# spotify/utils.py
from cryptography.fernet import Fernet
import os
import base64
import requests
from django.utils import timezone
from .models import SpotifyUser

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

fernet = Fernet(os.getenv("FERNET_KEY").encode())

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

def set_access_token(user: SpotifyUser, token: str, expires_in: int):
    user.access_token = encrypt_token(token)
    skew = 60
    user.expires_at = timezone.now() + timezone.timedelta(seconds=max(0, expires_in - skew))
    user.save(update_fields=["access_token", "expires_at"])

def get_stored_access_token(user: SpotifyUser) -> str | None:
    if user.access_token and user.expires_at and user.expires_at > timezone.now():
        return decrypt_token(user.access_token)
    return None

def refresh_access_token(user: SpotifyUser) -> str:
    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()

    payload = {"grant_type": "refresh_token", "refresh_token": decrypt_token(user.refresh_token)}
    headers = {"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"}

    r = requests.post(token_url, data=payload, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Failed to refresh token: {r.text}")

    token_data = r.json()
    new_access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)

    # Spotify may rotate the refresh token; persist if present
    if "refresh_token" in token_data and token_data["refresh_token"]:
        user.refresh_token = encrypt_token(token_data["refresh_token"])

    set_access_token(user, new_access_token, expires_in)
    return new_access_token

def get_valid_access_token(user: SpotifyUser) -> str:
    token = get_stored_access_token(user)
    if token:
        return token
    return refresh_access_token(user)
