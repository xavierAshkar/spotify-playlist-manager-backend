# spotify/models.py
from django.db import models

class SpotifyUser(models.Model):
    """
    Stores Spotify user profile & refresh token.
    """
    spotify_id = models.CharField(max_length=255, unique=True)  # Spotify's unique user ID
    display_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    refresh_token = models.TextField()  # TODO: encrypt in production
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.display_name or self.spotify_id}"
