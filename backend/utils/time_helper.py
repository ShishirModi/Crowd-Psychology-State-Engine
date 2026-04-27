from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()

def get_local_time(lat, lon):
    try:
        tz_str = _tf.timezone_at(lng=lon, lat=lat)
        if tz_str:
            target_tz = pytz.timezone(tz_str)
            return datetime.now(target_tz).strftime('%H:%M:%S')
    except Exception as e:
        print(f"Timezone Error: {e}")
    
    return datetime.now().strftime('%H:%M:%S') # Fallback to local
