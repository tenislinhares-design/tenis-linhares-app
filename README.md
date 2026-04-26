# Tênis Linhares - versão online para publicar hoje

Esta versão foi preparada para:
- ficar com layout verde e branco
- esconder textos internos do aluno
- publicar no Streamlit Community Cloud
- salvar tudo online no Supabase
- bloquear check-in de aluno inadimplente

## Estrutura do projeto
- `app.py` - aplicativo principal
- `schema.sql` - tabelas do Supabase
- `requirements.txt` - dependências
- `secrets.example.toml` - modelo dos segredos
- `assets/logo.jpeg` - logo

## Tabelas usadas
- `alunos`
- `eventos`
- `planos`
- `confirmacoes`

## Campos mínimos
### alunos
- nome
- whatsapp
- status_pagamento (`em_dia`, `pendente`, `inadimplente`)
- ativo

### eventos
- titulo
- data_evento
- local
- descricao
- ativo
- ordem

### planos
- nome_plano
- valor_mensal
- aulas_por_semana
- descricao
- ativo
- ordem

### confirmacoes
- nome
- whatsapp
- data_aula
- horario
- local
- status_pagamento

## Publicação rápida
1. Crie o projeto no Supabase.
2. Rode o `schema.sql` no SQL Editor.
3. Crie um repositório no GitHub e envie estes arquivos.
4. No Streamlit Community Cloud, publique apontando para `app.py`.
5. Nos Secrets do Streamlit, cole os valores do `secrets.example.toml`.

## Regras do app
- aluno só confirma se estiver `em_dia`
- `pendente` e `inadimplente` ficam bloqueados
- eventos e planos aparecem apenas se estiverem `ativo = true`
- painel admin fica escondido atrás de senha

## Observação importante
Nunca coloque a chave secreta do Supabase no repositório. Use apenas nos Secrets do Streamlit.
