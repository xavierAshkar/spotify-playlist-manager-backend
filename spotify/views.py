# spotify/views.py
from django.http import JsonResponse

def ping(_request):
    return JsonResponse({"ok": True})
