from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Tênis Linhares",
    page_icon="🎾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_NAME = "Tênis Linhares"
LOGO_PATHS = [Path("assets/logo.jpeg"), Path("assets/logo.jpg"), Path("assets/logo.png")]
DEFAULTS = {
    "PIX_EMAIL": "tenislinhares@gmail.com",
    "PIX_PHONE": "+55 27 99997-0109",
    "SECRETARIA_NOME": "Andrea Nascimento",
    "SECRETARIA_WHATSAPP": "+55 27 99997-0109",
    "ADMIN_PASSWORD": "Linhares@2026Admin",
}

FINANCE_CARDS = [
    {
        "title": "Aulas Semanais",
        "subtitle": "(Grupo)",
        "items": [
            ("1x por semana", "R$ 313,20"),
            ("2x por semana", "R$ 452,40"),
            ("3x por semana", "R$ 545,20"),
            ("4x por semana", "R$ 893,20"),
        ],
        "highlight": "Plano Ideal: 3x por semana",
        "footer": "Turmas organizadas por nível técnico.",
    },
    {
        "title": "Plano Individual",
        "subtitle": "",
        "items": [
            ("1x por semana", "R$ 580,00"),
            ("2x por semana", "R$ 1.160,00"),
            ("3x por semana", "R$ 1.740,00"),
        ],
        "highlight": "Treinamento personalizado",
        "footer": "Treinamento personalizado com foco na sua evolução.",
    },
    {
        "title": "Aula Avulsa",
        "subtitle": "",
        "items": [
            ("1 hora", "R$ 120,00"),
            ("2 horas", "R$ 210,00"),
            ("3 horas", "R$ 320,00"),
        ],
        "highlight": "Ideal para experimentar",
        "footer": "Ideal para treinos pontuais ou para experimentar a modalidade.",
    },
    {
        "title": "Plano Família",
        "subtitle": "",
        "items": [
            ("2 pessoas", "5% de desconto"),
            ("3 pessoas", "10% de desconto"),
            ("4 pessoas ou mais", "15% de desconto"),
        ],
        "highlight": "Desconto progressivo",
        "footer": "Esporte, disciplina e evolução para toda a família.",
    },
]

WEEKDAY_LABELS = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]


class AppError(Exception):
    pass


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    secret_key: str


class SupabaseREST:
    def __init__(self, config: SupabaseConfig) -> None:
        self.config = config

    def _headers(self, prefer: Optional[str] = None) -> dict[str, str]:
        headers = {
            "apikey": self.config.secret_key,
            "Authorization": f"Bearer {self.config.secret_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _url(self, path: str) -> str:
        return f"{self.config.url}/rest/v1/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Any = None,
        prefer: Optional[str] = None,
    ) -> Any:
        try:
            response = requests.request(
                method=method,
                url=self._url(path),
                headers=self._headers(prefer),
                params=params,
                json=json_body,
                timeout=20,
            )
        except requests.RequestException as exc:
            raise AppError("Falha de conexão com o banco de dados.") from exc

        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise AppError(message)

        if not response.text.strip():
            return None

        try:
            return response.json()
        except Exception:
            return response.text

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                details = payload.get("message") or payload.get("details") or payload.get("hint")
                if details:
                    text = str(details)
                    if "duplicate key value" in text.lower():
                        return "Registro duplicado. Verifique se esse dado já existe."
                    return text
        except Exception:
            pass

        text = response.text.strip()
        if "duplicate key value" in text.lower():
            return "Registro duplicado. Verifique se esse dado já existe."
        if text:
            return text
        return "Ocorreu um erro ao comunicar com o banco de dados."


