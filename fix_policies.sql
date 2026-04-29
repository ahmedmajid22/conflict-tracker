-- =========================
-- CLEAN RESET POLICIES
-- =========================

drop policy if exists "allow_public_read_events" on public.events;
drop policy if exists "Service full access events" on public.events;
drop policy if exists "Public read events" on public.events;
drop policy if exists "public_read_events" on public.events;

-- Ensure RLS is ON
alter table public.events enable row level security;

-- Allow public read (anon + authenticated)
create policy "public_read_events"
on public.events
for select
to anon, authenticated
using (true);

-- Allow backend full access (service role only)
create policy "service_full_access"
on public.events
for all
to service_role
using (true)
with check (true);
