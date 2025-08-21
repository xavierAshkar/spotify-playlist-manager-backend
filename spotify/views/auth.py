# spotify/views/auth.py
'''
This module handles the authentication flow for Spotify integration.
 - Redirects users to Spotify for login.
 - Handles the callback from Spotify after user login.
 - Exchanges the authorization code for access and refresh tokens.
 - Fetches the user's Spotify profile and upserts it into the database.
 - Provides CSRF-safe OAuth state generation and validation.
'''

import os, urllib.parse
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from ..services import auth as svc

SCOPES = [
    "user-read-private","user-read-email",
    "playlist-read-private","playlist-modify-public","playlist-modify-private",
    "user-library-read","user-library-modify",
]

def login_redirect(request):
    state = svc.generate_oauth_state()
    svc.save_oauth_state(request.session, state)
    params = {
        "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": os.getenv("SPOTIFY_REDIRECT_URI"),
        "scope": " ".join(SCOPES),
        "state": state,
    }
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    return HttpResponseRedirect(url)

def auth_callback(request):
    if "error" in request.GET:
        return HttpResponseBadRequest(f"Spotify auth error: {request.GET['error']}")
    if not svc.validate_oauth_state(request.session, request.GET.get("state")):
        return HttpResponseBadRequest("Invalid OAuth state")
    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("No authorization code")

    token_data = svc.exchange_code_for_tokens(code)
    me         = svc.fetch_me(token_data["access_token"])
    user       = svc.upsert_spotify_user(token_data, me)

    request.session["spotify_id"] = user.spotify_id
    request.session.set_expiry(60 * 60 * 24 * 7)

    frontend = os.getenv("FRONTEND_APP_URL") or "http://localhost:5173"
    return HttpResponseRedirect(frontend)
