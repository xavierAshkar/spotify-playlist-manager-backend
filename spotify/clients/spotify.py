# spotify/clients/spotify.py
''' 
Client layer for Spotify API interactions.
 - Provides functions to perform GET and POST requests with the necessary authentication headers.
 - Centralizes requests to the Spotify API, making it easier to manage and modify.
'''

import requests

BASE = "https://api.spotify.com/v1"

def sp_get(access_token: str, path: str, *, params=None, timeout=10):
    r = requests.get(
        f"{BASE}/{path.lstrip('/')}",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params or {},
        timeout=timeout,
    )
    return r

def sp_post_form(url: str, *, data: dict, headers: dict, timeout=10):
    # For token exchange/refresh (accounts.spotify.com endpoints)
    r = requests.post(url, data=data, headers=headers, timeout=timeout)
    return r
