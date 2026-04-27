from celery import shared_task


@shared_task(bind=True, max_retries=3)
def analyze_crowd(self, lat: float, lon: float, location_name: str,
                  env_params: dict, task_id: str):
    """Full pipeline implemented in Task 9."""
    return {'status': 'stub', 'task_id': task_id}
