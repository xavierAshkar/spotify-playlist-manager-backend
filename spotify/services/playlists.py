# spotify/services/playlists.py
'''
This module provides functions to for use by playlist grid and playlist detail views.
 - list_user_playlists: Get a single page of playlists for the current user.
 - summarize_user_playlists: Get a light summary of all playlists for the current user.
 - playlist_detail: Get detailed information about a specific playlist, including all tracks.
'''

from __future__ import annotations
from typing import Dict, Any, List, Optional
from ..utils import get_valid_access_token, refresh_access_token
from ..clients.spotify import sp_get, sp_get_with_backoff

TIMEOUT = 10
TRACK_TIMEOUT = 15

def _get(token: str, path_or_url: str, *, params=None, timeout=TIMEOUT, backoff=False):
    """
    One place to choose plain GET vs backoff GET.
    """
    r = (sp_get_with_backoff if backoff else sp_get)(
        token, path_or_url, params=params, timeout=timeout
    )
    return r

def list_user_playlists(
    user, *, limit: int = 50, offset: int = 0, fields: Optional[str] = None
) -> Dict[str, Any]:
    """
    Single page from /me/playlists. Returns raw Spotify JSON for that page.
    """
    token = get_valid_access_token(user)
    path = f"me/playlists?limit={limit}&offset={offset}"
    if fields:
        path += f"&fields={fields}"

    r = _get(token, path, timeout=TIMEOUT)
    if r.status_code == 401:
        token = refresh_access_token(user)
        r = _get(token, path, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def summarize_user_playlists(user) -> List[Dict[str, Any]]:
    """
    Light list for your center grid: [{id, name, image_url, tracks_total}]
    """
    token = get_valid_access_token(user)
    url = (
        "me/playlists"
        "?limit=50"
        "&fields=items(id,name,images(url),tracks(total),owner(display_name),public),next"
    )

    items: List[Dict[str, Any]] = []
    while url:
        r = _get(token, url, timeout=TIMEOUT, backoff=True)
        if r.status_code == 401:
            token = refresh_access_token(user)
            r = _get(token, url, timeout=TIMEOUT, backoff=True)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("items", []))
        url = data.get("next")  # full URL or None

    summaries = []
    for pl in items:
        img = (pl.get("images") or [{}])[0].get("url")
        summaries.append({
            "id": pl["id"],
            "name": pl["name"],
            "image_url": img,
            "tracks_total": pl.get("tracks", {}).get("total", 0),
        })
    return summaries

def playlist_detail(user, pid: str) -> Dict[str, Any]:
    """
    Basic playlist info + ALL track entries (id, name, artists, duration_ms, album.images).
    """
    token = get_valid_access_token(user)

    info = f"playlists/{pid}?fields=id,name,images(url),owner(display_name)"
    pr = _get(token, info, timeout=TIMEOUT)
    if pr.status_code == 401:
        token = refresh_access_token(user)
        pr = _get(token, info, timeout=TIMEOUT)
    pr.raise_for_status()
    pinfo = pr.json()

    items: List[Dict[str, Any]] = []
    turl = (
        f"playlists/{pid}/tracks"
        "?limit=100"
        "&fields=items(track(id,name,artists(name),duration_ms,album(images(url)))),next"
    )
    while turl:
        tr = _get(token, turl, timeout=TRACK_TIMEOUT, backoff=True)
        if tr.status_code == 401:
            token = refresh_access_token(user)
            tr = _get(token, turl, timeout=TRACK_TIMEOUT, backoff=True)
        tr.raise_for_status()
        tdata = tr.json()
        items.extend(tdata.get("items", []))
        turl = tdata.get("next")

    return {
        "id": pinfo["id"],
        "name": pinfo["name"],
        "images": pinfo.get("images", []),
        "owner": pinfo.get("owner"),
        "tracks": {"items": items},
    }