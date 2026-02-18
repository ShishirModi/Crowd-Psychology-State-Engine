import os
import sys

# Add parent directory to path to import from data_layer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from data_layer.database import get_db_client

def check_setup():
    print("--- CPSE Database Connection Check ---")
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ FAILED: SUPABASE_URL or SUPABASE_KEY missing from .env")
        return
        
    print(f"✅ Credentials found for: {url}")
    
    db = get_db_client()
    if not db.client:
        print("❌ FAILED: Could not initialize Supabase client.")
        return

    print("Attempting to fetch recent logs...")
    try:
        # Try to select 1 row
        logs = db.fetch_recent_logs(limit=1)
        print("✅ SUCCESS: Connection established and table exists.")
        print(f"   Fetched {len(logs)} records.")
    except Exception as e:
        print("❌ FAILED: API Error.")
        print(f"   Error: {e}")
        print("\nPossible Causes:")
        print("   1. Table 'crowd_telemetry' does not exist. (Run scripts/db_setup.sql in Supabase)")
        print("   2. Row Level Security (RLS) policies block access.")
        print("   3. Invalid API Key.")

if __name__ == "__main__":
    check_setup()
