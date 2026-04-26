# Tênis Linhares

Aplicativo online para check-in de aulas, eventos e financeiro.

## Arquivos principais
- `app.py` -> aplicação Streamlit
- `schema.sql` -> estrutura do banco no Supabase
- `requirements.txt` -> dependências
- `secrets.example.toml` -> modelo dos segredos
- `assets/logo.jpeg` -> logo

## Banco de dados
Rode o conteúdo de `schema.sql` no SQL Editor do Supabase.

## Segredos no Streamlit
Cole os segredos no painel do Streamlit Cloud em `App > Settings > Secrets`.

## Regras do app
- aluno `em_dia` -> pode confirmar aula
- aluno `pendente` -> bloqueado
- aluno `inadimplente` -> bloqueado
- confirmação duplicada no mesmo dia e horário -> bloqueada
- painel admin protegido por senha
