-- Run this once in the Supabase SQL Editor.
create table if not exists public.spaces_store (
  name text primary key check (name in ('venues', 'timetable', 'bookings')),
  data jsonb not null
);

alter table public.spaces_store enable row level security;
-- No public policies: only the Flask server uses the service-role key.
