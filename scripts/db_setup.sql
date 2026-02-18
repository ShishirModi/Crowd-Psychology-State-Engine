-- Copy and paste this into the Supabase SQL Editor to set up your project.

-- 1. Create the Telemetry Table
CREATE TABLE IF NOT EXISTS crowd_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Context
    location_name TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    
    -- Metrics
    congestion FLOAT NOT NULL,
    speed FLOAT NOT NULL,
    gradient FLOAT NOT NULL,
    velocity_var FLOAT NOT NULL,
    anomaly_score FLOAT NOT NULL,
    
    -- Analysis
    state TEXT NOT NULL,
    
    -- Metadata
    session_id TEXT
);

-- 2. Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_telemetry_time ON crowd_telemetry(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_loc ON crowd_telemetry(location_name);

-- 3. Row Level Security (RLS)
ALTER TABLE crowd_telemetry ENABLE ROW LEVEL SECURITY;

-- Allow INSERTs from authenticated keys (Service Role) AND anon keys 
-- (Change 'anon' to 'service_role' if you want to restrict client-side writes)
CREATE POLICY "Enable insert for authenticated and anon" 
ON crowd_telemetry FOR INSERT 
TO anon, authenticated 
WITH CHECK (true);

-- Allow SELECTs for everyone (Dashboard access)
CREATE POLICY "Enable read usage for all" 
ON crowd_telemetry FOR SELECT 
TO anon, authenticated
USING (true);
