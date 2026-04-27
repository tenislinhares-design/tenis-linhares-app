create extension if not exists pgcrypto;

create table if not exists public.alunos (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  whatsapp text not null unique,
  status_pagamento text not null default 'pendente',
  ativo boolean not null default true,
  observacao text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.alunos add column if not exists nome text;
alter table public.alunos add column if not exists whatsapp text;
alter table public.alunos add column if not exists status_pagamento text not null default 'pendente';
alter table public.alunos add column if not exists ativo boolean not null default true;
alter table public.alunos add column if not exists observacao text;
alter table public.alunos add column if not exists created_at timestamptz not null default now();
alter table public.alunos add column if not exists updated_at timestamptz not null default now();

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'alunos_status_pagamento_check') then
    alter table public.alunos add constraint alunos_status_pagamento_check
    check (status_pagamento in ('em_dia', 'pendente', 'inadimplente'));
  end if;
exception when others then null;
end $$;

create table if not exists public.eventos (
  id uuid primary key default gen_random_uuid(),
  titulo text not null,
  data_evento date not null,
  local text,
  descricao text,
  valor_inscricao numeric(10,2) not null default 0,
  ativo boolean not null default true,
  inscricoes_abertas boolean not null default true,
  ordem integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.eventos add column if not exists titulo text;
alter table public.eventos add column if not exists data_evento date;
alter table public.eventos add column if not exists local text;
alter table public.eventos add column if not exists descricao text;
alter table public.eventos add column if not exists valor_inscricao numeric(10,2) not null default 0;
alter table public.eventos add column if not exists ativo boolean not null default true;
alter table public.eventos add column if not exists inscricoes_abertas boolean not null default true;
alter table public.eventos add column if not exists ordem integer not null default 1;
alter table public.eventos add column if not exists created_at timestamptz not null default now();
alter table public.eventos add column if not exists updated_at timestamptz not null default now();

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

alter table public.confirmacoes add column if not exists aluno_id uuid;
alter table public.confirmacoes add column if not exists nome text;
alter table public.confirmacoes add column if not exists whatsapp text;
alter table public.confirmacoes add column if not exists data_aula date;
alter table public.confirmacoes add column if not exists dia_semana text;
alter table public.confirmacoes add column if not exists local text;
alter table public.confirmacoes add column if not exists horario text;
alter table public.confirmacoes add column if not exists status_pagamento text;
alter table public.confirmacoes add column if not exists created_at timestamptz not null default now();

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'confirmacoes_aluno_id_fkey'
  ) then
    alter table public.confirmacoes
      add constraint confirmacoes_aluno_id_fkey
      foreign key (aluno_id) references public.alunos(id) on delete set null;
  end if;
exception when others then null;
end $$;

create table if not exists public.inscricoes_eventos (
  id uuid primary key default gen_random_uuid(),
  evento_id uuid references public.eventos(id) on delete cascade,
  evento_titulo text not null,
  nome text not null,
  whatsapp text not null,
  categoria text not null,
  valor numeric(10,2),
  status_inscricao text not null default 'aguardando_pagamento',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.inscricoes_eventos add column if not exists evento_id uuid;
alter table public.inscricoes_eventos add column if not exists evento_titulo text;
alter table public.inscricoes_eventos add column if not exists nome text;
alter table public.inscricoes_eventos add column if not exists whatsapp text;
alter table public.inscricoes_eventos add column if not exists categoria text;
alter table public.inscricoes_eventos add column if not exists valor numeric(10,2);
alter table public.inscricoes_eventos add column if not exists status_inscricao text not null default 'aguardando_pagamento';
alter table public.inscricoes_eventos add column if not exists created_at timestamptz not null default now();
alter table public.inscricoes_eventos add column if not exists updated_at timestamptz not null default now();

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'inscricoes_eventos_evento_id_fkey'
  ) then
    alter table public.inscricoes_eventos
      add constraint inscricoes_eventos_evento_id_fkey
      foreign key (evento_id) references public.eventos(id) on delete cascade;
  end if;
exception when others then null;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'inscricoes_eventos_status_inscricao_check'
  ) then
    alter table public.inscricoes_eventos add constraint inscricoes_eventos_status_inscricao_check
    check (status_inscricao in ('aguardando_pagamento', 'pago', 'cancelada'));
  end if;
exception when others then null;
end $$;

create unique index if not exists uq_confirmacao_unica on public.confirmacoes (whatsapp, data_aula, horario);
create unique index if not exists uq_inscricao_evento_unica on public.inscricoes_eventos (evento_id, whatsapp);
create index if not exists idx_alunos_nome on public.alunos (nome);
create index if not exists idx_alunos_whatsapp on public.alunos (whatsapp);
create index if not exists idx_eventos_data on public.eventos (data_evento);
create index if not exists idx_confirmacoes_data on public.confirmacoes (data_aula);
create index if not exists idx_confirmacoes_horario on public.confirmacoes (horario);
create index if not exists idx_inscricoes_evento on public.inscricoes_eventos (evento_id);
create index if not exists idx_inscricoes_categoria on public.inscricoes_eventos (categoria);

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

drop trigger if exists trg_inscricoes_updated_at on public.inscricoes_eventos;
create trigger trg_inscricoes_updated_at
before update on public.inscricoes_eventos
for each row execute function public.set_updated_at();

delete from public.eventos e
where e.titulo = '1º Open Nico de Tênis'
  and not exists (select 1 from public.inscricoes_eventos i where i.evento_id = e.id);
