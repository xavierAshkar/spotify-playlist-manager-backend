# spotify/models.py
from django.db import models
from django.utils import timezone

class SpotifyUser(models.Model):
    spotify_id = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    refresh_token = models.TextField()   # TODO: encrypt this
    expires_at = models.DateTimeField()  # when access token expires

    created_at = models.DateTimeField(auto_now_add=True)  # set once
    updated_at = models.DateTimeField(auto_now=True)      # auto-update

    def __str__(self):
        return f"{self.display_name or self.spotify_id}"

