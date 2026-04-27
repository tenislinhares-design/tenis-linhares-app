
from __future__ import annotations

import os
import re
import json
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
    BASE_DIR / "logo.jpeg",
    BASE_DIR / "logo.jpg",
    BASE_DIR / "logo.png",
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
    "ADMIN_PASSWORD": "tenislinhares123@@",
}

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
CATEGORY_ORDER = {name: idx for idx, name in enumerate(TOURNAMENT_CATEGORIES)}

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
                text = str(data.get("message") or data.get("details") or data.get("hint") or "")
        except Exception:
            text = response.text.strip()

        lower = text.lower()
        if "duplicate key" in lower or "already exists" in lower:
            return "Esse registro já existe. Verifique se a confirmação ou inscrição já foi feita."
        if "column" in lower and "does not exist" in lower:
            return "O banco está desatualizado. Rode o schema.sql mais novo no Supabase."
        if "relation" in lower and "does not exist" in lower:
            return "Falta tabela no banco. Rode o schema.sql mais novo no Supabase."
        if "foreign key" in lower:
            return "Registro relacionado não foi encontrado no banco."
        if "violates check constraint" in lower:
            return "Algum dado enviado não está no formato esperado."
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

def weekday_index(value) -> int:
    """Retorna o dia da semana com segurança. Segunda=0, terça=1, ... domingo=6."""
    if isinstance(value, datetime):
        return value.date().weekday()
    if isinstance(value, date):
        return value.weekday()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date().weekday()
            except ValueError:
                pass
    return date.today().weekday()

def lesson_location(value: date) -> str:
    # Regra oficial Tênis Linhares:
    # segunda, quarta e sexta = Clube Mata do Lago
    # terça e quinta = Condomínios
    wd = weekday_index(value)
    if wd in (0, 2, 4):
        return "Clube Mata do Lago"
    if wd in (1, 3):
        return "Condomínios"
    return "Sem aula presencial"

def lesson_slots(value: date) -> list[str]:
    if weekday_index(value) >= 5:
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

def br_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
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

def pop_flash() -> Optional[dict[str, str]]:
    return st.session_state.pop("tl_flash", None)

def md_box(kind: str, text: str) -> None:
    cls = {"ok": "tl-alert-ok", "warn": "tl-alert-warn", "error": "tl-alert-error"}.get(kind, "tl-alert-warn")
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)

def show_flash() -> None:
    msg = pop_flash()
    if msg:
        md_box(msg["kind"], msg["text"])

def copy_button(label: str, value: str, key: str) -> None:
    """Botão de copiar com fallback seguro para não quebrar a tela."""
    value = str(value or "").strip()
    if not value:
        st.caption("Chave PIX não configurada.")
        return
    try:
        payload = json.dumps(value)
        label_js = json.dumps(label)
        copied_js = json.dumps("Copiado!")
        html = f"""
        <html>
          <body style="margin:0;padding:0;background:transparent;">
            <button id="{key}" onclick='navigator.clipboard.writeText({payload}).then(function(){{
                var btn=document.getElementById("{key}");
                btn.innerText={copied_js};
                setTimeout(function(){{btn.innerText={label_js};}}, 1300);
            }}).catch(function(){{
                var btn=document.getElementById("{key}");
                btn.innerText="Copie manualmente";
                setTimeout(function(){{btn.innerText={label_js};}}, 1500);
            }});'
            style="width:100%;height:44px;border-radius:14px;border:1px solid #8DB600;
                   background:linear-gradient(180deg,#CCFF00,#B5E000);font-weight:950;color:#101010;cursor:pointer;">
              {label}
            </button>
          </body>
        </html>
        """
        components.html(html, height=56, scrolling=False)
    except Exception:
        st.code(value, language=None)
        st.caption("Copie a chave PIX acima.")

