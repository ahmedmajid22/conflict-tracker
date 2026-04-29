-- HARD RESET ALL POLICIES ON events

drop policy if exists events_public_read on public.events;
drop policy if exists events_service_full_access on public.events;
drop policy if exists allow_select_events on public.events;
drop policy if exists public_read_events on public.events;

-- ensure RLS is enabled
alter table public.events enable row level security;

-- allow public read (anon + authenticated)
create policy events_public_read
on public.events
for select
to anon, authenticated
using (true);

-- allow full access for backend only
create policy events_service_full_access
on public.events
for all
to service_role
using (true)
with check (true);

