# spotify/urls.py
from django.urls import path
from .views import auth, session, playlists, root, tracks

urlpatterns = [
    # Root + health
    path("", root.root),
    path("health", root.health),

    # Auth
    path("auth/login", auth.login_redirect),
    path("auth/callback", auth.auth_callback),

    # Session
    path("api/session", session.session_me),

    # Playlists
    path("api/playlists", playlists.get_playlists),
    path("api/playlists/summary", playlists.get_playlists_summary),
    path("api/playlists/<str:pid>", playlists.get_playlist_detail),

    # Liked tracks (for the queue panel data source)
    path("api/spotify/liked-tracks", tracks.liked_tracks),
]
