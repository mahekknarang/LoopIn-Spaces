-- Run once on an existing normalized Supabase setup before deploying the app
-- version that reads the venues.bookable flag.
alter table public.venues
  add column if not exists bookable boolean not null default true;

-- Keep XICA Library unavailable until an administrator confirms permission.
update public.venues set bookable = false where name = 'XICA LIBRARY';

-- Keep the existing JSON backup consistent, if it is still present.
update public.spaces_store s
set data = coalesce((
  select jsonb_agg(
    case when item.value->>'name' = 'XICA LIBRARY'
      then jsonb_set(item.value, '{bookable}', 'false'::jsonb, true)
      else jsonb_set(item.value, '{bookable}', coalesce(item.value->'bookable', 'true'::jsonb), true)
    end
  )
  from jsonb_array_elements(s.data) as item(value)
), '[]'::jsonb)
where s.name = 'venues' and jsonb_typeof(s.data) = 'array';

-- Keep venue permission changes writable through the app's atomic storage RPC.
create or replace function public.loopin_save_venues(p_data jsonb)
returns void language plpgsql security invoker set search_path = public as $$
begin
  insert into public.venues(name, type, capacity, bookable)
  select x.name, x.type, x.capacity, coalesce(x.bookable, x.name <> 'XICA LIBRARY')
  from jsonb_to_recordset(p_data) as x(name text, type text, capacity integer, bookable boolean)
  on conflict (name) do update
    set type = excluded.type, capacity = excluded.capacity, bookable = excluded.bookable;
  delete from public.venues v
  where not exists (select 1 from jsonb_array_elements(p_data) x where x->>'name' = v.name);
end $$;

revoke all on function public.loopin_save_venues(jsonb) from public, anon, authenticated;
grant execute on function public.loopin_save_venues(jsonb) to service_role;
