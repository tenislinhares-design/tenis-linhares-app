-- Tênis Linhares - evolução do cadastro interno dos alunos
-- Agenda com dias e horários diferentes no mesmo aluno.
-- Rode no Supabase > SQL Editor > New query > Run
-- Não apaga nenhum dado existente. Só adiciona campos opcionais.

alter table public.alunos
    add column if not exists tipo_plano text default 'mensalidade';

alter table public.alunos
    add column if not exists dias_aula text;

alter table public.alunos
    add column if not exists aula_horario text;

alter table public.alunos
    add column if not exists aula_local text;

alter table public.alunos
    add column if not exists agenda_aulas text;

create index if not exists alunos_tipo_plano_idx
    on public.alunos (tipo_plano);

create index if not exists alunos_aula_horario_idx
    on public.alunos (aula_horario);
