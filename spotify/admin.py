# spotify/admin.py
from django.contrib import admin
from .models import SpotifyUser

@admin.register(SpotifyUser)
class SpotifyUserAdmin(admin.ModelAdmin):
    list_display = ("spotify_id", "display_name", "email", "expires_at", "created_at", "updated_at")
    search_fields = ("spotify_id", "display_name", "email")