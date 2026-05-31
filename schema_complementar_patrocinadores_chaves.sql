-- Tênis Linhares - complemento seguro
-- Patrocinadores + jogos de torneio para chaves/agenda/resultados.
-- Não apaga dados existentes. Pode rodar no Supabase sem perder nada.

create table if not exists public.patrocinadores (
    id uuid primary key default gen_random_uuid(),
    nome text not null,
    logo_url text,
    link_url text,
    ativo boolean not null default true,
    ordem integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists patrocinadores_ativo_ordem_idx
    on public.patrocinadores (ativo, ordem);

create table if not exists public.jogos_torneio (
    id uuid primary key default gen_random_uuid(),
    evento_id uuid,
    evento_titulo text,
    categoria text,
    fase text,
    jogador1 text,
    jogador2 text,
    data_jogo date,
    horario text,
    quadra text,
    placar text,
    status text not null default 'agendado',
    ordem integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists jogos_torneio_evento_categoria_idx
    on public.jogos_torneio (evento_id, categoria);

create index if not exists jogos_torneio_data_horario_idx
    on public.jogos_torneio (data_jogo, horario);

-- Se seu Supabase estiver com RLS ativado nessas tabelas, libere o service role/anon conforme seu padrão atual.
-- O app usa a chave configurada no Render; não há alteração de dados antigos.
