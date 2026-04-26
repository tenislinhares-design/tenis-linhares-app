create extension if not exists pgcrypto;

create table if not exists public.alunos (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  whatsapp text not null unique,
  status_pagamento text not null default 'pendente' check (status_pagamento in ('em_dia', 'pendente', 'inadimplente')),
  ativo boolean not null default true,
  observacao text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.eventos (
  id uuid primary key default gen_random_uuid(),
  titulo text not null,
  data_evento date not null,
  local text,
  descricao text,
  valor_inscricao numeric(10,2) not null default 0,
  ativo boolean not null default true,
  ordem integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.confirmacoes (
  id uuid primary key default gen_random_uuid(),
  aluno_id uuid references public.alunos(id) on delete set null,
  nome text not null,
  whatsapp text not null,
  data_aula date not null,
  dia_semana text,
  local text,
  horario text not null,
  status_pagamento text,
  created_at timestamptz not null default now()
);

create table if not exists public.inscricoes_eventos (
  id uuid primary key default gen_random_uuid(),
  evento_id uuid references public.eventos(id) on delete cascade,
  evento_titulo text not null,
  nome text not null,
  whatsapp text not null,
  categoria text not null,
  valor numeric(10,2),
  status_inscricao text not null default 'aguardando_pagamento' check (status_inscricao in ('aguardando_pagamento', 'pago', 'cancelada')),
  created_at timestamptz not null default now()
);

create unique index if not exists uq_confirmacao_unica on public.confirmacoes (whatsapp, data_aula, horario);
create unique index if not exists uq_inscricao_evento_unica on public.inscricoes_eventos (evento_id, whatsapp);
create index if not exists idx_alunos_nome on public.alunos (nome);
create index if not exists idx_alunos_whatsapp on public.alunos (whatsapp);
create index if not exists idx_eventos_data on public.eventos (data_evento);
create index if not exists idx_confirmacoes_data on public.confirmacoes (data_aula);
create index if not exists idx_inscricoes_evento on public.inscricoes_eventos (evento_id);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_alunos_updated_at on public.alunos;
create trigger trg_alunos_updated_at
before update on public.alunos
for each row execute function public.set_updated_at();

drop trigger if exists trg_eventos_updated_at on public.eventos;
create trigger trg_eventos_updated_at
before update on public.eventos
for each row execute function public.set_updated_at();

alter table public.eventos add column if not exists valor_inscricao numeric(10,2) not null default 0;

insert into public.eventos (titulo, data_evento, local, descricao, valor_inscricao, ativo, ordem)
select '1º Open Nico de Tênis', current_date + 15, 'Tênis Linhares', 'Em breve divulgaremos mais detalhes e inscrições.', 0, true, 1
where not exists (
  select 1 from public.eventos where titulo = '1º Open Nico de Tênis'
);
