from rest_framework import serializers
from .models import CrowdTelemetry, AnalysisTask


class CrowdTelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CrowdTelemetry
        fields = '__all__'


class AnalysisTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisTask
        fields = ['task_id', 'created_at', 'status', 'location_name', 'result_json']
