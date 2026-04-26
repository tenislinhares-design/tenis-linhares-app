from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATHS = [
    BASE_DIR / "assets" / "logo.jpeg",
    BASE_DIR / "assets" / "logo.jpg",
    BASE_DIR / "assets" / "logo.png",
]

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
        "subtitle": "Grupo",
        "highlight": "Plano Ideal: 3x por semana",
        "items": [
            ("1x por semana", "R$ 313,20"),
            ("2x por semana", "R$ 452,40"),
            ("3x por semana", "R$ 545,20"),
            ("4x por semana", "R$ 893,20"),
        ],
        "footer": "Turmas organizadas por nível técnico.",
    },
    {
        "title": "Plano Individual",
        "subtitle": "",
        "highlight": "Treinamento personalizado",
        "items": [
            ("1x por semana", "R$ 580,00"),
            ("2x por semana", "R$ 1.160,00"),
            ("3x por semana", "R$ 1.740,00"),
        ],
        "footer": "Treinamento personalizado com foco na sua evolução.",
    },
    {
        "title": "Aula Avulsa",
        "subtitle": "",
        "highlight": "Treinos pontuais",
        "items": [
            ("1 hora", "R$ 120,00"),
            ("2 horas", "R$ 210,00"),
            ("3 horas", "R$ 320,00"),
        ],
        "footer": "Ideal para treinos pontuais ou para experimentar a modalidade.",
    },
    {
        "title": "Plano Família",
        "subtitle": "",
        "highlight": "Desconto progressivo",
        "items": [
            ("2 pessoas", "5% de desconto"),
            ("3 pessoas", "10% de desconto"),
            ("4 pessoas ou mais", "15% de desconto"),
        ],
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
            raise AppError(self._extract_error_message(response))

        text = response.text.strip()
        if not text:
            return None
        try:
            return response.json()
        except Exception:
            return text

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                msg = payload.get("message") or payload.get("details") or payload.get("hint")
                if msg:
                    text = str(msg)
                    if "duplicate key value" in text.lower():
                        return "Registro duplicado. Verifique se esse dado já existe."
                    return text
        except Exception:
            pass
        raw = response.text.strip()
        if "duplicate key value" in raw.lower():
            return "Registro duplicado. Verifique se esse dado já existe."
        return raw or "Erro ao comunicar com o banco de dados."


# ------------------ Config / banco ------------------
def secret_value(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = st.secrets[name]
        if isinstance(value, str) and value.strip():
            return value.strip()
    except Exception:
        pass

    value = os.getenv(name)
    if isinstance(value, str) and value.strip():
        return value.strip()
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
    if not config:
        return None
    return SupabaseREST(config)


def db() -> SupabaseREST:
    client = get_db()
    if client is None:
        raise AppError("Aplicativo em fase final de configuração. Tente novamente em instantes.")
    return client


@st.cache_data(ttl=60, show_spinner=False)
def healthcheck() -> bool:
    db().request("GET", "alunos", params={"select": "id", "limit": "1"})
    return True


@st.cache_data(ttl=60, show_spinner=False)
def fetch_students(limit: int = 500) -> list[dict[str, Any]]:
    return db().request(
        "GET",
        "alunos",
        params={
            "select": "id,nome,whatsapp,status_pagamento,ativo,observacao,created_at,updated_at",
            "order": "nome.asc",
            "limit": str(limit),
        },
    ) or []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_events(limit: int = 100, admin: bool = False) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "select": "id,titulo,data_evento,local,descricao,valor_inscricao,ativo,inscricoes_abertas,ordem,created_at",
        "order": "data_evento.asc,ordem.asc",
        "limit": str(limit),
    }
    if not admin:
        params["ativo"] = "eq.true"
    return db().request("GET", "eventos", params=params) or []


@st.cache_data(ttl=30, show_spinner=False)
def fetch_confirmations(limit: int = 300) -> list[dict[str, Any]]:
    return db().request(
        "GET",
        "confirmacoes",
        params={
            "select": "id,nome,whatsapp,data_aula,dia_semana,local,horario,status_pagamento,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    ) or []


@st.cache_data(ttl=30, show_spinner=False)
def fetch_registrations(limit: int = 300) -> list[dict[str, Any]]:
    return db().request(
        "GET",
        "inscricoes_eventos",
        params={
            "select": "id,evento_id,evento_titulo,nome,whatsapp,categoria,valor,status_inscricao,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    ) or []


def clear_all_caches() -> None:
    healthcheck.clear()
    fetch_students.clear()
    fetch_events.clear()
    fetch_confirmations.clear()
    fetch_registrations.clear()


# ------------------ Visual ------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --tl-green: #CCFF00;
                --tl-green-2: #B7E600;
                --tl-dark: #101010;
                --tl-muted: #55603f;
                --tl-soft: #F8FFE8;
                --tl-border: #DDEFA4;
                --tl-shadow: 0 12px 34px rgba(16, 16, 16, 0.08);
            }
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(204,255,0,.18), transparent 35%),
                    linear-gradient(180deg, #ffffff 0%, #fbfff0 100%);
                color: var(--tl-dark);
            }
            .main .block-container {
                max-width: 1060px;
                padding-top: 1.1rem;
                padding-bottom: 2rem;
            }
            [data-testid="stSidebar"] {
                background: #ffffff;
                border-right: 1px solid var(--tl-border);
            }
            .tl-shell,
            .tl-card {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 26px;
                box-shadow: var(--tl-shadow);
                margin-bottom: 16px;
            }
            .tl-shell { padding: 24px 20px 20px; text-align: center; }
            .tl-card { padding: 20px; }
            .tl-brand-header {
                background: linear-gradient(180deg, #ffffff 0%, #F7FFE0 100%);
                border: 2px solid var(--tl-green);
            }
            .tl-logo {
                width: 148px;
                height: 148px;
                object-fit: contain;
                border-radius: 36px;
                border: 3px solid var(--tl-green);
                background: #ffffff;
                padding: 8px;
                box-shadow: 0 10px 26px rgba(16, 16, 16, .14);
            }
            .tl-title {
                margin: 12px 0 6px;
                font-size: 2.25rem;
                line-height: 1.02;
                font-weight: 950;
                color: var(--tl-dark);
            }
            .tl-subtitle { margin: 0 0 14px; color: var(--tl-muted); font-size: 1.02rem; }
            .tl-chip {
                display: inline-block;
                background: #F2FFC8;
                color: #111;
                border: 1px solid #D7ED74;
                border-radius: 999px;
                padding: 8px 12px;
                font-size: .82rem;
                font-weight: 850;
                margin: 0 6px 8px 0;
            }
            .tl-section { font-size: 1.35rem; font-weight: 950; margin: 0 0 4px; color: #111; }
            .tl-caption { color: var(--tl-muted); margin: 0 0 14px; }
            .tl-checkin-card {
                background: linear-gradient(180deg, #F5FFD8 0%, #FFFFFF 82%);
                border: 2px solid var(--tl-green);
            }
            div[data-testid="stForm"] {
                background: #ffffff;
                border: 1px solid #E3F2AC;
                border-radius: 22px;
                padding: 16px;
            }
            .tl-soft {
                background: var(--tl-soft);
                border: 1px solid var(--tl-border);
                border-radius: 18px;
                padding: 14px;
                margin-bottom: 12px;
            }
            .tl-event-card {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 20px;
                padding: 16px;
                box-shadow: 0 8px 24px rgba(16,16,16,.05);
                margin-bottom: 12px;
            }
            .tl-event-title { font-size: 1.08rem; font-weight: 950; margin-bottom: 6px; }
            .tl-price-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 16px;
                margin: 8px 0 18px;
            }
            .tl-fin-card {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 24px;
                overflow: hidden;
                box-shadow: var(--tl-shadow);
            }
            .tl-fin-header {
                background: linear-gradient(180deg, var(--tl-green) 0%, var(--tl-green-2) 100%);
                color: #101010;
                text-align: center;
                padding: 18px 14px 16px;
                font-weight: 950;
                font-size: 1.08rem;
                line-height: 1.1;
            }
            .tl-fin-sub { display: block; font-size: .86rem; margin-top: 3px; }
            .tl-fin-body { padding: 12px 14px 8px; }
            .tl-fin-highlight {
                display: inline-block;
                background: #F4FFD4;
                border: 1px solid #D8ED79;
                border-radius: 999px;
                padding: 6px 10px;
                font-size: .74rem;
                font-weight: 850;
                margin-bottom: 8px;
            }
            .tl-fin-list { list-style: none; padding: 0; margin: 0; }
            .tl-fin-list li {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                border-bottom: 1px solid #EEF4DD;
                padding: 7px 0;
                font-size: .96rem;
            }
            .tl-fin-list li:last-child { border-bottom: 0; }
            .tl-fin-list strong { white-space: nowrap; }
            .tl-fin-foot {
                background: var(--tl-soft);
                border-top: 1px solid var(--tl-border);
                padding: 12px 14px;
                font-size: .92rem;
                font-weight: 780;
                text-align: center;
                color: #1f2b17;
            }
            .stButton > button,
            .stDownloadButton > button {
                background: linear-gradient(180deg, var(--tl-green) 0%, var(--tl-green-2) 100%);
                color: #101010;
                border: 0;
                border-radius: 14px;
                font-weight: 900;
                min-height: 45px;
            }
            .stButton > button:hover,
            .stDownloadButton > button:hover {
                background: linear-gradient(180deg, #D7FF32 0%, #BEEB00 100%);
                color: #101010;
            }
            .stTabs [data-baseweb="tab-list"] { gap: 10px; }
            .stTabs [data-baseweb="tab"] {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 16px;
                padding: 10px 16px;
                font-weight: 850;
            }
            .stTabs [aria-selected="true"] {
                background: #F3FFD3 !important;
                border-color: #D3EA70 !important;
                color: #111 !important;
            }
            .tl-admin-divider { margin: 24px 0 12px; }
            @media (max-width: 780px) {
                .tl-price-grid { grid-template-columns: 1fr; }
                .tl-logo { width: 118px; height: 118px; }
                .tl-title { font-size: 1.85rem; }
                .tl-card, .tl-shell { padding: 16px; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logo_path() -> Optional[Path]:
    for path in LOGO_PATHS:
        if path.exists():
            return path
    return None


def logo_data_uri() -> Optional[str]:
    path = logo_path()
    if not path:
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('utf-8')}"


def render_header() -> None:
    logo = logo_path()

    with st.container(border=True):
        if logo:
            left, right = st.columns([1, 4])
            with left:
                st.image(str(logo), width=118)
            with right:
                st.title(APP_NAME)
                st.caption("Confirmação de aulas, inscrições em torneios, eventos e financeiro em um só lugar.")
        else:
            st.title(APP_NAME)
            st.caption("Confirmação de aulas, inscrições em torneios, eventos e financeiro em um só lugar.")

        c1, c2, c3 = st.columns(3)
        c1.success("Check-in de aulas")
        c2.success("Inscrição em torneios")
        c3.success("Financeiro com PIX")


def render_copy_button(label: str, value: str, key: str) -> None:
    st.code(value, language=None)
    st.caption(f"{label}: toque no código acima e copie.")


# ------------------ Regras de aula ------------------
def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def weekday_label(value: date) -> str:
    return WEEKDAY_LABELS[value.weekday()]


def next_class_day() -> date:
    d = date.today()
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def lesson_location(value: date) -> str:
    wd = value.weekday()
    if wd in (0, 2, 4):
        return "Clube Mata do Lago"
    if wd in (1, 3):
        return "Condomínio Unique"
    return "Sem aula presencial"


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


def money_br(value: Any) -> str:
    try:
        number = float(value or 0)
    except Exception:
        number = 0.0
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------ Operações de banco ------------------
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
            exact = next((r for r in rows if normalize_name(r.get("nome", "")) == target), None)
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


def registration_exists(evento_id: str, whatsapp: str) -> bool:
    rows = db().request(
        "GET",
        "inscricoes_eventos",
        params={
            "select": "id",
            "evento_id": f"eq.{evento_id}",
            "whatsapp": f"eq.{normalize_phone(whatsapp)}",
            "limit": "1",
        },
    ) or []
    return bool(rows)


def upsert_student(payload: dict[str, Any]) -> None:
    db().request(
        "POST",
        "alunos",
        params={"on_conflict": "whatsapp"},
        json_body=payload,
        prefer="resolution=merge-duplicates,return=representation",
    )
    fetch_students.clear()


def insert_confirmation(payload: dict[str, Any]) -> None:
    db().request("POST", "confirmacoes", json_body=payload, prefer="return=representation")
    fetch_confirmations.clear()


def insert_registration(payload: dict[str, Any]) -> None:
    db().request("POST", "inscricoes_eventos", json_body=payload, prefer="return=representation")
    fetch_registrations.clear()


def insert_event(payload: dict[str, Any]) -> None:
    db().request("POST", "eventos", json_body=payload, prefer="return=representation")
    fetch_events.clear()


def update_event(event_id: str, payload: dict[str, Any]) -> None:
    db().request(
        "PATCH",
        "eventos",
        params={"id": f"eq.{event_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_events.clear()


def update_registration_status(registration_id: str, new_status: str) -> None:
    db().request(
        "PATCH",
        "inscricoes_eventos",
        params={"id": f"eq.{registration_id}"},
        json_body={"status_inscricao": new_status},
        prefer="return=representation",
    )
    fetch_registrations.clear()


# ------------------ Área aluno ------------------
def render_student_checkin() -> None:
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card tl-checkin-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Check-in da aula</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Escolha seus dados, horário e confirme sua presença.</p>', unsafe_allow_html=True)

    with st.form("form_checkin"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome completo")
        whatsapp = c2.text_input("WhatsApp")

        c3, c4 = st.columns(2)
        data_aula = c3.date_input("Data da aula", min_value=date.today(), value=next_class_day())
        slots = lesson_slots(data_aula)
        horario = c4.selectbox("Horário", slots if slots else ["Sem horário disponível"], disabled=not bool(slots))

        c5, c6 = st.columns(2)
        c5.text_input("Dia da semana", value=weekday_label(data_aula), disabled=True)
        c6.text_input("Local", value=lesson_location(data_aula), disabled=True)

        submit = st.form_submit_button("Confirmar presença", use_container_width=True)

    if submit:
        if not nome.strip() or not whatsapp.strip():
            st.error("Preencha nome completo e WhatsApp.")
        elif data_aula.weekday() >= 5:
            st.warning("As confirmações online ficam disponíveis de segunda a sexta.")
        elif not slots:
            st.warning("Sem horário disponível para essa data.")
        else:
            try:
                aluno = find_student(nome, whatsapp)
                if not aluno:
                    st.error("Aluno não localizado. Fale com a secretaria para cadastro ou atualização de dados.")
                    st.info(f"Secretaria: {secretaria_nome} | WhatsApp: {secretaria_whatsapp}")
                    return

                status = str(aluno.get("status_pagamento") or "").strip().lower()
                if status != "em_dia":
                    st.error("Seu check-in está bloqueado por pendência financeira. Regularize com a secretaria da Tênis Linhares.")
                    st.info(f"Secretaria: {secretaria_nome} | WhatsApp: {secretaria_whatsapp}")
                    return

                if confirmation_exists(aluno.get("whatsapp") or whatsapp, data_aula.isoformat(), horario):
                    st.warning("Você já confirmou esse horário nesta data.")
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
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Eventos e inscrições</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Veja os eventos disponíveis e faça sua inscrição. O pagamento é manual por PIX.</p>', unsafe_allow_html=True)

    try:
        events = [event for event in fetch_events() if event.get("ativo")]
    except AppError as exc:
        st.error(str(exc))
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not events:
        st.info("Nenhum evento disponível no momento.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    for event in events:
        status_txt = "Inscrições abertas" if event.get("inscricoes_abertas", True) else "Inscrições encerradas"
        valor_txt = money_br(event.get("valor_inscricao")) if float(event.get("valor_inscricao") or 0) > 0 else "A confirmar"
        st.markdown('<div class="tl-event-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="tl-event-title">{event.get("titulo", "Evento")}</div>', unsafe_allow_html=True)
        st.caption(f"{format_date_br(event.get('data_evento'))} • {event.get('local') or 'Tênis Linhares'} • Inscrição: {valor_txt} • {status_txt}")
        if event.get("descricao"):
            st.write(event.get("descricao"))
        st.markdown('</div>', unsafe_allow_html=True)

    open_events = [e for e in events if e.get("inscricoes_abertas", True)]
    if not open_events:
        st.info("Os eventos publicados estão com inscrições encerradas no momento.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    with st.form("form_event_registration"):
        options = {f"{e.get('titulo')} - {format_date_br(e.get('data_evento'))}": e for e in open_events}
        evento_label = st.selectbox("Escolha o torneio/evento", list(options.keys()))
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome para inscrição")
        whatsapp = c2.text_input("WhatsApp para inscrição")
        categoria = st.text_input("Categoria")
        submit = st.form_submit_button("Confirmar inscrição", use_container_width=True)

    if submit:
        evento = options[evento_label]
        if not nome.strip() or not whatsapp.strip() or not categoria.strip():
            st.error("Preencha nome, WhatsApp e categoria.")
        else:
            try:
                if registration_exists(str(evento.get("id")), whatsapp):
                    st.warning("Você já se inscreveu nesse evento com esse WhatsApp.")
                else:
                    insert_registration(
                        {
                            "evento_id": evento.get("id"),
                            "evento_titulo": evento.get("titulo"),
                            "nome": nome.strip(),
                            "whatsapp": normalize_phone(whatsapp),
                            "categoria": categoria.strip(),
                            "valor": evento.get("valor_inscricao") or None,
                            "status_inscricao": "aguardando_pagamento",
                        }
                    )
                    st.success("Inscrição registrada com sucesso.")
                    st.info(f"Pagamento manual por PIX. Depois envie o comprovante para {secretaria_nome} - {secretaria_whatsapp}.")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption("PIX e-mail")
                        render_copy_button("Copiar", pix_email, "evt-email")
                    with c2:
                        st.caption("PIX telefone")
                        render_copy_button("Copiar", pix_phone, "evt-phone")
            except AppError as exc:
                st.error(str(exc))

    st.markdown('</div>', unsafe_allow_html=True)


def render_finance_cards() -> None:
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.subheader("Financeiro")
    st.caption("Confira os planos e realize o pagamento por PIX.")

    cols = st.columns(2)
    for index, card in enumerate(FINANCE_CARDS):
        with cols[index % 2]:
            with st.container(border=True):
                st.markdown(f"### {card['title']}")
                if card.get("subtitle"):
                    st.caption(card["subtitle"])
                if card.get("highlight"):
                    st.success(card["highlight"])

                for label, value in card["items"]:
                    line_left, line_right = st.columns([2.2, 1])
                    line_left.write(label)
                    line_right.markdown(f"**{value}**")

                st.caption(card["footer"])

    st.divider()
    st.markdown("### Pagamento por PIX")
    st.caption("Copie uma das chaves abaixo para realizar o pagamento.")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Chave PIX por e-mail**")
        render_copy_button("Copiar e-mail", pix_email, "pix-email")
    with p2:
        st.markdown("**Chave PIX por telefone**")
        render_copy_button("Copiar telefone", pix_phone, "pix-phone")
    st.info(f"Após o pagamento, envie o comprovante para {secretaria_nome} - {secretaria_whatsapp}.")


# ------------------ Admin ------------------
def render_admin_sidebar() -> bool:
    st.sidebar.markdown("### Área administrativa")
    st.sidebar.caption("Acesso restrito.")

    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    password = secret_value("ADMIN_PASSWORD", DEFAULTS["ADMIN_PASSWORD"])
    typed = st.sidebar.text_input("Senha", type="password", key="admin_password_input")

    c1, c2 = st.sidebar.columns(2)
    if c1.button("Entrar", use_container_width=True):
        if typed == password:
            st.session_state.admin_ok = True
            st.sidebar.success("Modo admin liberado.")
        else:
            st.session_state.admin_ok = False
            st.sidebar.error("Senha incorreta.")

    if c2.button("Sair", use_container_width=True):
        st.session_state.admin_ok = False
        st.session_state.admin_password_input = ""

    return bool(st.session_state.admin_ok)


def render_students_admin() -> None:
    with st.form("form_aluno", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do aluno")
        whatsapp = c2.text_input("WhatsApp")
        c3, c4 = st.columns(2)
        status = c3.selectbox("Status de pagamento", ["em_dia", "pendente", "inadimplente"])
        ativo = c4.selectbox("Aluno ativo", ["sim", "não"])
        observacao = st.text_input("Observação")
        submit = st.form_submit_button("Salvar aluno", use_container_width=True)

    if submit:
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
        rows = fetch_students()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum aluno cadastrado ainda.")
    except AppError as exc:
        st.error(str(exc))


def render_events_admin() -> None:
    st.markdown("#### Novo evento")
    with st.form("form_evento", clear_on_submit=True):
        titulo = st.text_input("Título do evento")
        c1, c2 = st.columns(2)
        data_evento = c1.date_input("Data do evento", value=date.today() + timedelta(days=15), key="new_event_date")
        local = c2.text_input("Local", value="Tênis Linhares")
        descricao = st.text_area("Descrição")
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor da inscrição", min_value=0.0, value=0.0, step=10.0)
        ordem = c4.number_input("Ordem", min_value=1, value=1, step=1)
        inscricoes_abertas = st.selectbox("Inscrições abertas?", ["sim", "não"])
        submit = st.form_submit_button("Adicionar evento", use_container_width=True)

    if submit:
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
                        "valor_inscricao": float(valor),
                        "ativo": True,
                        "inscricoes_abertas": inscricoes_abertas == "sim",
                        "ordem": int(ordem),
                    }
                )
                st.success("Evento cadastrado com sucesso.")
            except AppError as exc:
                st.error(str(exc))

    st.markdown("#### Editar evento existente")
    try:
        events = fetch_events(admin=True)
    except AppError as exc:
        st.error(str(exc))
        return

    if not events:
        st.info("Nenhum evento cadastrado ainda.")
        return

    labels = {f"{e.get('titulo')} - {format_date_br(e.get('data_evento'))}": e for e in events}
    chosen = st.selectbox("Escolha um evento", list(labels.keys()))
    event = labels[chosen]

    with st.form("form_edit_event"):
        titulo_edit = st.text_input("Título", value=event.get("titulo") or "")
        c1, c2 = st.columns(2)
        try:
            event_date_value = datetime.strptime(str(event.get("data_evento")), "%Y-%m-%d").date()
        except Exception:
            event_date_value = date.today()
        data_edit = c1.date_input("Data", value=event_date_value, key="edit_event_date")
        local_edit = c2.text_input("Local", value=event.get("local") or "")
        descricao_edit = st.text_area("Descrição", value=event.get("descricao") or "")
        c3, c4 = st.columns(2)
        valor_edit = c3.number_input("Valor da inscrição", min_value=0.0, value=float(event.get("valor_inscricao") or 0), step=10.0, key="edit_valor")
        ordem_edit = c4.number_input("Ordem", min_value=1, value=int(event.get("ordem") or 1), step=1, key="edit_ordem")
        c5, c6 = st.columns(2)
        ativo_edit = c5.selectbox("Evento visível?", ["sim", "não"], index=0 if event.get("ativo", True) else 1)
        abertas_edit = c6.selectbox("Inscrições abertas?", ["sim", "não"], index=0 if event.get("inscricoes_abertas", True) else 1)
        submit_edit = st.form_submit_button("Salvar alterações do evento", use_container_width=True)

    if submit_edit:
        try:
            update_event(
                str(event.get("id")),
                {
                    "titulo": titulo_edit.strip(),
                    "data_evento": data_edit.isoformat(),
                    "local": local_edit.strip() or None,
                    "descricao": descricao_edit.strip() or None,
                    "valor_inscricao": float(valor_edit),
                    "ordem": int(ordem_edit),
                    "ativo": ativo_edit == "sim",
                    "inscricoes_abertas": abertas_edit == "sim",
                },
            )
            st.success("Evento atualizado com sucesso.")
            st.rerun()
        except AppError as exc:
            st.error(str(exc))

    st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)


def render_registrations_admin() -> None:
    try:
        regs = fetch_registrations()
    except AppError as exc:
        st.error(str(exc))
        return

    if not regs:
        st.info("Nenhuma inscrição registrada ainda.")
        return

    df = pd.DataFrame(regs)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "Baixar inscrições CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"inscricoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    labels = {
        f"{r.get('nome')} | {r.get('evento_titulo')} | {r.get('status_inscricao')}": r
        for r in regs
    }
    with st.form("form_status_inscricao"):
        escolhido = st.selectbox("Escolha uma inscrição para atualizar", list(labels.keys()))
        novo_status = st.selectbox("Novo status", ["aguardando_pagamento", "pago", "cancelada"])
        submit = st.form_submit_button("Atualizar status", use_container_width=True)

    if submit:
        try:
            update_registration_status(str(labels[escolhido].get("id")), novo_status)
            st.success("Status atualizado com sucesso.")
            st.rerun()
        except AppError as exc:
            st.error(str(exc))


def render_confirmations_admin() -> None:
    try:
        rows = fetch_confirmations()
    except AppError as exc:
        st.error(str(exc))
        return

    if not rows:
        st.info("Nenhuma confirmação registrada ainda.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "Baixar confirmações CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"confirmacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_admin_panel() -> None:
    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Painel administrativo</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Cadastre alunos, controle eventos, inscrições e confirmações.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    tab_alunos, tab_eventos, tab_inscricoes, tab_confirmacoes = st.tabs(["Alunos", "Eventos", "Inscrições", "Confirmações"])
    with tab_alunos:
        render_students_admin()
    with tab_eventos:
        render_events_admin()
    with tab_inscricoes:
        render_registrations_admin()
    with tab_confirmacoes:
        render_confirmations_admin()


# ------------------ App ------------------
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

    tab_checkin, tab_eventos, tab_financeiro = st.tabs(["Check-in das aulas", "Eventos", "Financeiro"])
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
