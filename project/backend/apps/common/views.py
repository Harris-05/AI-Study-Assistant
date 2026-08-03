from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([])  # never throttle health checks -- monitors need to hit this freely
def health(request):
    return Response({"status": "ok", "debug": settings.DEBUG})
