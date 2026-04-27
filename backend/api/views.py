import json
import redis as redis_lib
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import CrowdTelemetry
from .serializers import CrowdTelemetrySerializer


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 100))
        location = request.query_params.get('location')
        anomaly_only = request.query_params.get('anomaly_only', 'false').lower() == 'true'

        try:
            qs = CrowdTelemetry.objects.all()
            if location and location != 'All':
                qs = qs.filter(location_name=location)
            if anomaly_only:
                qs = qs.filter(anomaly_score__gt=2.5)
            qs = qs[:limit]
            return Response(CrowdTelemetrySerializer(qs, many=True).data)
        except Exception:
            return Response([])


class LatestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        location = request.query_params.get('location', '')
        if not location:
            return Response(None)
        try:
            raw = _redis().get(f'cpse:last:{location}')
            data = json.loads(raw) if raw else None
            return Response(data)
        except Exception:
            return Response(None)
