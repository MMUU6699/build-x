-- Build X schema for Supabase (PostgreSQL).
-- Apply this in the Supabase SQL editor (or run the migration script) before
-- first startup. For local development, SQLAlchemy create_all covers this.

-- ============================================================
-- Profiles (identity lives in Supabase Auth; no password hashes)
-- ============================================================
create table if not exists profiles (
    user_id       text primary key,
    fullname      text not null,
    email         text not null unique,
    role          text not null default 'user',
    is_active     boolean not null default true,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    last_login_at timestamptz
);

-- ============================================================
-- Agents
-- ============================================================
create table if not exists agents (
    agent_id   text primary key,
    model_name text not null default '',
    temperature double precision not null default 0.7,
    max_tokens integer not null default 2000,
    memories   jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ============================================================
-- Sessions
-- ============================================================
create table if not exists sessions (
    session_id           text primary key,
    user_id              text not null,
    sandbox_id           text,
    agent_id             text not null default '',
    task_id              text,
    title                text,
    unread_message_count integer not null default 0,
    latest_message       text,
    latest_message_at    timestamptz,
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now(),
    events               jsonb not null default '[]'::jsonb,
    files                jsonb not null default '[]'::jsonb,
    status               text not null default 'pending',
    is_shared            boolean not null default false,
    is_favorite          boolean not null default false,
    is_pinned            boolean not null default false,
    project_id           text,
    task_mode            text not null default 'agent'
);

create index if not exists ix_sessions_user_latest
    on sessions (user_id, latest_message_at desc);
create index if not exists ix_sessions_user_favorite
    on sessions (user_id, is_favorite);
create index if not exists ix_sessions_user_pinned_latest
    on sessions (user_id, is_pinned desc, latest_message_at desc);
create index if not exists ix_sessions_user_id on sessions (user_id);
create index if not exists ix_sessions_project_id on sessions (project_id);

-- ============================================================
-- Projects
-- ============================================================
create table if not exists projects (
    project_id  text primary key,
    user_id     text not null,
    name        text not null,
    instruction text,
    is_pinned   boolean not null default false,
    sort_order  integer not null default 0,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index if not exists ix_projects_user_id on projects (user_id);
create index if not exists ix_projects_user_pinned_sort
    on projects (user_id, is_pinned desc, sort_order asc, updated_at desc);

-- ============================================================
-- File favorites
-- ============================================================
create table if not exists file_favorites (
    id         bigint generated always as identity primary key,
    user_id    text not null,
    file_id    text not null,
    created_at timestamptz not null default now(),
    unique (user_id, file_id)
);
create index if not exists ix_file_favorites_user_id on file_favorites (user_id);
create index if not exists ix_file_favorites_file_id on file_favorites (file_id);

-- ============================================================
-- Claws
-- ============================================================
create table if not exists claws (
    claw_id        text primary key,
    user_id        text not null unique,
    container_name text,
    container_ip   text,
    api_key        text not null default '',
    status         text not null default 'creating',
    error_message  text,
    expires_at     timestamptz,
    messages       jsonb not null default '[]'::jsonb,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);

-- ============================================================
-- Auth sessions (opaque ids; replaces Redis session keys)
-- ============================================================
create table if not exists auth_sessions (
    session_id   text primary key,
    user_id      text not null,
    client       text not null default 'unknown',
    created_at   timestamptz not null,
    expires_at   timestamptz not null,
    last_seen_at timestamptz not null,
    ip           text,
    user_agent   text,
    rotated_from text
);
create index if not exists ix_auth_sessions_user_id on auth_sessions (user_id);

-- ============================================================
-- Cache (replaces Redis keys; JSONB value + optional TTL)
-- ============================================================
create table if not exists cache_entries (
    cache_key  text primary key,
    value      jsonb not null,
    expires_at timestamptz
);
create index if not exists ix_cache_entries_expires_at on cache_entries (expires_at);

-- ============================================================
-- Task streams (replaces Redis Streams; id is the monotonic cursor)
-- ============================================================
create table if not exists task_streams (
    id         bigint generated always as identity primary key,
    stream_name text not null,
    data       jsonb not null,
    created_at timestamptz not null default now(),
    claimed_at timestamptz,
    claimed_by text
);
create index if not exists ix_task_streams_stream_id on task_streams (stream_name, id);

-- ============================================================
-- Task metadata + cancellation flags (replaces Redis meta/cancel keys)
-- ============================================================
create table if not exists task_meta (
    task_id    text primary key,
    status     text not null default 'pending',
    params     jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists task_cancel (
    task_id    text primary key,
    created_at timestamptz not null default now()
);

-- ============================================================
-- Files (object content lives in Supabase Storage; path in storage_path)
-- ============================================================
create table if not exists files (
    file_id      text primary key,
    storage_path text not null unique,
    filename     text not null default '',
    content_type text,
    size         bigint not null default 0,
    upload_date  timestamptz not null default now(),
    metadata     jsonb not null default '{}'::jsonb,
    user_id      text not null
);
create index if not exists ix_files_user_id on files (user_id);
