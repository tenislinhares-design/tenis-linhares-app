-- Complementary schema for sponsors and tournament brackets

-- Create sponsors table if it does not exist. This stores the sponsors that should appear
-- on the public site. If you don't add any sponsors the section will not be shown.
create table if not exists patrocinadores (
    id uuid primary key default uuid_generate_v4(),
    nome text,
    logo_url text,
    link text,
    ordem integer default 0,
    ativo boolean default true,
    created_at timestamptz default now()
);

-- Create tournament matches table if it does not exist. Matches belong to an event
-- (referencing the existing eventos table), and may be used to build a bracket,
-- agenda and results listing. Fase (stage) defines the round (e.g. Oitavas,
-- Quartas, Semifinal, Final), jogador1 and jogador2 are the player names,
-- data_hora contains the scheduled start time, quadra the court, resultado the
-- final result and status the progress (por exemplo "agendado", "concluido").
create table if not exists jogos_torneio (
    id uuid primary key default uuid_generate_v4(),
    torneio_id uuid references eventos(id) on delete cascade,
    fase text,
    jogador1 text,
    jogador2 text,
    data_hora timestamptz,
    quadra text,
    resultado text,
    status text,
    ordem integer default 0,
    created_at timestamptz default now()
);