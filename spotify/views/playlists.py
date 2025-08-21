# spotify/views/playlists.py
'''
This module handles playlist-related views for the Spotify app.
- Provides endpoints to get user playlists, a summary of playlists, and details of a specific playlist.
'''

from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET
from ..models import SpotifyUser
from ..services import playlists as svc

def _require_user(request):
    sid = request.session.get("spotify_id")
    if not sid:
        return None
    return SpotifyUser.objects.get(spotify_id=sid)

@require_GET
def get_playlists(request):
    user = _require_user(request)
    if not user:
        return HttpResponseForbidden("Not authenticated")

    limit  = int(request.GET.get("limit", 50))
    offset = int(request.GET.get("offset", 0))
    fields = request.GET.get("fields")
    data = svc.list_user_playlists(user, limit=limit, offset=offset, fields=fields)
    return JsonResponse(data, safe=False)

@require_GET
def get_playlists_summary(request):
    user = _require_user(request)
    if not user:
        return HttpResponseForbidden("Not authenticated")

    data = svc.summarize_user_playlists(user)
    return JsonResponse({"items": data}, safe=False)

@require_GET
def get_playlist_detail(request, pid):
    user = _require_user(request)
    if not user:
        return HttpResponseForbidden("Not authenticated")

    data = svc.playlist_detail(user, pid)
    return JsonResponse(data, safe=False)
