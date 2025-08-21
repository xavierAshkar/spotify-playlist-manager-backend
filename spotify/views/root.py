# spotify/views/root.py
'''
This module provides the root and health check views for the Spotify app.
- The root view serves a simple HTML page prompting users to connect their Spotify account.
- The health view returns a JSON response indicating the service is operational.
'''

from django.http import HttpResponse, JsonResponse

def root(_request):
    return HttpResponse("""
      <html>
        <head><title>Spotify Manager</title></head>
        <body style="font-family: sans-serif; padding: 24px;">
          <h1>Spotify Playlist Manager</h1>
          <p>Connect your Spotify to continue.</p>
          <a href="/auth/login"
             style="display:inline-block;padding:10px 14px;background:#1DB954;color:#fff;text-decoration:none;border-radius:6px;">
             Connect Spotify
          </a>
        </body>
      </html>
    """)

def health(_request):
    return JsonResponse({"ok": True})
