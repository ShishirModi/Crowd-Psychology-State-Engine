import uuid
from django.test import TestCase


class TestCrowdTelemetryModel(TestCase):
    def test_table_name_and_unmanaged(self):
        from api.models import CrowdTelemetry
        assert CrowdTelemetry._meta.db_table == 'crowd_telemetry'
        assert CrowdTelemetry._meta.managed is False


class TestAnalysisTaskModel(TestCase):
    def test_create_and_retrieve(self):
        from api.models import AnalysisTask
        tid = str(uuid.uuid4())
        task = AnalysisTask.objects.create(
            task_id=tid,
            status='pending',
            location_name='Test Location',
        )
        fetched = AnalysisTask.objects.get(task_id=tid)
        assert fetched.status == 'pending'
        assert fetched.result_json is None

    def test_result_json_stores_dict(self):
        from api.models import AnalysisTask
        task = AnalysisTask.objects.create(
            task_id=str(uuid.uuid4()),
            status='done',
            location_name='Delhi',
            result_json={'state': 'Stable', 'risk_score': 12.0},
        )
        fetched = AnalysisTask.objects.get(task_id=task.task_id)
        assert fetched.result_json['state'] == 'Stable'
