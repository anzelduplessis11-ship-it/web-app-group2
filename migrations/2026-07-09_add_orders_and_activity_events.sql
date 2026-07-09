-- Migration: orders + activity_events (applied to Supabase on 2026-07-09
-- as "add_orders_and_activity_events"). Kept here for the record; if you are
-- setting up a fresh Supabase project, paste this into the SQL editor.

-- Purchase records: one row per buyer "Request to buy" on a listing.
-- crop/category/region are copied from the listing at order time so the
-- recommendation engine can mine buying patterns with simple queries, and so
-- purchase history stays intact even if the listing later changes.
create table if not exists orders (
    id bigint generated always as identity primary key,
    listing_id bigint not null references listings(id),
    buyer_id bigint not null references users(id),
    farmer_id bigint not null references users(id),
    crop text not null,
    category text not null,
    region text not null,
    quantity_kg double precision not null check (quantity_kg > 0),
    price_per_kg double precision not null,
    status text not null default 'pending'
        check (status in ('pending', 'confirmed', 'declined', 'cancelled')),
    created_at timestamptz not null default now(),
    decided_at timestamptz
);

create index if not exists idx_orders_buyer_time on orders (buyer_id, created_at desc);
create index if not exists idx_orders_farmer_status on orders (farmer_id, status);
create index if not exists idx_orders_listing on orders (listing_id);

-- Lightweight usage tracking: which listings a user views and what they
-- search for on the market page. Feeds the "For you" recommendations
-- alongside actual purchases.
create table if not exists activity_events (
    id bigint generated always as identity primary key,
    user_id bigint not null references users(id),
    event_type text not null check (event_type in ('view_listing', 'search')),
    listing_id bigint references listings(id),
    crop text,
    category text,
    region text,
    created_at timestamptz not null default now()
);

create index if not exists idx_activity_user_time on activity_events (user_id, created_at desc);

-- Same security posture as the existing tables: RLS on. The Flask app
-- connects as the table owner (privileged role), which is unaffected;
-- the public REST API stays blocked.
alter table orders enable row level security;
alter table activity_events enable row level security;
