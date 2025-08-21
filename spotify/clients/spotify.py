# spotify/clients/spotify.py
''' 
Client layer for Spotify API interactions.
 - Provides functions to perform GET and POST requests with the necessary authentication headers.
 - Centralizes requests to the Spotify API, making it easier to manage and modify.
'''

import time
import requests

BASE = "https://api.spotify.com/v1"

def _to_url(path_or_url: str) -> str:
    return path_or_url if path_or_url.startswith("http") else f"{BASE}/{path_or_url.lstrip('/')}"

def sp_get(access_token: str, path_or_url: str, *, params=None, timeout=10):
    return requests.get(
        _to_url(path_or_url),
        headers={"Authorization": f"Bearer {access_token}"},
        params=params or {},
        timeout=timeout,
    )

# Optional helper with basic 429 handling
def sp_get_with_backoff(access_token: str, path_or_url: str, *, params=None, timeout=10, retries=1):
    r = sp_get(access_token, path_or_url, params=params, timeout=timeout)
    if r.status_code == 429 and retries > 0:
        wait = int(r.headers.get("Retry-After", "1"))
        time.sleep(max(0, wait))
        return sp_get_with_backoff(access_token, path_or_url, params=params, timeout=timeout, retries=retries - 1)
    return r

def sp_post_form(url: str, *, data: dict, headers: dict, timeout=10):
    return requests.post(url, data=data, headers=headers, timeout=timeout)