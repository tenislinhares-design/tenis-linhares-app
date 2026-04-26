create extension if not exists pgcrypto;

create table if not exists public.alunos (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  whatsapp text not null unique,
  status_pagamento text not null default 'pendente' check (status_pagamento in ('em_dia','pendente','inadimplente')),
  ativo boolean not null default true,
  observacao text,
  created_at timestamptz not null default now()
);

create table if not exists public.eventos (
  id uuid primary key default gen_random_uuid(),
  titulo text not null,
  data_evento date not null,
  local text,
  descricao text,
  ativo boolean not null default true,
  ordem integer not null default 1,
  created_at timestamptz not null default now()
);

create table if not exists public.confirmacoes (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  whatsapp text not null,
  data_aula date not null,
  horario text not null,
  local text not null,
  status_pagamento text,
  created_at timestamptz not null default now()
);

create index if not exists idx_alunos_whatsapp on public.alunos (whatsapp);
create index if not exists idx_eventos_data on public.eventos (data_evento);
create index if not exists idx_confirmacoes_data on public.confirmacoes (data_aula);
create unique index if not exists idx_confirmacoes_unique_slot on public.confirmacoes (whatsapp, data_aula, horario);

insert into public.eventos (titulo, data_evento, local, descricao, ativo, ordem)
select '1º Open Nico de Tênis', current_date + interval '10 day', 'Tênis Linhares', 'Em breve divulgaremos mais detalhes e inscrições.', true, 1
where not exists (
  select 1 from public.eventos where titulo = '1º Open Nico de Tênis'
);
