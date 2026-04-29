-- =========================
-- RESET EVENTS POLICIES CLEANLY
-- =========================

drop policy if exists "allow_select_events" on public.events;
drop policy if exists "public_read_events" on public.events;
drop policy if exists "service_full_access" on public.events;

-- Ensure RLS is ON
alter table public.events enable row level security;

-- PUBLIC READ (anon + authenticated)
create policy "events_public_read"
on public.events
for select
to anon, authenticated
using (true);

-- SERVICE ROLE FULL ACCESS
create policy "events_service_full_access"
on public.events
for all
to service_role
using (true)
with check (true);
