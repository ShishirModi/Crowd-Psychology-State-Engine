import os
from supabase import create_client, Client
from utils.config_loader import get_config
import streamlit as st
from datetime import datetime

class SupabaseManager:
    """
    Singleton-like wrapper for Supabase client.
    Handles connection and data insertion.
    """
    def __init__(self):
        # Prefer st.secrets for Cloud, fallback to os.getenv for local
        self.url = None
        self.key = None
        
        # Try loading from Streamlit secrets (might fail if no secrets.toml found)
        try:
            if "SUPABASE_URL" in st.secrets:
                self.url = st.secrets["SUPABASE_URL"]
            if "SUPABASE_KEY" in st.secrets:
                self.key = st.secrets["SUPABASE_KEY"]
        except Exception:
            # Secrets Not Found or other error, ignore and fall back to env
            pass
            
        if not self.url:
            self.url = os.getenv("SUPABASE_URL")
        if not self.key:
            self.key = os.getenv("SUPABASE_KEY")
        self.client: Client = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                print("DEBUG: Supabase client initialized.")
            except Exception as e:
                print(f"ERROR: Failed to init Supabase: {e}")
        else:
            print("WARNING: Supabase credentials missing.")

    def insert_telemetry(self, data: dict):
        """
        Inserts a telemetry record into 'crowd_telemetry'.
        Data dict must match schema.
        """
        if not self.client:
            return None
            
        try:
            # Map Python dict keys to DB columns if necessary, 
            # assuming data dict keys match DB columns for now.
            # Explicit mapping for safety:
            payload = {
                "location_name": data.get("location_name", "Unknown"),
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "congestion": data.get("congestion"),
                "speed": data.get("speed"),
                "gradient": data.get("gradient"),
                "velocity_var": data.get("velocity_var"),
                "anomaly_score": data.get("anomaly_score"),
                "state": data.get("state"),
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.client.table("crowd_telemetry").insert(payload).execute()
            return response
        except Exception as e:
            print(f"ERROR: Supabase Insert Failed: {e}")
            return None

    def fetch_history(self, location_name, limit=50):
        """
        Fetches recent history for a location.
        """
        if not self.client:
            return []
            
        try:
            response = self.client.table("crowd_telemetry")\
                .select("*")\
                .eq("location_name", location_name)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            data = response.data
            return data[::-1] if data else []
        except Exception as e:
            print(f"ERROR: Supabase Fetch Failed: {e}")
            return []

    def fetch_recent_logs(self, limit=100):
        """
        Fetches global recent logs (Admin usage).
        """
        if not self.client:
            return []
        try:
            response = self.client.table("crowd_telemetry")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            print(f"ERROR: Supabase Admin Fetch Failed: {e}")
            return []

# Factory
def get_db_client():
    return SupabaseManager()
