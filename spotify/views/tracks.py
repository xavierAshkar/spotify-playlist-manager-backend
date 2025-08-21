# spotify/views/tracks.py
'''
This module handles views related to tracks for the Spotify app.
- Provides an endpoint to retrieve liked tracks for the authenticated user.
'''

from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET
from ..models import SpotifyUser
from ..services.tracks import liked_tracks as svc_liked_tracks

def _require_user(request):
    sid = request.session.get("spotify_id")
    if not sid:
        return None
    return SpotifyUser.objects.get(spotify_id=sid)

@require_GET
def liked_tracks(request):
    user = _require_user(request)
    if not user:
        return HttpResponseForbidden("Not authenticated")

    limit  = int(request.GET.get("limit", 50))
    offset = int(request.GET.get("offset", 0))
    data = svc_liked_tracks(user, limit=limit, offset=offset)
    return JsonResponse(data)