def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root{
            --tl-green:#CCFF00;
            --tl-green-dark:#B5E000;
            --tl-green-soft:#F5FFD6;
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
            color:#101010 !important;
            border:1px solid #a8cf00;
            border-radius:999px;
            padding:10px 16px;
            font-weight:900;
            display:inline-block;
            text-decoration:none !important;
            white-space:nowrap;
        }
        .tl-pill:hover{ filter:brightness(.98); transform:translateY(-1px); }
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
            border:2px solid #dbeaa8;
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
        .tl-price-row:last-child{ border-bottom:none; }
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
        .tl-green-label{ color:#446100; font-weight:950; }
        .tl-alert-ok,.tl-alert-warn,.tl-alert-error{
            border-radius:18px; padding:14px; margin:10px 0; font-weight:850;
        }
        .tl-alert-ok{ background:#efffd4; border:1px solid #cfe96a; color:#2f4909; }
        .tl-alert-warn{ background:#fff4d9; border:1px solid #ffd26b; color:#5a3900; }
        .tl-alert-error{ background:#ffe7e7; border:1px solid #ffb7b7; color:#611313; }
        .tl-group-title{
            margin-top:8px; margin-bottom:6px; color:#23330b; font-weight:950; font-size:1.15rem;
        }
        .tl-admin-login{
            background:#ffffff; border:2px dashed #d4eb83; border-radius:24px; padding:18px; margin-bottom:18px;
        }
        /* Correção responsiva para iPhone, Android e navegador interno do WhatsApp */
        html, body, .stApp, [data-testid="stAppViewContainer"]{
            -webkit-text-size-adjust:100%;
            overflow-x:hidden !important;
        }
        .stTextInput label, .stTextArea label, .stDateInput label,
        .stNumberInput label, .stSelectbox label{
            color:#101010 !important;
            opacity:1 !important;
            font-weight:850 !important;
        }
        .stTextInput input, .stTextArea textarea, .stDateInput input, .stNumberInput input{
            color:#101010 !important;
            -webkit-text-fill-color:#101010 !important;
            caret-color:#101010 !important;
            box-shadow:none !important;
            outline:none !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus, .stNumberInput input:focus{
            border:2px solid #9FCA00 !important;
            box-shadow:0 0 0 3px rgba(204,255,0,.25) !important;
        }
        div[data-testid="stSelectbox"] > div{
            color:#101010 !important;
            box-shadow:none !important;
            outline:none !important;
        }

        button[data-testid="collapsedControl"]{
            position:fixed !important;
            top:12px !important;
            left:12px !important;
            z-index:999999 !important;
            width:56px !important;
            height:56px !important;
            border-radius:999px !important;
            border:2px solid #a8cf00 !important;
            background:linear-gradient(180deg,var(--tl-green),var(--tl-green-dark)) !important;
            box-shadow:0 10px 24px rgba(16,16,16,.18) !important;
            color:#101010 !important;
        }
        button[data-testid="collapsedControl"] svg{
            width:1.4rem !important;
            height:1.4rem !important;
        }
        @media(max-width:720px){
            .main .block-container{
                max-width:100% !important;
                padding-left:1rem !important;
                padding-right:1rem !important;
                padding-top:.75rem !important;
                padding-bottom:2rem !important;
            }
            [data-testid="stHorizontalBlock"]{
                flex-wrap:wrap !important;
                gap:.25rem !important;
            }
            [data-testid="stHorizontalBlock"] > div{
                min-width:100% !important;
                flex:1 1 100% !important;
            }
            .tl-hero{
                padding:18px 12px 16px !important;
                border-radius:24px !important;
                margin-left:0 !important;
                margin-right:0 !important;
            }
            .tl-title{
                font-size:2rem !important;
                line-height:1.05 !important;
            }
            .tl-subtitle{
                font-size:1rem !important;
                line-height:1.35 !important;
            }
            .tl-pill-row{
                display:grid !important;
                grid-template-columns:1fr !important;
                width:100% !important;
                gap:8px !important;
            }
            .tl-pill{
                width:100% !important;
                box-sizing:border-box !important;
                text-align:center !important;
                padding:12px 10px !important;
                font-size:.98rem !important;
            }
            .tl-card, .tl-checkin, .tl-admin{
                padding:16px !important;
                border-radius:22px !important;
                margin-left:0 !important;
                margin-right:0 !important;
                box-sizing:border-box !important;
            }
            div[data-testid="stForm"]{
                padding:14px !important;
                border-radius:22px !important;
                box-sizing:border-box !important;
            }
            .stTextInput input, .stTextArea textarea, .stDateInput input, .stNumberInput input{
                min-height:48px !important;
                width:100% !important;
                box-sizing:border-box !important;
                background:#fbfff2 !important;
                border:1.6px solid #b8d74a !important;
                border-radius:14px !important;
                font-size:16px !important;
            }
            div[data-testid="stSelectbox"] > div{
                min-height:48px !important;
                width:100% !important;
                box-sizing:border-box !important;
                background:#fbfff2 !important;
                border:1.6px solid #b8d74a !important;
                border-radius:14px !important;
                font-size:16px !important;
            }
            .stButton > button, .stDownloadButton > button{
                width:100% !important;
                min-height:48px !important;
                border-radius:14px !important;
            }
            .stTabs [data-baseweb="tab-list"]{
                gap:6px !important;
                overflow-x:auto !important;
                flex-wrap:nowrap !important;
                padding-bottom:4px !important;
            }
            .stTabs [data-baseweb="tab"]{
                min-width:max-content !important;
                padding:10px 12px !important;
                font-size:.95rem !important;
            }
            .tl-plan{
                border-radius:22px !important;
            }
            .tl-price-row{
                gap:8px !important;
                font-size:.98rem !important;
            }
            .tl-pix-box{
                padding:14px !important;
                border-radius:20px !important;
            }
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
        '<a class="tl-pill" href="#checkin">Check-in de aulas</a>'
        '<a class="tl-pill" href="#reposicao">Reposição de aula</a>'
        '<a class="tl-pill" href="#eventos">Inscrição em torneios</a>'
        '<a class="tl-pill" href="#financeiro">Financeiro com PIX</a>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

@st.cache_data(ttl=40, show_spinner=False)
def healthcheck() -> bool:
    db().request("GET", "alunos", params={"select": "id", "limit": "1"})
    db().request("GET", "eventos", params={"select": "id", "limit": "1"})
    db().request("GET", "confirmacoes", params={"select": "id", "limit": "1"})
    db().request("GET", "inscricoes_eventos", params={"select": "id", "limit": "1"})
    db().request("GET", "reposicoes_aula", params={"select": "id", "limit": "1"})
    return True

@st.cache_data(ttl=40, show_spinner=False)
def fetch_students(limit: int = 600) -> list[dict[str, Any]]:
    return db().request(
        "GET", "alunos",
        params={"select": "id,nome,whatsapp,status_pagamento,ativo,observacao,created_at,updated_at", "order": "nome.asc", "limit": str(limit)},
    ) or []

@st.cache_data(ttl=40, show_spinner=False)
def fetch_events(limit: int = 200, admin: bool = False) -> list[dict[str, Any]]:
    params = {
        "select": "id,titulo,data_evento,local,descricao,valor_inscricao,ativo,inscricoes_abertas,ordem,created_at,updated_at",
        "order": "data_evento.asc,ordem.asc",
        "limit": str(limit),
    }
    if not admin:
        params["ativo"] = "eq.true"
    return db().request("GET", "eventos", params=params) or []

@st.cache_data(ttl=20, show_spinner=False)
def fetch_confirmations(limit: int = 500) -> list[dict[str, Any]]:
    return db().request(
        "GET", "confirmacoes",
        params={
            "select": "id,nome,whatsapp,data_aula,dia_semana,local,horario,status_pagamento,created_at",
            "order": "data_aula.desc,horario.asc,created_at.desc",
            "limit": str(limit),
        },
    ) or []

@st.cache_data(ttl=20, show_spinner=False)
def fetch_registrations(limit: int = 500) -> list[dict[str, Any]]:
    return db().request(
        "GET", "inscricoes_eventos",
        params={
            "select": "id,evento_id,evento_titulo,nome,whatsapp,categoria,valor,status_inscricao,created_at",
            "order": "evento_titulo.asc,categoria.asc,created_at.desc",
            "limit": str(limit),
        },
    ) or []

@st.cache_data(ttl=20, show_spinner=False)
def fetch_makeup_requests(limit: int = 500) -> list[dict[str, Any]]:
    return db().request(
        "GET", "reposicoes_aula",
        params={
            "select": "id,nome,whatsapp,data_original,data_reposicao_preferida,motivo,status,created_at",
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
    fetch_makeup_requests.clear()

def find_student(nome: str, whatsapp: str) -> Optional[dict[str, Any]]:
    phone = normalize_phone(whatsapp)
    if phone:
        rows = db().request(
            "GET", "alunos",
            params={"select": "id,nome,whatsapp,status_pagamento,ativo,observacao", "whatsapp": f"eq.{phone}", "ativo": "eq.true", "limit": "1"},
        ) or []
        if rows:
            return rows[0]
    if nome.strip():
        rows = db().request(
            "GET", "alunos",
            params={"select": "id,nome,whatsapp,status_pagamento,ativo,observacao", "nome": f"ilike.*{nome.strip()}*", "ativo": "eq.true", "limit": "10"},
        ) or []
        if rows:
            return rows[0]
    return None

def confirmation_exists(whatsapp: str, data_aula: str, horario: str) -> bool:
    rows = db().request(
        "GET", "confirmacoes",
        params={"select": "id", "whatsapp": f"eq.{normalize_phone(whatsapp)}", "data_aula": f"eq.{data_aula}", "horario": f"eq.{horario}", "limit": "1"},
    ) or []
    return bool(rows)

def registration_exists(evento_id: str, whatsapp: str) -> bool:
    rows = db().request(
        "GET", "inscricoes_eventos",
        params={"select": "id", "evento_id": f"eq.{evento_id}", "whatsapp": f"eq.{normalize_phone(whatsapp)}", "limit": "1"},
    ) or []
    return bool(rows)

def insert_confirmation(payload: dict[str, Any]) -> None:
    db().request("POST", "confirmacoes", json_body=payload, prefer="return=representation")
    fetch_confirmations.clear()

def insert_registration(payload: dict[str, Any]) -> None:
    db().request("POST", "inscricoes_eventos", json_body=payload, prefer="return=representation")
    fetch_registrations.clear()
    fetch_makeup_requests.clear()

def upsert_student(payload: dict[str, Any]) -> None:
    db().request(
        "POST", "alunos",
        params={"on_conflict": "whatsapp"},
        json_body=payload,
        prefer="resolution=merge-duplicates,return=representation",
    )
    fetch_students.clear()

def update_student(student_id: str, payload: dict[str, Any]) -> None:
    db().request(
        "PATCH",
        "alunos",
        params={"id": f"eq.{student_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_students.clear()

def delete_past_confirmations(before_date: str) -> None:
    db().request(
        "DELETE",
        "confirmacoes",
        params={"data_aula": f"lt.{before_date}"},
        prefer="return=minimal",
    )
    fetch_confirmations.clear()

def delete_records_by_ids(table: str, ids: list[str]) -> None:
    """Apaga registros selecionados com segurança, sem alterar estrutura do banco."""
    clean_ids = [str(item).strip() for item in ids if str(item).strip()]
    if not clean_ids:
        return

    # Tenta apagar em lote. Se o provedor rejeitar o filtro, cai para exclusão individual.
    for start in range(0, len(clean_ids), 120):
        chunk = clean_ids[start:start + 120]
        try:
            db().request(
                "DELETE",
                table,
                params={"id": f"in.({','.join(chunk)})"},
                prefer="return=minimal",
            )
        except AppError:
            for item_id in chunk:
                db().request(
                    "DELETE",
                    table,
                    params={"id": f"eq.{item_id}"},
                    prefer="return=minimal",
                )

def insert_makeup_request(payload: dict[str, Any]) -> None:
    db().request("POST", "reposicoes_aula", json_body=payload, prefer="return=representation")
    fetch_makeup_requests.clear()

def update_makeup_request(request_id: str, payload: dict[str, Any]) -> None:
    db().request(
        "PATCH",
        "reposicoes_aula",
        params={"id": f"eq.{request_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_makeup_requests.clear()

def update_registration(registration_id: str, payload: dict[str, Any]) -> None:
    db().request(
        "PATCH",
        "inscricoes_eventos",
        params={"id": f"eq.{registration_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_registrations.clear()

def insert_event(payload: dict[str, Any]) -> None:
    db().request("POST", "eventos", json_body=payload, prefer="return=representation")
    fetch_events.clear()

def update_event(event_id: str, payload: dict[str, Any]) -> None:
    db().request("PATCH", "eventos", params={"id": f"eq.{event_id}"}, json_body=payload, prefer="return=representation")
    fetch_events.clear()

def status_color(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"em_dia", "pago"}:
        return "ok"
    if v in {"pendente", "aguardando_pagamento"}:
        return "warn"
    return "error"

def render_student_checkin() -> None:
    st.markdown('<div id="checkin"></div>', unsafe_allow_html=True)
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
                        insert_confirmation({
                            "aluno_id": aluno.get("id"),
                            "nome": aluno.get("nome") or nome.strip(),
                            "whatsapp": normalize_phone(aluno.get("whatsapp") or whatsapp),
                            "data_aula": data_aula.isoformat(),
                            "dia_semana": weekday_label(data_aula),
                            "local": lesson_location(data_aula),
                            "horario": horario,
                            "status_pagamento": status,
                        })
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
                            insert_registration({
                                "evento_id": event.get("id"),
                                "evento_titulo": event.get("titulo") or "Evento",
                                "nome": nome.strip(),
                                "whatsapp": normalize_phone(whatsapp),
                                "categoria": categoria,
                                "valor": valor,
                                "status_inscricao": "aguardando_pagamento",
                            })
                            flash_message("ok", f"Inscrição registrada com sucesso em {event.get('titulo')}. Faça o PIX e envie o comprovante para {secretaria_nome}: {secretaria_whatsapp}.")
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
        st.text_input("Chave PIX por e-mail", value=str(pix_email or ""), disabled=True, key="event_pix_email_field")
        copy_button("Copiar e-mail PIX", str(pix_email or ""), "copy_event_email")
    with c2:
        st.text_input("Chave PIX por telefone", value=str(pix_phone or ""), disabled=True, key="event_pix_phone_field")
        copy_button("Copiar telefone PIX", str(pix_phone or ""), "copy_event_phone")
    st.caption(f"Após o pagamento, envie o comprovante para {secretaria_nome}: {secretaria_whatsapp}.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_student_makeup() -> None:
    st.markdown('<div id="reposicao"></div>', unsafe_allow_html=True)
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card tl-checkin">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Reposição de aula</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Solicite uma reposição de aula para análise da administração.</div>', unsafe_allow_html=True)
    show_flash()

    with st.form("form_makeup", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome completo", key="make_name")
        whatsapp = c2.text_input("WhatsApp", key="make_whatsapp")
        c3, c4 = st.columns(2)
        data_original = c3.date_input("Data da aula perdida", value=date.today(), key="make_original")
        data_reposicao = c4.date_input("Data preferida para repor", value=next_class_day(), min_value=date.today(), key="make_replacement")
        motivo = st.text_area("Motivo", key="make_reason")
        submit = st.form_submit_button("Solicitar reposição", use_container_width=True)

    if submit:
        if not nome.strip() or not whatsapp.strip():
            md_box("error", "Preencha nome completo e WhatsApp.")
        else:
            try:
                aluno = find_student(nome, whatsapp)
                if not aluno:
                    md_box("error", f"Aluno não localizado. Fale com {secretaria_nome} pelo WhatsApp {secretaria_whatsapp}.")
                else:
                    insert_makeup_request({
                        "nome": aluno.get("nome") or nome.strip(),
                        "whatsapp": normalize_phone(aluno.get("whatsapp") or whatsapp),
                        "data_original": data_original.isoformat(),
                        "data_reposicao_preferida": data_reposicao.isoformat(),
                        "motivo": motivo.strip() or None,
                        "status": "solicitada",
                    })
                    flash_message("ok", "Sua solicitação de reposição foi enviada com sucesso. A administração irá analisar.")
                    st.rerun()
            except AppError as exc:
                md_box("error", f"Não foi possível registrar a reposição. {str(exc)}")
            except Exception:
                md_box("error", "Não foi possível registrar a reposição agora.")

    st.caption(f"Em caso de urgência, fale com {secretaria_nome}: {secretaria_whatsapp}.")
    st.markdown('</div>', unsafe_allow_html=True)


def render_finance() -> None:
    st.markdown('<div id="financeiro"></div>', unsafe_allow_html=True)
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    pix_name = secret_value("PIX_NAME", DEFAULTS["PIX_NAME"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Financeiro</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Confira os planos e realize o pagamento por PIX.</div>', unsafe_allow_html=True)

    # Cards dos planos: não dependem do banco e não devem bloquear o PIX.
    try:
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
    except Exception:
        md_box("warn", "Os planos não puderam ser exibidos agora, mas as chaves PIX estão disponíveis abaixo.")

    # PIX: fallback seguro. Mesmo se o botão de copiar falhar, as chaves aparecem.
    st.markdown('<div class="tl-pix-box">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section" style="font-size:1.25rem;">Pagamento por PIX</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="tl-green-label">Favorecido: {pix_name}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Chave PIX por e-mail", value=str(pix_email or ""), disabled=True, key="pix_email_field")
        copy_button("Copiar e-mail PIX", str(pix_email or ""), "copy_fin_email")
    with c2:
        st.text_input("Chave PIX por telefone", value=str(pix_phone or ""), disabled=True, key="pix_phone_field")
        copy_button("Copiar telefone PIX", str(pix_phone or ""), "copy_fin_phone")
    st.caption(f"Após o pagamento, envie o comprovante para {secretaria_nome}: {secretaria_whatsapp}.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_admin_access() -> bool:
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    password = secret_value("ADMIN_PASSWORD", DEFAULTS["ADMIN_PASSWORD"])

    st.sidebar.markdown("## Área administrativa")
    pwd_side = st.sidebar.text_input("Senha admin", type="password", key="admin_pwd_side")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("Entrar", use_container_width=True, key="side_enter"):
        if pwd_side == password:
            st.session_state.admin_ok = True
            flash_message("ok", "Área administrativa liberada.")
            st.rerun()
        else:
            st.sidebar.error("Senha incorreta.")
    if c2.button("Sair", use_container_width=True, key="side_exit"):
        st.session_state.admin_ok = False
        st.session_state.admin_pwd_side = ""
        st.rerun()

    if st.session_state.admin_ok:
        st.sidebar.success("Admin liberado.")
        return True

    st.sidebar.caption("Toque na seta no topo para abrir ou fechar esta área.")
    return False

def render_students_admin() -> None:
    st.markdown("### Alunos")
    st.caption("Cadastre novos alunos e atualize status financeiro, dados e atividade dos alunos já cadastrados.")

    with st.form("form_admin_student", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do aluno")
        whatsapp = c2.text_input("WhatsApp")
        c3, c4 = st.columns(2)
        status = c3.selectbox("Status de pagamento", ["em_dia", "pendente", "inadimplente"], key="novo_status_aluno")
        ativo = c4.selectbox("Aluno ativo", ["sim", "não"], key="novo_ativo_aluno")
        observacao = st.text_input("Observação")
        submit = st.form_submit_button("Salvar novo aluno", use_container_width=True)
    if submit:
        if not nome.strip() or not whatsapp.strip():
            md_box("error", "Preencha nome e WhatsApp.")
        else:
            try:
                upsert_student({
                    "nome": nome.strip(),
                    "whatsapp": normalize_phone(whatsapp),
                    "status_pagamento": status,
                    "ativo": ativo == "sim",
                    "observacao": observacao.strip() or None,
                })
                md_box("ok", "Aluno salvo com sucesso.")
                clear_caches()
            except AppError as exc:
                md_box("error", str(exc))

    try:
        rows = fetch_students()
        if not rows:
            st.info("Nenhum aluno cadastrado ainda.")
            return

        st.markdown("#### Editar aluno existente")
        student_options = {
            f"{row.get('nome', 'Aluno')} • {row.get('whatsapp', '')}": row
            for row in rows
        }
        selected_label = st.selectbox("Selecione um aluno para editar", list(student_options.keys()), key="editar_aluno_select")
        selected_student = student_options[selected_label]

        with st.form("form_edit_student"):
            c1, c2 = st.columns(2)
            edit_nome = c1.text_input("Nome", value=selected_student.get("nome") or "", key="edit_nome_aluno")
            edit_whatsapp = c2.text_input("WhatsApp", value=selected_student.get("whatsapp") or "", key="edit_whatsapp_aluno")

            status_options = ["em_dia", "pendente", "inadimplente"]
            current_status = selected_student.get("status_pagamento") or "pendente"
            status_index = status_options.index(current_status) if current_status in status_options else 1

            ativo_options = ["sim", "não"]
            ativo_index = 0 if selected_student.get("ativo", True) else 1

            c3, c4 = st.columns(2)
            edit_status = c3.selectbox("Status de pagamento", status_options, index=status_index, key="edit_status_aluno")
            edit_ativo = c4.selectbox("Aluno ativo", ativo_options, index=ativo_index, key="edit_ativo_aluno")
            edit_obs = st.text_input("Observação", value=selected_student.get("observacao") or "", key="edit_obs_aluno")
            submit_edit = st.form_submit_button("Atualizar aluno selecionado", use_container_width=True)

        if submit_edit:
            if not edit_nome.strip() or not edit_whatsapp.strip():
                md_box("error", "Preencha nome e WhatsApp do aluno selecionado.")
            else:
                try:
                    update_student(str(selected_student["id"]), {
                        "nome": edit_nome.strip(),
                        "whatsapp": normalize_phone(edit_whatsapp),
                        "status_pagamento": edit_status,
                        "ativo": edit_ativo == "sim",
                        "observacao": edit_obs.strip() or None,
                    })
                    clear_caches()
                    md_box("ok", "Aluno atualizado com sucesso.")
                except AppError as exc:
                    md_box("error", str(exc))

        st.markdown("#### Lista de alunos")
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("error", str(exc))

def render_events_admin() -> None:
    st.markdown("### Eventos")
    try:
        all_events = fetch_events(admin=True)
    except AppError as exc:
        md_box("error", str(exc))
        all_events = []

    mode = st.radio("Modo", ["Novo evento", "Editar evento"], horizontal=True)
    editing = None
    if mode == "Editar evento" and all_events:
        event_options = {f"{e['titulo']} • {br_date(e['data_evento'])}": e for e in all_events}
        selected_label = st.selectbox("Selecione o evento", list(event_options.keys()))
        editing = event_options[selected_label]
    elif mode == "Editar evento" and not all_events:
        st.info("Nenhum evento cadastrado ainda.")
        return

    with st.form("form_admin_event", clear_on_submit=(editing is None)):
        titulo = st.text_input("Título do evento", value=editing.get("titulo", "") if editing else "")
        c1, c2 = st.columns(2)
        default_date = datetime.strptime(str(editing.get("data_evento")), "%Y-%m-%d").date() if editing and editing.get("data_evento") else date.today()
        data_evento = c1.date_input("Data do evento", value=default_date)
        local = c2.text_input("Local", value=editing.get("local", "Tênis Linhares") if editing else "Tênis Linhares")
        descricao = st.text_area("Descrição", value=editing.get("descricao", "") if editing else "")
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor da inscrição", min_value=0.0, value=float(editing.get("valor_inscricao") or 0) if editing else 0.0, step=10.0)
        ordem = c4.number_input("Ordem", min_value=1, value=int(editing.get("ordem") or 1) if editing else 1, step=1)
        c5, c6 = st.columns(2)
        ativo = c5.selectbox("Evento visível?", ["sim", "não"], index=0 if not editing or editing.get("ativo", True) else 1)
        abertas = c6.selectbox("Inscrições abertas?", ["sim", "não"], index=0 if not editing or editing.get("inscricoes_abertas", True) else 1)
        submit = st.form_submit_button("Salvar evento" if editing else "Adicionar evento", use_container_width=True)
    if submit:
        if not titulo.strip():
            md_box("error", "Informe o título do evento.")
        else:
            payload = {
                "titulo": titulo.strip(),
                "data_evento": data_evento.isoformat(),
                "local": local.strip() or "Tênis Linhares",
                "descricao": descricao.strip() or None,
                "valor_inscricao": float(valor),
                "ativo": ativo == "sim",
                "inscricoes_abertas": abertas == "sim",
                "ordem": int(ordem),
            }
            try:
                if editing:
                    update_event(str(editing["id"]), payload)
                    md_box("ok", "Evento atualizado com sucesso.")
                else:
                    insert_event(payload)
                    md_box("ok", "Evento adicionado com sucesso.")
                clear_caches()
            except AppError as exc:
                md_box("error", str(exc))

    if all_events:
        df = pd.DataFrame(all_events)
        df["data_evento"] = df["data_evento"].map(br_date)
        df["valor_inscricao"] = df["valor_inscricao"].map(money_br)
        st.dataframe(df, use_container_width=True, hide_index=True)

def render_registrations_admin() -> None:
    st.markdown("### Inscrições")
    try:
        rows = fetch_registrations()
        if not rows:
            st.info("Nenhuma inscrição registrada ainda.")
            return

        df = pd.DataFrame(rows)
        df["categoria_ordem"] = df["categoria"].map(lambda x: CATEGORY_ORDER.get(x, 999))

        eventos = ["Todos"] + sorted([x for x in df["evento_titulo"].dropna().unique().tolist()])
        categorias = ["Todas"] + [c for c in TOURNAMENT_CATEGORIES if c in df["categoria"].dropna().unique().tolist()]
        status_list = ["Todos"] + sorted([x for x in df["status_inscricao"].dropna().unique().tolist()])

        c1, c2, c3 = st.columns(3)
        evento_filtro = c1.selectbox("Filtrar por evento", eventos, key="insc_evento_filtro")
        categoria_filtro = c2.selectbox("Filtrar por categoria", categorias, key="insc_categoria_filtro")
        status_filtro = c3.selectbox("Filtrar por status", status_list, key="insc_status_filtro")

        if evento_filtro != "Todos":
            df = df[df["evento_titulo"] == evento_filtro]
        if categoria_filtro != "Todas":
            df = df[df["categoria"] == categoria_filtro]
        if status_filtro != "Todos":
            df = df[df["status_inscricao"] == status_filtro]

        if df.empty:
            st.info("Nenhuma inscrição encontrada com esses filtros.")
            return

        df = df.sort_values(["evento_titulo", "categoria_ordem", "nome", "created_at"])

        with st.expander("Gerenciar inscrições selecionadas", expanded=False):
            st.caption("Use esta área para alterar status ou apagar inscrições. Dados apagados não voltam automaticamente.")
            options = {
                f"{row.get('evento_titulo','Evento')} • {row.get('categoria','Categoria')} • {row.get('nome','Aluno')} • {row.get('whatsapp','')}": str(row.get("id"))
                for _, row in df.iterrows()
            }
            selected_label = st.selectbox("Selecionar inscrição", list(options.keys()), key="admin_select_registration")
            selected_id = options[selected_label]
            c4, c5 = st.columns(2)
            new_status = c4.selectbox("Status da inscrição", ["aguardando_pagamento", "pago", "cancelada"], key="admin_registration_status")
            if c5.button("Atualizar status da inscrição", use_container_width=True, key="btn_update_registration_status"):
                try:
                    update_registration(selected_id, {"status_inscricao": new_status})
                    clear_caches()
                    md_box("ok", "Status da inscrição atualizado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

            st.markdown("---")
            st.write(f"Inscrições visíveis com os filtros atuais: **{len(df)}**")
            delete_mode = st.radio(
                "O que deseja apagar?",
                ["Apenas a inscrição selecionada", "Todas as inscrições filtradas acima"],
                horizontal=False,
                key="delete_registration_mode",
            )
            confirm_delete = st.checkbox("Confirmo que desejo apagar a(s) inscrição(ões) selecionada(s)", key="confirm_delete_registrations")
            if st.button("Apagar inscrição/inscrições", use_container_width=True, disabled=not confirm_delete, key="btn_delete_registrations"):
                try:
                    ids = [selected_id] if delete_mode == "Apenas a inscrição selecionada" else df["id"].astype(str).tolist()
                    delete_records_by_ids("inscricoes_eventos", ids)
                    clear_caches()
                    md_box("ok", "Inscrição(ões) apagada(s) com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        for event_title, event_group in df.groupby("evento_titulo"):
            st.markdown(f'<div class="tl-group-title">{event_title}</div>', unsafe_allow_html=True)
            event_group = event_group.drop(columns=["categoria_ordem"])
            if "valor" in event_group.columns:
                event_group["valor"] = event_group["valor"].map(money_br)
            if "created_at" in event_group.columns:
                event_group["created_at"] = event_group["created_at"].map(br_date)
            st.dataframe(event_group, use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("error", str(exc))

def render_confirmations_admin() -> None:
    st.markdown("### Confirmações")
    try:
        rows = fetch_confirmations()
        if not rows:
            st.info("Nenhuma confirmação registrada ainda.")
            return

        df = pd.DataFrame(rows)
        df["data_ordem"] = pd.to_datetime(df["data_aula"], errors="coerce")
        today = pd.Timestamp(date.today())

        c1, c2, c3 = st.columns(3)
        periodo = c1.selectbox("Período", ["Hoje", "Futuras", "Passadas", "Todas"], key="conf_periodo_filtro")
        horario_filtro = c2.selectbox("Horário", ["Todos"] + sorted([x for x in df["horario"].dropna().unique().tolist()]), key="conf_horario_filtro")
        status_filtro = c3.selectbox("Status", ["Todos"] + sorted([x for x in df["status_pagamento"].dropna().unique().tolist()]), key="conf_status_filtro")

        if periodo == "Hoje":
            df = df[df["data_ordem"] == today]
        elif periodo == "Futuras":
            df = df[df["data_ordem"] >= today]
        elif periodo == "Passadas":
            df = df[df["data_ordem"] < today]
        if horario_filtro != "Todos":
            df = df[df["horario"] == horario_filtro]
        if status_filtro != "Todos":
            df = df[df["status_pagamento"] == status_filtro]

        with st.expander("Limpeza segura de confirmações", expanded=False):
            st.caption("Use apenas para apagar confirmações antigas ou selecionadas. Dados apagados não voltam automaticamente.")

            cutoff_date = st.date_input("Apagar confirmações anteriores a", value=date.today(), key="delete_confirmations_before_date")
            all_df = pd.DataFrame(rows)
            all_df["data_ordem"] = pd.to_datetime(all_df["data_aula"], errors="coerce")
            preview_count = int((all_df["data_ordem"] < pd.Timestamp(cutoff_date)).sum())
            st.write(f"Confirmações anteriores a essa data: **{preview_count}**")
            confirm_old_delete = st.checkbox("Confirmo que quero apagar confirmações anteriores à data escolhida", key="confirm_delete_old_confirmations")
            if st.button("Apagar confirmações passadas", use_container_width=True, disabled=(not confirm_old_delete or preview_count == 0), key="btn_delete_old_confirmations"):
                try:
                    delete_past_confirmations(cutoff_date.isoformat())
                    clear_caches()
                    md_box("ok", "Confirmações passadas apagadas com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

            st.markdown("---")
            if df.empty:
                st.info("Nenhuma confirmação visível com os filtros atuais para apagar individualmente.")
            else:
                st.write(f"Confirmações visíveis com os filtros atuais: **{len(df)}**")
                options = {
                    f"{br_date(row.get('data_aula'))} • {row.get('horario','')} • {row.get('nome','Aluno')} • {row.get('whatsapp','')}": str(row.get("id"))
                    for _, row in df.sort_values(["data_ordem", "horario", "nome"], ascending=[False, True, True]).iterrows()
                }
                selected_label = st.selectbox("Selecionar confirmação", list(options.keys()), key="admin_select_confirmation_delete")
                selected_id = options[selected_label]
                delete_mode = st.radio(
                    "O que deseja apagar?",
                    ["Apenas a confirmação selecionada", "Todas as confirmações filtradas acima"],
                    key="delete_confirmation_mode",
                )
                confirm_delete = st.checkbox("Confirmo que desejo apagar a(s) confirmação(ões) selecionada(s)", key="confirm_delete_confirmations")
                if st.button("Apagar confirmação/confirmações", use_container_width=True, disabled=not confirm_delete, key="btn_delete_confirmations_filtered"):
                    try:
                        ids = [selected_id] if delete_mode == "Apenas a confirmação selecionada" else df["id"].astype(str).tolist()
                        delete_records_by_ids("confirmacoes", ids)
                        clear_caches()
                        md_box("ok", "Confirmação(ões) apagada(s) com sucesso.")
                        st.rerun()
                    except AppError as exc:
                        md_box("error", str(exc))

        if df.empty:
            st.info("Nenhuma confirmação encontrada com esses filtros.")
            return

        df = df.sort_values(["data_ordem", "horario", "nome"], ascending=[False, True, True])
        for data_label, group in df.groupby("data_aula", dropna=False):
            st.markdown(f'<div class="tl-group-title">{br_date(data_label)}</div>', unsafe_allow_html=True)
            group = group.drop(columns=["data_ordem"])
            if "created_at" in group.columns:
                group["created_at"] = group["created_at"].map(br_date)
            st.dataframe(group, use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("error", str(exc))

def render_admin_panel() -> None:
    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Painel administrativo</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Cadastre alunos, controle eventos, inscrições e confirmações.</div>', unsafe_allow_html=True)
    show_flash()
    t1, t2, t3, t4, t5 = st.tabs(["Alunos", "Eventos", "Inscrições", "Confirmações", "Reposições"])
    with t1:
        render_students_admin()
    with t2:
        render_events_admin()
    with t3:
        render_registrations_admin()
    with t4:
        render_confirmations_admin()
    with t5:
        render_makeups_admin()
    st.markdown('</div>', unsafe_allow_html=True)

def render_makeups_admin() -> None:
    st.markdown("### Reposições")
    try:
        rows = fetch_makeup_requests()
        if not rows:
            st.info("Nenhuma solicitação de reposição registrada ainda.")
            return

        df = pd.DataFrame(rows)
        df["data_original_ordem"] = pd.to_datetime(df["data_original"], errors="coerce")
        df["data_reposicao_ordem"] = pd.to_datetime(df["data_reposicao_preferida"], errors="coerce")

        status_options = ["Todos"] + sorted([x for x in df["status"].dropna().unique().tolist()])
        c1, c2 = st.columns(2)
        status_filtro = c1.selectbox("Filtrar por status", status_options, key="makeup_status_filter")
        periodo_filtro = c2.selectbox("Período da data preferida", ["Todas", "Futuras", "Passadas"], key="makeup_period_filter")

        today = pd.Timestamp(date.today())
        if status_filtro != "Todos":
            df = df[df["status"] == status_filtro]
        if periodo_filtro == "Futuras":
            df = df[df["data_reposicao_ordem"] >= today]
        elif periodo_filtro == "Passadas":
            df = df[df["data_reposicao_ordem"] < today]

        if df.empty:
            st.info("Nenhuma reposição encontrada com esse filtro.")
            return

        df = df.sort_values(["status", "data_reposicao_ordem", "created_at"], ascending=[True, True, False])

        with st.expander("Gerenciar reposições selecionadas", expanded=False):
            st.caption("Use esta área para atualizar status ou apagar solicitações. Dados apagados não voltam automaticamente.")
            options = {
                f"{row.get('nome','Aluno')} • {row.get('whatsapp','')} • preferida: {br_date(row.get('data_reposicao_preferida'))} • {row.get('status','')}": str(row.get("id"))
                for _, row in df.iterrows()
            }
            selected_label = st.selectbox("Selecionar reposição", list(options.keys()), key="admin_select_makeup")
            selected_id = options[selected_label]

            c3, c4 = st.columns(2)
            new_status = c3.selectbox("Status da reposição", ["solicitada", "aprovada", "concluida", "cancelada"], key="admin_makeup_status")
            if c4.button("Atualizar status da reposição", use_container_width=True, key="btn_update_makeup_status"):
                try:
                    update_makeup_request(selected_id, {"status": new_status})
                    clear_caches()
                    md_box("ok", "Status da reposição atualizado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

            st.markdown("---")
            st.write(f"Reposições visíveis com os filtros atuais: **{len(df)}**")
            delete_mode = st.radio(
                "O que deseja apagar?",
                ["Apenas a reposição selecionada", "Todas as reposições filtradas acima"],
                key="delete_makeup_mode",
            )
            confirm_delete = st.checkbox("Confirmo que desejo apagar a(s) reposição(ões) selecionada(s)", key="confirm_delete_makeups")
            if st.button("Apagar reposição/reposições", use_container_width=True, disabled=not confirm_delete, key="btn_delete_makeups"):
                try:
                    ids = [selected_id] if delete_mode == "Apenas a reposição selecionada" else df["id"].astype(str).tolist()
                    delete_records_by_ids("reposicoes_aula", ids)
                    clear_caches()
                    md_box("ok", "Reposição(ões) apagada(s) com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        display_df = df.drop(columns=["data_original_ordem", "data_reposicao_ordem"])
        display_df["data_original"] = display_df["data_original"].map(br_date)
        display_df["data_reposicao_preferida"] = display_df["data_reposicao_preferida"].map(br_date)
        display_df["created_at"] = display_df["created_at"].map(br_date)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("error", str(exc))

def render_setup_message() -> None:
    md_box("warn", "Aplicativo em configuração. Verifique Secrets do Streamlit e rode o schema.sql mais novo no Supabase.")

def main() -> None:
    inject_css()
    render_header()
    admin_ok = render_admin_access()

    if get_config() is None:
        render_setup_message()
        return

    try:
        healthcheck()
    except AppError as exc:
        md_box("warn", f"{str(exc)}")
        return
    except Exception:
        md_box("warn", "Banco ainda não está pronto. Rode o schema.sql mais novo no Supabase.")
        return

    try:
        tab_checkin, tab_makeup, tab_events, tab_finance = st.tabs(["Check-in das aulas", "Reposição de aula", "Eventos", "Financeiro"])
        with tab_checkin:
            try:
                render_student_checkin()
            except Exception:
                md_box("error", "Não foi possível carregar o check-in agora.")
        with tab_makeup:
            try:
                render_student_makeup()
            except Exception:
                md_box("error", "Não foi possível carregar a reposição agora.")
        with tab_events:
            try:
                render_student_events()
            except Exception:
                md_box("error", "Não foi possível carregar os eventos agora.")
        with tab_finance:
            try:
                render_finance()
            except Exception:
                md_box("error", "Não foi possível carregar o financeiro agora.")

        if admin_ok:
            render_admin_panel()
    except Exception:
        md_box("error", "Ocorreu um erro inesperado. Atualize a página e tente novamente.")

if __name__ == "__main__":
    main()
