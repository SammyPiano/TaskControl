from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def spa(request):
    """Entrega el index.html del build de React para cualquier ruta /app/…"""
    index = settings.FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
    if settings.DEBUG:
        return redirect(settings.FRONTEND_DEV_URL)
    return HttpResponse("Frontend no compilado. Ejecute «pnpm build» en frontend/.", status=503)