# ---------- Visual ----------
def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --tl-green: #b8d514;
                --tl-green-dark: #8ea90d;
                --tl-dark: #122118;
                --tl-soft: #f6fbf1;
                --tl-border: #dce7d2;
                --tl-muted: #4c6750;
            }
            .stApp {
                background: linear-gradient(180deg, #ffffff 0%, #f6fbf1 100%);
                color: var(--tl-dark);
            }
            .main .block-container {
                max-width: 980px;
                padding-top: 1.1rem;
                padding-bottom: 2.3rem;
            }
            [data-testid="stSidebar"] {
                background: #ffffff;
                border-right: 1px solid var(--tl-border);
            }
            .tl-shell {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 28px;
                box-shadow: 0 12px 30px rgba(18, 33, 24, 0.06);
                padding: 22px 20px 18px;
                margin-bottom: 16px;
            }
            .tl-title {
                color: #102814;
                font-size: 2.1rem;
                font-weight: 900;
                margin: 12px 0 4px;
                line-height: 1.04;
            }
            .tl-subtitle {
                color: var(--tl-muted);
                font-size: 1rem;
                margin: 0 0 16px;
            }
            .tl-chip {
                display: inline-block;
                margin: 0 8px 8px 0;
                background: #eef8e5;
                color: #223025;
                border: 1px solid #d9e9cf;
                border-radius: 999px;
                padding: 7px 12px;
                font-size: .82rem;
                font-weight: 800;
            }
            .tl-card {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 24px;
                box-shadow: 0 10px 22px rgba(19, 33, 23, 0.05);
                padding: 18px;
                margin-bottom: 14px;
            }
            .tl-section {
                color: #102814;
                font-size: 1.25rem;
                font-weight: 900;
                margin-bottom: .22rem;
            }
            .tl-caption {
                color: var(--tl-muted);
                font-size: .96rem;
                margin-bottom: .86rem;
            }
            .tl-soft {
                background: #f7fff1;
                border: 1px solid #dfedd7;
                border-radius: 18px;
                padding: 14px;
                margin-bottom: 12px;
            }
            .tl-fin-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 16px;
                margin: 12px 0 8px;
            }
            .tl-fin-card {
                background: #ffffff;
                color: var(--tl-dark);
                border-radius: 24px;
                padding: 0;
                border: 1px solid var(--tl-border);
                overflow: hidden;
                box-shadow: 0 10px 24px rgba(19, 33, 23, 0.05);
            }
            .tl-fin-header {
                background: linear-gradient(180deg, #c8e31a 0%, #afcf12 100%);
                color: #101410;
                padding: 18px 16px 16px;
                text-align: center;
                font-weight: 900;
                font-size: 1.12rem;
                line-height: 1.08;
            }
            .tl-fin-sub {
                display: block;
                font-size: .9rem;
                margin-top: 4px;
            }
            .tl-fin-body {
                padding: 16px;
            }
            .tl-fin-highlight {
                display: inline-block;
                background: #eff9e8;
                border: 1px solid #dceace;
                border-radius: 999px;
                padding: 6px 10px;
                font-size: .75rem;
                font-weight: 800;
                margin-bottom: 10px;
            }
            .tl-fin-list {
                list-style: none;
                margin: 0;
                padding: 0;
            }
            .tl-fin-list li {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                padding: 10px 0;
                border-bottom: 1px solid #eef3ea;
                font-size: .98rem;
            }
            .tl-fin-list li:last-child {
                border-bottom: 0;
            }
            .tl-fin-foot {
                background: #f7fff1;
                color: #203123;
                border-top: 1px solid var(--tl-border);
                padding: 12px 14px;
                text-align: center;
                font-size: .92rem;
                font-weight: 700;
            }
            .stButton > button,
            .stDownloadButton > button {
                border: none;
                border-radius: 14px;
                min-height: 46px;
                font-weight: 800;
                background: linear-gradient(180deg, #c4e117 0%, #a9c30d 100%);
                color: #111511;
            }
            .stButton > button:hover,
            .stDownloadButton > button:hover {
                background: linear-gradient(180deg, #bfdc11 0%, #96b107 100%);
                color: #111511;
            }
            .stTabs [data-baseweb="tab-list"] { gap: 10px; }
            .stTabs [data-baseweb="tab"] {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 14px;
                padding: 10px 16px;
                font-weight: 800;
            }
            .stTabs [aria-selected="true"] {
                background: #eef8e6 !important;
                border-color: #d5e7ca !important;
                color: #102814 !important;
            }
            .stAlert { border-radius: 16px; }
            .tl-admin-divider {
                margin: 24px 0 12px;
            }
            @media (max-width: 900px) {
                .tl-fin-grid { grid-template-columns: 1fr; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logo_path() -> Optional[str]:
    for path in LOGO_PATHS:
        if path.exists():
            return str(path)
    return None


def render_header() -> None:
    st.markdown('<div class="tl-shell">', unsafe_allow_html=True)
    logo = logo_path()
    if logo:
        st.image(logo, width=126)
    st.markdown(f'<div class="tl-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="tl-subtitle">Confirmação de aulas, eventos e financeiro em um só lugar.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="tl-chip">Check-in de aulas</span>'
        '<span class="tl-chip">Eventos</span>'
        '<span class="tl-chip">Financeiro</span>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ---------- Utilidades ----------
def secret_value(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = st.secrets[name]
        if isinstance(value, str) and value.strip():
            return value.strip()
    except Exception:
        pass

    env_value = os.getenv(name)
    if isinstance(env_value, str) and env_value.strip():
        return env_value.strip()

    return default


@st.cache_resource(show_spinner=False)
def get_config() -> Optional[SupabaseConfig]:
    url = secret_value("SUPABASE_URL")
    key = secret_value("SUPABASE_SECRET_KEY") or secret_value("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return SupabaseConfig(url=url.rstrip("/"), secret_key=key)


@st.cache_resource(show_spinner=False)
def get_db() -> Optional[SupabaseREST]:
    config = get_config()
    if config is None:
        return None
    return SupabaseREST(config)


def db() -> SupabaseREST:
    client = get_db()
    if client is None:
        raise AppError("Aplicativo em configuração. Tente novamente em instantes.")
    return client


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def weekday_label(value: date) -> str:
    return WEEKDAY_LABELS[value.weekday()]


def lesson_location(value: date) -> str:
    wd = value.weekday()
    if wd in (0, 2, 4):
        return "Clube Mata do Lago"
    if wd in (1, 3):
        return "Condomínio Unique"
    return "Consulte a secretaria"


def lesson_slots(value: date) -> list[str]:
    if value.weekday() >= 5:
        return []
    return [
        "06:00 às 07:00",
        "07:00 às 08:00",
        "08:00 às 09:00",
        "09:00 às 10:00",
        "15:00 às 16:00",
        "16:00 às 17:00",
        "17:00 às 18:00",
        "18:00 às 19:00",
        "19:00 às 20:00",
        "20:00 às 21:00",
    ]


def format_date_br(value: Any) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y")
    except Exception:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return str(value)


# ---------- Banco ----------
@st.cache_data(ttl=60, show_spinner=False)
def healthcheck() -> bool:
    _ = db().request("GET", "alunos", params={"select": "id", "limit": "1"})
    return True


@st.cache_data(ttl=60, show_spinner=False)
def fetch_events() -> list[dict[str, Any]]:
    data = db().request(
        "GET",
        "eventos",
        params={
            "select": "id,titulo,data_evento,local,descricao,ativo,ordem,created_at",
            "ativo": "eq.true",
            "order": "data_evento.asc,ordem.asc",
        },
    )
    return data or []


@st.cache_data(ttl=20, show_spinner=False)
def fetch_recent_confirmations(limit: int = 100) -> list[dict[str, Any]]:
    data = db().request(
        "GET",
        "confirmacoes",
        params={
            "select": "id,nome,whatsapp,data_aula,horario,local,status_pagamento,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    )
    return data or []


@st.cache_data(ttl=20, show_spinner=False)
def fetch_students(limit: int = 500) -> list[dict[str, Any]]:
    data = db().request(
        "GET",
        "alunos",
        params={
            "select": "id,nome,whatsapp,status_pagamento,ativo,observacao,created_at,updated_at",
            "order": "nome.asc",
            "limit": str(limit),
        },
    )
    return data or []


def clear_cached_lists() -> None:
    fetch_events.clear()
    fetch_recent_confirmations.clear()
    fetch_students.clear()
    healthcheck.clear()


def find_student(nome: str, whatsapp: str) -> Optional[dict[str, Any]]:
    phone = normalize_phone(whatsapp)
    if phone:
        rows = db().request(
            "GET",
            "alunos",
            params={
                "select": "id,nome,whatsapp,status_pagamento,ativo,observacao",
                "whatsapp": f"eq.{phone}",
                "ativo": "eq.true",
                "limit": "1",
            },
        ) or []
        if rows:
            return rows[0]

    clean_name = nome.strip()
    if clean_name:
        rows = db().request(
            "GET",
            "alunos",
            params={
                "select": "id,nome,whatsapp,status_pagamento,ativo,observacao",
                "nome": f"ilike.*{clean_name}*",
                "ativo": "eq.true",
                "limit": "10",
            },
        ) or []
        if rows:
            target = normalize_name(clean_name)
            exact = next((row for row in rows if normalize_name(row.get("nome", "")) == target), None)
            return exact or rows[0]
    return None


def confirmation_exists(whatsapp: str, data_aula: str, horario: str) -> bool:
    rows = db().request(
        "GET",
        "confirmacoes",
        params={
            "select": "id",
            "whatsapp": f"eq.{normalize_phone(whatsapp)}",
            "data_aula": f"eq.{data_aula}",
            "horario": f"eq.{horario}",
            "limit": "1",
        },
    ) or []
    return bool(rows)


def insert_confirmation(payload: dict[str, Any]) -> None:
    db().request(
        "POST",
        "confirmacoes",
        json_body=payload,
        prefer="return=representation",
    )
    fetch_recent_confirmations.clear()


def upsert_student(payload: dict[str, Any]) -> None:
    db().request(
        "POST",
        "alunos",
        params={"on_conflict": "whatsapp"},
        json_body=payload,
        prefer="resolution=merge-duplicates,return=representation",
    )
    fetch_students.clear()


def insert_event(payload: dict[str, Any]) -> None:
    db().request(
        "POST",
        "eventos",
        json_body=payload,
        prefer="return=representation",
    )
    fetch_events.clear()


# ---------- Telas aluno ----------
def render_student_checkin() -> None:
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Check-in de Aula</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Escolha sua data, horário e confirme sua presença.</p>', unsafe_allow_html=True)

    with st.form("form_checkin"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome completo")
        whatsapp = col2.text_input("WhatsApp")

        col3, col4 = st.columns(2)
        data_aula = col3.date_input("Data da aula", min_value=date.today(), value=date.today())
        slots = lesson_slots(data_aula)
        horario = col4.selectbox("Horário", slots if slots else ["Sem horário disponível"], disabled=not bool(slots))

        c5, c6 = st.columns(2)
        c5.text_input("Dia da semana", value=weekday_label(data_aula), disabled=True)
        c6.text_input("Local", value=lesson_location(data_aula), disabled=True)

        submit = st.form_submit_button("Confirmar presença", use_container_width=True)

    if submit:
        if not nome.strip() or not whatsapp.strip():
            st.error("Preencha nome completo e WhatsApp.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        if data_aula.weekday() >= 5:
            st.warning("As confirmações online ficam disponíveis de segunda a sexta.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        if not slots:
            st.warning("Sem horário disponível para essa data.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        try:
            aluno = find_student(nome, whatsapp)
        except AppError as exc:
            st.error(str(exc))
            st.markdown('</div>', unsafe_allow_html=True)
            return

        if not aluno:
            st.error("Aluno não localizado. Fale com a secretaria para cadastro ou atualização de dados.")
            st.info(f"Secretaria: {secretaria_nome} | WhatsApp: {secretaria_whatsapp}")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        status = str(aluno.get("status_pagamento") or "").strip().lower()
        if status != "em_dia":
            st.error("Seu check-in está bloqueado por pendência financeira. Regularize com a secretaria da Tênis Linhares.")
            st.info(f"Secretaria: {secretaria_nome} | WhatsApp: {secretaria_whatsapp}")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        try:
            if confirmation_exists(aluno.get("whatsapp") or whatsapp, data_aula.isoformat(), horario):
                st.warning("Você já confirmou esse horário nesta data.")
                st.markdown('</div>', unsafe_allow_html=True)
                return

            insert_confirmation(
                {
                    "aluno_id": aluno.get("id"),
                    "nome": aluno.get("nome") or nome.strip(),
                    "whatsapp": normalize_phone(aluno.get("whatsapp") or whatsapp),
                    "data_aula": data_aula.isoformat(),
                    "dia_semana": weekday_label(data_aula),
                    "local": lesson_location(data_aula),
                    "horario": horario,
                    "status_pagamento": status,
                }
            )
            st.success("Check-in confirmado com sucesso.")
        except AppError as exc:
            st.error(str(exc))

    st.markdown('</div>', unsafe_allow_html=True)


def render_student_events() -> None:
    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Eventos</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Torneios, clínicas e avisos especiais.</p>', unsafe_allow_html=True)

    try:
        events = fetch_events()
    except AppError as exc:
        st.error(str(exc))
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not events:
        st.info("Nenhum evento publicado no momento.")
    else:
        for event in events:
            st.markdown('<div class="tl-soft">', unsafe_allow_html=True)
            st.markdown(f"**{event.get('titulo', 'Evento')}**")
            local = event.get("local") or "Tênis Linhares"
            st.caption(f"{format_date_br(event.get('data_evento'))} • {local}")
            if event.get("descricao"):
                st.write(event["descricao"])
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_finance_cards() -> None:
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Financeiro</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Confira os planos e realize o pagamento por PIX.</p>', unsafe_allow_html=True)

    html = ['<div class="tl-fin-grid">']
    for card in FINANCE_CARDS:
        items_html = ''.join(
            f'<li><span>{label}</span><strong>{value}</strong></li>' for label, value in card["items"]
        )
        subtitle = f'<span class="tl-fin-sub">{card["subtitle"]}</span>' if card["subtitle"] else ''
        highlight = f'<div class="tl-fin-highlight">{card["highlight"]}</div>' if card.get("highlight") else ''
        html.append(
            f'''
            <div class="tl-fin-card">
                <div class="tl-fin-header">{card['title']}{subtitle}</div>
                <div class="tl-fin-body">
                    {highlight}
                    <ul class="tl-fin-list">{items_html}</ul>
                </div>
                <div class="tl-fin-foot">{card['footer']}</div>
            </div>
            '''
        )
    html.append('</div>')
    st.markdown(''.join(html), unsafe_allow_html=True)

    st.markdown('<div class="tl-soft">', unsafe_allow_html=True)
    st.markdown('**Pagamento por PIX**')
    col1, col2 = st.columns(2)
    col1.text_input('Chave PIX por e-mail', value=pix_email, disabled=True)
    col2.text_input('Chave PIX por telefone', value=pix_phone, disabled=True)
    st.caption(f'Após o pagamento, envie o comprovante para {secretaria_nome} - {secretaria_whatsapp}.')
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------- Admin ----------
def render_admin_sidebar() -> bool:
    st.sidebar.markdown("### Área administrativa")
    st.sidebar.caption("Acesso restrito à administração.")

    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    admin_password = secret_value("ADMIN_PASSWORD", DEFAULTS["ADMIN_PASSWORD"])
    entered_password = st.sidebar.text_input("Senha", type="password", key="admin_password_input")

    col1, col2 = st.sidebar.columns(2)
    if col1.button("Entrar", use_container_width=True):
        if entered_password == admin_password:
            st.session_state.admin_ok = True
        else:
            st.session_state.admin_ok = False
            st.sidebar.error("Senha incorreta.")

    if col2.button("Sair", use_container_width=True):
        st.session_state.admin_ok = False
        st.session_state.admin_password_input = ""

    if st.session_state.admin_ok:
        st.sidebar.success("Modo admin liberado.")

    return bool(st.session_state.admin_ok)


def render_admin_panel() -> None:
    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Painel administrativo</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Cadastre alunos, publique eventos e acompanhe confirmações.</p>', unsafe_allow_html=True)

    tab_alunos, tab_eventos, tab_confirmacoes = st.tabs(["Alunos", "Eventos", "Confirmações"])

    with tab_alunos:
        with st.form("form_aluno", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome do aluno")
            whatsapp = c2.text_input("WhatsApp")

            c3, c4 = st.columns(2)
            status = c3.selectbox("Status de pagamento", ["em_dia", "pendente", "inadimplente"])
            ativo = c4.selectbox("Aluno ativo", ["sim", "não"])
            observacao = st.text_input("Observação")
            submit_aluno = st.form_submit_button("Salvar aluno", use_container_width=True)

            if submit_aluno:
                if not nome.strip() or not whatsapp.strip():
                    st.error("Preencha nome e WhatsApp.")
                else:
                    try:
                        upsert_student(
                            {
                                "nome": nome.strip(),
                                "whatsapp": normalize_phone(whatsapp),
                                "status_pagamento": status,
                                "ativo": ativo == "sim",
                                "observacao": observacao.strip() or None,
                            }
                        )
                        st.success("Aluno salvo com sucesso.")
                    except AppError as exc:
                        st.error(str(exc))

        try:
            students = fetch_students()
            if students:
                df = pd.DataFrame(students)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum aluno cadastrado ainda.")
        except AppError as exc:
            st.error(str(exc))

    with tab_eventos:
        with st.form("form_evento", clear_on_submit=True):
            titulo = st.text_input("Título do evento")
            c1, c2 = st.columns(2)
            data_evento = c1.date_input("Data do evento", value=date.today())
            local = c2.text_input("Local")
            descricao = st.text_area("Descrição")
            ordem = st.number_input("Ordem", min_value=1, value=1, step=1)
            submit_evento = st.form_submit_button("Adicionar evento", use_container_width=True)
            if submit_evento:
                if not titulo.strip():
                    st.error("Informe o título do evento.")
                else:
                    try:
                        insert_event(
                            {
                                "titulo": titulo.strip(),
                                "data_evento": data_evento.isoformat(),
                                "local": local.strip() or None,
                                "descricao": descricao.strip() or None,
                                "ativo": True,
                                "ordem": int(ordem),
                            }
                        )
                        st.success("Evento cadastrado com sucesso.")
                    except AppError as exc:
                        st.error(str(exc))

        try:
            events = fetch_events()
            if events:
                st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum evento publicado ainda.")
        except AppError as exc:
            st.error(str(exc))

    with tab_confirmacoes:
        try:
            confirmations = fetch_recent_confirmations(300)
            if confirmations:
                df = pd.DataFrame(confirmations)
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
        except AppError as exc:
            st.error(str(exc))

    st.markdown('</div>', unsafe_allow_html=True)


# ---------- App ----------
def render_setup_message() -> None:
    st.warning("Aplicativo em fase final de configuração. Tente novamente em instantes.")


def main() -> None:
    inject_css()
    admin_ok = render_admin_sidebar()
    render_header()

    if get_config() is None:
        render_setup_message()
        return

    try:
        healthcheck()
    except AppError:
        render_setup_message()
        return

    tab_checkin, tab_eventos, tab_financeiro = st.tabs(["Check-in de aulas", "Eventos", "Financeiro"])

    with tab_checkin:
        render_student_checkin()

    with tab_eventos:
        render_student_events()

    with tab_financeiro:
        render_finance_cards()

    if admin_ok:
        st.markdown('<div class="tl-admin-divider"></div>', unsafe_allow_html=True)
        render_admin_panel()


if __name__ == "__main__":
    main()
