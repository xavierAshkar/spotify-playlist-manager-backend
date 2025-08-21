# spotify/views/session.py
'''
This module handles session-related views for the Spotify app.
 - Provides an endpoint to check the current user's session.
 - Returns user details if authenticated, or a 401 error if not.
'''

from django.http import JsonResponse
from ..models import SpotifyUser

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
