# spotify/views.py
import os
import urllib.parse
import requests
import time
import base64
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import timedelta
from .models import SpotifyUser
from .utils import encrypt_token, decrypt_token, refresh_access_token, get_valid_access_token

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
    refresh_token = token_data.get("refresh_token")
    expires_in   = token_data["expires_in"]

    # compute expiry now so creation won't violate NOT NULL
    expires_at = timezone.now() + timedelta(seconds=expires_in)

    # fetch profile (unchanged)
    me_resp = requests.get("https://api.spotify.com/v1/me",
                           headers={"Authorization": f"Bearer {access_token}"})
    if me_resp.status_code != 200:
        return HttpResponseBadRequest("Failed to fetch user profile")
    me = me_resp.json()
    spotify_id = me["id"]

    # build defaults; only set refresh_token if present (Spotify may omit on re-auth)
    defaults = {
        "display_name": me.get("display_name") or me.get("id"),
        "email": me.get("email"),
        "expires_at": expires_at,
        # Optional: write the access token now to avoid a second update.
        "access_token": encrypt_token(access_token),
    }
    if refresh_token:
        defaults["refresh_token"] = encrypt_token(refresh_token)

    user, _ = SpotifyUser.objects.update_or_create(
        spotify_id=spotify_id,
        defaults=defaults,
    )

    # If you prefer to centralize token writes, keep this — it’ll just update again.
    # from .utils import set_access_token
    # set_access_token(user, access_token, expires_in)

    request.session['spotify_id'] = user.spotify_id
    request.session.set_expiry(60 * 60 * 24 * 7)

    frontend = os.getenv("FRONTEND_APP_URL") or "http://localhost:5173"
    return HttpResponseRedirect(frontend)


@require_GET
def session_me(request):
    sid = request.session.get("spotify_id")
    if not sid:
        return JsonResponse({"authenticated": False}, status=401)
    u = SpotifyUser.objects.get(spotify_id=sid)
    return JsonResponse({
        "authenticated": True,
        "spotify_id": u.spotify_id,
        "display_name": u.display_name,
        "email": u.email,
    })

@require_GET
def get_playlists(request):
    sid = request.session.get("spotify_id")
    if not sid:
        return HttpResponseForbidden("Not authenticated")

    user = SpotifyUser.objects.get(spotify_id=sid)
    access_token = get_valid_access_token(user)

    def fetch(token):
        return requests.get(
            "https://api.spotify.com/v1/me/playlists",
            headers={"Authorization": f"Bearer {token}"}
        )

    r = fetch(access_token)
    if r.status_code == 401:
        access_token = refresh_access_token(user)
        r = fetch(access_token)

    return JsonResponse(r.json(), safe=False, status=r.status_code)

@require_GET
def get_playlists_summary(request):
    sid = request.session.get("spotify_id")
    if not sid:
        return HttpResponseForbidden("Not authenticated")

    user = SpotifyUser.objects.get(spotify_id=sid)
    token = get_valid_access_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    # fetch all playlists (50 per page) with only fields we need
    playlists = []
    url = "https://api.spotify.com/v1/me/playlists?limit=50&fields=items(id,name,images(url),tracks(total),owner(display_name),public),next"
    while url:
        r = requests.get(url, headers=headers)
        if r.status_code == 401:
            token = refresh_access_token(user)
            headers["Authorization"] = f"Bearer {token}"
            r = requests.get(url, headers=headers)
        if r.status_code != 200:
            return JsonResponse({"error": r.text}, status=r.status_code, safe=False)
        data = r.json()
        playlists.extend(data.get("items", []))
        url = data.get("next")

    # sum durations for each playlist
    summaries = []
    for pl in playlists:
        pid = pl["id"]
        image_url = (pl.get("images") or [{}])[0].get("url")
        tracks_total = pl.get("tracks", {}).get("total", 0)

        total_ms = 0
        turl = f"https://api.spotify.com/v1/playlists/{pid}/tracks?limit=100&fields=items(track(duration_ms)),next"
        while turl:
            tr = requests.get(turl, headers=headers)
            if tr.status_code == 401:
                token = refresh_access_token(user)
                headers["Authorization"] = f"Bearer {token}"
                tr = requests.get(turl, headers=headers)
            if tr.status_code != 200:
                total_ms = None  # fall back if something goes wrong
                break
            tdata = tr.json()
            for item in tdata.get("items", []):
                track = item.get("track") or {}
                dur = track.get("duration_ms")
                if isinstance(dur, int):
                    total_ms += dur
            turl = tdata.get("next")

        summaries.append({
            "id": pid,
            "name": pl["name"],
            "image_url": image_url,
            "tracks_total": tracks_total,
            "total_duration_ms": total_ms,
        })

    return JsonResponse({"items": summaries}, safe=False)

def root(_request):
    return HttpResponse("""
      <html>
        <head><title>Spotify Manager</title></head>
        <body style="font-family: sans-serif; padding: 24px;">
          <h1>Spotify Playlist Manager</h1>
          <p>Connect your Spotify to continue.</p>
          <a href="/auth/login"
             style="display:inline-block;padding:10px 14px;background:#1DB954;color:#fff;text-decoration:none;border-radius:6px;">
             Connect Spotify
          </a>
        </body>
      </html>
    """)