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
import streamlit.components.v1 as components

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
    "PIX_NAME": "Tênis Linhares",
    "SECRETARIA_NOME": "Andrea Nascimento",
    "SECRETARIA_WHATSAPP": "+55 27 99997-0109",
    "ADMIN_PASSWORD": "Linhares@2026Admin",
}

FINANCE_CARDS = [
    {
        "title": "Aulas Semanais",
        "subtitle": "Grupo",
        "highlight": "Plano ideal: 3x por semana",
        "items": [
            ("1 vez por semana", "R$ 313,20"),
            ("2x por semana", "R$ 452,40"),
            ("3 vezes por semana", "R$ 545,20"),
            ("4 vezes por semana", "R$ 893,20"),
        ],
        "footer": "Turmas organizadas por nível técnico.",
    },
    {
        "title": "Plano Individual",
        "subtitle": "",
        "highlight": "Treinamento personalizado",
        "items": [
            ("1 vez por semana", "R$ 580,00"),
            ("2x por semana", "R$ 1.160,00"),
            ("3 vezes por semana", "R$ 1.740,00"),
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

TOURNAMENT_CATEGORIES = [
    "1ª classe Masculina",
    "2ª classe Masculina",
    "3ª classe Masculina",
    "4ª classe Masculina",
    "5ª classe Masculina",
    "Iniciantes",
    "1ª classe Feminina",
    "2ª classe Feminina",
    "3ª classe Feminina",
    "4ª classe Feminina",
    "1ª classe Duplas",
    "2ª classe Duplas",
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
    key: str


class SupabaseREST:
    def __init__(self, config: SupabaseConfig) -> None:
        self.config = config

    def _headers(self, prefer: Optional[str] = None) -> dict[str, str]:
        headers = {
            "apikey": self.config.key,
            "Authorization": f"Bearer {self.config.key}",
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
                timeout=25,
            )
        except requests.RequestException as exc:
            raise AppError("Falha de conexão com o banco de dados. Tente novamente.") from exc

        if response.status_code >= 400:
            raise AppError(self._read_error(response))

        if not response.text.strip():
            return None
        try:
            return response.json()
        except Exception:
            return response.text

    @staticmethod
    def _read_error(response: requests.Response) -> str:
        text = ""
        try:
            data = response.json()
            if isinstance(data, dict):
                text = str(
                    data.get("message")
                    or data.get("details")
                    or data.get("hint")
                    or ""
                )
        except Exception:
            text = response.text.strip()

        lower = text.lower()
        if "duplicate key" in lower or "already exists" in lower:
            return "Esse registro já existe. Verifique se a confirmação ou inscrição já foi feita."
        if "does not exist" in lower and "column" in lower:
            return "O banco está desatualizado. Rode o schema.sql mais novo no Supabase."
        if "foreign key" in lower:
            return "Registro relacionado não foi encontrado no banco."
        return text or "Erro ao comunicar com o banco de dados."


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
    return SupabaseConfig(url=url.rstrip("/"), key=key)


@st.cache_resource(show_spinner=False)
def get_db() -> Optional[SupabaseREST]:
    cfg = get_config()
    return SupabaseREST(cfg) if cfg else None


def db() -> SupabaseREST:
    client = get_db()
    if client is None:
        raise AppError("Aplicativo em configuração. Verifique os Secrets do Streamlit.")
    return client


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def weekday_label(value: date) -> str:
    return WEEKDAY_LABELS[value.weekday()]


def next_class_day() -> date:
    d = date.today()
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def lesson_location(value: date) -> str:
    if value.weekday() in (0, 2, 4):
        return "Clube Mata do Lago"
    if value.weekday() in (1, 3):
        return "Condomínio Unique"
    return "Sem aula presencial"


def lesson_slots(value: date) -> list[str]:
    if value.weekday() in (0, 2, 4):
        return [
            "06:00 às 07:00",
            "07:00 às 08:00",
            "08:00 às 09:00",
            "09:00 às 10:00",
        ]
    if value.weekday() in (1, 3):
        return [
            "15:00 às 16:00",
            "16:00 às 17:00",
            "17:00 às 18:00",
            "18:00 às 19:00",
            "19:00 às 20:00",
            "20:00 às 21:00",
        ]
    return []


def br_date(value: Any) -> str:
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


def logo_path() -> Optional[str]:
    for path in LOGO_PATHS:
        if path.exists():
            return str(path)
    return None


def flash_message(kind: str, text: str) -> None:
    st.session_state["tl_flash"] = {"kind": kind, "text": text}


def show_flash() -> None:
    msg = st.session_state.pop("tl_flash", None)
    if not msg:
        return
    md_box(msg["kind"], msg["text"])


def md_box(kind: str, text: str) -> None:
    cls = {
        "ok": "tl-alert-ok",
        "warn": "tl-alert-warn",
        "error": "tl-alert-error",
    }.get(kind, "tl-alert-warn")
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root{
            --tl-green:#CCFF00;
            --tl-green-dark:#B5E000;
            --tl-green-soft:#F5FFD6;
            --tl-green-soft-2:#ECFFD1;
            --tl-border:#D2ED77;
            --tl-dark:#101010;
            --tl-muted:#5A664F;
        }
        .stApp{
            background:
                radial-gradient(circle at top left, rgba(204,255,0,.18), transparent 28%),
                radial-gradient(circle at top right, rgba(204,255,0,.10), transparent 24%),
                linear-gradient(180deg,#ffffff 0%, #fbfff2 100%);
            color:var(--tl-dark);
        }
        .main .block-container{
            max-width:1100px;
            padding-top:1rem;
            padding-bottom:2.25rem;
        }
        [data-testid="stSidebar"]{
            background:#ffffff;
            border-right:1px solid var(--tl-border);
        }
        .stButton > button, .stDownloadButton > button{
            background:linear-gradient(180deg,var(--tl-green),var(--tl-green-dark));
            color:#101010;
            border:1px solid #a8cf00;
            border-radius:16px;
            font-weight:900;
            min-height:46px;
            box-shadow:0 8px 18px rgba(16,16,16,.08);
        }
        .stButton > button:hover, .stDownloadButton > button:hover{
            background:linear-gradient(180deg,#D8FF3D,#B7E600);
            color:#101010;
            border-color:#9bc100;
        }
        .stTabs [data-baseweb="tab-list"]{
            gap:10px;
            border-bottom:1px solid #dbeaa8;
        }
        .stTabs [data-baseweb="tab"]{
            background:#ffffff;
            border:1px solid #d6e897;
            border-radius:18px 18px 0 0;
            padding:12px 18px;
            font-weight:900;
            color:#202020;
        }
        .stTabs [aria-selected="true"]{
            background:linear-gradient(180deg,var(--tl-green),var(--tl-green-dark)) !important;
            color:#101010 !important;
            border-color:#aacb00 !important;
        }
        div[data-testid="stForm"]{
            border:1px solid #d9ec95;
            border-radius:24px;
            padding:18px;
            background:#ffffff;
            box-shadow:0 10px 24px rgba(16,16,16,.05);
        }
        .stTextInput input, .stTextArea textarea, .stDateInput input, .stNumberInput input{
            background:#f8ffe9 !important;
            border:1px solid #dceb9f !important;
            border-radius:13px !important;
        }
        div[data-testid="stSelectbox"] > div{
            background:#f8ffe9 !important;
            border-radius:13px !important;
        }
        .tl-card{
            background:#ffffff;
            border:2px solid #d7ec90;
            border-radius:30px;
            padding:22px;
            box-shadow:0 12px 32px rgba(16,16,16,.07);
            margin-bottom:18px;
        }
        .tl-hero{
            text-align:center;
            background:linear-gradient(180deg,#ffffff 0%, #f5ffd6 100%);
            border:2px solid var(--tl-green);
            border-radius:34px;
            padding:26px 20px 22px;
            box-shadow:0 14px 32px rgba(16,16,16,.08);
            margin-bottom:18px;
        }
        .tl-logo{
            width:142px;
            height:142px;
            object-fit:contain;
            border-radius:34px;
            border:3px solid var(--tl-green);
            background:#fff;
            box-shadow:0 10px 22px rgba(0,0,0,.12);
            padding:8px;
        }
        .tl-title{
            font-size:2.55rem;
            line-height:1;
            font-weight:950;
            color:#101010;
            margin:14px 0 6px;
        }
        .tl-subtitle{
            font-size:1.05rem;
            color:var(--tl-muted);
            margin:0 0 16px;
        }
        .tl-pill-row{
            display:flex;
            justify-content:center;
            gap:10px;
            flex-wrap:wrap;
        }
        .tl-pill{
            background:linear-gradient(180deg,var(--tl-green),var(--tl-green-dark));
            color:#101010;
            border:1px solid #a8cf00;
            border-radius:999px;
            padding:10px 14px;
            font-weight:900;
            display:inline-block;
        }
        .tl-section{
            font-size:1.55rem;
            line-height:1.1;
            font-weight:950;
            color:#101010;
            margin-bottom:4px;
        }
        .tl-caption{
            color:var(--tl-muted);
            font-size:1rem;
            margin-bottom:14px;
        }
        .tl-checkin{
            background:linear-gradient(180deg,#ffffff 0%, #f4ffd2 100%);
            border:2px solid var(--tl-green);
        }
        .tl-admin{
            background:linear-gradient(180deg,#ffffff 0%, #f9ffeb 100%);
            border:2px solid var(--tl-green);
        }
        .tl-plan{
            border:1px solid #dbeaa8;
            border-radius:26px;
            overflow:hidden;
            background:#ffffff;
            box-shadow:0 10px 24px rgba(16,16,16,.05);
            margin-bottom:18px;
        }
        .tl-plan-head{
            background:linear-gradient(180deg,var(--tl-green),var(--tl-green-dark));
            color:#101010;
            font-weight:950;
            font-size:1.2rem;
            text-align:center;
            padding:18px 16px 16px;
        }
        .tl-plan-sub{
            display:block;
            font-size:.94rem;
            margin-top:4px;
        }
        .tl-plan-body{
            padding:18px;
        }
        .tl-tag{
            display:inline-block;
            background:#f3ffd1;
            border:1px solid #d5ec8f;
            border-radius:14px;
            padding:8px 11px;
            font-weight:850;
            margin-bottom:10px;
        }
        .tl-price-row{
            display:flex;
            justify-content:space-between;
            gap:14px;
            border-bottom:1px solid #edf5da;
            padding:10px 0;
        }
        .tl-price-row:last-child{
            border-bottom:none;
        }
        .tl-foot{
            background:#fbfff2;
            border-top:1px solid #edf5da;
            color:#415035;
            padding:13px 16px;
            font-weight:800;
        }
        .tl-pix-box{
            background:linear-gradient(180deg,#fbfff2 0%, #f1ffd0 100%);
            border:2px solid var(--tl-green);
            border-radius:22px;
            padding:16px;
            margin-top:16px;
        }
        .tl-green-label{
            color:#446100;
            font-weight:950;
        }
        .tl-alert-ok{
            background:#efffd4;
            border:1px solid #cfe96a;
            color:#2f4909;
            border-radius:18px;
            padding:14px;
            margin:10px 0;
            font-weight:850;
        }
        .tl-alert-warn{
            background:#fff4d9;
            border:1px solid #ffd26b;
            color:#5a3900;
            border-radius:18px;
            padding:14px;
            margin:10px 0;
            font-weight:850;
        }
        .tl-alert-error{
            background:#ffe7e7;
            border:1px solid #ffb7b7;
            color:#611313;
            border-radius:18px;
            padding:14px;
            margin:10px 0;
            font-weight:850;
        }
        .tl-group-title{
            margin-top:8px;
            margin-bottom:6px;
            color:#23330b;
            font-weight:950;
            font-size:1.15rem;
        }
        @media(max-width:720px){
            .tl-title{font-size:2rem;}
            .tl-logo{width:118px;height:118px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown('<div class="tl-hero">', unsafe_allow_html=True)
    logo = logo_path()
    if logo:
        st.image(logo, width=140)
    st.markdown(f'<div class="tl-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-subtitle">Confirmação de aulas, inscrições em torneios, eventos e financeiro em um só lugar.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tl-pill-row">'
        '<span class="tl-pill">Check-in de aulas</span>'
        '<span class="tl-pill">Inscrição em torneios</span>'
        '<span class="tl-pill">Financeiro com PIX</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


@st.cache_data(ttl=40, show_spinner=False)
def healthcheck() -> bool:
    db().request("GET", "alunos", params={"select": "id", "limit": "1"})
    return True


@st.cache_data(ttl=40, show_spinner=False)
def fetch_students(limit: int = 600) -> list[dict[str, Any]]:
    return db().request(
        "GET",
        "alunos",
        params={
            "select": "id,nome,whatsapp,status_pagamento,ativo,observacao,created_at",
            "order": "nome.asc",
            "limit": str(limit),
        },
    ) or []


@st.cache_data(ttl=40, show_spinner=False)
def fetch_events(limit: int = 200, admin: bool = False) -> list[dict[str, Any]]:
    params = {
        "select": "id,titulo,data_evento,local,descricao,valor_inscricao,ativo,inscricoes_abertas,ordem,created_at",
        "order": "data_evento.asc,ordem.asc",
        "limit": str(limit),
    }
    if not admin:
        params["ativo"] = "eq.true"
    return db().request("GET", "eventos", params=params) or []


@st.cache_data(ttl=20, show_spinner=False)
def fetch_confirmations(limit: int = 500) -> list[dict[str, Any]]:
    return db().request(
        "GET",
        "confirmacoes",
        params={
            "select": "id,nome,whatsapp,data_aula,dia_semana,local,horario,status_pagamento,created_at",
            "order": "data_aula.desc,horario.asc,created_at.desc",
            "limit": str(limit),
        },
    ) or []


@st.cache_data(ttl=20, show_spinner=False)
def fetch_registrations(limit: int = 500) -> list[dict[str, Any]]:
    return db().request(
        "GET",
        "inscricoes_eventos",
        params={
            "select": "id,evento_id,evento_titulo,nome,whatsapp,categoria,valor,status_inscricao,created_at",
            "order": "evento_titulo.asc,categoria.asc,created_at.desc",
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
    clean = nome.strip()
    if clean:
        rows = db().request(
            "GET",
            "alunos",
            params={
                "select": "id,nome,whatsapp,status_pagamento,ativo,observacao",
                "nome": f"ilike.*{clean}*",
                "ativo": "eq.true",
                "limit": "10",
            },
        ) or []
        if rows:
            return rows[0]
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
    db().request(
        "POST",
        "confirmacoes",
        json_body=payload,
        prefer="return=representation",
    )
    fetch_confirmations.clear()


def insert_registration(payload: dict[str, Any]) -> None:
    db().request(
        "POST",
        "inscricoes_eventos",
        json_body=payload,
        prefer="return=representation",
    )
    fetch_registrations.clear()


def insert_event(payload: dict[str, Any]) -> None:
    db().request(
        "POST",
        "eventos",
        json_body=payload,
        prefer="return=representation",
    )
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


def copy_button(label: str, value: str, key: str) -> None:
    safe_value = value.replace("\\", "\\\\").replace("'", "\\'")
    html = f"""
    <button onclick="navigator.clipboard.writeText('{safe_value}'); this.innerText='Copiado!';" style="
        background:linear-gradient(180deg,#CCFF00,#B5E000);
        border:1px solid #A9CC00;
        border-radius:14px;
        padding:10px 16px;
        font-weight:900;
        color:#101010;
        cursor:pointer;
        width:100%;
        font-family:Arial;
        box-shadow:0 6px 14px rgba(0,0,0,.08);
    ">{label}</button>
    """
    components.html(html, height=52, scrolling=False)


def render_student_checkin() -> None:
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card tl-checkin">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Check-in da aula</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Escolha seus dados, horário e confirme sua presença.</div>', unsafe_allow_html=True)
    show_flash()

    with st.form("form_checkin", clear_on_submit=True):
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
            md_box("error", "Preencha nome completo e WhatsApp.")
        elif data_aula.weekday() >= 5:
            md_box("warn", "As confirmações online ficam disponíveis de segunda a sexta.")
        elif not slots:
            md_box("warn", "Sem horário disponível para essa data.")
        else:
            try:
                aluno = find_student(nome, whatsapp)
                if not aluno:
                    md_box("error", f"Aluno não localizado. Fale com {secretaria_nome} pelo WhatsApp {secretaria_whatsapp}.")
                else:
                    status = str(aluno.get("status_pagamento") or "").strip().lower()
                    if status != "em_dia":
                        md_box("error", f"Seu check-in está bloqueado por pendência financeira. Regularize com {secretaria_nome}: {secretaria_whatsapp}.")
                    elif confirmation_exists(aluno.get("whatsapp") or whatsapp, data_aula.isoformat(), horario):
                        md_box("warn", "Você já confirmou esse horário nesta data.")
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
                        flash_message("ok", f"Presença confirmada com sucesso para {br_date(data_aula.isoformat())}, às {horario}, em {lesson_location(data_aula)}.")
                        st.rerun()
            except AppError as exc:
                md_box("error", f"Não foi possível confirmar agora. {str(exc)}")
            except Exception:
                md_box("error", "Não foi possível confirmar agora. Tente novamente em instantes.")
    st.markdown('</div>', unsafe_allow_html=True)


def render_student_events() -> None:
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    pix_name = secret_value("PIX_NAME", DEFAULTS["PIX_NAME"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Eventos e inscrições</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Veja os eventos disponíveis e faça sua inscrição. O pagamento é manual por PIX.</div>', unsafe_allow_html=True)
    show_flash()

    try:
        events = fetch_events(admin=False)
    except AppError as exc:
        md_box("error", str(exc))
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not events:
        st.info("Nenhum evento disponível no momento.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    for event in events:
        valor = float(event.get("valor_inscricao") or 0)
        st.markdown('<div class="tl-card" style="padding:18px; margin-bottom:14px;">', unsafe_allow_html=True)
        st.markdown(f"### {event.get('titulo') or 'Evento'}")
        st.caption(f"{br_date(event.get('data_evento'))} • {event.get('local') or 'Tênis Linhares'}")
        if event.get("descricao"):
            st.write(event.get("descricao"))
        st.write(f"**Valor da inscrição:** {money_br(valor) if valor > 0 else 'A confirmar'}")

        if event.get("inscricoes_abertas", True):
            with st.form(f"form_evento_{event.get('id')}", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome completo", key=f"ev_nome_{event.get('id')}")
                whatsapp = c2.text_input("WhatsApp", key=f"ev_zap_{event.get('id')}")
                categoria = st.selectbox("Categoria", TOURNAMENT_CATEGORIES, key=f"ev_cat_{event.get('id')}")
                submit = st.form_submit_button("Confirmar inscrição", use_container_width=True)
            if submit:
                if not nome.strip() or not whatsapp.strip():
                    md_box("error", "Preencha nome completo e WhatsApp.")
                else:
                    try:
                        if registration_exists(str(event.get("id")), whatsapp):
                            md_box("warn", "Esse WhatsApp já está inscrito neste evento.")
                        else:
                            insert_registration(
                                {
                                    "evento_id": event.get("id"),
                                    "evento_titulo": event.get("titulo") or "Evento",
                                    "nome": nome.strip(),
                                    "whatsapp": normalize_phone(whatsapp),
                                    "categoria": categoria,
                                    "valor": valor,
                                    "status_inscricao": "aguardando_pagamento",
                                }
                            )
                            flash_message(
                                "ok",
                                f"Inscrição registrada com sucesso em {event.get('titulo')}. Faça o PIX e envie o comprovante para {secretaria_nome}: {secretaria_whatsapp}.",
                            )
                            st.rerun()
                    except AppError as exc:
                        md_box("error", f"Não foi possível registrar a inscrição. {str(exc)}")
                    except Exception:
                        md_box("error", "Não foi possível registrar a inscrição agora.")
        else:
            md_box("warn", "Inscrições encerradas para este evento.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tl-pix-box">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section" style="font-size:1.25rem;">PIX para inscrições</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="tl-green-label">Favorecido: {pix_name}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Chave PIX por e-mail", value=pix_email, disabled=True)
        copy_button("Copiar e-mail PIX", pix_email, "copy_event_email")
    with c2:
        st.text_input("Chave PIX por telefone", value=pix_phone, disabled=True)
        copy_button("Copiar telefone PIX", pix_phone, "copy_event_phone")
    st.caption(f"Após o pagamento, envie o comprovante para {secretaria_nome}: {secretaria_whatsapp}.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_finance() -> None:
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    pix_name = secret_value("PIX_NAME", DEFAULTS["PIX_NAME"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Financeiro</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Confira os planos e realize o pagamento por PIX.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for idx, card in enumerate(FINANCE_CARDS):
        with (col1 if idx % 2 == 0 else col2):
            st.markdown('<div class="tl-plan">', unsafe_allow_html=True)
            subtitle = f'<span class="tl-plan-sub">{card["subtitle"]}</span>' if card.get("subtitle") else ""
            st.markdown(f'<div class="tl-plan-head">{card["title"]}{subtitle}</div>', unsafe_allow_html=True)
            st.markdown('<div class="tl-plan-body">', unsafe_allow_html=True)
            st.markdown(f'<div class="tl-tag">{card["highlight"]}</div>', unsafe_allow_html=True)
            for label, value in card["items"]:
                st.markdown(f'<div class="tl-price-row"><span>{label}</span><strong>{value}</strong></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="tl-foot">{card["footer"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tl-pix-box">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section" style="font-size:1.25rem;">Pagamento por PIX</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="tl-green-label">Favorecido: {pix_name}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Chave PIX por e-mail", value=pix_email, disabled=True)
        copy_button("Copiar e-mail PIX", pix_email, "copy_fin_email")
    with c2:
        st.text_input("Chave PIX por telefone", value=pix_phone, disabled=True)
        copy_button("Copiar telefone PIX", pix_phone, "copy_fin_phone")
    st.caption(f"Após o pagamento, envie o comprovante para {secretaria_nome}: {secretaria_whatsapp}.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_admin_sidebar() -> bool:
    st.sidebar.markdown("### Administração")
    st.sidebar.caption("Área restrita da Tênis Linhares.")
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    password = secret_value("ADMIN_PASSWORD", DEFAULTS["ADMIN_PASSWORD"])
    entered = st.sidebar.text_input("Senha admin", type="password")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("Entrar", use_container_width=True):
        st.session_state.admin_ok = entered == password
        if not st.session_state.admin_ok:
            st.sidebar.error("Senha incorreta.")
    if c2.button("Sair", use_container_width=True):
        st.session_state.admin_ok = False
    if st.session_state.admin_ok:
        st.sidebar.success("Admin liberado.")
    return bool(st.session_state.admin_ok)


def safe_dataframe(rows: list[dict[str, Any]], empty_msg: str) -> None:
    if not rows:
        st.info(empty_msg)
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def admin_students() -> None:
    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.subheader("Cadastrar ou atualizar aluno")
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
            md_box("error", "Preencha nome e WhatsApp.")
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
                md_box("ok", "Aluno salvo com sucesso.")
            except AppError as exc:
                md_box("error", str(exc))
            except Exception:
                md_box("error", "Não foi possível salvar o aluno.")
    try:
        rows = fetch_students()
        if rows:
            df = pd.DataFrame(rows)
            df = df.rename(
                columns={
                    "nome": "Nome",
                    "whatsapp": "WhatsApp",
                    "status_pagamento": "Pagamento",
                    "ativo": "Ativo",
                    "observacao": "Observação",
                    "created_at": "Criado em",
                }
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum aluno cadastrado ainda.")
    except AppError as exc:
        md_box("error", str(exc))
    st.markdown('</div>', unsafe_allow_html=True)


def admin_events() -> None:
    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.subheader("Novo evento")
    with st.form("form_evento", clear_on_submit=True):
        titulo = st.text_input("Título do evento")
        c1, c2 = st.columns(2)
        data_evento = c1.date_input("Data do evento", value=date.today())
        local = c2.text_input("Local", value="Tênis Linhares")
        descricao = st.text_area("Descrição")
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor da inscrição", min_value=0.0, value=0.0, step=10.0, format="%.2f")
        ordem = c4.number_input("Ordem", min_value=1, value=1, step=1)
        abertas = st.selectbox("Inscrições abertas?", ["sim", "não"])
        submit = st.form_submit_button("Adicionar evento", use_container_width=True)
    if submit:
        if not titulo.strip():
            md_box("error", "Informe o título do evento.")
        else:
            try:
                insert_event(
                    {
                        "titulo": titulo.strip(),
                        "data_evento": data_evento.isoformat(),
                        "local": local.strip() or None,
                        "descricao": descricao.strip() or None,
                        "valor_inscricao": float(valor),
                        "ordem": int(ordem),
                        "ativo": True,
                        "inscricoes_abertas": abertas == "sim",
                    }
                )
                md_box("ok", "Evento adicionado com sucesso.")
            except AppError as exc:
                md_box("error", str(exc))
            except Exception:
                md_box("error", "Não foi possível adicionar o evento.")
    st.markdown('</div>', unsafe_allow_html=True)

    try:
        events = fetch_events(admin=True)
    except AppError as exc:
        md_box("error", str(exc))
        return

    if not events:
        st.info("Nenhum evento cadastrado ainda.")
        return

    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.subheader("Editar evento existente")
    labels = {f"{br_date(e.get('data_evento'))} | {e.get('titulo')}": e for e in events}
    chosen = st.selectbox("Escolha o evento", list(labels.keys()))
    current = labels[chosen]
    with st.form("form_editar_evento"):
        titulo = st.text_input("Título", value=current.get("titulo") or "")
        try:
            data_default = datetime.strptime(str(current.get("data_evento")), "%Y-%m-%d").date()
        except Exception:
            data_default = date.today()
        c1, c2 = st.columns(2)
        data_evento = c1.date_input("Data", value=data_default)
        local = c2.text_input("Local", value=current.get("local") or "")
        descricao = st.text_area("Descrição", value=current.get("descricao") or "")
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor", min_value=0.0, value=float(current.get("valor_inscricao") or 0), step=10.0, format="%.2f")
        ordem = c4.number_input("Ordem", min_value=1, value=int(current.get("ordem") or 1), step=1)
        c5, c6 = st.columns(2)
        ativo = c5.selectbox("Visível no site?", ["sim", "não"], index=0 if current.get("ativo", True) else 1)
        abertas = c6.selectbox("Inscrições abertas?", ["sim", "não"], index=0 if current.get("inscricoes_abertas", True) else 1)
        submit = st.form_submit_button("Salvar alterações", use_container_width=True)
    if submit:
        try:
            update_event(
                str(current.get("id")),
                {
                    "titulo": titulo.strip(),
                    "data_evento": data_evento.isoformat(),
                    "local": local.strip() or None,
                    "descricao": descricao.strip() or None,
                    "valor_inscricao": float(valor),
                    "ordem": int(ordem),
                    "ativo": ativo == "sim",
                    "inscricoes_abertas": abertas == "sim",
                },
            )
            md_box("ok", "Evento atualizado com sucesso.")
            st.rerun()
        except AppError as exc:
            md_box("error", str(exc))
        except Exception:
            md_box("error", "Não foi possível atualizar o evento.")

    df = pd.DataFrame(events).rename(
        columns={
            "titulo": "Título",
            "data_evento": "Data",
            "local": "Local",
            "descricao": "Descrição",
            "valor_inscricao": "Valor",
            "ativo": "Ativo",
            "inscricoes_abertas": "Inscrições abertas",
            "ordem": "Ordem",
        }
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)


def admin_registrations() -> None:
    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.subheader("Inscrições organizadas")
    try:
        rows = fetch_registrations()
    except AppError as exc:
        md_box("error", str(exc))
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not rows:
        st.info("Nenhuma inscrição registrada ainda.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    df = pd.DataFrame(rows)
    df["valor"] = df["valor"].apply(money_br)
    st.download_button(
        "Baixar inscrições CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"inscricoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    for evento, evento_df in df.sort_values(["evento_titulo", "categoria", "nome"]).groupby("evento_titulo"):
        st.markdown(f'<div class="tl-group-title">{evento}</div>', unsafe_allow_html=True)
        for categoria, cat_df in evento_df.groupby("categoria"):
            st.markdown(f"**{categoria}**")
            view = cat_df[
                ["nome", "whatsapp", "categoria", "valor", "status_inscricao", "created_at"]
            ].rename(
                columns={
                    "nome": "Nome",
                    "whatsapp": "WhatsApp",
                    "categoria": "Categoria",
                    "valor": "Valor",
                    "status_inscricao": "Status",
                    "created_at": "Criado em",
                }
            )
            st.dataframe(view, use_container_width=True, hide_index=True)

    labels = {f"{r.get('nome')} | {r.get('evento_titulo')} | {r.get('categoria')}": r for r in rows}
    with st.form("form_status_inscricao"):
        chosen = st.selectbox("Atualizar status de inscrição", list(labels.keys()))
        status = st.selectbox("Novo status", ["aguardando_pagamento", "pago", "cancelada"])
        submit = st.form_submit_button("Atualizar status", use_container_width=True)
    if submit:
        try:
            update_registration_status(str(labels[chosen].get("id")), status)
            md_box("ok", "Status da inscrição atualizado com sucesso.")
            st.rerun()
        except AppError as exc:
            md_box("error", str(exc))
        except Exception:
            md_box("error", "Não foi possível atualizar o status.")
    st.markdown('</div>', unsafe_allow_html=True)


def admin_confirmations() -> None:
    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.subheader("Confirmações organizadas")
    try:
        rows = fetch_confirmations()
    except AppError as exc:
        md_box("error", str(exc))
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not rows:
        st.info("Nenhuma confirmação registrada ainda.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    df = pd.DataFrame(rows)
    st.download_button(
        "Baixar confirmações CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"confirmacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    grouped = df.sort_values(["data_aula", "horario", "nome"], ascending=[False, True, True]).groupby(["data_aula", "horario"])
    for (data_aula, horario), group in grouped:
        st.markdown(f'<div class="tl-group-title">{br_date(data_aula)} • {horario}</div>', unsafe_allow_html=True)
        view = group[
            ["nome", "whatsapp", "local", "status_pagamento", "created_at"]
        ].rename(
            columns={
                "nome": "Nome",
                "whatsapp": "WhatsApp",
                "local": "Local",
                "status_pagamento": "Pagamento",
                "created_at": "Criado em",
            }
        )
        st.dataframe(view, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_admin_panel() -> None:
    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Painel administrativo</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Cadastre alunos, controle eventos, inscrições e confirmações.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Alunos", "Eventos", "Inscrições", "Confirmações"])
    with tab1:
        admin_students()
    with tab2:
        admin_events()
    with tab3:
        admin_registrations()
    with tab4:
        admin_confirmations()


def render_setup() -> None:
    md_box("warn", "Aplicativo em configuração. Verifique os Secrets do Streamlit e rode o schema.sql mais novo no Supabase.")


def main() -> None:
    inject_css()
    admin_ok = render_admin_sidebar()
    render_header()

    if get_config() is None:
        render_setup()
        return

    try:
        healthcheck()
    except AppError as exc:
        md_box("error", str(exc))
        return
    except Exception:
        md_box("error", "Não foi possível validar o banco de dados. Rode o schema.sql mais novo no Supabase.")
        return

    tab1, tab2, tab3 = st.tabs(["Check-in das aulas", "Eventos", "Financeiro"])
    with tab1:
        render_student_checkin()
    with tab2:
        render_student_events()
    with tab3:
        render_finance()

    if admin_ok:
        render_admin_panel()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        inject_css()
        md_box("error", "Ocorreu um erro inesperado. Atualize a página e, se persistir, faça reboot do app e rode o schema.sql mais novo no Supabase.")
