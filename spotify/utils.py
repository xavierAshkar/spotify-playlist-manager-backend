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

def refresh_access_token(user: SpotifyUser) -> str:
    """
    Refreshes the access token for the given user.
    Returns the new access token.
    """
    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    refresh_token = decrypt_token(user.refresh_token)

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(token_url, data=payload, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Failed to refresh token: {r.text}")

    token_data = r.json()
    new_access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)
    new_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)

    # Update DB
    user.expires_at = new_expires_at
    user.save(update_fields=["expires_at"])

    return new_access_token