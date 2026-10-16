-- Update existing Supabase data after changing the college's room capacities.
-- Safe to run whether this project uses the normalized tables or the legacy
-- spaces_store JSON collection (or both).
do $$
begin
  if to_regclass('public.venues') is not null then
    update public.venues
    set capacity = 80
    where name in ('LR1', 'LR2', 'LR3', 'LR4', 'LR5', 'LR6',
                   'LAB1', 'LAB2', 'LAB3', 'LAB4', 'LAB5', 'BDA LAB');

    update public.venues set capacity = 200 where name = 'XICA AUDI';
  end if;

  if to_regclass('public.spaces_store') is not null then
    update public.spaces_store s
    set data = coalesce((
      select jsonb_agg(
        case
          when item.value->>'name' in ('LR1', 'LR2', 'LR3', 'LR4', 'LR5', 'LR6',
                                       'LAB1', 'LAB2', 'LAB3', 'LAB4', 'LAB5', 'BDA LAB')
            then jsonb_set(item.value, '{capacity}', to_jsonb(80), true)
          when item.value->>'name' = 'XICA AUDI'
            then jsonb_set(item.value, '{capacity}', to_jsonb(200), true)
          else item.value
        end
      )
      from jsonb_array_elements(s.data) as item(value)
    ), '[]'::jsonb)
    where s.name = 'venues' and jsonb_typeof(s.data) = 'array';
  end if;
end $$;
