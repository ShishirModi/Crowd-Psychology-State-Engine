from django.db import models


class CrowdTelemetry(models.Model):
    created_at    = models.DateTimeField(auto_now_add=True)
    location_name = models.TextField()
    latitude      = models.FloatField(default=0)
    longitude     = models.FloatField(default=0)
    congestion    = models.FloatField(default=0)
    speed         = models.FloatField(null=True, blank=True)
    gradient      = models.FloatField(null=True, blank=True)
    velocity_var  = models.FloatField(null=True, blank=True)
    anomaly_score = models.FloatField(null=True, blank=True)
    risk_score    = models.FloatField(null=True, blank=True)
    state         = models.TextField(default='Unknown')
    session_id    = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'crowd_telemetry'
        managed  = False           # table already exists in Supabase
        ordering = ['-created_at']


class AnalysisTask(models.Model):
    task_id       = models.CharField(max_length=255, unique=True, db_index=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    status        = models.CharField(max_length=20, default='pending')
    location_name = models.TextField()
    result_json   = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'analysis_task'
        ordering = ['-created_at']
