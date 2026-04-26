from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

st.set_page_config(
    page_title="Tênis Linhares",
    page_icon="🎾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_NAME = "Tênis Linhares"
PIX_EMAIL_DEFAULT = "tenislinhares@gmail.com"
PIX_PHONE_DEFAULT = "+55 27 99997-0109"
SECRETARIA_DEFAULT = "Andrea Nascimento"
ADMIN_PASSWORD_DEFAULT = "tenislinhares123"

LOGO_CANDIDATES = [
    Path("assets/logo.png"),
    Path("assets/logo.jpg"),
    Path("assets/logo.jpeg"),
]

FINANCE_CARDS = [
    {
        "title": "Aulas Semanais <span>(Grupo)</span>",
        "items": [
            "1x por semana: R$ 313,20",
            "2x por semana: R$ 452,40",
            "3x por semana (Plano Ideal): R$ 545,20",
            "4x por semana: R$ 893,20",
        ],
        "footer": "Turmas organizadas por nível técnico.",
    },
    {
        "title": "Plano Individual",
        "items": [
            "1x por semana: R$ 580,00",
            "2x por semana: R$ 1.160,00",
            "3x por semana: R$ 1.740,00",
        ],
        "footer": "Treinamento personalizado com foco na sua evolução.",
    },
    {
        "title": "Aula Avulsa",
        "items": [
            "1 hora: R$ 120,00",
            "2 horas: R$ 210,00",
            "3 horas: R$ 320,00",
        ],
        "footer": "Ideal para treinos pontuais ou para experimentar a modalidade.",
    },
    {
        "title": "Plano Família",
        "items": [
            "2 pessoas: 5% de desconto",
            "3 pessoas: 10% de desconto",
            "4 pessoas ou mais: 15% de desconto",
        ],
        "footer": "Esporte, disciplina e evolução para toda a família.",
    },
]


# ----------------------------- UI / STYLES -----------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: linear-gradient(180deg, #FFFFFF 0%, #F6FFF8 100%);
                color: #132117;
            }
            .main .block-container {
                padding-top: 1.2rem;
                padding-bottom: 3rem;
                max-width: 900px;
            }
            .tl-header {
                background: #FFFFFF;
                border: 1px solid #DDEDDD;
                box-shadow: 0 8px 24px rgba(13, 91, 43, 0.08);
                border-radius: 26px;
                padding: 24px 20px 20px;
                margin-bottom: 14px;
                text-align: center;
            }
            .tl-title {
                color: #0C7A34;
                font-size: 2.1rem;
                font-weight: 800;
                line-height: 1.1;
                margin-top: 10px;
                margin-bottom: 6px;
            }
            .tl-subtitle {
                color: #2D4D35;
                font-size: 1rem;
                margin-bottom: 0;
            }
            .tl-card {
                background: white;
                border: 1px solid #E2EEE4;
                border-radius: 24px;
                box-shadow: 0 8px 22px rgba(13, 91, 43, 0.05);
                padding: 20px 20px 14px;
                margin-bottom: 12px;
            }
            .tl-soft {
                background: #F4FFF6;
                border: 1px solid #D6EFD9;
                border-radius: 18px;
                padding: 14px 14px 12px;
                margin-bottom: 12px;
            }
            .tl-section-title {
                color: #0C7A34;
                font-weight: 800;
                font-size: 1.15rem;
                margin-bottom: .35rem;
            }
            .tl-small {
                color: #48614D;
                font-size: 0.96rem;
            }
            .tl-highlight {
                background: #EAF9EE;
                color: #0C7A34;
                border: 1px solid #BEE2C5;
                border-radius: 999px;
                padding: 5px 12px;
                font-weight: 700;
                display: inline-block;
                margin: 2px 4px 8px;
                font-size: .82rem;
            }
            .tl-fin-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0,1fr));
                gap: 16px;
                margin-top: 8px;
                margin-bottom: 16px;
            }
            .tl-fin-card {
                background: #0C0C0C;
                color: white;
                border-radius: 24px;
                padding: 14px;
                border: 6px solid #0C0C0C;
                box-shadow: 0 8px 18px rgba(0,0,0,.08);
                min-height: 315px;
                display: flex;
                flex-direction: column;
            }
            .tl-fin-title {
                background: #CDE312;
                color: black;
                border-radius: 18px;
                text-align: center;
                font-size: 1.2rem;
                font-weight: 800;
                padding: 18px 14px;
                line-height: 1.08;
                margin-bottom: 18px;
            }
            .tl-fin-title span {
                display: block;
                font-size: 0.92rem;
            }
            .tl-fin-list {
                flex: 1;
                margin: 0;
                padding-left: 18px;
                font-size: 1.02rem;
                line-height: 1.7;
                font-weight: 700;
            }
            .tl-fin-footer {
                margin-top: 18px;
                background: #CDE312;
                color: black;
                border-radius: 16px;
                padding: 12px 14px;
                text-align: center;
                font-size: 0.95rem;
                font-weight: 700;
            }
            .tl-fin-note {
                color: #48614D;
                font-size: 0.95rem;
                margin-top: 8px;
            }
            .stButton > button, .stDownloadButton > button {
                background: linear-gradient(180deg, #13AA46 0%, #0C7A34 100%);
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: 700;
                min-height: 46px;
            }
            .stButton > button:hover, .stDownloadButton > button:hover {
                background: linear-gradient(180deg, #10933D 0%, #096329 100%);
                color: white;
            }
            [data-testid="stSidebar"] {
                background: #F7FFF9;
                border-right: 1px solid #E2EFE4;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
            }
            .stTabs [data-baseweb="tab"] {
                background: white;
                border: 1px solid #DAEEDA;
                border-radius: 12px;
                padding: 8px 14px;
            }
            .stTabs [aria-selected="true"] {
                background: #EAF9EE !important;
                color: #0C7A34 !important;
                border-color: #BFE6C8 !important;
            }
            .stTextInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] > div {
                border-radius: 14px !important;
            }
            .stAlert {
                border-radius: 14px;
            }
            @media (max-width: 900px) {
                .tl-fin-grid {
                    grid-template-columns: 1fr;
                }
                .main .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    logo_path = next((p for p in LOGO_CANDIDATES if p.exists()), None)
    st.markdown('<div class="tl-header">', unsafe_allow_html=True)
    if logo_path:
        st.image(str(logo_path), width=126)
    st.markdown(f'<div class="tl-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="tl-subtitle">Confirmação de aulas, eventos e financeiro em um só lugar.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div><span class="tl-highlight">Check-in de aulas</span><span class="tl-highlight">Eventos</span><span class="tl-highlight">Financeiro</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------- HELPERS -----------------------------
def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def weekday_label(day: date) -> str:
    labels = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return labels[day.weekday()]


def weekday_location(day: date) -> str:
    wd = day.weekday()  # Mon=0
    if wd in (0, 2, 4):
        return "Clube Mata do Lago"
    if wd in (1, 3):
        return "Condomínio Unique"
    return "Definir com a secretaria"


def available_slots(day: date) -> list[str]:
    if day.weekday() >= 5:
        return []
    morning = ["06:00 às 07:00", "07:00 às 08:00", "08:00 às 09:00", "09:00 às 10:00"]
    afternoon = [
        "15:00 às 16:00",
        "16:00 às 17:00",
        "17:00 às 18:00",
        "18:00 às 19:00",
        "19:00 às 20:00",
        "20:00 às 21:00",
    ]
    return morning + afternoon


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        return st.secrets[name]
    except Exception:
        return default


@st.cache_resource(show_spinner=False)
def get_supabase() -> Optional[Client]:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SECRET_KEY") or get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None

    return create_client(
        url,
        key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


def require_supabase() -> Client:
    client = get_supabase()
    if client is None:
        raise RuntimeError("Supabase não configurado")
    return client


def safe_records(response: Any) -> list[dict[str, Any]]:
    if response is None:
        return []
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def fetch_eventos() -> list[dict[str, Any]]:
    supabase = require_supabase()
    resp = (
        supabase.table("eventos")
        .select("id,titulo,data_evento,local,descricao,ativo,ordem")
        .eq("ativo", True)
        .order("data_evento", desc=False)
        .order("ordem", desc=False)
        .execute()
    )
    return safe_records(resp)


def fetch_recent_confirmacoes(limit: int = 50) -> list[dict[str, Any]]:
    supabase = require_supabase()
    resp = (
        supabase.table("confirmacoes")
        .select("id,nome,whatsapp,data_aula,horario,local,status_pagamento,created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return safe_records(resp)


def lookup_aluno(nome: str, whatsapp: str) -> Optional[dict[str, Any]]:
    supabase = require_supabase()
    phone = normalize_phone(whatsapp)

    if phone:
        resp = (
            supabase.table("alunos")
            .select("id,nome,whatsapp,status_pagamento,ativo,observacao")
            .eq("whatsapp", phone)
            .eq("ativo", True)
            .limit(1)
            .execute()
        )
        rows = safe_records(resp)
        if rows:
            return rows[0]

    if nome.strip():
        resp = (
            supabase.table("alunos")
            .select("id,nome,whatsapp,status_pagamento,ativo,observacao")
            .ilike("nome", nome.strip())
            .eq("ativo", True)
            .limit(5)
            .execute()
        )
        rows = safe_records(resp)
        if rows:
            target = normalize_name(nome)
            exact = next((r for r in rows if normalize_name(r.get("nome", "")) == target), None)
            return exact or rows[0]

    return None


def check_duplicate_confirmacao(whatsapp: str, data_aula: str, horario: str) -> bool:
    supabase = require_supabase()
    resp = (
        supabase.table("confirmacoes")
        .select("id")
        .eq("whatsapp", normalize_phone(whatsapp))
        .eq("data_aula", data_aula)
        .eq("horario", horario)
        .limit(1)
        .execute()
    )
    return bool(safe_records(resp))


def insert_confirmacao(payload: dict[str, Any]) -> None:
    supabase = require_supabase()
    supabase.table("confirmacoes").insert(payload).execute()


def upsert_aluno(payload: dict[str, Any]) -> None:
    supabase = require_supabase()
    supabase.table("alunos").upsert(payload, on_conflict="whatsapp").execute()


def insert_evento(payload: dict[str, Any]) -> None:
    supabase = require_supabase()
    supabase.table("eventos").insert(payload).execute()


# ----------------------------- SIDEBAR / ADMIN -----------------------------
def render_sidebar() -> bool:
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    st.sidebar.markdown("### Acesso administrativo")
    password = st.sidebar.text_input("Senha", type="password")
    admin_password = get_secret("ADMIN_PASSWORD", ADMIN_PASSWORD_DEFAULT)

    cols = st.sidebar.columns(2)
    if cols[0].button("Entrar", use_container_width=True):
        st.session_state.admin_ok = password == admin_password
        if not st.session_state.admin_ok:
            st.sidebar.error("Senha incorreta.")
    if cols[1].button("Sair", use_container_width=True):
        st.session_state.admin_ok = False

    if st.session_state.admin_ok:
        st.sidebar.success("Modo admin liberado.")
        st.sidebar.caption("Cadastre alunos, publique eventos e baixe confirmações.")

    return bool(st.session_state.admin_ok)


def render_admin_panel() -> None:
    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section-title">Painel administrativo</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-small">Controle rápido de alunos, eventos e confirmações.</p>', unsafe_allow_html=True)

    admin_tabs = st.tabs(["Alunos", "Eventos", "Confirmações"])

    with admin_tabs[0]:
        with st.form("form_admin_aluno", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome do aluno")
            whatsapp = c2.text_input("WhatsApp")
            c3, c4 = st.columns(2)
            status = c3.selectbox("Status de pagamento", ["em_dia", "pendente", "inadimplente"])
            ativo = c4.selectbox("Aluno ativo", ["sim", "não"])
            observacao = st.text_input("Observação")
            submitted = st.form_submit_button("Salvar aluno", use_container_width=True)
            if submitted:
                if not nome.strip() or not whatsapp.strip():
                    st.error("Preencha nome e WhatsApp.")
                else:
                    upsert_aluno(
                        {
                            "nome": nome.strip(),
                            "whatsapp": normalize_phone(whatsapp),
                            "status_pagamento": status,
                            "ativo": ativo == "sim",
                            "observacao": observacao.strip() or None,
                        }
                    )
                    st.success("Aluno salvo com sucesso.")

    with admin_tabs[1]:
        with st.form("form_admin_evento", clear_on_submit=True):
            titulo = st.text_input("Título")
            c1, c2 = st.columns(2)
            data_evento = c1.date_input("Data do evento", value=date.today())
            local = c2.text_input("Local")
            descricao = st.text_area("Descrição")
            ordem = st.number_input("Ordem", min_value=1, value=1, step=1)
            submitted = st.form_submit_button("Adicionar evento", use_container_width=True)
            if submitted:
                if not titulo.strip():
                    st.error("Informe o título do evento.")
                else:
                    insert_evento(
                        {
                            "titulo": titulo.strip(),
                            "data_evento": data_evento.isoformat(),
                            "local": local.strip() or None,
                            "descricao": descricao.strip() or None,
                            "ativo": True,
                            "ordem": int(ordem),
                        }
                    )
                    st.success("Evento cadastrado.")

    with admin_tabs[2]:
        rows = fetch_recent_confirmacoes(limit=100)
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Baixar confirmações CSV",
                data=csv_data,
                file_name=f"confirmacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Nenhuma confirmação registrada ainda.")

    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------- MAIN CONTENT -----------------------------
def render_checkin() -> None:
    secretaria = get_secret("SECRETARIA_NOME", SECRETARIA_DEFAULT)
    secretaria_whatsapp = get_secret("SECRETARIA_WHATSAPP", PIX_PHONE_DEFAULT)

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section-title">Check-in de aula</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-small">Escolha a data, confirme o horário e registre sua presença.</p>', unsafe_allow_html=True)

    with st.form("form_checkin", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome completo")
        whatsapp = c2.text_input("WhatsApp")
        c3, c4 = st.columns(2)
        aula_data = c3.date_input("Data da aula", min_value=date.today(), value=date.today())
        slots = available_slots(aula_data)
        horario = c4.selectbox("Horário", slots if slots else ["Sem horário disponível"], disabled=not bool(slots))
        st.text_input("Dia da semana", value=weekday_label(aula_data), disabled=True)
        st.text_input("Local", value=weekday_location(aula_data), disabled=True)
        submit = st.form_submit_button("Confirmar presença", use_container_width=True)

    if submit:
        if aula_data.weekday() >= 5:
            st.warning("As confirmações online estão liberadas apenas de segunda a sexta.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        if not nome.strip() or not whatsapp.strip():
            st.error("Informe nome completo e WhatsApp.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        aluno = lookup_aluno(nome, whatsapp)
        if not aluno:
            st.error("Aluno não localizado. Fale com a secretaria para cadastrar ou atualizar seus dados.")
            st.markdown(f'<div class="tl-soft"><p class="tl-small"><strong>Secretaria:</strong> {secretaria}<br><strong>WhatsApp:</strong> {secretaria_whatsapp}</p></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            return

        status = (aluno.get("status_pagamento") or "").strip().lower()
        if status != "em_dia":
            st.error("Seu check-in está bloqueado por pendência financeira. Regularize com a secretaria da Tênis Linhares.")
            st.markdown(f'<div class="tl-soft"><p class="tl-small"><strong>Secretaria:</strong> {secretaria}<br><strong>WhatsApp:</strong> {secretaria_whatsapp}</p></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            return

        if check_duplicate_confirmacao(aluno.get("whatsapp") or whatsapp, aula_data.isoformat(), horario):
            st.info("Você já confirmou esse mesmo horário nesta data.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        payload = {
            "nome": aluno.get("nome") or nome.strip(),
            "whatsapp": normalize_phone(aluno.get("whatsapp") or whatsapp),
            "data_aula": aula_data.isoformat(),
            "horario": horario,
            "local": weekday_location(aula_data),
            "status_pagamento": status,
        }
        insert_confirmacao(payload)
        st.success("Check-in confirmado com sucesso.")

    st.markdown('</div>', unsafe_allow_html=True)


def render_eventos() -> None:
    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section-title">Eventos</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-small">Torneios, clínicas e avisos especiais.</p>', unsafe_allow_html=True)

    eventos = fetch_eventos()
    if not eventos:
        st.info("Nenhum evento publicado no momento.")
    else:
        for ev in eventos:
            data_evento = ev.get("data_evento") or ""
            try:
                dt = datetime.fromisoformat(str(data_evento)).strftime("%d/%m/%Y")
            except Exception:
                dt = str(data_evento)
            st.markdown('<div class="tl-soft">', unsafe_allow_html=True)
            st.markdown(f"**{ev.get('titulo', 'Evento')}**")
            st.caption(f"{dt} • {ev.get('local', 'Tênis Linhares')}")
            if ev.get("descricao"):
                st.write(ev["descricao"])
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_financeiro() -> None:
    pix_email = get_secret("PIX_EMAIL", PIX_EMAIL_DEFAULT)
    pix_phone = get_secret("PIX_PHONE", PIX_PHONE_DEFAULT)
    secretaria = get_secret("SECRETARIA_NOME", SECRETARIA_DEFAULT)
    secretaria_whatsapp = get_secret("SECRETARIA_WHATSAPP", PIX_PHONE_DEFAULT)

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section-title">Financeiro</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-small">Confira os planos e realize o pagamento por PIX.</p>', unsafe_allow_html=True)

    html_cards = ['<div class="tl-fin-grid">']
    for card in FINANCE_CARDS:
        items_html = "".join(f"<li>{item}</li>" for item in card["items"])
        html_cards.append(
            f'''
            <div class="tl-fin-card">
                <div class="tl-fin-title">{card["title"]}</div>
                <ul class="tl-fin-list">{items_html}</ul>
                <div class="tl-fin-footer">{card["footer"]}</div>
            </div>
            '''
        )
    html_cards.append("</div>")
    st.markdown("".join(html_cards), unsafe_allow_html=True)

    st.markdown('<div class="tl-soft">', unsafe_allow_html=True)
    st.markdown("**Pagamento por PIX**")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Chave PIX por e-mail", value=pix_email, disabled=True)
    with c2:
        st.text_input("Chave PIX por telefone", value=pix_phone, disabled=True)
    st.caption(f"Após o pagamento, envie o comprovante para {secretaria} - {secretaria_whatsapp}.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------- EMPTY STATE -----------------------------
def render_setup_help() -> None:
    st.error("Configuração pendente para colocar o app online.")
    st.markdown(
        """
        1. Crie um projeto no Supabase.
        2. Rode o arquivo `schema.sql` no SQL Editor.
        3. Adicione `SUPABASE_URL`, `SUPABASE_SECRET_KEY` e `ADMIN_PASSWORD` nos Secrets do Streamlit Cloud.
        4. Publique no Streamlit Community Cloud apontando para `app.py`.
        """
    )


# ----------------------------- APP -----------------------------
def main() -> None:
    inject_css()
    admin_ok = render_sidebar()
    render_header()

    try:
        require_supabase()
    except Exception:
        render_setup_help()
        return

    tab1, tab2, tab3 = st.tabs(["Check-in", "Eventos", "Financeiro"])

    try:
        with tab1:
            render_checkin()
        with tab2:
            render_eventos()
        with tab3:
            render_financeiro()

        if admin_ok:
            render_admin_panel()
    except Exception as exc:
        st.error("Ocorreu um erro ao carregar os dados do app.")
        st.exception(exc)


if __name__ == "__main__":
    main()
