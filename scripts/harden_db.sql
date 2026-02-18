-- SECURITY HARDENING SCRIPT
-- Run this in Supabase SQL Editor to restrict write access.

-- 1. Drop the loose "allow all" policy
DROP POLICY IF EXISTS "Enable insert for authenticated and anon" ON crowd_telemetry;

-- 2. Create a stricter policy: Only Service Role can INSERT
-- This means the 'anon' key (public) can NO LONGER write data.
-- You must usage the SERVICE_ROLE_KEY in your app's .env for this to work.
CREATE POLICY "Enable insert for Service Role only" 
ON crowd_telemetry FOR INSERT 
TO service_role 
WITH CHECK (true);

-- 3. (Optional) Restrict SELECTs if you want to make data private
-- DROP POLICY IF EXISTS "Enable read usage for all" ON crowd_telemetry;
-- CREATE POLICY "Enable read for authenticated users only"
-- ON crowd_telemetry FOR SELECT
-- TO authenticated
-- USING (true);
