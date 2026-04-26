# Tênis Linhares - versão final limpa

Esta versão foi preparada para publicar no Streamlit Community Cloud com Supabase.

## O que inclui

- Logo da Tênis Linhares no topo.
- Visual verde fluorescente e branco.
- Check-in de aulas.
- Bloqueio de aluno pendente ou inadimplente.
- Eventos sem dados de exemplo automáticos.
- Inscrição simples em eventos/torneios com pagamento manual por PIX.
- Financeiro em cards com os valores corretos.
- Botões para copiar chaves PIX.
- Painel administrativo para alunos, eventos, inscrições e confirmações.

## Arquivos

- `app.py` - aplicativo principal.
- `schema.sql` - estrutura do banco Supabase.
- `requirements.txt` - dependências.
- `assets/logo.jpeg` - logo.
- `secrets.example.toml` - modelo de secrets, não colocar chaves reais no GitHub.

## Secrets no Streamlit

Cole no Streamlit Cloud > App > Settings > Secrets:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_SECRET_KEY = "SUA_SB_SECRET"
ADMIN_PASSWORD = "Linhares@2026Admin"
PIX_EMAIL = "tenislinhares@gmail.com"
PIX_PHONE = "+55 27 99997-0109"
SECRETARIA_NOME = "Andrea Nascimento"
SECRETARIA_WHATSAPP = "+55 27 99997-0109"
```


## Versão v6
- Header e financeiro renderizados com componentes nativos do Streamlit para evitar HTML/código aparecendo na tela.
- Logo mantida em assets/logo.jpeg.
- Eventos começam vazios e são cadastrados pelo Admin.
