import os
import urllib.parse
import requests
import time
import base64
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect

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
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")  # seconds (usually 3600)

    # Calculate expiration time (epoch seconds)
    expires_at = int(time.time()) + expires_in

    # TODO: Store refresh_token securely in DB (encrypted) with user record
    # For now, just log it
    print("Refresh token (save securely!):", refresh_token)

    # Send access token & expiry to frontend
    return JsonResponse({
        "access_token": access_token,
        "expires_at": expires_at
    })