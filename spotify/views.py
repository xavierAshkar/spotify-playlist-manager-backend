# spotify/views.py
import os
import urllib.parse
import requests
import time
import base64
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.utils import timezone
from .models import SpotifyUser
from .utils import encrypt_token, decrypt_token

# Load env vars
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Your chosen scopes
SCOPES = [
    "user-read-private",
    "user-read-email",
    "playlist-read-private",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-library-read",
    "user-library-modify"
]

def login_redirect(_request):
    """
    Step 1: Redirect user to Spotify's authorization page.
    """
    scope_str = " ".join(SCOPES)
    
    query_params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": scope_str
    }
    
    auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(query_params)}"
    return HttpResponseRedirect(auth_url)



def auth_callback(request):
    code = request.GET.get("code")
    error = request.GET.get("error")

    if error:
        return HttpResponseBadRequest(f"Spotify auth error: {error}")
    if not code:
        return HttpResponseBadRequest("No code returned from Spotify")

    # Prepare token request
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

    # Request tokens
    r = requests.post(token_url, data=payload, headers=headers)
    if r.status_code != 200:
        return HttpResponseBadRequest(f"Failed to get token: {r.text}")

    token_data = r.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data["expires_in"]

    expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)

    # Get user profile from Spotify
    me_resp = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if me_resp.status_code != 200:
        return HttpResponseBadRequest("Failed to fetch user profile")

    me = me_resp.json()
    spotify_id = me["id"]
    display_name = me.get("display_name")
    email = me.get("email")

    # Save or update the user in DB
    user, _ = SpotifyUser.objects.update_or_create(
        spotify_id=spotify_id,
        defaults={
            "display_name": display_name,
            "email": email,
            "refresh_token": encrypt_token(refresh_token),
            "expires_at": expires_at,
        }
    )

    # Send tokens + profile to frontend
    return JsonResponse({
        "access_token": access_token,
        "expires_at": int(time.time()) + expires_in,
        "spotify_id": spotify_id,
        "display_name": display_name,
        "email": email,
    })