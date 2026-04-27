import json
import uuid
import redis as redis_lib
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import CrowdTelemetry
from .serializers import CrowdTelemetrySerializer
from tasks.analysis import analyze_crowd
from cache.result_store import get_result


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


@method_decorator(csrf_exempt, name='dispatch')
class AnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({'error': 'Invalid JSON'}, status=400)

        lat = body.get('lat')
        lon = body.get('lon')
        if lat is None or lon is None:
            return Response({'error': 'lat and lon are required'}, status=400)

        location_name = body.get('location_name', 'Unknown')
        env_params = {
            'env_weather_risk': float(body.get('env_weather_risk', 0.0)),
            'env_width_factor': float(body.get('env_width_factor', 1.0)),
            'env_event_active': bool(body.get('env_event_active', False)),
        }

        task_id = str(uuid.uuid4())
        async_result = analyze_crowd.delay(
            lat=float(lat),
            lon=float(lon),
            location_name=location_name,
            env_params=env_params,
            task_id=task_id,
        )
        return Response({'task_id': async_result.id}, status=202)


class ResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: str):
        result = get_result(task_id)
        if result is None:
            return Response({'status': 'pending', 'task_id': task_id})
        return Response(result)
