# CPSE Database Guide (Supabase)

This project uses [Supabase](https://supabase.com/) (PostgreSQL) for persisting crowd telemetry and anomaly events.

## 1. Setup

### Prerequisites
-   A Supabase project.
-   `SUPABASE_URL` and `SUPABASE_KEY` (Service Role or Anon, depending on RLS policies).

### Environment Variables
Add these to your `.env` file (local) or Streamlit Secrets (cloud):

```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-anon-or-service-key"
```

## 2. Schema

Run the following SQL in your Supabase **SQL Editor** to create the necessary table and policies.

```sql
-- Create the main telemetry table
CREATE TABLE IF NOT EXISTS crowd_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Location Context
    location_name TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    
    -- Metrics
    congestion FLOAT NOT NULL,
    speed FLOAT NOT NULL,
    gradient FLOAT NOT NULL,
    velocity_var FLOAT NOT NULL,
    anomaly_score FLOAT NOT NULL,
    
    -- Classification
    state TEXT NOT NULL,
    
    -- Metadata
    session_id TEXT -- Optional: to track which session generated data
);

-- Index for fast time-range queries
CREATE INDEX idx_telemetry_time ON crowd_telemetry(created_at DESC);
CREATE INDEX idx_telemetry_loc ON crowd_telemetry(location_name);

-- Row Level Security (RLS)
-- Enable RLS
ALTER TABLE crowd_telemetry ENABLE ROW LEVEL SECURITY;

-- Policy: Allow Anon/Public to INSERT data (if using Anon key)
-- or restricted to authenticated service role.
-- For simple dashboards:
CREATE POLICY "Enable insert for authenticated users only" 
ON crowd_telemetry FOR INSERT 
TO authenticated, anon -- 'anon' allows the client key to write if you want that
WITH CHECK (true);

-- Policy: Allow Anon/Public to SELECT data
CREATE POLICY "Enable read access for all users" 
ON crowd_telemetry FOR SELECT 
TO authenticated, anon
USING (true);
```

## 3. Security Hardening (Recommended)

To prevent public write access (spam protection), run the hardening script:

1.  Open Supabase SQL Editor.
2.  Run the contents of `scripts/harden_db.sql`.
3.  This disables `anon` inserts and restricts writes to the `service_role` key only.

## 4. Python Integration

The `data_layer/database.py` module handles the connection.

```python
from data_layer.database import get_db_client

db = get_db_client()
db.insert_telemetry({...})

# Admin Fetch
last_100_logs = db.fetch_recent_logs(limit=100)
```

## 4. Admin Dashboard

The application now includes an **Admin Console**.
-   **Access**: Log in with the **first password** in your `APP_PASSWORD` list (in `secrets.toml`).
-   **Features**: View global telemetry logs, refresh data, and download as CSV.
