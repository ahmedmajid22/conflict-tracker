-- REMOVE ALL OLD POLICIES
drop policy if exists events_public_read on public.events;
drop policy if exists events_public_read_events on public.events;
drop policy if exists events_service_full_access on public.events;

-- ENABLE RLS (important)
alter table public.events enable row level security;

-- PUBLIC READ ACCESS
create policy events_public_read
on public.events
for select
to anon, authenticated
using (true);

-- SERVICE FULL ACCESS
create policy events_service_full_access
on public.events
for all
to service_role
using (true)
with check (true);
