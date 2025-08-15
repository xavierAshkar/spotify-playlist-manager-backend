import os
import urllib.parse
from django.http import HttpResponseRedirect

# Load env vars
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
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
