# spotify/services/tracks.py
'''
This module provides functionality to fetch and normalize tracks for use by the queue panel.
 - liked_tracks: Fetches a page of liked tracks for the current user, normalizing the data for use in a queue panel.
'''

from __future__ import annotations
from typing import Dict, Any
from ..utils import get_valid_access_token, refresh_access_token
from ..clients.spotify import sp_get, sp_get_with_backoff

TIMEOUT = 10

def liked_tracks(user, *, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Normalized Liked Songs for the queue panel.
    Returns: { items: [TrackLite], total, nextOffset, pageSize }
    """
    token = get_valid_access_token(user)

    def fetch(tok: str):
        return sp_get(tok, "me/tracks", params={"limit": limit, "offset": offset}, timeout=TIMEOUT)

    r = fetch(token)
    if r.status_code == 401:
        token = refresh_access_token(user)
        r = fetch(token)
    r.raise_for_status()
    data = r.json()

    def lite(item: Dict[str, Any]) -> Dict[str, Any]:
        t = item["track"]
        imgs = (t.get("album", {}).get("images") or [])
        return {
            "id": t["id"],
            "name": t["name"],
            "artists": [a["name"] for a in t.get("artists", [])],
            "album": t.get("album", {}).get("name"),
            "image": imgs[0]["url"] if imgs else None,
            "duration_ms": t.get("duration_ms"),
            "preview_url": t.get("preview_url"),
            "uri": t.get("uri"),
            "added_at": item.get("added_at"),
        }

    items = [lite(it) for it in data.get("items", [])]
    total = int(data.get("total", 0))
    next_offset = offset + limit if offset + limit < total else None

    return {
        "items": items,
        "total": total,
        "nextOffset": next_offset,
        "pageSize": limit,
    }