-- LoopIn: Spaces normalized database setup and one-time migration.
-- Run once in the Supabase SQL Editor. Existing spaces_store rows are copied;
-- the old table remains in place as a rollback/backup source.

create table if not exists public.spaces_store (
  name text primary key check (name in ('venues', 'timetable', 'bookings')),
  data jsonb not null
);
alter table public.spaces_store enable row level security;

create table if not exists public.venues (
  name text primary key,
  type text not null,
  capacity integer not null check (capacity > 0)
);

create table if not exists public.timetable (
  venue_name text not null references public.venues(name) on update cascade on delete cascade,
  day text not null check (day in ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')),
  slot text not null,
  lecture text not null,
  primary key (venue_name, day, slot)
);

create table if not exists public.bookings (
  id text primary key,
  name text not null,
  contact text not null,
  event_name text not null,
  purpose text not null,
  venue_name text not null references public.venues(name) on update cascade on delete restrict,
  booking_date date not null,
  status text not null check (status in ('Pending', 'Approved', 'Rejected')),
  reason text not null default '',
  created_at text not null,
  approved_at text
);

create table if not exists public.booking_slots (
  booking_id text not null references public.bookings(id) on delete cascade,
  slot text not null,
  primary key (booking_id, slot)
);

create index if not exists bookings_date_venue_idx on public.bookings (booking_date, venue_name);
create index if not exists bookings_status_created_idx on public.bookings (status, created_at);

alter table public.venues enable row level security;
alter table public.timetable enable row level security;
alter table public.bookings enable row level security;
alter table public.booking_slots enable row level security;

-- Migrate the old JSONB collections without deleting or altering spaces_store.
do $$
declare
  stored jsonb;
begin
  -- Only import the backup into a completely uninitialized normalized store.
  -- This makes it safe to rerun the setup script after the first migration.
  if not exists (select 1 from public.venues) then
  select data into stored from public.spaces_store where name = 'venues';
  if jsonb_typeof(stored) = 'array' then
    insert into public.venues (name, type, capacity)
    select x.name, x.type, x.capacity
    from jsonb_to_recordset(stored) as x(name text, type text, capacity integer)
    on conflict (name) do update set type = excluded.type, capacity = excluded.capacity;
  end if;

  select data into stored from public.spaces_store where name = 'timetable';
  if jsonb_typeof(stored) = 'array' then
    insert into public.timetable (venue_name, day, slot, lecture)
    select x.venue, x.day, x.slot, x.lecture
    from jsonb_to_recordset(stored) as x(venue text, day text, slot text, lecture text)
    where exists (select 1 from public.venues v where v.name = x.venue)
    on conflict (venue_name, day, slot) do update set lecture = excluded.lecture;
  end if;

  select data into stored from public.spaces_store where name = 'bookings';
  if jsonb_typeof(stored) = 'array' then
    insert into public.bookings (id, name, contact, event_name, purpose, venue_name, booking_date, status, reason, created_at, approved_at)
    select x.id, x.name, x.contact, x.event, x.purpose, x.venue, x.date::date, x.status,
           coalesce(x.reason, ''), coalesce(x.created_at, now()::text), x.approved_at
    from jsonb_to_recordset(stored) as x(
      id text, name text, contact text, event text, purpose text, venue text, date text,
      status text, reason text, created_at text, approved_at text
    )
    where exists (select 1 from public.venues v where v.name = x.venue)
    on conflict (id) do update set
      name = excluded.name, contact = excluded.contact, event_name = excluded.event_name,
      purpose = excluded.purpose, venue_name = excluded.venue_name,
      booking_date = excluded.booking_date, status = excluded.status,
      reason = excluded.reason, created_at = excluded.created_at, approved_at = excluded.approved_at;

    delete from public.booking_slots bs
    using jsonb_to_recordset(stored) as x(id text)
    where bs.booking_id = x.id;
    insert into public.booking_slots (booking_id, slot)
    select x.id, slot.value
    from jsonb_to_recordset(stored) as x(id text, slots jsonb)
    cross join lateral jsonb_array_elements_text(coalesce(x.slots, '[]'::jsonb)) as slot(value)
    on conflict do nothing;
  end if;
  end if;
end $$;

-- Atomic collection writes keep the app's existing list-based interface while
-- storing each field/relationship in its own database column/row.
create or replace function public.loopin_save_venues(p_data jsonb)
returns void language plpgsql security invoker set search_path = public as $$
begin
  insert into public.venues(name, type, capacity)
  select x.name, x.type, x.capacity
  from jsonb_to_recordset(p_data) as x(name text, type text, capacity integer)
  on conflict (name) do update set type = excluded.type, capacity = excluded.capacity;
  delete from public.venues v
  where not exists (select 1 from jsonb_array_elements(p_data) x where x->>'name' = v.name);
end $$;

create or replace function public.loopin_save_timetable(p_data jsonb)
returns void language plpgsql security invoker set search_path = public as $$
begin
  insert into public.timetable(venue_name, day, slot, lecture)
  select x.venue, x.day, x.slot, x.lecture
  from jsonb_to_recordset(p_data) as x(venue text, day text, slot text, lecture text)
  on conflict (venue_name, day, slot) do update set lecture = excluded.lecture;
  delete from public.timetable t
  where not exists (
    select 1 from jsonb_to_recordset(p_data) as x(venue text, day text, slot text)
    where x.venue = t.venue_name and x.day = t.day and x.slot = t.slot
  );
end $$;

create or replace function public.loopin_save_bookings(p_data jsonb)
returns void language plpgsql security invoker set search_path = public as $$
begin
  insert into public.bookings(id, name, contact, event_name, purpose, venue_name, booking_date, status, reason, created_at, approved_at)
  select x.id, x.name, x.contact, x.event, x.purpose, x.venue, x.date::date,
         x.status, coalesce(x.reason, ''), x.created_at, x.approved_at
  from jsonb_to_recordset(p_data) as x(
    id text, name text, contact text, event text, purpose text, venue text, date text,
    status text, reason text, created_at text, approved_at text
  )
  on conflict (id) do update set
    name = excluded.name, contact = excluded.contact, event_name = excluded.event_name,
    purpose = excluded.purpose, venue_name = excluded.venue_name,
    booking_date = excluded.booking_date, status = excluded.status,
    reason = excluded.reason, created_at = excluded.created_at, approved_at = excluded.approved_at;

  delete from public.booking_slots bs
  where exists (select 1 from jsonb_to_recordset(p_data) as x(id text) where x.id = bs.booking_id);
  insert into public.booking_slots(booking_id, slot)
  select x.id, slot.value
  from jsonb_to_recordset(p_data) as x(id text, slots jsonb)
  cross join lateral jsonb_array_elements_text(coalesce(x.slots, '[]'::jsonb)) as slot(value)
  on conflict do nothing;

  delete from public.bookings b
  where not exists (select 1 from jsonb_array_elements(p_data) x where x->>'id' = b.id);
end $$;

revoke all on function public.loopin_save_venues(jsonb) from public, anon, authenticated;
revoke all on function public.loopin_save_timetable(jsonb) from public, anon, authenticated;
revoke all on function public.loopin_save_bookings(jsonb) from public, anon, authenticated;
grant execute on function public.loopin_save_venues(jsonb) to service_role;
grant execute on function public.loopin_save_timetable(jsonb) to service_role;
grant execute on function public.loopin_save_bookings(jsonb) to service_role;
