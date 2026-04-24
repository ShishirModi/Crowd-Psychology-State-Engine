import sys
from unittest.mock import Mock
import builtins
import time

sys.path.append('.')

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("HTTP Error")

mock_requests = Mock()
mock_requests.get.return_value = MockResponse({
    "flowSegmentData": {
        "frc": "FRC3",
        "currentSpeed": 41,
        "freeFlowSpeed": 50,
    }
}, 200)

sys.modules['requests'] = mock_requests

from signals.tomtom import TomTomSignal
signal = TomTomSignal()
signal.api_key = "test_key"
signal.location = {'lat': 28.6139, 'lon': 77.2090}
result = signal.fetch_telemetry()

print("Result:", result)
print("Request URL:", mock_requests.get.call_args[0][0])
print("Request Params:", mock_requests.get.call_args[1]['params'])

