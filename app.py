
from __future__ import annotations

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
        "subtitle": "(Grupo)",
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
        "highlight": "Ideal para treinos pontuais",
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
    cfg = get_config()
    if cfg is None:
        return None
    return SupabaseREST(cfg)


def db() -> SupabaseREST:
    client = get_db()
    if client is None:
        raise AppError("Aplicativo em fase final de configuração. Tente novamente em instantes.")
    return client


def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --tl-green: #CCFF00;
                --tl-green-dark: #B7E600;
                --tl-dark: #101010;
                --tl-soft: #F8FFE8;
                --tl-border: #DCEAB1;
                --tl-muted: #526040;
                --tl-card-shadow: 0 10px 30px rgba(16, 16, 16, 0.06);
            }
            .stApp {
                background: linear-gradient(180deg, #ffffff 0%, #fbfff4 100%);
                color: var(--tl-dark);
            }
            .main .block-container {
                max-width: 1050px;
                padding-top: 1.2rem;
                padding-bottom: 2rem;
            }
            [data-testid="stSidebar"] {
                background: #ffffff;
                border-right: 1px solid var(--tl-border);
            }
            .tl-shell {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 28px;
                box-shadow: var(--tl-card-shadow);
                padding: 24px 22px 18px;
                margin-bottom: 14px;
            }
            .tl-title {
                font-size: 2.2rem;
                font-weight: 900;
                line-height: 1;
                color: var(--tl-dark);
                margin: 12px 0 6px;
            }
            .tl-subtitle {
                color: var(--tl-muted);
                font-size: 1rem;
                margin: 0 0 14px;
            }
            .tl-chip {
                display: inline-block;
                background: #f2ffca;
                color: #1b2414;
                border: 1px solid #d9ef76;
                border-radius: 999px;
                padding: 8px 12px;
                font-size: .82rem;
                font-weight: 800;
                margin-right: 8px;
                margin-bottom: 8px;
            }
            .tl-card {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 24px;
                box-shadow: var(--tl-card-shadow);
                padding: 18px;
                margin-bottom: 14px;
            }
            .tl-section {
                font-size: 1.3rem;
                font-weight: 900;
                color: var(--tl-dark);
                margin-bottom: .15rem;
            }
            .tl-caption {
                color: var(--tl-muted);
                margin-bottom: .9rem;
            }
            .tl-soft {
                background: var(--tl-soft);
                border: 1px solid var(--tl-border);
                border-radius: 18px;
                padding: 14px;
                margin-bottom: 12px;
            }
            .tl-fin-card {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 24px;
                overflow: hidden;
                box-shadow: var(--tl-card-shadow);
                margin-bottom: 16px;
            }
            .tl-fin-header {
                background: linear-gradient(180deg, #CCFF00 0%, #B7E600 100%);
                color: #111111;
                text-align: center;
                padding: 18px 14px 16px;
                font-weight: 900;
                font-size: 1.08rem;
                line-height: 1.1;
            }
            .tl-fin-sub {
                display: block;
                font-size: .9rem;
                margin-top: 4px;
            }
            .tl-fin-body { padding: 14px 16px; }
            .tl-fin-highlight {
                display: inline-block;
                background: #f3ffcf;
                border: 1px solid #d9ec8b;
                border-radius: 999px;
                padding: 6px 10px;
                font-size: .75rem;
                font-weight: 800;
                margin-bottom: 10px;
            }
            .tl-fin-list { list-style: none; padding: 0; margin: 0; }
            .tl-fin-list li {
                display: flex;
                justify-content: space-between;
                gap: 10px;
                border-bottom: 1px solid #eef4dd;
                padding: 10px 0;
                font-size: .98rem;
            }
            .tl-fin-list li:last-child { border-bottom: 0; }
            .tl-fin-foot {
                background: var(--tl-soft);
                border-top: 1px solid var(--tl-border);
                padding: 12px 14px;
                font-size: .92rem;
                font-weight: 700;
                text-align: center;
                color: #1f2b17;
            }
            .stButton > button,
            .stDownloadButton > button {
                background: linear-gradient(180deg, #CCFF00 0%, #B7E600 100%);
                color: #111111;
                border: 0;
                border-radius: 14px;
                font-weight: 900;
                min-height: 46px;
            }
            .stButton > button:hover,
            .stDownloadButton > button:hover {
                background: linear-gradient(180deg, #C4F500 0%, #AEDD00 100%);
                color: #111111;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
            }
            .stTabs [data-baseweb="tab"] {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 16px;
                padding: 10px 16px;
                font-weight: 800;
            }
            .stTabs [aria-selected="true"] {
                background: #f4ffda !important;
                border-color: #d4ea78 !important;
                color: #111111 !important;
            }
            .tl-event-card {
                background: #ffffff;
                border: 1px solid var(--tl-border);
                border-radius: 20px;
                padding: 16px;
                box-shadow: var(--tl-card-shadow);
                margin-bottom: 12px;
            }
            .tl-event-title {
                font-size: 1.05rem;
                font-weight: 900;
                margin-bottom: 6px;
            }
            .tl-admin-divider { margin: 22px 0 12px; }
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
        st.image(logo, width=150)
    st.markdown(f'<div class="tl-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="tl-subtitle">Confirmação de aulas, inscrições em torneios, eventos e financeiro em um só lugar.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="tl-chip">Check-in de aulas</span>'
        '<span class="tl-chip">Inscrição em torneios</span>'
        '<span class="tl-chip">Financeiro</span>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


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
def fetch_events(limit: int = 100) -> list[dict[str, Any]]:
    return db().request(
        "GET",
        "eventos",
        params={
            "select": "id,titulo,data_evento,local,descricao,ativo,ordem,valor_inscricao,created_at",
            "ativo": "eq.true",
            "order": "data_evento.asc,ordem.asc",
            "limit": str(limit),
        },
    ) or []


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
            "select": "id,evento_id,evento_titulo,nome,whatsapp,categoria,status_inscricao,valor,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    ) or []


def clear_caches() -> None:
    healthcheck.clear()
    fetch_students.clear()
    fetch_events.clear()
    fetch_confirmations.clear()
    fetch_registrations.clear()


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


def insert_event(payload: dict[str, Any]) -> None:
    db().request("POST", "eventos", json_body=payload, prefer="return=representation")
    fetch_events.clear()


def insert_confirmation(payload: dict[str, Any]) -> None:
    db().request("POST", "confirmacoes", json_body=payload, prefer="return=representation")
    fetch_confirmations.clear()


def insert_registration(payload: dict[str, Any]) -> None:
    db().request("POST", "inscricoes_eventos", json_body=payload, prefer="return=representation")
    fetch_registrations.clear()


def update_registration_status(registration_id: str, new_status: str) -> None:
    db().request(
        "PATCH",
        "inscricoes_eventos",
        params={"id": f"eq.{registration_id}"},
        json_body={"status_inscricao": new_status},
        prefer="return=representation",
    )
    fetch_registrations.clear()


def render_student_checkin() -> None:
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Check-in da Aula</div>', unsafe_allow_html=True)
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
            except AppError as exc:
                st.error(str(exc))
                aluno = None

            if not aluno:
                st.error("Aluno não localizado. Fale com a secretaria para cadastro ou atualização de dados.")
                st.info(f"Secretaria: {secretaria_nome} | WhatsApp: {secretaria_whatsapp}")
            else:
                status = str(aluno.get("status_pagamento") or "").strip().lower()
                if status != "em_dia":
                    st.error("Seu check-in está bloqueado por pendência financeira. Regularize com a secretaria da Tênis Linhares.")
                    st.info(f"Secretaria: {secretaria_nome} | WhatsApp: {secretaria_whatsapp}")
                else:
                    try:
                        if confirmation_exists(aluno.get("whatsapp") or whatsapp, data_aula.isoformat(), horario):
                            st.warning("Você já confirmou esse horário nesta data.")
                        else:
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
    st.markdown('<p class="tl-caption">Veja os eventos disponíveis e faça sua inscrição. O pagamento da inscrição é manual por PIX.</p>', unsafe_allow_html=True)

    try:
        events = fetch_events()
    except AppError as exc:
        st.error(str(exc))
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not events:
        st.info("Nenhum evento publicado no momento.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    for event in events:
        valor = event.get("valor_inscricao")
        valor_txt = f"R$ {float(valor):.2f}".replace(".", ",") if valor not in (None, "", 0, 0.0) else "A confirmar"
        st.markdown('<div class="tl-event-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="tl-event-title">{event.get("titulo", "Evento")}</div>', unsafe_allow_html=True)
        st.caption(f"{format_date_br(event.get('data_evento'))} • {event.get('local') or 'Tênis Linhares'} • Inscrição: {valor_txt}")
        if event.get("descricao"):
            st.write(event.get("descricao"))
        st.markdown('</div>', unsafe_allow_html=True)

    with st.form("form_event_registration"):
        options = {f"{e.get('titulo')} - {format_date_br(e.get('data_evento'))}": e for e in events}
        evento_label = st.selectbox("Escolha o torneio/evento", list(options.keys()))
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome para inscrição")
        whatsapp = c2.text_input("WhatsApp para inscrição")
        categoria = st.text_input("Categoria")
        submit_registration = st.form_submit_button("Confirmar inscrição", use_container_width=True)

    if submit_registration:
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
                            "status_inscricao": "aguardando_pagamento",
                            "valor": evento.get("valor_inscricao") or None,
                        }
                    )
                    st.success("Inscrição registrada com sucesso.")
                    st.info(
                        f"Pagamento manual por PIX. Chave e-mail: {pix_email} | Chave telefone: {pix_phone}. Depois envie o comprovante para {secretaria_nome} - {secretaria_whatsapp}."
                    )
            except AppError as exc:
                st.error(str(exc))

    st.markdown('</div>', unsafe_allow_html=True)


def render_finance_cards() -> None:
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Financeiro</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Confira os planos e realize o pagamento por PIX.</p>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    cols = [col_left, col_right]

    for idx, card in enumerate(FINANCE_CARDS):
        items_html = "".join([f"<li><span>{a}</span><strong>{b}</strong></li>" for a, b in card["items"]])
        subtitle = f'<span class="tl-fin-sub">{card["subtitle"]}</span>' if card["subtitle"] else ""
        highlight = f'<div class="tl-fin-highlight">{card["highlight"]}</div>' if card.get("highlight") else ""
        card_html = f"""
            <div class="tl-fin-card">
                <div class="tl-fin-header">{card['title']}{subtitle}</div>
                <div class="tl-fin-body">
                    {highlight}
                    <ul class="tl-fin-list">{items_html}</ul>
                </div>
                <div class="tl-fin-foot">{card['footer']}</div>
            </div>
        """
        with cols[idx % 2]:
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown('<div class="tl-soft">', unsafe_allow_html=True)
    st.markdown("**Pagamento por PIX**")
    c1, c2 = st.columns(2)
    c1.text_input("Chave PIX por e-mail", value=pix_email, disabled=True)
    c2.text_input("Chave PIX por telefone", value=pix_phone, disabled=True)
    st.caption(f"Após o pagamento, envie o comprovante para {secretaria_nome} - {secretaria_whatsapp}.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


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
        else:
            st.session_state.admin_ok = False
            st.sidebar.error("Senha incorreta.")
    if c2.button("Sair", use_container_width=True):
        st.session_state.admin_ok = False
        st.session_state.admin_password_input = ""

    if st.session_state.admin_ok:
        st.sidebar.success("Modo admin liberado.")

    return bool(st.session_state.admin_ok)


def render_admin_panel() -> None:
    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Painel administrativo</div>', unsafe_allow_html=True)
    st.markdown('<p class="tl-caption">Cadastre alunos, publique eventos e acompanhe confirmações e inscrições.</p>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Alunos", "Eventos", "Inscrições", "Confirmações"])

    with tab1:
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
            data = fetch_students()
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum aluno cadastrado ainda.")
        except AppError as exc:
            st.error(str(exc))

    with tab2:
        with st.form("form_evento", clear_on_submit=True):
            titulo = st.text_input("Título do evento")
            c1, c2 = st.columns(2)
            data_evento = c1.date_input("Data do evento", value=date.today() + timedelta(days=15))
            local = c2.text_input("Local", value="Tênis Linhares")
            descricao = st.text_area("Descrição")
            c3, c4 = st.columns(2)
            ordem = c3.number_input("Ordem", min_value=1, value=1, step=1)
            valor_inscricao = c4.number_input("Valor da inscrição", min_value=0.0, value=0.0, step=10.0)
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
                                "ativo": True,
                                "ordem": int(ordem),
                                "valor_inscricao": float(valor_inscricao),
                            }
                        )
                        st.success("Evento cadastrado com sucesso.")
                    except AppError as exc:
                        st.error(str(exc))
        try:
            data = fetch_events()
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum evento cadastrado ainda.")
        except AppError as exc:
            st.error(str(exc))

    with tab3:
        try:
            regs = fetch_registrations()
            if regs:
                df = pd.DataFrame(regs)
                st.dataframe(df, use_container_width=True, hide_index=True)
                with st.form("form_status_inscricao"):
                    reg_id = st.text_input("ID da inscrição para atualizar")
                    novo_status = st.selectbox("Novo status", ["aguardando_pagamento", "pago", "cancelada"])
                    submit = st.form_submit_button("Atualizar status", use_container_width=True)
                    if submit:
                        if not reg_id.strip():
                            st.error("Informe o ID da inscrição.")
                        else:
                            try:
                                update_registration_status(reg_id.strip(), novo_status)
                                st.success("Status atualizado com sucesso.")
                            except AppError as exc:
                                st.error(str(exc))
            else:
                st.info("Nenhuma inscrição registrada ainda.")
        except AppError as exc:
            st.error(str(exc))

    with tab4:
        try:
            data = fetch_confirmations()
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Baixar confirmações CSV",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"confirmacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.info("Nenhuma confirmação registrada ainda.")
        except AppError as exc:
            st.error(str(exc))

    st.markdown('</div>', unsafe_allow_html=True)


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
