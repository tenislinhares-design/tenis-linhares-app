
from __future__ import annotations

import os
import re
import json
import base64
import io
import hmac
import hashlib
import secrets
from urllib.parse import quote
from html import escape
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
    BASE_DIR / "logo.png",
    BASE_DIR / "assets" / "logo.png",
    BASE_DIR / "logo.jpeg",
    BASE_DIR / "logo.jpg",
    BASE_DIR / "assets" / "logo.jpeg",
    BASE_DIR / "assets" / "logo.jpg",
]

DEFAULTS = {
    "PIX_EMAIL": "tenislinhares@gmail.com",
    "PIX_PHONE": "+55 27 99997-0109",
    "PIX_NAME": "Tênis Linhares",
    "SECRETARIA_NOME": "Andrea Nascimento",
    "SECRETARIA_WHATSAPP": "+55 27 99997-0109",
    "ADMIN_PASSWORD": "",
    "TOURNAMENT_SOCIO_PRICE": "180",
    "TOURNAMENT_NAO_SOCIO_PRICE": "210",
    "TOURNAMENT_PIX_LABEL": "Pagamento via PIX",
    "TOURNAMENT_PIX_KEY": "",
    "TOURNAMENT_PIX_FAVORECIDO": "",
}

TOURNAMENT_CATEGORIES = [
    "Classe Especial",
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
TOURNAMENT_CATEGORY_LIMIT = 16
STRINGING_DEFAULT_TOTAL = 170.0
STRINGING_DEFAULT_LABOR = 45.0


TOURNAMENT_PRICE_OPTIONS = [
    {"label": "Sócio Atal e Cincate — R$ 180,00", "value": "socio_atl", "amount": 180.0},
    {"label": "Não sócio — R$ 210,00", "value": "nao_socio", "amount": 210.0},
]

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
    {
        "title": "Serviços de Raquete",
        "subtitle": "Encordoamento",
        "highlight": "Cuidado técnico para sua raquete",
        "items": [
            ("Com corda Tênis Linhares", "R$ 170,00"),
            ("Mão de obra com corda do cliente", "R$ 45,00"),
        ],
        "footer": "Serviço sujeito à disponibilidade de agenda e material.",
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

CLASS_DAY_OPTIONS = WEEKDAY_LABELS[:5]
CLASS_TIME_OPTIONS = [
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
CLASS_LOCATION_OPTIONS = ["Clube Mata do Lago", "Condomínio Unique", "Condomínios"]
PLAN_TYPE_OPTIONS = ["mensalidade", "pacote_de_aulas"]

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
    """
    Lê configurações somente das variáveis de ambiente do Render.
    Isso evita o erro visual do Streamlit: "Nenhum arquivo de segredos encontrado".
    """
    aliases = {
        "SUPABASE_SECRET_KEY": ["SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"],
        "SUPABASE_SERVICE_ROLE_KEY": ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"],
        "ADMIN_PASSWORD": ["ADMIN_PASSWORD", "ADMIN_PASS", "ADMIN_TOKEN", "ADMIN_SECRET"],
    }
    names = aliases.get(name, [name])
    for env_name in names:
        value = os.getenv(env_name)
        if isinstance(value, str) and value.strip():
            return value.strip().strip('"').strip("'")
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
        raise AppError("Aplicativo em configuração. Verifique as variáveis de ambiente SUPABASE_URL e SUPABASE_SECRET_KEY no Render.")
    return client

def _admin_password_fallback() -> str:
    # Segurança: não aceita mais senha fixa antiga no código.
    # Só usa a senha salva no app/Supabase ou a variável ADMIN_PASSWORD do Render.
    return str(secret_value("ADMIN_PASSWORD", "") or "").strip()


def _hash_admin_password(password: str, salt_hex: Optional[str] = None) -> dict[str, Any]:
    """Gera hash seguro usando apenas biblioteca padrão do Python."""
    clean_password = str(password or "").strip()
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    iterations = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", clean_password.encode("utf-8"), salt, iterations)
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": iterations,
        "salt": salt.hex(),
        "hash": digest.hex(),
    }


def _get_admin_password_config() -> Optional[dict[str, Any]]:
    """
    Busca a senha administrativa salva no Supabase.
    Se a tabela ainda não existir, o app continua usando ADMIN_PASSWORD do Render.
    """
    try:
        rows = db().request(
            "GET",
            "app_settings",
            params={"select": "key,value,updated_at", "key": "eq.admin_password_hash", "limit": "1"},
        ) or []
        if not rows:
            return None
        value = rows[0].get("value")
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            return json.loads(value)
    except Exception:
        return None
    return None


def verify_admin_password(password: str) -> bool:
    """Valida primeiro pela senha salva no app/Supabase; se não existir, usa ADMIN_PASSWORD do Render."""
    typed = str(password or "").strip()
    stored = _get_admin_password_config()
    if stored and stored.get("algorithm") == "pbkdf2_sha256":
        try:
            iterations = int(stored.get("iterations") or 260_000)
            salt = bytes.fromhex(str(stored.get("salt") or ""))
            expected = str(stored.get("hash") or "")
            digest = hashlib.pbkdf2_hmac("sha256", typed.encode("utf-8"), salt, iterations).hex()
            return hmac.compare_digest(digest, expected)
        except Exception:
            return False
    fallback = _admin_password_fallback()
    if fallback:
        return hmac.compare_digest(typed, fallback)
    return False


def save_admin_password(new_password: str) -> None:
    """Salva nova senha administrativa no Supabase, sem depender do Render."""
    record = _hash_admin_password(new_password)
    payload = {
        "key": "admin_password_hash",
        "value": record,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    db().request(
        "POST",
        "app_settings",
        params={"on_conflict": "key"},
        json_body=payload,
        prefer="resolution=merge-duplicates,return=representation",
    )

def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")

def whatsapp_link(phone: str, text: str) -> str:
    digits = normalize_phone(phone)
    if not digits:
        return "#"
    return f"https://wa.me/{digits}?text={quote(text)}"

def tournament_price_options() -> list[dict[str, Any]]:
    return [
        {"label": "Sócio ATAL — R$ 180,00", "value": "socio_atal", "amount": 180.0},
        {"label": "Sócio CINCATE — R$ 200,00", "value": "socio_cincate", "amount": 200.0},
        {"label": "Não sócio — R$ 230,00", "value": "nao_socio", "amount": 230.0},
    ]

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
    return CLASS_TIME_OPTIONS.copy()

def parse_student_days(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        text = str(value).strip()
        try:
            loaded = json.loads(text)
            raw_items = loaded if isinstance(loaded, list) else [text]
        except Exception:
            raw_items = re.split(r"[,;|]", text)
    valid = []
    for item in raw_items:
        day = str(item or "").strip()
        if day in CLASS_DAY_OPTIONS and day not in valid:
            valid.append(day)
    return valid

def serialize_student_days(days: list[str]) -> str:
    return ", ".join([day for day in days if day in CLASS_DAY_OPTIONS])

def mask_phone_last4(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[-4:] if len(digits) >= 4 else digits

def default_location_for_day_label(day_label: str) -> str:
    if day_label in {"Segunda-feira", "Quarta-feira", "Sexta-feira"}:
        return "Clube Mata do Lago"
    if day_label in {"Terça-feira", "Quinta-feira"}:
        return "Condomínio Unique"
    return ""

def parse_student_schedule_entries(value: Any, fallback_student: Optional[dict[str, Any]] = None) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if value not in (None, ""):
        raw_items = []
        if isinstance(value, list):
            raw_items = value
        else:
            text_value = str(value).strip()
            try:
                loaded = json.loads(text_value)
                if isinstance(loaded, list):
                    raw_items = loaded
            except Exception:
                raw_items = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            day = str(item.get("dia") or "").strip()
            horario = str(item.get("horario") or "").strip()
            local = str(item.get("local") or "").strip()
            if day in CLASS_DAY_OPTIONS and horario in CLASS_TIME_OPTIONS:
                entries.append({
                    "dia": day,
                    "horario": horario,
                    "local": local or default_location_for_day_label(day),
                })
    if not entries and fallback_student:
        fallback_days = parse_student_days(fallback_student.get("dias_aula"))
        fallback_horario = str(fallback_student.get("aula_horario") or "").strip()
        fallback_local = str(fallback_student.get("aula_local") or "").strip()
        if fallback_days and fallback_horario:
            for day in fallback_days:
                entries.append({
                    "dia": day,
                    "horario": fallback_horario,
                    "local": fallback_local or default_location_for_day_label(day),
                })
    unique: list[dict[str, str]] = []
    seen = set()
    for item in entries:
        key = (item.get("dia"), item.get("horario"), item.get("local"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique

def serialize_student_schedule_entries(entries: list[dict[str, str]]) -> Optional[str]:
    clean = []
    for item in entries:
        day = str(item.get("dia") or "").strip()
        horario = str(item.get("horario") or "").strip()
        local = str(item.get("local") or "").strip() or default_location_for_day_label(day)
        if day in CLASS_DAY_OPTIONS and horario in CLASS_TIME_OPTIONS:
            clean.append({"dia": day, "horario": horario, "local": local})
    return json.dumps(clean, ensure_ascii=False) if clean else None

def student_schedule_entries(student: Optional[dict[str, Any]]) -> list[dict[str, str]]:
    if not student:
        return []
    return parse_student_schedule_entries(student.get("agenda_aulas"), student)

def student_schedule_for_day(student: Optional[dict[str, Any]], value: date) -> list[dict[str, str]]:
    day_label = weekday_label(value)
    return [item for item in student_schedule_entries(student) if item.get("dia") == day_label]

def student_schedule_summary(student: Optional[dict[str, Any]]) -> str:
    entries = student_schedule_entries(student)
    if not entries:
        return "horários não cadastrados"
    day_map = {
        "Segunda-feira": "seg",
        "Terça-feira": "ter",
        "Quarta-feira": "qua",
        "Quinta-feira": "qui",
        "Sexta-feira": "sex",
        "Sábado": "sáb",
        "Domingo": "dom",
    }
    pieces = []
    for item in entries:
        day = day_map.get(item.get("dia", ""), item.get("dia", ""))
        horario = str(item.get("horario") or "")
        short_horario = horario.split(" às ")[0] if " às " in horario else horario
        pieces.append(f"{day} {short_horario}")
    return ", ".join(pieces)

def student_has_class_on(student: dict[str, Any], value: date) -> bool:
    entries = student_schedule_for_day(student, value)
    if entries:
        return True
    days = parse_student_days(student.get("dias_aula"))
    return weekday_label(value) in days if days else False

def schedule_start_time(horario: Any) -> Optional[datetime.time]:
    text_value = str(horario or "").strip()
    if not text_value:
        return None
    start_text = text_value.split(" às ")[0].strip()
    try:
        return datetime.strptime(start_text, "%H:%M").time()
    except Exception:
        return None

def next_student_class(student: Optional[dict[str, Any]], ref: Optional[datetime] = None) -> Optional[dict[str, Any]]:
    if not student:
        return None
    entries = student_schedule_entries(student)
    if not entries:
        return None
    now = ref or datetime.now()
    weekday_index = {label: idx for idx, label in enumerate(WEEKDAY_LABELS)}
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for item in entries:
        day_label = str(item.get("dia") or "").strip()
        target_idx = weekday_index.get(day_label)
        if target_idx is None:
            continue
        start_time = schedule_start_time(item.get("horario")) or datetime.strptime("00:00", "%H:%M").time()
        days_ahead = (target_idx - now.weekday()) % 7
        candidate_date = now.date() + timedelta(days=days_ahead)
        candidate_dt = datetime.combine(candidate_date, start_time)
        if candidate_dt < now:
            candidate_date = candidate_date + timedelta(days=7)
            candidate_dt = datetime.combine(candidate_date, start_time)
        candidates.append((candidate_dt, {
            "data": candidate_date,
            "horario": str(item.get("horario") or ""),
            "local": str(item.get("local") or "") or default_location_for_day_label(day_label),
            "dia_semana": day_label,
        }))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]

def resolve_active_student_by_name(name: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    term = str(name or "").strip()
    if not term:
        return None, None
    try:
        rows = [row for row in fetch_students(1000) if row.get("ativo", True)]
    except Exception:
        return None, "Busca indisponível agora. Tente novamente em instantes."
    norm = re.sub(r"\s+", " ", term).strip().lower()
    exact = [row for row in rows if re.sub(r"\s+", " ", str(row.get("nome") or "")).strip().lower() == norm]
    if len(exact) == 1:
        return exact[0], None
    if len(exact) > 1:
        return None, "Encontramos mais de um cadastro com esse nome. Digite o nome completo para confirmar."
    partial = [row for row in rows if norm in re.sub(r"\s+", " ", str(row.get("nome") or "")).strip().lower()]
    if len(partial) == 1:
        return partial[0], None
    if len(partial) > 1:
        return None, "Encontramos mais de um aluno parecido. Digite o nome completo para confirmar."
    return None, None

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

def clamp_due_day(value: Any, default: int = 5) -> int:
    """Dia fixo de vencimento recorrente mensal, sem mês/ano."""
    try:
        day = int(float(value))
    except Exception:
        day = default
    return max(1, min(31, day))

def due_day_from_student(row: dict[str, Any] | pd.Series) -> Optional[int]:
    """Usa o novo dia recorrente; se não existir, aproveita o dia da data antiga."""
    raw_day = None
    try:
        raw_day = row.get("dia_vencimento_mensalidade")
    except Exception:
        raw_day = None
    if raw_day not in (None, ""):
        return clamp_due_day(raw_day)
    try:
        old_date = row.get("data_vencimento_mensalidade")
    except Exception:
        old_date = None
    parsed = parse_date_optional(old_date)
    return parsed.day if parsed else None

def is_paid_status(value: Any) -> bool:
    status = str(value or "").strip().lower()
    return status in {"pago", "paga", "pagamento_confirmado", "confirmado", "confirmada"}

def is_pending_status(value: Any) -> bool:
    status = str(value or "").strip().lower()
    return bool(status) and not is_paid_status(status) and is_not_cancelled(status)

def current_month_reference_date(day: int) -> str:
    hoje = date.today()
    safe_day = min(clamp_due_day(day), 28)
    return date(hoje.year, hoje.month, safe_day).isoformat()

ADMIN_HIDDEN_COLUMNS = {
    "id",
    "evento_id",
    "created_at",
    "updated_at",
    "data_vencimento_mensalidade",
    "categoria_ordem",
    "data_ordem",
    "data_original_ordem",
    "data_reposicao_ordem",
}

def clean_admin_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove colunas técnicas das tabelas visíveis no painel administrativo."""
    if df is None or df.empty:
        return df
    display_df = df.copy()
    hidden = [col for col in ADMIN_HIDDEN_COLUMNS if col in display_df.columns]
    if hidden:
        display_df = display_df.drop(columns=hidden, errors="ignore")
    return display_df

def parse_date_or_today(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value.strip()[:10], fmt).date()
            except ValueError:
                pass
    return date.today()

def parse_date_optional(value: Any) -> Optional[date]:
    """Converte datas do Supabase com segurança, sem quebrar o painel administrativo."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except Exception:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw[:10], fmt).date()
            except ValueError:
                pass
    return None

def is_not_cancelled(value: Any) -> bool:
    status = str(value or "").strip().lower()
    return status not in {"cancelado", "cancelada", "cancelled", "cancelada/pago"}

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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        :root{
            --tl-navy:#07111f;
            --tl-navy-2:#0d2238;
            --tl-slate:#14263b;
            --tl-lime:#c9ff12;
            --tl-lime-2:#9fd900;
            --tl-soft:#f6ffe6;
            --tl-white:#ffffff;
            --tl-muted:#93a4b7;
            --tl-line:rgba(201,255,18,.24);
            --tl-card:rgba(255,255,255,.94);
            --tl-shadow:0 28px 80px rgba(7,17,31,.18);
        }

        html, body, [class*="css"], .stApp {
            font-family:'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            -webkit-font-smoothing:antialiased;
            text-rendering:optimizeLegibility;
        }

        .stApp, [data-testid="stAppViewContainer"]{
            background:
                radial-gradient(circle at 50% -10%, rgba(201,255,18,.34), transparent 28rem),
                radial-gradient(circle at 100% 6%, rgba(15,55,89,.38), transparent 24rem),
                linear-gradient(180deg, #07111f 0%, #0d2238 18rem, #f7faef 18.05rem, #ffffff 100%) !important;
            color:var(--tl-navy);
            overflow-x:hidden !important;
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        footer {
            visibility:hidden !important;
            height:0 !important;
        }

        .main .block-container,
        .block-container{
            max-width:1120px !important;
            padding-top:1.2rem !important;
            padding-bottom:4rem !important;
        }

        [data-testid="stSidebar"]{
            background:linear-gradient(180deg, #07111f 0%, #0d2238 100%) !important;
            border-right:1px solid rgba(201,255,18,.22) !important;
            color:white !important;
        }
        [data-testid="stSidebar"] *{ color:white !important; }
        [data-testid="stSidebar"] input{
            background:rgba(255,255,255,.08) !important;
            border:1px solid rgba(201,255,18,.35) !important;
            color:white !important;
            -webkit-text-fill-color:white !important;
        }

        /* Admin mobile open button */
        button[data-testid="collapsedControl"]{
            position:fixed !important;
            top:12px !important;
            left:12px !important;
            z-index:999999 !important;
            width:54px !important;
            height:54px !important;
            border-radius:999px !important;
            border:1px solid rgba(201,255,18,.65) !important;
            background:linear-gradient(180deg, var(--tl-lime), var(--tl-lime-2)) !important;
            box-shadow:0 14px 32px rgba(0,0,0,.26) !important;
            color:#06101c !important;
        }

        .tl-hero{
            text-align:center;
            position:relative;
            overflow:hidden;
            padding:34px 26px 30px;
            border-radius:38px;
            margin:14px auto 22px;
            background:
                radial-gradient(circle at 50% 0%, rgba(201,255,18,.22), transparent 20rem),
                linear-gradient(145deg, rgba(10,26,44,.98), rgba(7,17,31,.98));
            border:1px solid rgba(201,255,18,.28);
            box-shadow:0 32px 90px rgba(0,0,0,.28);
        }
        .tl-hero:before{
            content:"";
            position:absolute;
            inset:-20%;
            background:
                linear-gradient(120deg, transparent 25%, rgba(255,255,255,.06) 26%, transparent 28%),
                radial-gradient(circle at 12% 25%, rgba(201,255,18,.18), transparent 18rem);
            pointer-events:none;
        }
        .tl-logo-shell{
            width:176px;
            height:176px;
            margin:0 auto 18px;
            display:flex;
            align-items:center;
            justify-content:center;
            border-radius:50%;
            background:rgba(255,255,255,.96);
            border:1px solid rgba(201,255,18,.50);
            box-shadow:
                0 24px 60px rgba(0,0,0,.35),
                0 0 0 10px rgba(255,255,255,.035),
                inset 0 0 0 1px rgba(255,255,255,.86);
        }
        .tl-logo-shell img{
            max-width:138px !important;
            max-height:138px !important;
            object-fit:contain !important;
            display:block !important;
            filter:drop-shadow(0 10px 20px rgba(0,0,0,.18));
        }
        .tl-title{
            position:relative;
            color:#fff;
            font-size:clamp(2.4rem, 5vw, 4.8rem);
            line-height:.92;
            font-weight:950;
            letter-spacing:-.075em;
            margin:0 0 12px;
        }
        .tl-subtitle{
            position:relative;
            max-width:720px;
            margin:0 auto 22px;
            color:rgba(255,255,255,.82);
            font-size:1.06rem;
            line-height:1.55;
            font-weight:600;
        }
        .tl-pill-row{
            position:relative;
            display:flex;
            flex-wrap:wrap;
            justify-content:center;
            gap:10px;
        }
        .tl-pill{
            color:#07111f !important;
            text-decoration:none !important;
            font-weight:900;
            letter-spacing:-.02em;
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-height:46px;
            padding:0 18px;
            border-radius:999px;
            background:linear-gradient(180deg, #dfff49, var(--tl-lime-2));
            border:1px solid rgba(255,255,255,.34);
            box-shadow:0 14px 34px rgba(142,190,0,.24);
            transition:.18s ease;
        }
        .tl-pill:hover{ transform:translateY(-2px); filter:brightness(1.02); }

        .tl-card,
        .tl-checkin,
        .tl-admin,
        .tl-plan,
        .tl-pix-box,
        div[data-testid="stForm"]{
            border-radius:30px !important;
            border:1px solid rgba(201,255,18,.32) !important;
            background:var(--tl-card) !important;
            box-shadow:var(--tl-shadow) !important;
            backdrop-filter:blur(18px) !important;
        }
        .tl-card,.tl-checkin,.tl-admin{
            padding:24px !important;
            margin-bottom:22px !important;
        }

        .tl-section{
            font-size:clamp(1.65rem, 2.6vw, 2.35rem);
            line-height:1.05;
            font-weight:950;
            letter-spacing:-.055em;
            color:var(--tl-navy) !important;
            margin-bottom:8px;
        }
        .tl-caption{
            color:#53647a !important;
            font-weight:600;
            font-size:1.02rem;
            line-height:1.55;
            margin-bottom:18px;
        }

        .tl-premium-strip{
            display:grid;
            grid-template-columns:repeat(3,1fr);
            gap:12px;
            margin:18px 0 4px;
        }
        .tl-premium-mini{
            padding:14px;
            border-radius:20px;
            background:rgba(255,255,255,.08);
            border:1px solid rgba(201,255,18,.20);
            color:rgba(255,255,255,.86);
            font-weight:800;
        }
        .tl-premium-mini strong{
            display:block;
            color:var(--tl-lime);
            font-size:1.2rem;
        }

        /* Forms */
        label, .stTextInput label, .stTextArea label, .stDateInput label,
        .stNumberInput label, .stSelectbox label{
            color:#172033 !important;
            opacity:1 !important;
            font-weight:850 !important;
            letter-spacing:-.025em;
        }
        .stTextInput input,
        .stTextArea textarea,
        .stDateInput input,
        .stNumberInput input,
        div[data-testid="stSelectbox"] > div,
        .stSelectbox div[data-baseweb="select"] > div{
            color:#101827 !important;
            -webkit-text-fill-color:#101827 !important;
            background:#fbfff1 !important;
            border:1.5px solid rgba(159,217,0,.62) !important;
            border-radius:18px !important;
            min-height:50px !important;
            box-shadow:inset 0 0 0 1px rgba(255,255,255,.65) !important;
            outline:none !important;
            font-size:16px !important;
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stDateInput input:focus,
        .stNumberInput input:focus{
            border-color:var(--tl-lime-2) !important;
            box-shadow:0 0 0 4px rgba(201,255,18,.22) !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton button,
        button[kind="primary"],
        button[kind="secondary"]{
            width:100%;
            border-radius:999px !important;
            min-height:50px !important;
            font-weight:950 !important;
            letter-spacing:-.03em;
            border:1px solid rgba(7,17,31,.12) !important;
            background:linear-gradient(180deg, #dfff49, var(--tl-lime-2)) !important;
            color:#07111f !important;
            box-shadow:0 16px 34px rgba(135,176,0,.24) !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"]{
            gap:10px;
            border-bottom:1px solid rgba(7,17,31,.10);
        }
        .stTabs [data-baseweb="tab"]{
            border-radius:999px 999px 0 0;
            padding:12px 18px;
            font-weight:900;
        }
        .stTabs [aria-selected="true"]{
            background:linear-gradient(180deg, #dfff49, var(--tl-lime-2)) !important;
            color:#07111f !important;
        }

        /* Event / tournament */
        .tl-event-hero{
            background:
                radial-gradient(circle at 90% 0%, rgba(201,255,18,.24), transparent 16rem),
                linear-gradient(135deg,#07111f 0%, #123653 100%) !important;
            color:#ffffff !important;
            border-radius:34px !important;
            padding:28px !important;
            margin-bottom:20px !important;
            box-shadow:0 28px 80px rgba(7,17,31,.22) !important;
            border:1px solid rgba(201,255,18,.25) !important;
        }
        .tl-event-hero-title{
            font-size:clamp(1.8rem,3.5vw,3rem);
            font-weight:950;
            line-height:1;
            letter-spacing:-.055em;
            margin-bottom:12px;
            color:#fff !important;
        }
        .tl-event-hero-text{
            font-size:1.08rem;
            line-height:1.55;
            color:rgba(255,255,255,.86) !important;
            font-weight:600;
        }
        .tl-event-card{
            background:#ffffff;
            border:1px solid rgba(201,255,18,.42);
            border-radius:28px;
            padding:22px;
            margin-bottom:16px;
            box-shadow:0 20px 50px rgba(7,17,31,.08);
        }
        .tl-event-title{
            font-size:1.35rem;
            line-height:1.12;
            font-weight:950;
            letter-spacing:-.045em;
            color:#0d2238;
            margin-bottom:6px;
        }
        .tl-event-meta{
            color:#53647a;
            font-weight:800;
            margin-bottom:10px;
        }
        .tl-event-desc{
            color:#26384d;
            font-weight:600;
            line-height:1.45;
            margin-bottom:12px;
        }
        .tl-plan-inline{
            background:#f1ffd2;
            border:1px solid rgba(159,217,0,.35);
            color:#102014;
            border-radius:18px;
            padding:13px 15px;
            font-weight:900;
            margin:10px 0 14px 0;
        }

        /* Confirmation after tournament */
        .tl-confirm-card{
            background:linear-gradient(180deg,#efffe6 0%, #ddf8d8 100%);
            border:1px solid rgba(33,180,75,.24);
            border-radius:32px;
            padding:26px;
            margin:16px 0 22px;
            box-shadow:0 24px 60px rgba(33,180,75,.12);
        }
        .tl-confirm-title{
            font-size:clamp(1.65rem,3vw,2.3rem);
            font-weight:950;
            color:#155d33;
            letter-spacing:-.05em;
            margin-bottom:12px;
        }
        .tl-confirm-text{
            font-size:1.1rem;
            line-height:1.55;
            color:#28643d;
            font-weight:650;
            margin-bottom:16px;
        }
        .tl-confirm-value{
            background:#ffffff;
            border:2px solid #cdecc6;
            border-radius:24px;
            padding:16px;
            text-align:center;
            font-size:1.9rem;
            font-weight:950;
            color:#15683c;
            margin-bottom:18px;
        }
        .tl-pix-stage{
            background:#ffffff;
            border:1px solid rgba(7,17,31,.12);
            border-radius:26px;
            padding:22px;
            margin-bottom:18px;
            box-shadow:0 18px 42px rgba(7,17,31,.08);
        }
        .tl-pix-stage-title{
            color:#1e6a3d;
            font-size:1.22rem;
            font-weight:950;
            text-align:center;
            margin-bottom:8px;
        }
        .tl-pix-stage-name{
            color:#2b6b43;
            font-size:1.05rem;
            text-align:center;
            font-weight:800;
            margin-bottom:10px;
        }
        .tl-pix-stage-key{
            color:#08162e;
            font-size:1.65rem;
            font-weight:950;
            text-align:center;
            line-height:1.1;
            margin-bottom:14px;
            word-break:break-word;
        }
        .tl-proof-btn{
            display:block;
            width:100%;
            text-align:center;
            text-decoration:none;
            padding:16px 18px;
            border-radius:999px;
            background:linear-gradient(180deg,#23bd52,#188c3a);
            color:#ffffff !important;
            font-size:1.1rem;
            font-weight:950;
            margin-top:10px;
            box-shadow:0 16px 34px rgba(24,140,58,.22);
        }
        .tl-confirm-card{
            background:
                radial-gradient(circle at 90% 0%, rgba(201,255,18,.12), transparent 16rem),
                linear-gradient(135deg, rgba(7,17,31,.96), rgba(15,74,35,.92));
            border:1px solid rgba(201,255,18,.28);
            border-radius:32px;
            padding:26px;
            margin:16px 0 22px;
            box-shadow:0 24px 60px rgba(0,0,0,.20);
        }
        .tl-confirm-title{
            font-size:clamp(1.65rem,3vw,2.3rem);
            font-weight:950;
            color:#ffffff !important;
            letter-spacing:-.05em;
            margin-bottom:12px;
            text-shadow:0 6px 18px rgba(0,0,0,.28);
        }
        .tl-confirm-text{
            font-size:1.1rem;
            line-height:1.6;
            color:rgba(255,255,255,.96) !important;
            font-weight:700;
            margin-bottom:16px;
            text-shadow:0 4px 12px rgba(0,0,0,.22);
        }
        .tl-confirm-text strong{
            color:#ffffff !important;
        }
        .tl-confirm-list{
            margin-top:16px;
            padding:18px 20px;
            border-radius:24px;
            background:rgba(255,255,255,.08);
            border:1px solid rgba(201,255,18,.18);
        }
        .tl-confirm-list-title{
            color:#ffffff !important;
            font-weight:900;
            margin-bottom:10px;
        }
        .tl-confirm-list ol{
            margin:0 0 0 1rem;
            padding:0;
        }
        .tl-confirm-list li{
            color:rgba(255,255,255,.90) !important;
            margin:0 0 8px 0;
            line-height:1.45;
            font-weight:600;
        }
        .tl-copy-btn{
            width:100%;
            min-height:50px;
            border-radius:999px;
            border:1px solid rgba(7,17,31,.10);
            background:linear-gradient(180deg, #dfff49, #9fd900);
            color:#07111f !important;
            font-size:1.1rem;
            font-weight:950;
            box-shadow:0 16px 34px rgba(135,176,0,.24);
            cursor:pointer;
        }

        /* Finance price cards */
        .tl-plan{
            overflow:hidden !important;
            margin-bottom:18px !important;
            background:#07111f !important;
            border:1px solid rgba(201,255,18,.28) !important;
            box-shadow:0 24px 60px rgba(7,17,31,.16) !important;
        }
        .tl-plan-head{
            background:linear-gradient(180deg,#dfff49,var(--tl-lime-2)) !important;
            color:#07111f !important;
            font-weight:950 !important;
            font-size:1.28rem !important;
            text-align:center !important;
            padding:18px 16px !important;
        }
        .tl-plan-sub{
            display:block;
            font-size:.9rem;
            margin-top:4px;
        }
        .tl-plan-body{
            padding:18px !important;
            color:white !important;
        }
        .tl-tag{
            display:inline-block;
            background:rgba(201,255,18,.12);
            border:1px solid rgba(201,255,18,.28);
            color:var(--tl-lime);
            border-radius:999px;
            padding:8px 12px;
            font-weight:900;
            margin-bottom:10px;
        }
        .tl-price-row{
            display:flex;
            justify-content:space-between;
            gap:14px;
            color:white;
            border-bottom:1px solid rgba(255,255,255,.10);
            padding:11px 0;
        }
        .tl-price-row strong{ color:white; }
        .tl-price-row:last-child{ border-bottom:none; }
        .tl-foot{
            background:rgba(201,255,18,.12);
            border-top:1px solid rgba(201,255,18,.18);
            color:#eaffb8;
            padding:14px 16px;
            font-weight:850;
        }
        .tl-pix-box{
            background:linear-gradient(180deg,#ffffff,#f6ffe6) !important;
            border:1px solid rgba(201,255,18,.42) !important;
            border-radius:28px !important;
            padding:20px !important;
            margin-top:18px !important;
        }
        .tl-green-label{ color:#315000; font-weight:950; }

        .tl-alert-ok,.tl-alert-warn,.tl-alert-error{
            border-radius:20px; padding:15px; margin:10px 0; font-weight:850;
        }
        .tl-alert-ok{ background:#efffd4; border:1px solid #cfe96a; color:#2f4909; }
        .tl-alert-warn{ background:#fff4d9; border:1px solid #ffd26b; color:#5a3900; }
        .tl-alert-error{ background:#ffe7e7; border:1px solid #ffb7b7; color:#611313; }
        .tl-group-title{
            margin-top:12px; margin-bottom:8px; color:#0d2238; font-weight:950; font-size:1.18rem;
        }

        /* Aula experimental */
        .tl-experimental{
            background:
                radial-gradient(circle at 100% 0%, rgba(201,255,18,.18), transparent 16rem),
                linear-gradient(135deg, #07111f 0%, #123653 100%) !important;
            color:#fff !important;
            border:1px solid rgba(201,255,18,.28) !important;
        }
        .tl-experimental .tl-section,
        .tl-experimental .tl-caption{ color:white !important; }
        .tl-experimental .tl-caption{ color:rgba(255,255,255,.82) !important; }

        @media(max-width:768px){
            .main .block-container,.block-container{
                max-width:100% !important;
                padding-left:1rem !important;
                padding-right:1rem !important;
                padding-top:.85rem !important;
            }
            .tl-hero{
                padding:26px 16px 22px !important;
                border-radius:30px !important;
                margin-top:10px !important;
            }
            .tl-logo-shell{
                width:132px !important;
                height:132px !important;
                margin-bottom:14px !important;
            }
            .tl-logo-shell img{
                max-width:104px !important;
                max-height:104px !important;
            }
            .tl-title{
                font-size:2.15rem !important;
                line-height:1 !important;
            }
            .tl-subtitle{
                font-size:.98rem !important;
                line-height:1.45 !important;
            }
            .tl-pill-row{
                display:grid !important;
                grid-template-columns:1fr !important;
                width:100% !important;
                gap:9px !important;
            }
            .tl-pill{
                width:100% !important;
                box-sizing:border-box !important;
                padding:0 12px !important;
            }
            .tl-premium-strip{
                grid-template-columns:1fr !important;
            }
            [data-testid="stHorizontalBlock"]{
                flex-wrap:wrap !important;
                gap:.25rem !important;
            }
            [data-testid="stHorizontalBlock"] > div{
                min-width:100% !important;
                flex:1 1 100% !important;
            }
            .tl-card,.tl-checkin,.tl-admin,div[data-testid="stForm"]{
                padding:16px !important;
                border-radius:24px !important;
                box-sizing:border-box !important;
            }
            .tl-section{
                font-size:1.7rem !important;
            }
            .tl-event-hero-title{font-size:1.65rem !important;}
            .tl-confirm-value{font-size:1.45rem !important;}
            .tl-pix-stage-key{font-size:1.22rem !important;}
            .stTabs [data-baseweb="tab-list"]{
                overflow-x:auto !important;
                flex-wrap:nowrap !important;
                padding-bottom:5px !important;
            }
            .stTabs [data-baseweb="tab"]{
                min-width:max-content !important;
                padding:10px 12px !important;
                font-size:.95rem !important;
            }
        }
        

/* =========================
   AJUSTE FINAL DE VISIBILIDADE E MARCA
   ========================= */
.stApp, [data-testid="stAppViewContainer"]{
    background:
        radial-gradient(circle at 50% -8%, rgba(201,255,18,.22), transparent 26rem),
        linear-gradient(180deg, #07111f 0%, #0e2b32 34rem, #f7fbef 34.05rem, #ffffff 100%) !important;
}
.tl-hero{
    text-align:center !important;
    padding:34px 18px 26px !important;
    background:
        radial-gradient(circle at 50% 4%, rgba(201,255,18,.16), transparent 18rem),
        linear-gradient(145deg, rgba(7,17,31,.98), rgba(14,43,50,.98)) !important;
}
.tl-logo-shell{
    width:230px !important;
    height:auto !important;
    margin:0 auto 18px !important;
    padding:0 !important;
    background:transparent !important;
    border:none !important;
    border-radius:0 !important;
    box-shadow:none !important;
}
.tl-logo-shell img{
    max-width:230px !important;
    max-height:230px !important;
    width:230px !important;
    height:auto !important;
    object-fit:contain !important;
    filter:drop-shadow(0 18px 30px rgba(0,0,0,.45)) drop-shadow(0 0 16px rgba(201,255,18,.22)) !important;
}
.tl-title{
    color:#ffffff !important;
    text-shadow:0 8px 22px rgba(0,0,0,.35) !important;
}
.tl-subtitle{
    color:rgba(255,255,255,.92) !important;
    text-shadow:0 6px 18px rgba(0,0,0,.28) !important;
}
.tl-premium-strip,
.tl-premium-mini{
    display:none !important;
}

/* Abas legíveis para alunos e admin */
.stTabs [data-baseweb="tab-list"]{
    background:rgba(7,17,31,.95) !important;
    border:1px solid rgba(201,255,18,.22) !important;
    border-radius:24px !important;
    padding:8px !important;
    gap:8px !important;
    box-shadow:0 16px 34px rgba(7,17,31,.18) !important;
}
.stTabs [data-baseweb="tab"]{
    color:#ffffff !important;
    font-weight:850 !important;
    border-radius:999px !important;
    min-height:42px !important;
}
.stTabs [data-baseweb="tab"] p{
    color:inherit !important;
}
.stTabs [aria-selected="true"]{
    background:linear-gradient(180deg, #dfff49, #9fd900) !important;
    color:#07111f !important;
}
.stTabs [aria-selected="true"] p{
    color:#07111f !important;
}

/* Cartões claros sempre com texto escuro legível */
.tl-card, .tl-checkin, .tl-admin, div[data-testid="stForm"]{
    background:rgba(255,255,255,.96) !important;
}
.tl-card *, .tl-checkin *, .tl-admin *, div[data-testid="stForm"] *{
    text-shadow:none !important;
}

/* Mantém admin fora da comunicação pública: só pela sidebar */
[data-testid="stSidebar"]{
    z-index:999999 !important;
}

@media(max-width:768px){
    .tl-logo-shell{
        width:178px !important;
        margin-bottom:14px !important;
    }
    .tl-logo-shell img{
        width:178px !important;
        max-width:178px !important;
        max-height:178px !important;
    }
    .tl-hero{
        padding:28px 16px 24px !important;
    }
    .tl-title{
        font-size:2.2rem !important;
        line-height:1.02 !important;
    }
    .tl-subtitle{
        font-size:1rem !important;
        line-height:1.45 !important;
    }
    .stTabs [data-baseweb="tab-list"]{
        overflow-x:auto !important;
        flex-wrap:nowrap !important;
    }
    .stTabs [data-baseweb="tab"]{
        min-width:max-content !important;
    }
}



/* =========================
   CORREÇÃO FINAL — VISIBILIDADE, FUNDO ÚNICO E ADMIN DISCRETO
   ========================= */

/* Fundo único premium para evitar choque entre fundo branco e escuro */
.stApp, [data-testid="stAppViewContainer"]{
    background:
        radial-gradient(circle at 50% -5%, rgba(201,255,18,.20), transparent 26rem),
        linear-gradient(180deg, #07111f 0%, #0e2b32 100%) !important;
    color:#ffffff !important;
}

/* Área principal sem faixas brancas */
.main .block-container,
.block-container{
    background:transparent !important;
}

/* Header com logo transparente, grande, com aura premium */
.tl-hero{
    background:
        radial-gradient(circle at 50% 0%, rgba(201,255,18,.18), transparent 16rem),
        linear-gradient(145deg, rgba(7,17,31,.96), rgba(14,43,50,.96)) !important;
    border:1px solid rgba(201,255,18,.30) !important;
    box-shadow:0 30px 90px rgba(0,0,0,.26) !important;
    border-radius:34px !important;
    padding:30px 18px 28px !important;
}
.tl-logo-shell{
    width:240px !important;
    height:auto !important;
    margin:0 auto 18px !important;
    padding:0 !important;
    background:transparent !important;
    border:none !important;
    border-radius:0 !important;
    box-shadow:none !important;
}
.tl-logo-shell img{
    width:240px !important;
    max-width:240px !important;
    height:auto !important;
    object-fit:contain !important;
    filter:
      drop-shadow(0 0 2px rgba(255,255,255,.95))
      drop-shadow(0 14px 24px rgba(0,0,0,.40))
      drop-shadow(0 0 18px rgba(201,255,18,.18)) !important;
}
.tl-title{
    color:#ffffff !important;
    text-shadow:0 8px 22px rgba(0,0,0,.36) !important;
}
.tl-subtitle{
    color:rgba(255,255,255,.92) !important;
    text-shadow:0 5px 16px rgba(0,0,0,.26) !important;
}

/* Remove definitivamente cards públicos de admin/benefícios técnicos */
.tl-premium-strip,
.tl-premium-mini{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    overflow:hidden !important;
}

/* Cards e formulários: fundo claro controlado, texto escuro legível */
.tl-card,
.tl-checkin,
.tl-admin,
div[data-testid="stForm"]{
    background:#ffffff !important;
    border:1px solid rgba(201,255,18,.42) !important;
    color:#07111f !important;
    box-shadow:0 24px 70px rgba(0,0,0,.18) !important;
}
.tl-card *,
.tl-checkin *,
.tl-admin *,
div[data-testid="stForm"] *{
    color:inherit;
    text-shadow:none !important;
}
.tl-section{
    color:#07111f !important;
}
.tl-caption{
    color:#405168 !important;
}

/* Seções escuras internas ficam legíveis */
.tl-event-hero,
.tl-experimental{
    background:linear-gradient(135deg,#07111f 0%,#0e2b32 100%) !important;
    color:#ffffff !important;
}
.tl-event-hero *,
.tl-experimental .tl-section,
.tl-experimental .tl-caption{
    color:#ffffff !important;
}

/* Abas: fundo escuro e texto sempre visível */
.stTabs [data-baseweb="tab-list"]{
    background:rgba(7,17,31,.96) !important;
    border:1px solid rgba(201,255,18,.28) !important;
    border-radius:22px !important;
    padding:8px !important;
    gap:8px !important;
    box-shadow:0 18px 40px rgba(0,0,0,.22) !important;
}
.stTabs [data-baseweb="tab"]{
    color:#ffffff !important;
    font-weight:850 !important;
    border-radius:999px !important;
}
.stTabs [data-baseweb="tab"] p{
    color:inherit !important;
}
.stTabs [aria-selected="true"]{
    background:linear-gradient(180deg,#dfff49,#9fd900) !important;
    color:#07111f !important;
}
.stTabs [aria-selected="true"] p{
    color:#07111f !important;
}

/* Inputs sempre legíveis */
.stTextInput input,
.stTextArea textarea,
.stDateInput input,
.stNumberInput input,
div[data-testid="stSelectbox"] > div,
.stSelectbox div[data-baseweb="select"] > div{
    background:#fbfff2 !important;
    color:#07111f !important;
    -webkit-text-fill-color:#07111f !important;
    border:1.6px solid rgba(159,217,0,.74) !important;
}
label, .stTextInput label, .stTextArea label, .stDateInput label,
.stNumberInput label, .stSelectbox label{
    color:#07111f !important;
    opacity:1 !important;
}

/* Login admin: somente botão discreto pela seta/sidebar, sem texto público */
button[data-testid="collapsedControl"]{
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:52px !important;
    height:52px !important;
    border-radius:999px !important;
    border:1px solid rgba(201,255,18,.65) !important;
    background:linear-gradient(180deg,#dfff49,#9fd900) !important;
    box-shadow:0 14px 32px rgba(0,0,0,.28) !important;
    color:#07111f !important;
}

/* Sidebar admin preservada */
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#07111f 0%,#0e2b32 100%) !important;
    color:#ffffff !important;
    border-right:1px solid rgba(201,255,18,.25) !important;
}
[data-testid="stSidebar"] *{
    color:#ffffff !important;
}

/* Financeiro/cards escuros continuam legíveis */
.tl-plan{
    background:#07111f !important;
    color:#ffffff !important;
}
.tl-plan *{
    color:inherit;
}
.tl-plan-head{
    color:#07111f !important;
}
.tl-price-row,
.tl-price-row strong{
    color:#ffffff !important;
}
.tl-foot{
    color:#eaffb8 !important;
}

/* Mobile */
@media(max-width:768px){
    .tl-logo-shell{
        width:190px !important;
    }
    .tl-logo-shell img{
        width:190px !important;
        max-width:190px !important;
    }
    .tl-hero{
        padding:26px 14px 24px !important;
        border-radius:28px !important;
    }
    .tl-title{
        font-size:2.2rem !important;
        line-height:1.02 !important;
    }
    .tl-subtitle{
        font-size:1rem !important;
        line-height:1.45 !important;
    }
    .stTabs [data-baseweb="tab-list"]{
        overflow-x:auto !important;
        flex-wrap:nowrap !important;
    }
    .stTabs [data-baseweb="tab"]{
        min-width:max-content !important;
    }
}



/* Ajuste final:  discreto + logo branca legível */
.tl-admin-pill{
    background:rgba(255,255,255,.08) !important;
    color:#ffffff !important;
    border:1px solid rgba(255,255,255,.22) !important;
    box-shadow:none !important;
}
.tl-admin-pill:hover{
    background:rgba(255,255,255,.14) !important;
}
.tl-admin-login-link{
    max-width:520px;
    margin:18px auto 8px;
    padding:12px 16px;
    border-radius:999px;
    background:rgba(255,255,255,.08);
    border:1px solid rgba(201,255,18,.20);
    color:rgba(255,255,255,.78);
    text-align:center;
    font-size:.92rem;
    font-weight:700;
}
.tl-logo-shell img{
    filter:
      drop-shadow(0 0 2px rgba(255,255,255,.98))
      drop-shadow(0 16px 26px rgba(0,0,0,.45))
      drop-shadow(0 0 18px rgba(201,255,18,.24)) !important;
}
@media(max-width:768px){
    .tl-admin-pill{
        order:99;
    }
    .tl-admin-login-link{
        font-size:.84rem;
        margin-top:14px;
    }
}



/* AJUSTE DEFINITIVO: admin só na lateral + logo corrigida */
.tl-admin-pill,
.tl-admin-login-link,
a[href="#admin-login"]{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    overflow:hidden !important;
}

button[data-testid="collapsedControl"]{
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:54px !important;
    height:54px !important;
    border-radius:999px !important;
    border:1px solid rgba(255,255,255,.90) !important;
    background:#ffffff !important;
    box-shadow:0 14px 32px rgba(0,0,0,.30) !important;
    color:#07111f !important;
}
button[data-testid="collapsedControl"] svg{
    color:#07111f !important;
    fill:#07111f !important;
    stroke:#07111f !important;
}

.tl-logo-shell{
    width:250px !important;
    margin:0 auto 18px !important;
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
}
.tl-logo-shell img{
    width:250px !important;
    max-width:250px !important;
    height:auto !important;
    object-fit:contain !important;
    filter:
      drop-shadow(0 16px 28px rgba(0,0,0,.42))
      drop-shadow(0 0 18px rgba(201,255,18,.20)) !important;
}

@media(max-width:768px){
    .tl-logo-shell{
        width:200px !important;
    }
    .tl-logo-shell img{
        width:200px !important;
        max-width:200px !important;
    }
}



/* CORREÇÃO 100%: botão ADM funcional + logo original limpa */
.{
    position:fixed !important;
    top:14px !important;
    left:14px !important;
    z-index:999999 !important;
    width:58px !important;
    height:42px !important;
    border-radius:999px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    background:#ffffff !important;
    color:#07111f !important;
    border:1px solid rgba(255,255,255,.92) !important;
    box-shadow:0 14px 32px rgba(0,0,0,.34) !important;
    text-decoration:none !important;
    font-weight:950 !important;
    font-size:.92rem !important;
    letter-spacing:.02em !important;
}
.:hover{
    filter:brightness(.96) !important;
    transform:translateY(-1px) !important;
}

/* Esconde mensagens antigas de admin público, caso estejam em cache/CSS */
.tl-admin-pill,
.tl-admin-login-link,
a[href="#admin-login"]{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    overflow:hidden !important;
}

/* Painel direto de login só aparece após clicar no botão ADM */
.{
    max-width:560px !important;
    margin:18px auto 22px !important;
    padding:20px !important;
    border-radius:26px !important;
    background:#ffffff !important;
    border:1px solid rgba(201,255,18,.42) !important;
    box-shadow:0 24px 70px rgba(0,0,0,.22) !important;
    color:#07111f !important;
}
.tl-admin-direct-title{
    font-size:1.45rem !important;
    font-weight:950 !important;
    color:#07111f !important;
    margin-bottom:12px !important;
    text-align:center !important;
}

/* Logo original: sem recorte e sem conversão de cor */
.tl-logo-shell{
    width:250px !important;
    height:auto !important;
    margin:0 auto 18px !important;
    padding:12px !important;
    background:#ffffff !important;
    border:1px solid rgba(201,255,18,.42) !important;
    border-radius:32px !important;
    box-shadow:0 18px 38px rgba(0,0,0,.34) !important;
}
.tl-logo-shell img{
    width:100% !important;
    max-width:100% !important;
    height:auto !important;
    object-fit:contain !important;
    filter:none !important;
    display:block !important;
    border-radius:22px !important;
}

/* Mantém botão lateral padrão do Streamlit discreto, mas o principal agora é o ADM fixo */
button[data-testid="collapsedControl"]{
    background:#ffffff !important;
    color:#07111f !important;
    border:1px solid rgba(255,255,255,.90) !important;
}

@media(max-width:768px){
    .{
        top:10px !important;
        left:10px !important;
        width:54px !important;
        height:38px !important;
        font-size:.84rem !important;
    }
    .tl-logo-shell{
        width:210px !important;
        padding:10px !important;
        border-radius:28px !important;
    }
}



/* FINAL: ADMIN APENAS NA SETA LATERAL/SIDEBAR */
.,
.tl-admin-pill,
.tl-admin-login-link,
.,
a[href="#admin-login"],
a[href="?admin=1#"]{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    width:0 !important;
    overflow:hidden !important;
    pointer-events:none !important;
}

/* Botão/seta lateral do Streamlit visível para abrir a área administrativa */
button[data-testid="collapsedControl"]{
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:54px !important;
    height:54px !important;
    border-radius:999px !important;
    border:1px solid rgba(255,255,255,.92) !important;
    background:#ffffff !important;
    box-shadow:0 14px 32px rgba(0,0,0,.30) !important;
    color:#07111f !important;
}
button[data-testid="collapsedControl"] svg{
    color:#07111f !important;
    fill:#07111f !important;
    stroke:#07111f !important;
}

/* Logo: arquivo já tem fundo externo transparente e fundo branco interno */
.tl-logo-shell{
    width:250px !important;
    height:auto !important;
    margin:0 auto 18px !important;
    padding:0 !important;
    background:transparent !important;
    border:none !important;
    border-radius:0 !important;
    box-shadow:none !important;
}
.tl-logo-shell img{
    width:250px !important;
    max-width:250px !important;
    height:auto !important;
    object-fit:contain !important;
    border-radius:0 !important;
    filter:drop-shadow(0 16px 30px rgba(0,0,0,.38)) !important;
}

@media(max-width:768px){
    .tl-logo-shell{
        width:210px !important;
    }
    .tl-logo-shell img{
        width:210px !important;
        max-width:210px !important;
    }
}



/* VERIFICAÇÃO FINAL — admin apenas pela seta/sidebar e associação correta */
.,
.tl-admin-pill,
.tl-admin-login-link,
.,
a[href="#admin-login"],
a[href="?admin=1#"]{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    width:0 !important;
    overflow:hidden !important;
    pointer-events:none !important;
}
button[data-testid="collapsedControl"]{
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:54px !important;
    height:54px !important;
    border-radius:999px !important;
    border:1px solid rgba(255,255,255,.92) !important;
    background:#ffffff !important;
    box-shadow:0 14px 32px rgba(0,0,0,.30) !important;
    color:#07111f !important;
}
button[data-testid="collapsedControl"] svg{
    color:#07111f !important;
    fill:#07111f !important;
    stroke:#07111f !important;
}
.tl-assoc-label{
    display:inline-flex;
    margin-top:14px;
    padding:9px 14px;
    border-radius:999px;
    background:rgba(201,255,18,.14);
    border:1px solid rgba(201,255,18,.32);
    color:#dfff49 !important;
    font-weight:900;
    letter-spacing:-.02em;
}



/* DEFINITIVO: ADMIN SOMENTE PELA SETA/SIDEBAR */
a[href="#admin-login"],
a[href=""],
.tl-admin-pill,
.tl-admin-login-link{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    width:0 !important;
    overflow:hidden !important;
    pointer-events:none !important;
}

/* Seta/botão lateral do Streamlit visível como nas versões antigas */
button[data-testid="collapsedControl"]{
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:54px !important;
    height:54px !important;
    border-radius:999px !important;
    border:1px solid rgba(255,255,255,.92) !important;
    background:#ffffff !important;
    box-shadow:0 14px 32px rgba(0,0,0,.30) !important;
    color:#07111f !important;
}
button[data-testid="collapsedControl"] svg{
    color:#07111f !important;
    fill:#07111f !important;
    stroke:#07111f !important;
}

/* Logo: arquivo com fundo externo transparente e fundo branco interno */
.tl-logo-shell{
    width:250px !important;
    height:auto !important;
    margin:0 auto 18px !important;
    padding:0 !important;
    background:transparent !important;
    border:none !important;
    border-radius:0 !important;
    box-shadow:none !important;
}
.tl-logo-shell img{
    width:250px !important;
    max-width:250px !important;
    height:auto !important;
    object-fit:contain !important;
    border-radius:0 !important;
    filter:drop-shadow(0 16px 30px rgba(0,0,0,.38)) !important;
}

@media(max-width:768px){
    .tl-logo-shell{ width:210px !important; }
    .tl-logo-shell img{ width:210px !important; max-width:210px !important; }
}



/* Admin revisado: somente sidebar */
a[href="#admin-login"],
a[href="?admin=1#"],
.tl-admin-pill,
.tl-admin-login-link,
.,
.,
.{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    width:0 !important;
    overflow:hidden !important;
    pointer-events:none !important;
}

button[data-testid="collapsedControl"]{
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:54px !important;
    height:54px !important;
    border-radius:999px !important;
    border:1px solid rgba(255,255,255,.92) !important;
    background:#ffffff !important;
    box-shadow:0 14px 32px rgba(0,0,0,.30) !important;
    color:#07111f !important;
}
button[data-testid="collapsedControl"] svg{
    color:#07111f !important;
    fill:#07111f !important;
    stroke:#07111f !important;
}



/* FINAL ESTÁVEL: ADMIN SOMENTE NA SETA/SIDEBAR DO STREAMLIT */
a[href="#admin-login"],
a[href=""],
.tl-admin-pill,
.tl-admin-login-link,
.,
.,
.{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    width:0 !important;
    overflow:hidden !important;
    pointer-events:none !important;
}

/* Botão/seta lateral nativo do Streamlit sempre visível */
button[data-testid="collapsedControl"]{
    display:flex !important;
    visibility:visible !important;
    opacity:1 !important;
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:54px !important;
    height:54px !important;
    border-radius:999px !important;
    border:1px solid rgba(255,255,255,.92) !important;
    background:#ffffff !important;
    box-shadow:0 14px 32px rgba(0,0,0,.30) !important;
    color:#07111f !important;
}
button[data-testid="collapsedControl"] svg{
    color:#07111f !important;
    fill:#07111f !important;
    stroke:#07111f !important;
}

/* Sidebar preservada para admin */
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#07111f 0%,#0e2b32 100%) !important;
    border-right:1px solid rgba(201,255,18,.28) !important;
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label{
    color:#ffffff !important;
}
[data-testid="stSidebar"] input{
    background:#ffffff !important;
    color:#07111f !important;
    -webkit-text-fill-color:#07111f !important;
    border:1px solid rgba(201,255,18,.65) !important;
}



/* FINAL DO ZERO RENDER: admin somente na seta/sidebar */
a[href="#admin-login"],
a[href="?admin=1#admin-login-panel"],
.tl-admin-pill,
.tl-admin-login-link,
.tl-fixed-admin-btn,
.tl-side-admin-open,
.tl-admin-direct-card{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    width:0 !important;
    overflow:hidden !important;
    pointer-events:none !important;
}

button[data-testid="collapsedControl"]{
    display:flex !important;
    visibility:visible !important;
    opacity:1 !important;
    position:fixed !important;
    top:12px !important;
    left:12px !important;
    z-index:999999 !important;
    width:54px !important;
    height:54px !important;
    border-radius:999px !important;
    border:1px solid rgba(255,255,255,.92) !important;
    background:#ffffff !important;
    box-shadow:0 14px 32px rgba(0,0,0,.30) !important;
    color:#07111f !important;
}
button[data-testid="collapsedControl"] svg{
    color:#07111f !important;
    fill:#07111f !important;
    stroke:#07111f !important;
}

[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#07111f 0%,#0e2b32 100%) !important;
    border-right:1px solid rgba(201,255,18,.28) !important;
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label{
    color:#ffffff !important;
}
[data-testid="stSidebar"] input{
    background:#ffffff !important;
    color:#07111f !important;
    -webkit-text-fill-color:#07111f !important;
    border:1px solid rgba(201,255,18,.65) !important;
}



/* AJUSTE VERDE FINAL — mantém admin/sidebar funcionando */
.stApp, [data-testid="stAppViewContainer"]{
    background:
        radial-gradient(circle at 50% -8%, rgba(204,255,0,.34), transparent 28rem),
        radial-gradient(circle at 100% 4%, rgba(27,94,32,.42), transparent 24rem),
        linear-gradient(180deg, #06130a 0%, #0b2f17 42%, #11451f 100%) !important;
}

.tl-hero{
    background:
        radial-gradient(circle at 50% 0%, rgba(204,255,0,.22), transparent 18rem),
        linear-gradient(145deg, rgba(5,24,10,.98), rgba(10,58,26,.96)) !important;
    border:1px solid rgba(204,255,0,.36) !important;
}

.tl-title{
    color:#ffffff !important;
    text-shadow:0 8px 24px rgba(0,0,0,.38) !important;
}

.tl-subtitle{
    color:rgba(255,255,255,.92) !important;
}

.tl-logo-shell{
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
    padding:0 !important;
}

.tl-logo-shell img{
    filter:
      drop-shadow(0 18px 34px rgba(0,0,0,.45))
      drop-shadow(0 0 20px rgba(204,255,0,.22)) !important;
}

.tl-pill,
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton button,
button[kind="primary"],
button[kind="secondary"]{
    background:linear-gradient(180deg,#dcff42,#a8e000) !important;
    color:#07111f !important;
    border:1px solid rgba(255,255,255,.24) !important;
}

[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#06130a 0%,#0b2f17 100%) !important;
    border-right:1px solid rgba(204,255,0,.28) !important;
}

.tl-assoc-label{
    display:inline-flex;
    margin-top:14px;
    padding:9px 14px;
    border-radius:999px;
    background:rgba(204,255,0,.16);
    border:1px solid rgba(204,255,0,.38);
    color:#dcff42 !important;
    font-weight:950;
    letter-spacing:-.02em;
}



        /* AJUSTE DE LEGIBILIDADE — somente textos que estavam difíceis de ler */
        .tl-event-title{
            color:#f2fbff !important;
            text-shadow:0 2px 10px rgba(0,0,0,.34) !important;
        }

        .tl-event-meta{
            color:#d8e9ff !important;
            font-weight:850 !important;
            text-shadow:0 2px 8px rgba(0,0,0,.28) !important;
        }

        .tl-event-desc{
            color:rgba(255,255,255,.92) !important;
            font-weight:700 !important;
            line-height:1.55 !important;
            text-shadow:0 2px 8px rgba(0,0,0,.24) !important;
        }

        .tl-caption{
            color:#5f738c !important;
        }

        .tl-card .tl-caption,
        .tl-checkin .tl-caption,
        .tl-admin .tl-caption,
        div[data-testid="stForm"] .tl-caption{
            color:#4b6079 !important;
        }

        /* AJUSTE PROFISSIONAL DE LEGIBILIDADE — somente cor de texto, sem mexer em layout */
        .stApp [data-testid="stMarkdownContainer"] p,
        .stApp [data-testid="stMarkdownContainer"] li,
        .stApp [data-testid="stMarkdownContainer"] span,
        .stApp .stCaptionContainer,
        .stApp small{
            color:inherit !important;
        }

        /* Textos soltos sobre o fundo verde/escuro ficam brancos */
        .stApp > div [data-testid="stMarkdownContainer"]:not(.tl-card *):not(.tl-admin *):not(div[data-testid="stForm"] *){
            color:#ffffff !important;
        }

        /* Dentro dos cards claros, rótulos e textos ficam escuros e fortes */
        .tl-card p, .tl-card span, .tl-card li,
        .tl-admin p, .tl-admin span, .tl-admin li,
        div[data-testid="stForm"] p, div[data-testid="stForm"] span, div[data-testid="stForm"] li,
        .tl-card [data-testid="stMarkdownContainer"],
        .tl-admin [data-testid="stMarkdownContainer"],
        div[data-testid="stForm"] [data-testid="stMarkdownContainer"]{
            color:#07111f !important;
        }

        .tl-admin h1, .tl-admin h2, .tl-admin h3, .tl-admin h4,
        .tl-card h1, .tl-card h2, .tl-card h3, .tl-card h4,
        div[data-testid="stForm"] h1, div[data-testid="stForm"] h2, div[data-testid="stForm"] h3, div[data-testid="stForm"] h4{
            color:#07111f !important;
        }

        /* Correção de cinza/azul fraco em avisos, métricas e labels */
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stMetricDelta"],
        [data-testid="stWidgetLabel"],
        [data-testid="stCaptionContainer"],
        .stAlert,
        .stAlert *{
            color:#07111f !important;
            opacity:1 !important;
        }

        /* Em fundos escuros/sidebar, mantém branco */
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        .tl-event-hero p,
        .tl-event-hero span,
        .tl-event-hero li,
        .tl-experimental p,
        .tl-experimental span,
        .tl-experimental li,
        .tl-confirm-card p,
        .tl-confirm-card span,
        .tl-confirm-card li{
            color:#ffffff !important;
            opacity:1 !important;
        }

        /* Tabelas: cabeçalho e células com contraste, sem exibir colunas técnicas */
        [data-testid="stDataFrame"] div,
        [data-testid="stDataFrame"] span{
            color:#07111f !important;
        }




        /* REFORÇO FINAL DE LEGIBILIDADE — apenas cor/sombra de texto, sem alterar estrutura */
        .tl-section,
        .tl-caption,
        .tl-green-label,
        .tl-assoc-label,
        .tl-event-title,
        .tl-event-meta,
        .tl-event-desc,
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4{
            color:#ffffff !important;
            opacity:1 !important;
            -webkit-text-fill-color:#ffffff !important;
            text-shadow:0 2px 10px rgba(0,0,0,.55) !important;
        }

        .tl-assoc-label,
        .tl-event-meta{
            color:#e8ff7a !important;
            -webkit-text-fill-color:#e8ff7a !important;
        }

        /* Dentro de cards claros e formulários, mantém texto escuro para contraste */
        .tl-card .tl-section,
        .tl-card .tl-caption,
        .tl-checkin .tl-section,
        .tl-checkin .tl-caption,
        .tl-plan .tl-section,
        .tl-plan .tl-caption,
        div[data-testid="stForm"] .tl-section,
        div[data-testid="stForm"] .tl-caption,
        div[data-testid="stForm"] h1,
        div[data-testid="stForm"] h2,
        div[data-testid="stForm"] h3,
        div[data-testid="stForm"] h4{
            color:#07111f !important;
            -webkit-text-fill-color:#07111f !important;
            text-shadow:none !important;
        }

        /* Textos soltos do Streamlit sobre fundo escuro ficam legíveis */
        .stApp [data-testid="stCaptionContainer"],
        .stApp .stCaptionContainer,
        .stApp div[data-testid="stMarkdownContainer"] > p,
        .stApp div[data-testid="stMarkdownContainer"] > ul,
        .stApp div[data-testid="stMarkdownContainer"] > ol{
            color:#ffffff !important;
            opacity:1 !important;
            text-shadow:0 2px 8px rgba(0,0,0,.42) !important;
        }

        /* Conteúdos de formulário/tabelas/inputs continuam com contraste escuro */
        div[data-testid="stForm"] [data-testid="stCaptionContainer"],
        div[data-testid="stForm"] div[data-testid="stMarkdownContainer"] > p,
        div[data-testid="stForm"] div[data-testid="stMarkdownContainer"] > ul,
        div[data-testid="stForm"] div[data-testid="stMarkdownContainer"] > ol,
        [data-testid="stDataFrame"] div,
        [data-testid="stDataFrame"] span,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stMetricDelta"],
        label,
        .stTextInput label,
        .stTextArea label,
        .stDateInput label,
        .stNumberInput label,
        .stSelectbox label{
            color:#07111f !important;
            -webkit-text-fill-color:#07111f !important;
            text-shadow:none !important;
            opacity:1 !important;
        }


        /* Legibilidade reforçada especificamente no check-in */
        .tl-checkin .tl-section,
        .tl-checkin .tl-caption,
        .tl-checkin label,
        .tl-checkin [data-testid="stWidgetLabel"],
        .tl-checkin [data-testid="stMarkdownContainer"] p{
            color:#ffffff !important;
            -webkit-text-fill-color:#ffffff !important;
            text-shadow:0 2px 8px rgba(0,0,0,.48) !important;
            opacity:1 !important;
        }

</style>
        """,
        unsafe_allow_html=True,
    )

#
# Additional CSS overrides
#
# The original stylesheet defined a dark theme. To refresh the look and bring it
# closer to the light and airy feel requested, we provide a second CSS
# injection that overrides some variables and defines extra classes. Placing
# these definitions in a separate function that runs after the original
# injection allows us to override variables without editing the large
# preexisting CSS block. See `inject_fresh_css()` below.

def inject_fresh_css() -> None:
    """Inject lighter color palette and sponsor/bracket styles."""
    st.markdown(
        """
        <style>
        /* Mantém a identidade visual aprovada do app; aqui só entram estilos extras. */

        /* Sponsor bar on the landing section */
        .tl-sponsors{
            display:flex;
            flex-wrap:wrap;
            justify-content:center;
            gap:20px;
            margin-top:24px;
            align-items:center;
        }
        .tl-sponsors a,
        .tl-sponsors span{
            display:inline-flex;
            align-items:center;
            justify-content:center;
            padding:4px;
        }
        .tl-sponsors img{
            height:60px;
            width:auto;
            object-fit:contain;
            border-radius:6px;
            box-shadow:0 4px 12px rgba(0,0,0,.08);
        }

        /* Match rows for tournament bracket */
        .tl-match{
            display:flex;
            justify-content:space-between;
            align-items:center;
            padding:6px 10px;
            margin:4px 0;
            border-radius:12px;
            background:rgba(255,255,255,.6);
            border:1px solid rgba(0,0,0,.05);
        }
        .tl-match span.tl-status{
            color:var(--tl-muted);
            margin-left:auto;
            margin-right:10px;
            font-size:.85rem;
        }
        .tl-match span.tl-result{
            font-weight:700;
            color:var(--tl-slate);
        }

        .tl-upload-card{
            margin:14px 0 20px;
            padding:16px;
            border-radius:22px;
            background:rgba(255,255,255,.84);
            border:1px solid rgba(201,255,18,.28);
            box-shadow:0 10px 26px rgba(7,17,31,.08);
        }
        .tl-upload-title{
            font-weight:950;
            letter-spacing:-.03em;
            color:#07111f;
            margin-bottom:4px;
        }
        .tl-upload-meta{
            font-size:.92rem;
            font-weight:700;
            color:#56687b;
            margin-bottom:12px;
        }
        .tl-schedule-row{
            display:grid;
            grid-template-columns:88px 1fr;
            gap:10px;
            align-items:start;
            padding:10px 12px;
            border-radius:16px;
            margin:8px 0;
            background:#fbfff1;
            border:1px solid rgba(159,217,0,.35);
        }
        .tl-schedule-time{
            font-weight:950;
            color:#07111f;
        }
        .tl-schedule-main{
            color:#07111f;
            font-weight:800;
            line-height:1.35;
        }
        .tl-schedule-meta{
            color:#596b7d;
            font-size:.88rem;
            font-weight:700;
            margin-top:2px;
        }

        /* Legibilidade final: texto escuro em cards claros e branco no fundo escuro */
        .tl-event-card, .tl-upload-card, .tl-schedule-row, div[data-testid="stForm"]{
            color:#07111f !important;
            -webkit-text-fill-color:initial !important;
            text-shadow:none !important;
        }
        .tl-event-card *, .tl-upload-card *, .tl-schedule-row *, div[data-testid="stForm"] *{
            text-shadow:none !important;
        }
        .tl-event-card .tl-section, .tl-event-card h1, .tl-event-card h2, .tl-event-card h3, .tl-event-card h4,
        .tl-event-card p, .tl-event-card span, .tl-event-card label{
            color:#07111f !important;
            -webkit-text-fill-color:#07111f !important;
            opacity:1 !important;
        }
        .tl-event-hero, .tl-event-hero *{
            color:#ffffff !important;
            -webkit-text-fill-color:#ffffff !important;
        }
        .tl-public-tabs-label{
            margin:16px 0 6px;
            font-weight:950;
            color:#07111f !important;
            font-size:1.1rem;
        }

        /* Abas com contraste alto: botão ativo sempre com texto escuro legível. */
        .stTabs [data-baseweb="tab-list"]{
            background:rgba(7,17,31,.86) !important;
            border-radius:999px !important;
            padding:6px !important;
            gap:6px !important;
        }
        .stTabs [data-baseweb="tab"]{
            border-radius:999px !important;
            color:#ffffff !important;
            font-weight:900 !important;
            min-height:44px !important;
            padding:0 18px !important;
        }
        .stTabs [data-baseweb="tab"] p{
            color:#ffffff !important;
            -webkit-text-fill-color:#ffffff !important;
            font-weight:900 !important;
        }
        .stTabs [aria-selected="true"]{
            background:linear-gradient(180deg,#dfff49,#b5e000) !important;
            color:#07111f !important;
        }
        .stTabs [aria-selected="true"] p{
            color:#07111f !important;
            -webkit-text-fill-color:#07111f !important;
            font-weight:950 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_official_admin_css() -> None:
    """Ajuste final do login admin.

    Mantém a área administrativa discreta: sidebar pela setinha do Streamlit
    e um expander simples no final da página para garantir que o admin
    consiga entrar mesmo quando a setinha ficar difícil de visualizar.
    """
    st.markdown(
        """
        <style>
        /* Esconde apenas botões antigos experimentais. O expander público discreto fica ativo. */
        .tl-admin-login-link,
        .tl-admin-direct-card,
        .tl-fixed-admin-btn,
        a[href="#admin-login"],
        a[href="?admin=1#admin-login-panel"]{
            display:none !important;
            visibility:hidden !important;
            height:0 !important;
            width:0 !important;
            overflow:hidden !important;
            pointer-events:none !important;
        }
        .tl-admin-login-public{
            margin:18px auto 8px !important;
            max-width:920px !important;
        }
        .tl-admin-login-public [data-testid="stExpander"]{
            background:rgba(255,255,255,.06) !important;
            border:1px solid rgba(201,255,18,.22) !important;
            border-radius:16px !important;
        }
        .tl-admin-login-public [data-testid="stExpander"] *{
            color:#ffffff !important;
        }
        .tl-admin-login-public input{
            background:#ffffff !important;
            color:#07111f !important;
            -webkit-text-fill-color:#07111f !important;
        }

        /* Seta lateral discreta, mas sempre clicável — estilo igual ao site oficial */
        button[data-testid="collapsedControl"],
        button[aria-label="Open sidebar"],
        button[title="Open sidebar"],
        button[aria-label="Abrir barra lateral"],
        button[title="Abrir barra lateral"]{
            display:flex !important;
            visibility:visible !important;
            opacity:1 !important;
            position:fixed !important;
            top:78px !important;
            left:14px !important;
            z-index:999999 !important;
            width:34px !important;
            height:34px !important;
            border-radius:999px !important;
            border:0 !important;
            background:rgba(7,17,31,.04) !important;
            box-shadow:none !important;
            color:rgba(255,255,255,.72) !important;
            padding:0 !important;
            align-items:center !important;
            justify-content:center !important;
        }
        button[data-testid="collapsedControl"] svg,
        button[aria-label="Open sidebar"] svg,
        button[title="Open sidebar"] svg,
        button[aria-label="Abrir barra lateral"] svg,
        button[title="Abrir barra lateral"] svg{
            color:rgba(255,255,255,.72) !important;
            fill:rgba(255,255,255,.72) !important;
            stroke:rgba(255,255,255,.72) !important;
        }
        button[data-testid="collapsedControl"]:hover,
        button[aria-label="Open sidebar"]:hover,
        button[title="Open sidebar"]:hover,
        button[aria-label="Abrir barra lateral"]:hover,
        button[title="Abrir barra lateral"]:hover{
            background:rgba(255,255,255,.10) !important;
        }

        /* Botão fallback criado por JS se o botão nativo não renderizar no celular */
        #tl-admin-open-sidebar-fallback{
            position:fixed !important;
            top:78px !important;
            left:14px !important;
            z-index:999998 !important;
            width:34px !important;
            height:34px !important;
            border-radius:999px !important;
            border:0 !important;
            background:rgba(7,17,31,.04) !important;
            color:rgba(255,255,255,.72) !important;
            font-size:34px !important;
            line-height:26px !important;
            padding:0 !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            cursor:pointer !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_admin_sidebar_fallback() -> None:
    """Cria uma setinha discreta caso o botão nativo da sidebar não apareça.

    Em alguns celulares/navegadores, o botão nativo do Streamlit pode ficar
    escondido por atualização do layout. Este fallback mantém o login do admin
    discreto: ele apenas tenta clicar no botão nativo; se não achar, abre uma
    rota com painel de login discreto.
    """
    components.html(
        """
        <script>
        (function(){
            const doc = window.parent.document;
            function visible(el){
                if(!el) return false;
                const rect = el.getBoundingClientRect();
                const style = window.parent.getComputedStyle(el);
                return rect.width > 8 && rect.height > 8 && style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0;
            }
            function nativeButtons(){
                return Array.from(doc.querySelectorAll(
                    'button[data-testid="collapsedControl"], button[aria-label="Open sidebar"], button[title="Open sidebar"], button[aria-label="Abrir barra lateral"], button[title="Abrir barra lateral"]'
                ));
            }
            function sidebarOpen(){
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if(!sidebar) return false;
                const rect = sidebar.getBoundingClientRect();
                const style = window.parent.getComputedStyle(sidebar);
                return rect.width > 180 && style.visibility !== 'hidden' && style.display !== 'none';
            }
            function ensureFallback(){
                let btn = doc.getElementById('tl-admin-open-sidebar-fallback');
                if(!btn){
                    btn = doc.createElement('button');
                    btn.id = 'tl-admin-open-sidebar-fallback';
                    btn.type = 'button';
                    btn.innerHTML = '›';
                    btn.setAttribute('aria-label','Abrir área administrativa');
                    btn.title = 'Abrir área administrativa';
                    btn.onclick = function(e){
                        e.preventDefault();
                        e.stopPropagation();
                        const natives = nativeButtons();
                        const target = natives.find(visible) || natives[0];
                        if(target){
                            target.click();
                            return;
                        }
                        try{
                            const url = new URL(window.parent.location.href);
                            url.searchParams.set('admin_panel','1');
                            window.parent.location.href = url.toString();
                        }catch(err){}
                    };
                    doc.body.appendChild(btn);
                }
                const nativeVisible = nativeButtons().some(visible);
                btn.style.display = (nativeVisible || sidebarOpen()) ? 'none' : 'flex';
            }
            ensureFallback();
            setTimeout(ensureFallback, 400);
            setTimeout(ensureFallback, 1200);
            const obs = new MutationObserver(ensureFallback);
            obs.observe(doc.body, {childList:true, subtree:true, attributes:true});
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def admin_panel_query_requested() -> bool:
    """Retorna True quando o fallback precisa mostrar login discreto na página."""
    try:
        value = st.query_params.get("admin_panel", "")
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value).strip() == "1"
    except Exception:
        return False

def render_header() -> None:
    st.markdown('<div class="tl-hero">', unsafe_allow_html=True)
    logo = logo_path()
    if logo:
        import base64
        try:
            logo_bytes = Path(logo).read_bytes()
            logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")
            st.markdown(
                f'<div class="tl-logo-shell"><img src="data:image/png;base64,{logo_b64}" alt="Tênis Linhares"></div>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.image(logo, width=160)
    st.markdown(f'<div class="tl-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tl-subtitle">Aulas, torneios, reposições e pagamentos em uma experiência simples, rápida e profissional.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="tl-pill-row">'
        '<a class="tl-pill" href="#experimental" data-target-hash="#experimental">Agendar aula experimental</a>'
        '<a class="tl-pill" href="#checkin" data-target-hash="#checkin">Check-in de aulas</a>'
        '<a class="tl-pill" href="#eventos" data-target-hash="#eventos">Torneios</a>'
        '<a class="tl-pill" href="#financeiro" data-target-hash="#financeiro">Financeiro com PIX</a>'
        '<a class="tl-pill" href="#reposicao" data-target-hash="#reposicao">Reposição</a>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
    # Render the sponsor bar below the hero if sponsors are configured
    try:
        render_sponsors_public()
    except Exception:
        pass

def render_navigation_router() -> None:
    components.html(
        """
        <script>
        (function () {
            const HASH_TO_TAB = {
                "#experimental": "Aula experimental",
                "#checkin": "Check-in das aulas",
                "#reposicao": "Reposição de aula",
                "#eventos": "Eventos",
                "#financeiro": "Financeiro"
            };

            function clickTabByLabel(label) {
                const doc = window.parent.document;
                const tabs = Array.from(doc.querySelectorAll('[data-baseweb="tab"]'));
                const target = tabs.find((tab) => (tab.innerText || "").trim() === label);
                if (target) {
                    target.click();
                    return true;
                }
                return false;
            }

            function goToSection(hash) {
                const label = HASH_TO_TAB[hash];
                if (!label) return;
                clickTabByLabel(label);
                setTimeout(function () {
                    const target = window.parent.document.getElementById(hash.replace("#", ""));
                    if (target) {
                        target.scrollIntoView({ behavior: "smooth", block: "start" });
                    }
                }, 260);
                try {
                    window.parent.location.hash = hash;
                } catch (e) {}
            }

            function bindButtons() {
                const doc = window.parent.document;
                const buttons = Array.from(doc.querySelectorAll('.tl-pill[data-target-hash]'));
                buttons.forEach(function (button) {
                    if (button.dataset.boundNav === "1") return;
                    button.dataset.boundNav = "1";
                    button.addEventListener("click", function (event) {
                        event.preventDefault();
                        goToSection(button.dataset.targetHash);
                    });
                });

                const currentHash = window.parent.location.hash;
                if (currentHash && HASH_TO_TAB[currentHash]) {
                    goToSection(currentHash);
                }
            }

            const observer = new MutationObserver(function () {
                bindButtons();
            });
            observer.observe(window.parent.document.body, { childList: true, subtree: true });

            setTimeout(bindButtons, 200);
            setTimeout(bindButtons, 700);
            setTimeout(bindButtons, 1400);
        })();
        </script>
        """,
        height=0,
        width=0,
    )


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
    params = {
        "select": "id,nome,whatsapp,status_pagamento,ativo,observacao,valor_mensalidade,dia_vencimento_mensalidade,data_vencimento_mensalidade,tipo_plano,dias_aula,aula_horario,aula_local,agenda_aulas,created_at,updated_at",
        "order": "nome.asc",
        "limit": str(limit),
    }
    try:
        return db().request("GET", "alunos", params=params) or []
    except AppError as exc:
        if "desatualizado" not in str(exc).lower():
            raise
        # Compatibilidade: se o banco ainda não tiver o novo campo de dia fixo,
        # mantém a mensalidade e usa o dia da data antiga como fallback.
        try:
            rows = db().request(
                "GET", "alunos",
                params={"select": "id,nome,whatsapp,status_pagamento,ativo,observacao,valor_mensalidade,data_vencimento_mensalidade,created_at,updated_at", "order": "nome.asc", "limit": str(limit)},
            ) or []
            for row in rows:
                row.setdefault("dia_vencimento_mensalidade", None)
                row.setdefault("tipo_plano", None)
                row.setdefault("dias_aula", None)
                row.setdefault("aula_horario", None)
                row.setdefault("aula_local", None)
                row.setdefault("agenda_aulas", None)
            return rows
        except AppError:
            rows = db().request(
                "GET", "alunos",
                params={"select": "id,nome,whatsapp,status_pagamento,ativo,observacao,created_at,updated_at", "order": "nome.asc", "limit": str(limit)},
            ) or []
            for row in rows:
                row.setdefault("valor_mensalidade", 0)
                row.setdefault("dia_vencimento_mensalidade", None)
                row.setdefault("data_vencimento_mensalidade", None)
                row.setdefault("tipo_plano", None)
                row.setdefault("dias_aula", None)
                row.setdefault("aula_horario", None)
                row.setdefault("aula_local", None)
                row.setdefault("agenda_aulas", None)
            return rows

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
    params = {
        "select": "id,evento_id,evento_titulo,nome,whatsapp,categoria,tipo_inscricao,valor,status_inscricao,created_at",
        "order": "evento_titulo.asc,categoria.asc,created_at.desc",
        "limit": str(limit),
    }
    try:
        return db().request("GET", "inscricoes_eventos", params=params) or []
    except AppError as exc:
        lower = str(exc).lower()
        if "column" in lower and "tipo_inscricao" in lower:
            params["select"] = "id,evento_id,evento_titulo,nome,whatsapp,categoria,valor,status_inscricao,created_at"
            return db().request("GET", "inscricoes_eventos", params=params) or []
        raise

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


@st.cache_data(ttl=20, show_spinner=False)
def fetch_trial_requests(limit: int = 500) -> list[dict[str, Any]]:
    try:
        return db().request(
            "GET", "aulas_experimentais",
            params={
                "select": "id,nome,whatsapp,objetivo,nivel,disponibilidade,status,observacao,created_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        ) or []
    except AppError:
        return []

@st.cache_data(ttl=20, show_spinner=False)
def fetch_stringings(limit: int = 500) -> list[dict[str, Any]]:
    return db().request(
        "GET", "encordoamentos",
        params={
            "select": "id,aluno_nome,whatsapp,data_servico,valor_total,valor_corda,valor_mao_obra,observacao,created_at",
            "order": "data_servico.desc,created_at.desc",
            "limit": str(limit),
        },
    ) or []

def insert_stringing(payload: dict[str, Any]) -> None:
    db().request("POST", "encordoamentos", json_body=payload, prefer="return=representation")
    fetch_stringings.clear()

def insert_trial_request(payload: dict[str, Any]) -> None:
    db().request("POST", "aulas_experimentais", json_body=payload, prefer="return=representation")
    fetch_trial_requests.clear()

def update_trial_request(request_id: str, payload: dict[str, Any]) -> None:
    db().request(
        "PATCH",
        "aulas_experimentais",
        params={"id": f"eq.{request_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_trial_requests.clear()

def clear_caches() -> None:
    healthcheck.clear()
    fetch_students.clear()
    fetch_events.clear()
    fetch_confirmations.clear()
    fetch_registrations.clear()
    fetch_makeup_requests.clear()
    fetch_trial_requests.clear()
    try:
        fetch_stringings.clear()
    except NameError:
        pass

def find_student(nome: str, whatsapp: str) -> Optional[dict[str, Any]]:
    phone = normalize_phone(whatsapp)
    if phone:
        rows = db().request(
            "GET", "alunos",
            params={"select": "id,nome,whatsapp,status_pagamento,ativo,observacao,tipo_plano,dias_aula,aula_horario,aula_local,agenda_aulas", "whatsapp": f"eq.{phone}", "ativo": "eq.true", "limit": "1"},
        ) or []
        if rows:
            return rows[0]
    if nome.strip():
        rows = db().request(
            "GET", "alunos",
            params={"select": "id,nome,whatsapp,status_pagamento,ativo,observacao,tipo_plano,dias_aula,aula_horario,aula_local,agenda_aulas", "nome": f"ilike.*{nome.strip()}*", "ativo": "eq.true", "limit": "10"},
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

def registration_exists(evento_id: str, whatsapp: str, categoria: str) -> bool:
    rows = db().request(
        "GET", "inscricoes_eventos",
        params={
            "select": "id",
            "evento_id": f"eq.{evento_id}",
            "whatsapp": f"eq.{normalize_phone(whatsapp)}",
            "categoria": f"eq.{categoria}",
            "limit": "1",
        },
    ) or []
    return bool(rows)

def tournament_category_count(evento_id: str, categoria: str) -> int:
    rows = db().request(
        "GET", "inscricoes_eventos",
        params={
            "select": "id,status_inscricao",
            "evento_id": f"eq.{evento_id}",
            "categoria": f"eq.{categoria}",
            "limit": "1000",
        },
    ) or []
    active_rows = [
        row for row in rows
        if str(row.get("status_inscricao") or "").strip().lower() not in {"cancelado", "cancelada"}
    ]
    return len(active_rows)

def insert_confirmation(payload: dict[str, Any]) -> None:
    db().request("POST", "confirmacoes", json_body=payload, prefer="return=representation")
    fetch_confirmations.clear()

def insert_registration(payload: dict[str, Any]) -> None:
    try:
        db().request("POST", "inscricoes_eventos", json_body=payload, prefer="return=representation")
    except AppError as exc:
        lower = str(exc).lower()
        if "column" in lower and "tipo_inscricao" in lower:
            fallback_payload = dict(payload)
            fallback_payload.pop("tipo_inscricao", None)
            db().request("POST", "inscricoes_eventos", json_body=fallback_payload, prefer="return=representation")
        else:
            raise
    fetch_registrations.clear()
    fetch_makeup_requests.clear()

def _student_payload_without_class_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Fallback para bancos que ainda não têm os campos de aula fixa."""
    fallback = dict(payload)
    fallback.pop("tipo_plano", None)
    fallback.pop("dias_aula", None)
    fallback.pop("aula_horario", None)
    fallback.pop("aula_local", None)
    fallback.pop("agenda_aulas", None)
    return fallback

def _student_payload_without_due_day(payload: dict[str, Any]) -> dict[str, Any]:
    """Fallback para bancos que ainda não têm o campo novo de dia fixo."""
    fallback = _student_payload_without_class_fields(payload)
    fallback.pop("dia_vencimento_mensalidade", None)
    return fallback

def _student_payload_without_new_finance_fields(payload: dict[str, Any]) -> dict[str, Any]:
    fallback = _student_payload_without_class_fields(payload)
    fallback.pop("valor_mensalidade", None)
    fallback.pop("dia_vencimento_mensalidade", None)
    fallback.pop("data_vencimento_mensalidade", None)
    return fallback

def upsert_student(payload: dict[str, Any]) -> None:
    try:
        db().request(
            "POST", "alunos",
            params={"on_conflict": "whatsapp"},
            json_body=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
    except AppError as exc:
        if "desatualizado" not in str(exc).lower():
            raise
        try:
            db().request(
                "POST", "alunos",
                params={"on_conflict": "whatsapp"},
                json_body=_student_payload_without_class_fields(payload),
                prefer="resolution=merge-duplicates,return=representation",
            )
            flash_message("warn", "Aluno salvo sem os campos novos de aula fixa. Para salvar agenda por dia/horário, rode o SQL novo no Supabase.")
        except AppError:
            try:
                db().request(
                    "POST", "alunos",
                    params={"on_conflict": "whatsapp"},
                    json_body=_student_payload_without_due_day(payload),
                    prefer="resolution=merge-duplicates,return=representation",
                )
                flash_message("warn", "Aluno salvo. Para usar o dia fixo recorrente e aula fixa, rode o SQL novo no Supabase.")
            except AppError:
                db().request(
                    "POST", "alunos",
                    params={"on_conflict": "whatsapp"},
                    json_body=_student_payload_without_new_finance_fields(payload),
                    prefer="resolution=merge-duplicates,return=representation",
                )
                flash_message("warn", "Dados básicos do aluno salvos. Para salvar mensalidade, dia fixo e aula fixa, rode o SQL novo no Supabase.")
    fetch_students.clear()

def update_student(student_id: str, payload: dict[str, Any]) -> None:
    try:
        db().request(
            "PATCH",
            "alunos",
            params={"id": f"eq.{student_id}"},
            json_body=payload,
            prefer="return=representation",
        )
    except AppError as exc:
        if "desatualizado" not in str(exc).lower():
            raise
        try:
            db().request(
                "PATCH",
                "alunos",
                params={"id": f"eq.{student_id}"},
                json_body=_student_payload_without_class_fields(payload),
                prefer="return=representation",
            )
            flash_message("warn", "Aluno atualizado sem os campos novos de aula fixa. Para salvar agenda por dia/horário, rode o SQL novo no Supabase.")
        except AppError:
            try:
                db().request(
                    "PATCH",
                    "alunos",
                    params={"id": f"eq.{student_id}"},
                    json_body=_student_payload_without_due_day(payload),
                    prefer="return=representation",
                )
                flash_message("warn", "Aluno atualizado. Para usar o dia fixo recorrente e aula fixa, rode o SQL novo no Supabase.")
            except AppError:
                db().request(
                    "PATCH",
                    "alunos",
                    params={"id": f"eq.{student_id}"},
                    json_body=_student_payload_without_new_finance_fields(payload),
                    prefer="return=representation",
                )
                flash_message("warn", "Dados básicos do aluno atualizados. Para salvar mensalidade, dia fixo e aula fixa, rode o SQL novo no Supabase.")
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

# -----------------------------------------------------------------------------
# Patrocinadores (Sponsors) API helpers
#
# These functions encapsulate all operations with the patrocinadores table in
# Supabase. We keep them simple and rely on db().request() to communicate with
# the backend. Caching is provided via st.cache_data to avoid unnecessary
# requests on each rerender.

@st.cache_data(ttl=60, show_spinner=False)
def fetch_sponsors(include_inactive: bool = False) -> list[dict[str, Any]]:
    """Fetch sponsors from the database. When include_inactive is False
    only active sponsors are returned."""
    try:
        params: dict[str, str] = {"select": "id,nome,logo_url,link,ordem,ativo"}
        if not include_inactive:
            params["ativo"] = "eq.true"
        rows = db().request("GET", "patrocinadores", params=params) or []
        # Ensure deterministic ordering on the client side
        rows = sorted(rows, key=lambda x: (x.get("ordem") or 0, x.get("nome") or ""))
        return rows
    except Exception:
        return []

def insert_sponsor(payload: dict[str, Any]) -> None:
    """Insert a new sponsor."""
    db().request("POST", "patrocinadores", json_body=payload, prefer="return=representation")
    fetch_sponsors.clear()

def update_sponsor(sponsor_id: str, payload: dict[str, Any]) -> None:
    """Update an existing sponsor."""
    db().request(
        "PATCH",
        "patrocinadores",
        params={"id": f"eq.{sponsor_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_sponsors.clear()

def delete_sponsor(sponsor_id: str) -> None:
    """Delete a sponsor by id."""
    db().request(
        "DELETE",
        "patrocinadores",
        params={"id": f"eq.{sponsor_id}"},
        prefer="return=minimal",
    )
    fetch_sponsors.clear()

# -----------------------------------------------------------------------------
# Torneio matches (bracket/agenda/results) API helpers
#
# A series of helpers to interact with the jogos_torneio table, which holds
# individual matches for tournament brackets. Each match belongs to an event
# (torneio_id). Fase defines the round (e.g. "Oitavas"), jogador1 and
# jogador2 contain the player names. Data/hora define schedule, quadra the
# court, resultado the final score and status the match status (e.g. "agendado"
# or "concluido").

@st.cache_data(ttl=30, show_spinner=False)
def fetch_bracket_matches(event_id: str) -> list[dict[str, Any]]:
    """Return a list of matches for a given event, including category when available."""
    if not event_id:
        return []
    try:
        params: dict[str, str] = {
            "select": "id,fase,categoria,jogador1,jogador2,data_hora,quadra,resultado,status,ordem",
            "torneio_id": f"eq.{event_id}",
            "order": "data_hora.asc,ordem.asc",
        }
        rows = db().request("GET", "jogos_torneio", params=params) or []
        return rows
    except Exception:
        # Backward compatibility: if an older table does not yet have categoria
        try:
            params = {
                "select": "id,fase,jogador1,jogador2,data_hora,quadra,resultado,status,ordem",
                "torneio_id": f"eq.{event_id}",
                "order": "data_hora.asc,ordem.asc",
            }
            rows = db().request("GET", "jogos_torneio", params=params) or []
            for r in rows:
                r.setdefault("categoria", "")
            return rows
        except Exception:
            return []

def insert_bracket_matches(event_id: str, matches: list[dict[str, Any]]) -> None:
    """Insert multiple matches for an event."""
    if not matches:
        return
    payload = []
    for m in matches:
        entry = m.copy()
        entry["torneio_id"] = event_id
        payload.append(entry)
    db().request("POST", "jogos_torneio", json_body=payload, prefer="return=representation")
    fetch_bracket_matches.clear()

def update_bracket_match(match_id: str, payload: dict[str, Any]) -> None:
    """Update a single match."""
    db().request(
        "PATCH",
        "jogos_torneio",
        params={"id": f"eq.{match_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_bracket_matches.clear()

def delete_bracket_matches(ids: list[str]) -> None:
    """Delete multiple matches by id."""
    clean_ids = [str(item).strip() for item in ids if str(item).strip()]
    if not clean_ids:
        return
    for start in range(0, len(clean_ids), 120):
        chunk = clean_ids[start:start + 120]
        try:
            db().request(
                "DELETE",
                "jogos_torneio",
                params={"id": f"in.({','.join(chunk)})"},
                prefer="return=minimal",
            )
        except AppError:
            for item_id in chunk:
                db().request(
                    "DELETE",
                    "jogos_torneio",
                    params={"id": f"eq.{item_id}"},
                    prefer="return=minimal",
                )
    fetch_bracket_matches.clear()


# -----------------------------------------------------------------------------
# Upload de chaves prontas e programação em arquivo
#
# Estas funções salvam arquivos pequenos (JPG/PNG/PDF/CSV) em base64 dentro do
# Supabase. Assim você consegue subir chaves feitas manualmente sem precisar
# configurar Supabase Storage. Use arquivos leves para manter o app rápido.

@st.cache_data(ttl=30, show_spinner=False)
def fetch_tournament_files(event_id: str, tipo: Optional[str] = None, include_inactive: bool = False) -> list[dict[str, Any]]:
    if not event_id:
        return []
    try:
        params: dict[str, str] = {
            "select": "id,torneio_id,tipo,titulo,categoria,arquivo_nome,mime_type,arquivo_base64,texto,ordem,ativo,created_at",
            "torneio_id": f"eq.{event_id}",
            "order": "ordem.asc,created_at.asc",
        }
        if tipo:
            params["tipo"] = f"eq.{tipo}"
        if not include_inactive:
            params["ativo"] = "eq.true"
        return db().request("GET", "arquivos_torneio", params=params) or []
    except Exception:
        return []

def insert_tournament_file(payload: dict[str, Any]) -> None:
    db().request("POST", "arquivos_torneio", json_body=payload, prefer="return=representation")
    fetch_tournament_files.clear()

def update_tournament_file(file_id: str, payload: dict[str, Any]) -> None:
    db().request(
        "PATCH",
        "arquivos_torneio",
        params={"id": f"eq.{file_id}"},
        json_body=payload,
        prefer="return=representation",
    )
    fetch_tournament_files.clear()

def delete_tournament_file(file_id: str) -> None:
    db().request(
        "DELETE",
        "arquivos_torneio",
        params={"id": f"eq.{file_id}"},
        prefer="return=minimal",
    )
    fetch_tournament_files.clear()

def _file_to_base64(uploaded_file: Any, max_mb: float = 4.0) -> tuple[str, str, str]:
    """Return filename, mime type and base64 content for a Streamlit uploaded file."""
    data = uploaded_file.getvalue()
    max_bytes = int(max_mb * 1024 * 1024)
    if len(data) > max_bytes:
        raise AppError(f"Arquivo muito grande. Use arquivo de até {max_mb:.1f} MB para manter o app leve.")
    name = getattr(uploaded_file, "name", "arquivo") or "arquivo"
    mime = getattr(uploaded_file, "type", None) or "application/octet-stream"
    return name, mime, base64.b64encode(data).decode("utf-8")

def _parse_schedule_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a CSV/XLSX dataframe into jogos_torneio payloads.

    Accepted columns, flexible naming:
    data, hora, data_hora, quadra, categoria, fase, jogador1, jogador2,
    status, resultado, ordem.
    """
    if df is None or df.empty:
        return []
    original_columns = list(df.columns)
    rename_map: dict[str, str] = {}
    aliases = {
        "data": ["data", "dia", "date"],
        "hora": ["hora", "horario", "horário", "time"],
        "data_hora": ["data_hora", "data e hora", "datetime", "data/hora"],
        "quadra": ["quadra", "court"],
        "categoria": ["categoria", "classe", "category"],
        "fase": ["fase", "rodada", "round"],
        "jogador1": ["jogador1", "jogador 1", "atleta1", "atleta 1", "player1", "player 1"],
        "jogador2": ["jogador2", "jogador 2", "atleta2", "atleta 2", "player2", "player 2"],
        "status": ["status", "situação", "situacao"],
        "resultado": ["resultado", "placar", "score"],
        "ordem": ["ordem", "order"],
    }
    normalized = {str(c).strip().lower(): c for c in original_columns}
    for target, names in aliases.items():
        for name in names:
            if name in normalized:
                rename_map[normalized[name]] = target
                break
    df = df.rename(columns=rename_map)
    matches: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        def val(col: str) -> str:
            try:
                x = row.get(col)
            except Exception:
                return ""
            if pd.isna(x):
                return ""
            return str(x).strip()

        data_hora_iso: Optional[str] = None
        raw_dt = val("data_hora")
        raw_data = val("data")
        raw_hora = val("hora")
        if raw_dt:
            try:
                dt_parsed = pd.to_datetime(raw_dt, dayfirst=True, errors="coerce")
                if not pd.isna(dt_parsed):
                    data_hora_iso = dt_parsed.isoformat()
            except Exception:
                data_hora_iso = None
        elif raw_data or raw_hora:
            try:
                joined = f"{raw_data} {raw_hora}".strip()
                dt_parsed = pd.to_datetime(joined, dayfirst=True, errors="coerce")
                if not pd.isna(dt_parsed):
                    data_hora_iso = dt_parsed.isoformat()
            except Exception:
                data_hora_iso = None

        categoria = val("categoria") or "Sem categoria"
        fase = val("fase") or "Programação"
        ordem_val = val("ordem")
        payload: dict[str, Any] = {
            "categoria": categoria,
            "fase": fase,
            "jogador1": val("jogador1") or None,
            "jogador2": val("jogador2") or None,
            "data_hora": data_hora_iso,
            "quadra": val("quadra") or None,
            "resultado": val("resultado") or None,
            "status": val("status") or "agendado",
            "ordem": int(float(ordem_val)) if ordem_val.replace(".", "", 1).isdigit() else idx,
        }
        if payload["jogador1"] or payload["jogador2"] or payload["data_hora"]:
            matches.append(payload)
    return matches

def _read_schedule_upload(uploaded_file: Any) -> pd.DataFrame:
    name = (getattr(uploaded_file, "name", "") or "").lower()
    data = uploaded_file.getvalue()
    if name.endswith(".csv"):
        # Try common encodings and separators
        for encoding in ("utf-8-sig", "latin1"):
            try:
                text = data.decode(encoding)
                # sep=None lets pandas infer comma/semicolon/tab
                return pd.read_csv(io.StringIO(text), sep=None, engine="python")
            except Exception:
                continue
        raise AppError("Não consegui ler o CSV. Salve como CSV UTF-8 ou envie em XLSX.")
    if name.endswith(".xlsx"):
        try:
            return pd.read_excel(io.BytesIO(data))
        except Exception:
            raise AppError("Não consegui ler o XLSX. Confirme se o arquivo está no formato Excel normal.")
    raise AppError("Formato não aceito para programação. Envie CSV ou XLSX.")

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

def render_trial_request() -> None:
    st.markdown('<div id="experimental"></div>', unsafe_allow_html=True)
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card tl-experimental">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Agendar aula experimental</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tl-caption">Preencha seus dados para a equipe da Tênis Linhares organizar o melhor horário para você começar ou evoluir no tênis.</div>',
        unsafe_allow_html=True,
    )

    with st.form("form_trial_request", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome completo", key="trial_nome")
        whatsapp = c2.text_input("WhatsApp", key="trial_whatsapp")
        c3, c4 = st.columns(2)
        objetivo = c3.selectbox("Objetivo", ["Hobby", "Saúde", "Emagrecimento", "Competição", "Aprender do zero", "Outro"], key="trial_objetivo")
        nivel = c4.selectbox("Nível de experiência", ["Iniciante", "Intermediário", "Avançado"], key="trial_nivel")
        disponibilidade = st.text_input("Disponibilidade de horário", placeholder="Ex.: terça e quinta à tarde, segunda 7h, sábado pela manhã...", key="trial_disponibilidade")
        observacao = st.text_area("Observações", placeholder="Conte algo importante sobre sua rotina, objetivo ou preferência.", key="trial_obs")
        submit = st.form_submit_button("Solicitar aula experimental", use_container_width=True)

    if submit:
        if not nome.strip() or not whatsapp.strip() or not disponibilidade.strip():
            md_box("error", "Preencha nome, WhatsApp e disponibilidade de horário.")
        else:
            try:
                insert_trial_request({
                    "nome": nome.strip(),
                    "whatsapp": normalize_phone(whatsapp),
                    "objetivo": objetivo,
                    "nivel": nivel,
                    "disponibilidade": disponibilidade.strip(),
                    "status": "novo",
                    "observacao": observacao.strip() or None,
                })
                md_box("ok", f"Solicitação enviada com sucesso. A equipe Tênis Linhares entrará em contato pelo WhatsApp. Se preferir, fale com {secretaria_nome}: {secretaria_whatsapp}.")
            except AppError as exc:
                md_box("error", "Não foi possível registrar sua solicitação agora. Fale diretamente com a secretaria pelo WhatsApp.")
    st.markdown('</div>', unsafe_allow_html=True)

def render_student_checkin() -> None:
    st.markdown('<div id="checkin"></div>', unsafe_allow_html=True)
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])

    st.markdown('<div class="tl-card tl-checkin">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Check-in da aula</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Digite seu nome para confirmar sua aula.</div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    .tl-checkin label,
    .tl-checkin label p,
    .tl-checkin [data-testid="stTextInput"] label,
    .tl-checkin [data-testid="stTextInput"] label p,
    .tl-checkin [data-testid="stMarkdownContainer"] p,
    .tl-checkin .tl-caption,
    .tl-checkin .tl-section {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        text-shadow: 0 2px 8px rgba(0,0,0,.45) !important;
        opacity: 1 !important;
    }
    .tl-checkin .tl-checkin-summary {
        background: rgba(255,255,255,.08);
        border: 1px solid rgba(204,255,0,.28);
        border-radius: 18px;
        padding: 14px 16px;
        margin: 10px 0 16px;
        color: #ffffff;
    }
    .tl-checkin .tl-checkin-summary strong { color:#d8ff3f; }
    </style>
    """, unsafe_allow_html=True)
    show_flash()

    nome_busca = st.text_input("Digite seu nome para confirmar a aula", key="checkin_nome_direto")
    aluno, aviso_busca = resolve_active_student_by_name(nome_busca) if nome_busca.strip() else (None, None)
    proxima_aula = next_student_class(aluno) if aluno else None

    if aviso_busca:
        md_box("warn", aviso_busca)
    elif nome_busca.strip() and not aluno:
        st.caption("Aluno não localizado no cadastro. Se precisar, fale com a secretaria.")

    if aluno and proxima_aula:
        st.markdown(
            f"""
            <div class="tl-checkin-summary">
                <strong>Aluno localizado:</strong> {escape(str(aluno.get('nome') or 'Aluno'))}<br>
                <strong>Próxima aula:</strong> {br_date(proxima_aula['data'])} • {escape(str(proxima_aula['dia_semana']))} • {escape(str(proxima_aula['horario']))}<br>
                <strong>Local:</strong> {escape(str(proxima_aula['local']))}
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif aluno and not proxima_aula:
        md_box("warn", "Esse aluno ainda não tem agenda fixa cadastrada. Fale com a secretaria para completar o cadastro.")

    confirmar = st.button("Confirmar minha aula", use_container_width=True, key="btn_confirmar_checkin_direto")

    if confirmar:
        if not nome_busca.strip():
            md_box("error", "Digite seu nome para confirmar a aula.")
        elif aviso_busca:
            md_box("warn", aviso_busca)
        elif not aluno:
            md_box("error", f"Aluno não localizado. Fale com {secretaria_nome} pelo WhatsApp {secretaria_whatsapp}.")
        elif not proxima_aula:
            md_box("warn", "Esse aluno ainda não tem agenda fixa cadastrada. Fale com a secretaria para completar o cadastro.")
        elif proxima_aula["data"].weekday() >= 5:
            md_box("warn", "As confirmações online ficam disponíveis de segunda a sexta.")
        else:
            try:
                status = str(aluno.get("status_pagamento") or "").strip().lower()
                if status != "em_dia":
                    md_box("error", f"Seu check-in está bloqueado por pendência financeira. Regularize com {secretaria_nome}: {secretaria_whatsapp}.")
                elif confirmation_exists(aluno.get("whatsapp") or "", proxima_aula["data"].isoformat(), proxima_aula["horario"]):
                    md_box("warn", "Você já confirmou essa aula.")
                else:
                    insert_confirmation({
                        "aluno_id": aluno.get("id"),
                        "nome": aluno.get("nome") or nome_busca.strip(),
                        "whatsapp": normalize_phone(aluno.get("whatsapp") or ""),
                        "data_aula": proxima_aula["data"].isoformat(),
                        "dia_semana": proxima_aula["dia_semana"],
                        "local": proxima_aula["local"],
                        "horario": proxima_aula["horario"],
                        "status_pagamento": status,
                    })
                    flash_message("ok", f"Presença confirmada com sucesso para {br_date(proxima_aula['data'])}, às {proxima_aula['horario']}, em {proxima_aula['local']}.")
                    st.rerun()
            except AppError as exc:
                md_box("error", f"Não foi possível confirmar agora. {str(exc)}")
            except Exception:
                md_box("error", "Não foi possível confirmar agora. Tente novamente em instantes.")
    st.markdown('</div>', unsafe_allow_html=True)

def render_event_success_card(reg: dict[str, Any], secretaria_nome: str, secretaria_whatsapp: str) -> None:
    favored_name = secret_value("TOURNAMENT_PIX_FAVORECIDO") or secret_value("PIX_NAME", DEFAULTS["PIX_NAME"])
    pix_key = "torneiotenislinhares@gmail.com"
    pix_label = secret_value("TOURNAMENT_PIX_LABEL", DEFAULTS["TOURNAMENT_PIX_LABEL"]) or "Pagamento via PIX"
    receipt_text = (
        f"Olá, {secretaria_nome}. Acabei de me inscrever no torneio {reg.get('evento_titulo', 'Tênis Linhares')} "
        f"na categoria {reg.get('categoria', '')}. Segue meu comprovante. "
        f"Nome: {reg.get('nome', '')}. Plano: {reg.get('tipo_inscricao', '')}. Valor: {money_br(reg.get('valor', 0))}."
    )
    proof_url = whatsapp_link(secretaria_whatsapp, receipt_text)

    evento_titulo = escape(str(reg.get("evento_titulo", "Evento") or "Evento"))
    categoria = escape(str(reg.get("categoria", "") or ""))
    tipo_inscricao = escape(str(reg.get("tipo_inscricao", "Inscrição") or "Inscrição"))
    restricao = escape(str(reg.get("restricao_horario", "") or "")).strip()
    restricao_html = f"<br>Restrição de horário: <strong>{restricao}</strong>" if restricao else ""

    st.markdown(
        f"""
        <div class="tl-confirm-card">
            <div class="tl-confirm-title">Obrigado pela sua inscrição! 🎾</div>
            <div class="tl-confirm-text">
                Recebemos seus dados com sucesso para <strong>{evento_titulo}</strong>.<br>
                Categoria: <strong>{categoria}</strong><br>
                Plano escolhido: <strong>{tipo_inscricao}</strong>.{restricao_html}
                <br>Para confirmar sua vaga, realize o pagamento e envie o comprovante no botão abaixo.
            </div>
            <div class="tl-confirm-value">Valor: {money_br(reg.get("valor", 0))}</div>
            <div class="tl-pix-stage">
                <div class="tl-pix-stage-title">{escape(str(pix_label))}</div>
                <div class="tl-pix-stage-name">{escape(str(favored_name))}</div>
                <div class="tl-pix-stage-key">{escape(str(pix_key))}</div>
                <button type="button" id="tl-copy-tournament-pix" class="tl-copy-btn">Copiar PIX</button>
                <a class="tl-proof-btn" target="_blank" rel="noopener noreferrer" href="{proof_url}">Enviar comprovante</a>
            </div>
            <div class="tl-confirm-list">
                <div class="tl-confirm-list-title">Informações importantes</div>
                <ol>
                    <li>A organização do torneio poderá ajustar sua classe caso seja necessário equilibrar o nível técnico e o número de participantes.</li>
                    <li>A programação completa será divulgada com antecedência nos grupos oficiais e canais da Tênis Linhares.</li>
                    <li>Em caso de impossibilidade de comparecimento, comunique a organização com antecedência.</li>
                </ol>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        f"""
        <script>
        (function () {{
            const pixValue = {json.dumps(str(pix_key))};
            const normalText = "Copiar PIX";

            function setButtonText(button, text, delay) {{
                button.innerText = text;
                if (delay) {{
                    setTimeout(function () {{ button.innerText = normalText; }}, delay);
                }}
            }}

            function fallbackCopy() {{
                const doc = window.parent.document;
                const textarea = doc.createElement("textarea");
                textarea.value = pixValue;
                textarea.setAttribute("readonly", "");
                textarea.style.position = "fixed";
                textarea.style.left = "-9999px";
                textarea.style.top = "0";
                textarea.style.opacity = "0";
                doc.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                textarea.setSelectionRange(0, textarea.value.length);
                let copied = false;
                try {{ copied = doc.execCommand("copy"); }} catch (e) {{ copied = false; }}
                if (textarea.parentNode) {{
                    textarea.parentNode.removeChild(textarea);
                }}
                return copied;
            }}

            async function copyPix(button) {{
                try {{
                    if (window.parent.navigator.clipboard && window.parent.isSecureContext) {{
                        await window.parent.navigator.clipboard.writeText(pixValue);
                    }} else if (!fallbackCopy()) {{
                        throw new Error("copy-failed");
                    }}
                    setButtonText(button, "Copiado!", 1300);
                }} catch (e) {{
                    if (fallbackCopy()) {{
                        setButtonText(button, "Copiado!", 1300);
                    }} else {{
                        setButtonText(button, "Copie manualmente", 1500);
                    }}
                }}
            }}

            function bindCopyButton() {{
                const doc = window.parent.document;
                const button = doc.getElementById("tl-copy-tournament-pix");
                if (!button || button.dataset.copyPixBound === "1") return;
                button.dataset.copyPixBound = "1";
                button.addEventListener("click", function (event) {{
                    event.preventDefault();
                    copyPix(button);
                }});
            }}

            const observer = new MutationObserver(function () {{ bindCopyButton(); }});
            observer.observe(window.parent.document.body, {{ childList: true, subtree: true }});
            setTimeout(bindCopyButton, 100);
            setTimeout(bindCopyButton, 500);
            setTimeout(bindCopyButton, 1200);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

def render_student_events() -> None:
    pix_email = secret_value("PIX_EMAIL", DEFAULTS["PIX_EMAIL"])
    pix_phone = secret_value("PIX_PHONE", DEFAULTS["PIX_PHONE"])
    pix_name = secret_value("PIX_NAME", DEFAULTS["PIX_NAME"])
    secretaria_nome = secret_value("SECRETARIA_NOME", DEFAULTS["SECRETARIA_NOME"])
    secretaria_whatsapp = secret_value("SECRETARIA_WHATSAPP", DEFAULTS["SECRETARIA_WHATSAPP"])
    pricing_options = tournament_price_options()

    st.markdown('<div id="eventos"></div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tl-event-hero"><div class="tl-event-hero-title">Torneios e inscrições</div>'
        '<div class="tl-event-hero-text">Inscrição, chaves, programação e resultados em um só lugar.</div></div>',
        unsafe_allow_html=True,
    )
    show_flash()

    last_registration = st.session_state.get("tl_last_registration")
    if last_registration:
        render_event_success_card(last_registration, secretaria_nome, secretaria_whatsapp)
        if st.button("Fechar mensagem da inscrição", use_container_width=True, key="close_last_registration"):
            st.session_state.pop("tl_last_registration", None)
            st.rerun()

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
        st.markdown('<div class="tl-event-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="tl-event-title">{event.get("titulo") or "Evento"}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="tl-event-meta">{br_date(event.get("data_evento"))} • {event.get("local") or "Tênis Linhares"}</div>', unsafe_allow_html=True)
        if event.get("descricao"):
            st.markdown(f'<div class="tl-event-desc">{event.get("descricao")}</div>', unsafe_allow_html=True)

        # Tudo fica dentro das abas do próprio evento, sem informações soltas.
        render_event_public_tabs(
            event=event,
            pricing_options=pricing_options,
            pix_name=pix_name,
            pix_email=pix_email,
            pix_phone=pix_phone,
            secretaria_nome=secretaria_nome,
            secretaria_whatsapp=secretaria_whatsapp,
        )
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
        if not nome.strip() or (not whatsapp.strip() and not selected_student):
            md_box("error", "Preencha nome completo. Se você não selecionar seu cadastro, informe também o WhatsApp.")
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
    """
    Área administrativa somente na sidebar, aberta pela seta lateral do Streamlit.
    Fica disponível mesmo antes de consultar o Supabase.
    """
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    st.sidebar.markdown("## Área administrativa")
    st.sidebar.caption("Acesse para ver reservas, confirmações, inscrições, reposições, alunos e eventos.")
    senha_admin = st.sidebar.text_input("Senha admin", type="password", key="admin_pwd_side")

    col_entrar, col_sair = st.sidebar.columns(2)

    if col_entrar.button("Entrar", use_container_width=True, key="side_enter"):
        senha_digitada = str(senha_admin or "").strip()
        if verify_admin_password(senha_digitada):
            st.session_state.admin_ok = True
            flash_message("ok", "Área administrativa liberada.")
            st.rerun()
        else:
            st.sidebar.error("Senha incorreta.")

    if col_sair.button("Sair", use_container_width=True, key="side_exit"):
        st.session_state.admin_ok = False
        st.session_state.admin_pwd_side = ""
        st.rerun()

    if st.session_state.admin_ok:
        st.sidebar.success("Admin liberado.")
        st.sidebar.caption("O painel administrativo aparecerá abaixo das áreas dos alunos.")
        return True

    st.sidebar.info("Toque na seta lateral para abrir/fechar esta área.")
    return False


def render_admin_login_public(admin_ok: bool) -> bool:
    """
    Login administrativo visível na página pública.

    Mantém a sidebar original, mas também oferece um botão/expander na página
    para não depender da setinha lateral do Streamlit, que em alguns celulares
    ou temas pode ficar difícil de ver.
    """
    if admin_ok:
        return True

    st.markdown('<div class="tl-admin-login-public">', unsafe_allow_html=True)
    with st.expander("🔐 Área administrativa / Login", expanded=False):
        st.caption("Acesso exclusivo do administrador. Alunos continuam usando o site sem senha.")
        senha_admin = st.text_input("Senha admin", type="password", key="admin_pwd_main")
        col_entrar, col_sair = st.columns(2)
        if col_entrar.button("Entrar na área administrativa", use_container_width=True, key="main_admin_enter"):
            senha_digitada = str(senha_admin or "").strip()
            if verify_admin_password(senha_digitada):
                st.session_state.admin_ok = True
                flash_message("ok", "Área administrativa liberada.")
                st.rerun()
            else:
                md_box("error", "Senha incorreta.")
        if col_sair.button("Limpar", use_container_width=True, key="main_admin_clear"):
            st.session_state.admin_pwd_main = ""
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    return bool(st.session_state.get("admin_ok"))


def render_students_admin() -> None:
    st.markdown("### Alunos")
    st.caption("Cadastre novos alunos e atualize status financeiro, dados e atividade dos alunos já cadastrados.")
    show_flash()

    with st.form("form_admin_student", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do aluno")
        whatsapp = c2.text_input("WhatsApp")
        c3, c4 = st.columns(2)
        status = c3.selectbox("Status de pagamento", ["em_dia", "pendente", "inadimplente"], key="novo_status_aluno")
        ativo = c4.selectbox("Aluno ativo", ["sim", "não"], key="novo_ativo_aluno")
        c5, c6 = st.columns(2)
        valor_mensalidade = c5.number_input("Valor da mensalidade", min_value=0.0, value=0.0, step=10.0, key="novo_valor_mensalidade")
        dia_vencimento = c6.number_input("Dia fixo do vencimento", min_value=1, max_value=31, value=5, step=1, key="novo_dia_vencimento_mensalidade")
        c7, c8 = st.columns(2)
        tipo_plano = c7.selectbox("Tipo de aluno", PLAN_TYPE_OPTIONS, key="novo_tipo_plano_aluno")
        local_padrao = c8.selectbox("Local padrão do aluno (opcional)", [""] + CLASS_LOCATION_OPTIONS, key="novo_local_padrao_aluno")
        st.markdown("#### Agenda fixa do aluno")
        st.caption("Cadastre dias e horários diferentes, por exemplo: segunda 06h, quarta 06h e sexta 19h.")
        schedule_entries = []
        for idx in range(1, 5):
            d1, d2, d3 = st.columns(3)
            dia_item = d1.selectbox(f"Dia {idx}", [""] + CLASS_DAY_OPTIONS, key=f"novo_agenda_dia_{idx}")
            horario_item = d2.selectbox(f"Horário {idx}", [""] + CLASS_TIME_OPTIONS, key=f"novo_agenda_horario_{idx}")
            local_item = d3.selectbox(f"Local {idx}", [""] + CLASS_LOCATION_OPTIONS, key=f"novo_agenda_local_{idx}")
            if dia_item and horario_item:
                schedule_entries.append({"dia": dia_item, "horario": horario_item, "local": local_item or local_padrao or default_location_for_day_label(dia_item)})
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
                    "valor_mensalidade": float(valor_mensalidade),
                    "dia_vencimento_mensalidade": int(dia_vencimento),
                    "data_vencimento_mensalidade": current_month_reference_date(int(dia_vencimento)),
                    "tipo_plano": tipo_plano,
                    "dias_aula": serialize_student_days([item["dia"] for item in schedule_entries]),
                    "aula_horario": schedule_entries[0]["horario"] if schedule_entries else None,
                    "aula_local": (local_padrao or (schedule_entries[0]["local"] if schedule_entries else None)) or None,
                    "agenda_aulas": serialize_student_schedule_entries(schedule_entries),
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

        df_students = pd.DataFrame(rows)
        if "valor_mensalidade" in df_students.columns:
            finance_df = df_students.copy()
            finance_df["valor_mensalidade_num"] = pd.to_numeric(finance_df["valor_mensalidade"], errors="coerce").fillna(0)
            finance_df["dia_vencimento"] = finance_df.apply(due_day_from_student, axis=1)
            finance_df = finance_df[(finance_df["valor_mensalidade_num"] > 0) & (finance_df["dia_vencimento"].notna())]
            if not finance_df.empty:
                st.markdown("#### Valores mensais a receber por dia fixo")
                resumo = finance_df.groupby("dia_vencimento", dropna=False)["valor_mensalidade_num"].sum().reset_index()
                resumo["dia_vencimento"] = resumo["dia_vencimento"].map(lambda x: f"Dia {int(x)}")
                resumo["valor_mensalidade_num"] = resumo["valor_mensalidade_num"].map(money_br)
                resumo = resumo.rename(columns={
                    "dia_vencimento": "vencimento_recorrente",
                    "valor_mensalidade_num": "valor_a_receber_todo_mes",
                })
                st.dataframe(resumo, use_container_width=True, hide_index=True)

        st.markdown("#### Editar aluno existente")
        student_options = {
            f"{row.get('nome', 'Aluno')} • final {mask_phone_last4(row.get('whatsapp')) if mask_phone_last4(row.get('whatsapp')) else 'sem número'}": row
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
            c5, c6 = st.columns(2)
            edit_valor_mensalidade = c5.number_input(
                "Valor da mensalidade",
                min_value=0.0,
                value=float(selected_student.get("valor_mensalidade") or 0),
                step=10.0,
                key="edit_valor_mensalidade",
            )
            current_due_day = due_day_from_student(selected_student) or 5
            edit_dia_vencimento = c6.number_input(
                "Dia fixo do vencimento",
                min_value=1,
                max_value=31,
                value=int(current_due_day),
                step=1,
                key="edit_dia_vencimento_mensalidade",
            )
            c7, c8 = st.columns(2)
            current_plan = selected_student.get("tipo_plano") or "mensalidade"
            plan_index = PLAN_TYPE_OPTIONS.index(current_plan) if current_plan in PLAN_TYPE_OPTIONS else 0
            edit_tipo_plano = c7.selectbox("Tipo de aluno", PLAN_TYPE_OPTIONS, index=plan_index, key="edit_tipo_plano_aluno")
            current_local = selected_student.get("aula_local") or ""
            local_options = [""] + CLASS_LOCATION_OPTIONS
            local_index = local_options.index(current_local) if current_local in local_options else 0
            edit_local_padrao = c8.selectbox("Local padrão do aluno (opcional)", local_options, index=local_index, key="edit_local_padrao_aluno")
            st.markdown("#### Agenda fixa do aluno")
            st.caption("Edite dias e horários diferentes do mesmo aluno sem mostrar o WhatsApp completo no check-in.")
            existing_schedule_entries = student_schedule_entries(selected_student)
            while len(existing_schedule_entries) < 4:
                existing_schedule_entries.append({"dia": "", "horario": "", "local": ""})
            edit_schedule_entries = []
            for idx in range(1, 5):
                current_item = existing_schedule_entries[idx-1]
                d1, d2, d3 = st.columns(3)
                day_opts = [""] + CLASS_DAY_OPTIONS
                current_day = current_item.get("dia") or ""
                day_index = day_opts.index(current_day) if current_day in day_opts else 0
                edit_day = d1.selectbox(f"Dia {idx}", day_opts, index=day_index, key=f"edit_agenda_dia_{idx}")
                time_opts = [""] + CLASS_TIME_OPTIONS
                current_time = current_item.get("horario") or ""
                time_index = time_opts.index(current_time) if current_time in time_opts else 0
                edit_time = d2.selectbox(f"Horário {idx}", time_opts, index=time_index, key=f"edit_agenda_horario_{idx}")
                local_opts = [""] + CLASS_LOCATION_OPTIONS
                current_loc = current_item.get("local") or ""
                loc_index = local_opts.index(current_loc) if current_loc in local_opts else 0
                edit_loc = d3.selectbox(f"Local {idx}", local_opts, index=loc_index, key=f"edit_agenda_local_{idx}")
                if edit_day and edit_time:
                    edit_schedule_entries.append({"dia": edit_day, "horario": edit_time, "local": edit_loc or edit_local_padrao or default_location_for_day_label(edit_day)})
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
                        "valor_mensalidade": float(edit_valor_mensalidade),
                        "dia_vencimento_mensalidade": int(edit_dia_vencimento),
                        "data_vencimento_mensalidade": current_month_reference_date(int(edit_dia_vencimento)),
                        "tipo_plano": edit_tipo_plano,
                        "dias_aula": serialize_student_days([item["dia"] for item in edit_schedule_entries]),
                        "aula_horario": edit_schedule_entries[0]["horario"] if edit_schedule_entries else None,
                        "aula_local": (edit_local_padrao or (edit_schedule_entries[0]["local"] if edit_schedule_entries else None)) or None,
                        "agenda_aulas": serialize_student_schedule_entries(edit_schedule_entries),
                        "observacao": edit_obs.strip() or None,
                    })
                    clear_caches()
                    md_box("ok", "Aluno atualizado com sucesso.")
                except AppError as exc:
                    md_box("error", str(exc))

        with st.expander("Apagar aluno", expanded=False):
            st.caption("Use apenas se precisar remover um aluno cadastrado. Dados apagados não voltam automaticamente.")
            delete_student_options = {
                f"{row.get('nome', 'Aluno')} • final {mask_phone_last4(row.get('whatsapp')) if mask_phone_last4(row.get('whatsapp')) else 'sem número'}": str(row.get("id"))
                for row in rows
            }
            delete_student_label = st.selectbox("Selecionar aluno para apagar", list(delete_student_options.keys()), key="admin_select_student_delete")
            confirm_delete_student = st.checkbox("Confirmo que desejo apagar o aluno selecionado", key="confirm_delete_student")
            if st.button("Apagar aluno selecionado", use_container_width=True, disabled=not confirm_delete_student, key="btn_delete_student"):
                try:
                    delete_records_by_ids("alunos", [delete_student_options[delete_student_label]])
                    clear_caches()
                    md_box("ok", "Aluno apagado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        st.markdown("#### Lista de alunos")
        df = pd.DataFrame(rows)
        if "valor_mensalidade" in df.columns:
            df["valor_mensalidade"] = df["valor_mensalidade"].map(money_br)
        df["dia_vencimento_mensalidade"] = df.apply(due_day_from_student, axis=1).map(lambda x: f"Dia {int(x)}" if pd.notna(x) else "")
        if "agenda_aulas" in df.columns:
            df["agenda_aulas"] = df.apply(lambda row: student_schedule_summary(row.to_dict()), axis=1)
        st.dataframe(clean_admin_dataframe(df), use_container_width=True, hide_index=True)
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
        with st.expander("Apagar evento/torneio", expanded=False):
            st.caption("Use apenas se precisar remover um evento cadastrado. Dados apagados não voltam automaticamente.")
            delete_event_options = {
                f"{event.get('titulo', 'Evento')} • {br_date(event.get('data_evento'))}": str(event.get("id"))
                for event in all_events
            }
            delete_event_label = st.selectbox("Selecionar evento para apagar", list(delete_event_options.keys()), key="admin_select_event_delete")
            confirm_delete_event = st.checkbox("Confirmo que desejo apagar o evento selecionado", key="confirm_delete_event")
            if st.button("Apagar evento selecionado", use_container_width=True, disabled=not confirm_delete_event, key="btn_delete_event"):
                try:
                    delete_records_by_ids("eventos", [delete_event_options[delete_event_label]])
                    clear_caches()
                    md_box("ok", "Evento apagado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        df = pd.DataFrame(all_events)
        df["data_evento"] = df["data_evento"].map(br_date)
        df["valor_inscricao"] = df["valor_inscricao"].map(money_br)
        st.dataframe(clean_admin_dataframe(df), use_container_width=True, hide_index=True)

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
        evento_filtro = c1.selectbox("Filtrar por evento", eventos)
        categoria_filtro = c2.selectbox("Filtrar por categoria", categorias)
        status_filtro = c3.selectbox("Filtrar por status", status_list)

        if evento_filtro != "Todos":
            df = df[df["evento_titulo"] == evento_filtro]
        if categoria_filtro != "Todas":
            df = df[df["categoria"] == categoria_filtro]
        if status_filtro != "Todos":
            df = df[df["status_inscricao"] == status_filtro]

        if df.empty:
            st.info("Nenhuma inscrição encontrada com esses filtros.")
            return

        df_status_base = df.copy()
        df_status_base["valor_num"] = pd.to_numeric(df_status_base.get("valor", pd.Series(dtype=float)), errors="coerce").fillna(0)
        df_status_base["status_normalizado"] = df_status_base.get("status_inscricao", pd.Series(dtype=str)).fillna("").astype(str).str.lower().str.strip()
        pagas_df = df_status_base[df_status_base["status_normalizado"].isin(["pago", "paga", "pagamento_confirmado", "confirmado", "confirmada"])]
        pendentes_df = df_status_base[~df_status_base["status_normalizado"].isin(["pago", "paga", "pagamento_confirmado", "confirmado", "confirmada", "cancelado", "cancelada"])]

        valor_recebido_inscricoes = float(pagas_df["valor_num"].sum()) if not pagas_df.empty else 0.0
        valor_pendente_inscricoes = float(pendentes_df["valor_num"].sum()) if not pendentes_df.empty else 0.0
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Inscrições pagas", f"{len(pagas_df)}")
        s2.metric("Valor recebido", money_br(valor_recebido_inscricoes))
        s3.metric("Inscrições pendentes", f"{len(pendentes_df)}")
        s4.metric("Valor pendente", money_br(valor_pendente_inscricoes))

        with st.expander("Atualizar pagamento das inscrições", expanded=False):
            st.caption("Use esta área para marcar inscrição como paga ou pendente. O painel financeiro é atualizado imediatamente após salvar.")
            payment_options = {
                f"{row.get('evento_titulo','Evento')} • {row.get('categoria','Categoria')} • {row.get('nome','Aluno')} • {row.get('whatsapp','')} • {money_br(row.get('valor', 0))} • {row.get('status_inscricao','')}": str(row.get("id"))
                for _, row in df_status_base.sort_values(["evento_titulo", "categoria_ordem", "nome", "created_at"]).iterrows()
            }
            selected_payment_label = st.selectbox("Selecionar inscrição", list(payment_options.keys()), key="admin_select_registration_payment")
            selected_payment_id = payment_options[selected_payment_label]
            status_pagamento_inscricao = st.radio(
                "Status do pagamento",
                ["Pago", "Pendente / não pago", "Comprovante enviado", "Cancelado"],
                horizontal=True,
                key="admin_registration_payment_status",
            )
            status_payload_map = {
                "Pago": "pago",
                "Pendente / não pago": "aguardando_pagamento",
                "Comprovante enviado": "comprovante_enviado",
                "Cancelado": "cancelado",
            }
            if st.button("Salvar status da inscrição", use_container_width=True, key="btn_update_registration_payment_status"):
                try:
                    update_registration(selected_payment_id, {"status_inscricao": status_payload_map[status_pagamento_inscricao]})
                    clear_caches()
                    md_box("ok", "Status da inscrição atualizado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        with st.expander("Alterar categoria do atleta", expanded=False):
            st.caption("Área administrativa: use apenas para corrigir a categoria de uma inscrição já registrada. Isso não aparece na área pública.")
            category_options = {
                f"{row.get('evento_titulo','Evento')} • {row.get('categoria','Categoria')} • {row.get('nome','Aluno')} • {row.get('whatsapp','')}": row
                for _, row in df_status_base.sort_values(["evento_titulo", "categoria_ordem", "nome", "created_at"]).iterrows()
            }
            selected_category_label = st.selectbox("Selecionar inscrição para alterar categoria", list(category_options.keys()), key="admin_select_registration_category_change")
            selected_category_row = category_options[selected_category_label]
            current_category = str(selected_category_row.get("categoria") or "")
            default_category_index = TOURNAMENT_CATEGORIES.index(current_category) if current_category in TOURNAMENT_CATEGORIES else 0
            new_category = st.selectbox("Nova categoria", TOURNAMENT_CATEGORIES, index=default_category_index, key="admin_registration_new_category")
            confirm_category_change = st.checkbox("Confirmo que desejo alterar a categoria desta inscrição", key="confirm_category_change")
            if st.button("Salvar nova categoria", use_container_width=True, disabled=not confirm_category_change, key="btn_update_registration_category"):
                try:
                    if new_category == current_category:
                        md_box("warn", "A inscrição já está nessa categoria.")
                    elif tournament_category_count(str(selected_category_row.get("evento_id")), new_category) >= TOURNAMENT_CATEGORY_LIMIT:
                        md_box("warn", f"A categoria {new_category} já atingiu o limite de {TOURNAMENT_CATEGORY_LIMIT} inscritos.")
                    elif registration_exists(str(selected_category_row.get("evento_id")), str(selected_category_row.get("whatsapp") or ""), new_category):
                        md_box("warn", "Esse WhatsApp já possui inscrição nessa categoria.")
                    else:
                        update_registration(str(selected_category_row.get("id")), {"categoria": new_category})
                        clear_caches()
                        md_box("ok", "Categoria da inscrição atualizada com sucesso.")
                        st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        with st.expander("Apagar inscrições do torneio", expanded=False):
            st.caption("Use apenas para apagar inscrições selecionadas. Dados apagados não voltam automaticamente.")
            st.write(f"Inscrições visíveis com os filtros atuais: **{len(df)}**")
            delete_options = {
                f"{row.get('evento_titulo','Evento')} • {row.get('categoria','Categoria')} • {row.get('nome','Aluno')} • {row.get('whatsapp','')}": str(row.get("id"))
                for _, row in df.sort_values(["evento_titulo", "categoria_ordem", "nome", "created_at"]).iterrows()
            }
            selected_label = st.selectbox("Selecionar inscrição", list(delete_options.keys()), key="admin_select_registration_delete")
            selected_id = delete_options[selected_label]
            delete_mode = st.radio(
                "O que deseja apagar?",
                ["Apenas a inscrição selecionada", "Todas as inscrições filtradas acima"],
                key="delete_registration_mode",
            )
            confirm_delete = st.checkbox("Confirmo que desejo apagar a(s) inscrição(ões) selecionada(s)", key="confirm_delete_registrations")
            if st.button("Apagar inscrição/inscrições", use_container_width=True, disabled=not confirm_delete, key="btn_delete_registrations_filtered"):
                try:
                    ids = [selected_id] if delete_mode == "Apenas a inscrição selecionada" else df["id"].astype(str).tolist()
                    delete_records_by_ids("inscricoes_eventos", ids)
                    clear_caches()
                    md_box("ok", "Inscrição(ões) apagada(s) com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        if "valor" in df.columns:
            df["valor"] = df["valor"].map(money_br)
        if "created_at" in df.columns:
            df["created_at"] = df["created_at"].map(br_date)

        df = df.sort_values(["evento_titulo", "categoria_ordem", "nome", "created_at"])
        for event_title, event_group in df.groupby("evento_titulo"):
            st.markdown(f'<div class="tl-group-title">{event_title}</div>', unsafe_allow_html=True)
            event_group = event_group.drop(columns=["categoria_ordem"])
            st.dataframe(clean_admin_dataframe(event_group), use_container_width=True, hide_index=True)
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
            st.dataframe(clean_admin_dataframe(group), use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("error", str(exc))

def render_stringing_admin() -> None:
    st.markdown("### Encordoamentos")
    st.caption("Registre encordoamentos e acompanhe separado o valor da corda e da mão de obra.")

    with st.form("form_admin_stringing", clear_on_submit=True):
        c1, c2 = st.columns(2)
        aluno_nome = c1.text_input("Nome do aluno/cliente", key="stringing_nome")
        whatsapp = c2.text_input("WhatsApp", key="stringing_whatsapp")
        c3, c4 = st.columns(2)
        data_servico = c3.date_input("Data do serviço", value=date.today(), key="stringing_data")
        valor_total = c4.number_input("Valor cobrado", min_value=0.0, value=STRINGING_DEFAULT_TOTAL, step=5.0, key="stringing_total")
        c5, c6 = st.columns(2)
        valor_mao_obra = c5.number_input("Mão de obra", min_value=0.0, value=STRINGING_DEFAULT_LABOR, step=5.0, key="stringing_labor")
        valor_corda = max(float(valor_total) - float(valor_mao_obra), 0.0)
        c6.markdown(f"**Valor da corda:** {money_br(valor_corda)}")
        observacao = st.text_input("Observação", key="stringing_obs")
        submit = st.form_submit_button("Registrar encordoamento", use_container_width=True)

    if submit:
        if not aluno_nome.strip():
            md_box("error", "Informe o nome do aluno/cliente.")
        else:
            try:
                insert_stringing({
                    "aluno_nome": aluno_nome.strip(),
                    "whatsapp": normalize_phone(whatsapp),
                    "data_servico": data_servico.isoformat(),
                    "valor_total": float(valor_total),
                    "valor_corda": float(valor_corda),
                    "valor_mao_obra": float(valor_mao_obra),
                    "observacao": observacao.strip() or None,
                })
                clear_caches()
                md_box("ok", "Encordoamento registrado com sucesso.")
            except AppError as exc:
                md_box("error", f"Não foi possível salvar o encordoamento. {str(exc)}")

    try:
        rows = fetch_stringings()
        if not rows:
            st.info("Nenhum encordoamento registrado ainda.")
            return
        df = pd.DataFrame(rows)
        for col in ["valor_total", "valor_corda", "valor_mao_obra"]:
            if col in df.columns:
                df[f"{col}_num"] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        total_geral = float(df.get("valor_total_num", pd.Series(dtype=float)).sum())
        total_corda = float(df.get("valor_corda_num", pd.Series(dtype=float)).sum())
        total_mao_obra = float(df.get("valor_mao_obra_num", pd.Series(dtype=float)).sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Total encordoamentos", money_br(total_geral))
        m2.metric("Valor em corda", money_br(total_corda))
        m3.metric("Mão de obra", money_br(total_mao_obra))

        with st.expander("Apagar encordoamento", expanded=False):
            st.caption("Use apenas se precisar remover um encordoamento registrado. Dados apagados não voltam automaticamente.")
            delete_stringing_options = {
                f"{br_date(row.get('data_servico'))} • {row.get('aluno_nome', 'Cliente')} • {money_br(row.get('valor_total', 0))}": str(row.get("id"))
                for _, row in df.iterrows()
            }
            delete_stringing_label = st.selectbox("Selecionar encordoamento para apagar", list(delete_stringing_options.keys()), key="admin_select_stringing_delete")
            confirm_delete_stringing = st.checkbox("Confirmo que desejo apagar o encordoamento selecionado", key="confirm_delete_stringing")
            if st.button("Apagar encordoamento selecionado", use_container_width=True, disabled=not confirm_delete_stringing, key="btn_delete_stringing"):
                try:
                    delete_records_by_ids("encordoamentos", [delete_stringing_options[delete_stringing_label]])
                    clear_caches()
                    md_box("ok", "Encordoamento apagado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        display_df = df.drop(columns=[col for col in df.columns if col.endswith("_num")], errors="ignore")
        if "data_servico" in display_df.columns:
            display_df["data_servico"] = display_df["data_servico"].map(br_date)
        for col in ["valor_total", "valor_corda", "valor_mao_obra"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].map(money_br)
        st.dataframe(clean_admin_dataframe(display_df), use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("warn", f"Área de encordoamentos ainda precisa da tabela no Supabase. {str(exc)}")

def render_financial_expectation_admin() -> None:
    st.markdown("### Expectativa financeira")
    st.caption("Mensalidades recorrentes até dia 10, encordoamentos do mês até dia 10 e torneios contabilizados pelo total geral de inscrições pagas.")

    # Mantém o painel financeiro atualizado com o banco na hora.
    for _cache_func in (fetch_students, fetch_registrations, fetch_stringings):
        try:
            _cache_func.clear()
        except Exception:
            pass

    hoje = date.today()
    c1, c2 = st.columns(2)
    mes = c1.selectbox(
        "Mês dos encordoamentos",
        list(range(1, 13)),
        index=hoje.month - 1,
        format_func=lambda x: f"{x:02d}",
        key="finance_expectation_month",
    )
    anos = list(range(hoje.year - 1, hoje.year + 3))
    ano = c2.selectbox(
        "Ano dos encordoamentos",
        anos,
        index=anos.index(hoje.year) if hoje.year in anos else 1,
        key="finance_expectation_year",
    )
    data_limite = date(int(ano), int(mes), 10)
    st.caption(
        f"Mensalidades: alunos ativos com dia fixo de vencimento até **dia 10**. "
        f"Encordoamentos: serviços até **{br_date(data_limite)}**. "
        "Torneios: total geral de inscrições marcadas como **pago**, sem limitar por mês."
    )

    total_mensalidades = 0.0
    total_torneios_pagos = 0.0
    total_torneios_pendentes = 0.0
    total_encordoamentos = 0.0
    total_corda = 0.0
    total_mao_obra = 0.0

    detalhes_mensalidades = pd.DataFrame()
    detalhes_torneios_pagos = pd.DataFrame()
    detalhes_torneios_pendentes = pd.DataFrame()
    detalhes_encordoamentos = pd.DataFrame()

    try:
        alunos = fetch_students(1000)
        if alunos:
            df_alunos = pd.DataFrame(alunos)
            if "valor_mensalidade" in df_alunos.columns:
                df_alunos["valor_num"] = pd.to_numeric(df_alunos["valor_mensalidade"], errors="coerce").fillna(0)
                df_alunos["dia_vencimento"] = df_alunos.apply(due_day_from_student, axis=1)
                if "ativo" in df_alunos.columns:
                    df_alunos = df_alunos[df_alunos["ativo"].fillna(True).astype(bool)]
                df_mensal = df_alunos[
                    (df_alunos["valor_num"] > 0)
                    & (df_alunos["dia_vencimento"].notna())
                    & (df_alunos["dia_vencimento"].astype(float) <= 10)
                ].copy()
                total_mensalidades = float(df_mensal["valor_num"].sum()) if not df_mensal.empty else 0.0
                if not df_mensal.empty:
                    detalhes_mensalidades = df_mensal[["nome", "whatsapp", "status_pagamento", "dia_vencimento", "valor_mensalidade"]].copy()
                    detalhes_mensalidades["dia_vencimento"] = detalhes_mensalidades["dia_vencimento"].map(lambda x: f"Dia {int(x)}")
                    detalhes_mensalidades["valor_mensalidade"] = detalhes_mensalidades["valor_mensalidade"].map(money_br)
                    detalhes_mensalidades = detalhes_mensalidades.rename(columns={
                        "dia_vencimento": "vencimento_recorrente"
                    })
    except AppError as exc:
        md_box("warn", f"Não foi possível calcular mensalidades. {str(exc)}")

    try:
        encordoamentos = fetch_stringings(2000)
        if encordoamentos:
            df_enc = pd.DataFrame(encordoamentos)
            df_enc["data_calc"] = df_enc.get("data_servico", pd.Series(dtype=object)).map(parse_date_optional)
            for col in ["valor_total", "valor_corda", "valor_mao_obra"]:
                if col in df_enc.columns:
                    df_enc[f"{col}_num"] = pd.to_numeric(df_enc[col], errors="coerce").fillna(0)
                else:
                    df_enc[f"{col}_num"] = 0.0
            df_enc = df_enc[
                df_enc["data_calc"].map(lambda d: d is not None and d.year == int(ano) and d.month == int(mes) and d.day <= 10)
            ].copy()
            total_encordoamentos = float(df_enc["valor_total_num"].sum()) if not df_enc.empty else 0.0
            total_corda = float(df_enc["valor_corda_num"].sum()) if not df_enc.empty else 0.0
            total_mao_obra = float(df_enc["valor_mao_obra_num"].sum()) if not df_enc.empty else 0.0
            if not df_enc.empty:
                detalhes_encordoamentos = df_enc.drop(columns=[col for col in df_enc.columns if col.endswith("_num") or col == "data_calc"], errors="ignore").copy()
                if "data_servico" in detalhes_encordoamentos.columns:
                    detalhes_encordoamentos["data_servico"] = detalhes_encordoamentos["data_servico"].map(br_date)
                for col in ["valor_total", "valor_corda", "valor_mao_obra"]:
                    if col in detalhes_encordoamentos.columns:
                        detalhes_encordoamentos[col] = detalhes_encordoamentos[col].map(money_br)
    except AppError as exc:
        md_box("warn", f"Não foi possível calcular encordoamentos. {str(exc)}")

    try:
        inscricoes = fetch_registrations(3000)
        if inscricoes:
            df_insc = pd.DataFrame(inscricoes)
            df_insc["valor_num"] = pd.to_numeric(df_insc.get("valor", pd.Series(dtype=float)), errors="coerce").fillna(0)
            df_insc["status_normalizado"] = df_insc.get("status_inscricao", pd.Series(dtype=str)).fillna("").astype(str).str.lower().str.strip()
            df_insc = df_insc[df_insc["status_normalizado"].map(is_not_cancelled)].copy()
            df_pagas = df_insc[df_insc["status_normalizado"].map(is_paid_status)].copy()
            df_pendentes = df_insc[df_insc["status_normalizado"].map(is_pending_status)].copy()

            total_torneios_pagos = float(df_pagas["valor_num"].sum()) if not df_pagas.empty else 0.0
            total_torneios_pendentes = float(df_pendentes["valor_num"].sum()) if not df_pendentes.empty else 0.0

            if not df_pagas.empty:
                detalhes_torneios_pagos = df_pagas.drop(columns=["valor_num", "status_normalizado"], errors="ignore").copy()
                if "valor" in detalhes_torneios_pagos.columns:
                    detalhes_torneios_pagos["valor"] = detalhes_torneios_pagos["valor"].map(money_br)
                if "created_at" in detalhes_torneios_pagos.columns:
                    detalhes_torneios_pagos["created_at"] = detalhes_torneios_pagos["created_at"].map(br_date)
            if not df_pendentes.empty:
                detalhes_torneios_pendentes = df_pendentes.drop(columns=["valor_num", "status_normalizado"], errors="ignore").copy()
                if "valor" in detalhes_torneios_pendentes.columns:
                    detalhes_torneios_pendentes["valor"] = detalhes_torneios_pendentes["valor"].map(money_br)
                if "created_at" in detalhes_torneios_pendentes.columns:
                    detalhes_torneios_pendentes["created_at"] = detalhes_torneios_pendentes["created_at"].map(br_date)
    except AppError as exc:
        md_box("warn", f"Não foi possível calcular torneios. {str(exc)}")

    total_expectativa_recebida = total_mensalidades + total_encordoamentos + total_torneios_pagos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mensalidades até dia 10", money_br(total_mensalidades))
    c2.metric("Encordoamentos até dia 10", money_br(total_encordoamentos))
    c3.metric("Torneios pagos geral", money_br(total_torneios_pagos))
    c4.metric("Total previsto/recebido", money_br(total_expectativa_recebida))

    c5, c6, c7 = st.columns(3)
    c5.metric("Torneios pendentes", money_br(total_torneios_pendentes))
    c6.metric("Corda", money_br(total_corda))
    c7.metric("Mão de obra", money_br(total_mao_obra))

    resumo = pd.DataFrame([
        {"origem": "Mensalidades recorrentes até dia 10", "valor": money_br(total_mensalidades)},
        {"origem": "Encordoamentos do mês até dia 10", "valor": money_br(total_encordoamentos)},
        {"origem": "Torneios pagos geral", "valor": money_br(total_torneios_pagos)},
        {"origem": "Torneios pendentes geral", "valor": money_br(total_torneios_pendentes)},
        {"origem": "Total sem pendentes", "valor": money_br(total_expectativa_recebida)},
    ])
    st.markdown("#### Resumo")
    st.dataframe(resumo, use_container_width=True, hide_index=True)

    with st.expander("Detalhes das mensalidades consideradas", expanded=False):
        if detalhes_mensalidades.empty:
            st.info("Nenhuma mensalidade ativa com vencimento recorrente até dia 10.")
        else:
            st.dataframe(clean_admin_dataframe(detalhes_mensalidades), use_container_width=True, hide_index=True)

    with st.expander("Detalhes dos encordoamentos considerados", expanded=False):
        if detalhes_encordoamentos.empty:
            st.info("Nenhum encordoamento registrado até dia 10 nesse mês.")
        else:
            st.dataframe(clean_admin_dataframe(detalhes_encordoamentos), use_container_width=True, hide_index=True)

    with st.expander("Detalhes das inscrições pagas de torneio", expanded=False):
        if detalhes_torneios_pagos.empty:
            st.info("Nenhuma inscrição de torneio marcada como paga.")
        else:
            st.dataframe(clean_admin_dataframe(detalhes_torneios_pagos), use_container_width=True, hide_index=True)

    with st.expander("Detalhes das inscrições pendentes de torneio", expanded=False):
        if detalhes_torneios_pendentes.empty:
            st.info("Nenhuma inscrição pendente de torneio.")
        else:
            st.dataframe(clean_admin_dataframe(detalhes_torneios_pendentes), use_container_width=True, hide_index=True)

def render_security_admin() -> None:
    st.markdown("### Segurança")
    st.caption("Troque a senha da área administrativa sem precisar mexer no Render. Após salvar, o app passa a usar a senha salva aqui.")

    with st.form("form_admin_password_change"):
        senha_atual = st.text_input("Senha atual", type="password", key="senha_atual_admin_change")
        nova_senha = st.text_input("Nova senha", type="password", key="nova_senha_admin_change")
        confirmar_senha = st.text_input("Confirmar nova senha", type="password", key="confirmar_senha_admin_change")
        submitted = st.form_submit_button("Atualizar senha administrativa", use_container_width=True)

    if submitted:
        if not verify_admin_password(senha_atual):
            st.error("Senha atual incorreta.")
            return
        if len(str(nova_senha or "").strip()) < 6:
            st.error("Use uma senha com pelo menos 6 caracteres.")
            return
        if str(nova_senha or "").strip() != str(confirmar_senha or "").strip():
            st.error("A confirmação da nova senha não confere.")
            return
        try:
            save_admin_password(str(nova_senha or "").strip())
            st.session_state.admin_ok = False
            st.success("Senha administrativa atualizada. Entre novamente usando a nova senha.")
        except AppError as exc:
            st.error(f"Não foi possível salvar a senha no banco: {exc}")
            st.info("Rode o SQL novo no Supabase para criar a tabela app_settings e tente novamente.")

    st.info("Enquanto nenhuma senha for salva aqui, o app usa ADMIN_PASSWORD do Render. A senha fixa antiga do código não é mais aceita.")


def render_admin_panel() -> None:
    st.markdown('<div class="tl-card tl-admin">', unsafe_allow_html=True)
    st.markdown('<div class="tl-section">Painel administrativo</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-caption">Cadastre alunos, controle eventos, inscrições e confirmações.</div>', unsafe_allow_html=True)
    show_flash()
    # Redefine tabs to include sponsors and bracket administration
    tabs = [
        "Painel financeiro",
        "Alunos",
        "Eventos/Torneios",
        "Chaves / Agenda",
        "Inscrições",
        "Confirmações de aulas",
        "Reposições",
        "Encordoamentos",
        "Aula experimental",
        "Patrocinadores",
        "Segurança",
    ]
    (
        t1,
        t2,
        t3,
        t4,
        t5,
        t6,
        t7,
        t8,
        t9,
        t10,
        t11,
    ) = st.tabs(tabs)
    with t1:
        render_financial_expectation_admin()
    with t2:
        render_students_admin()
    with t3:
        render_events_admin()
    with t4:
        # Chaves / Agenda management
        render_bracket_admin()
    with t5:
        render_registrations_admin()
    with t6:
        render_confirmations_admin()
    with t7:
        render_makeups_admin()
    with t8:
        render_stringing_admin()
    with t9:
        render_trial_requests_admin()
    with t10:
        render_sponsors_admin()
    with t11:
        render_security_admin()
    st.markdown('</div>', unsafe_allow_html=True)


################################################################################
# Patrocinadores e Chaves — Funções auxiliares e telas
#
# A partir deste ponto adicionamos suporte para gerenciamento de patrocinadores
# e a criação de chaves/agenda de torneios. Essas funções não interferem
# nas funcionalidades existentes e são carregadas de maneira preguiçosa
# (lazy) graças aos decoradores st.cache_data.

# PUBLIC: renderiza as logos dos patrocinadores na página inicial
def render_sponsors_public() -> None:
    sponsors = fetch_sponsors(include_inactive=False)
    if not sponsors:
        return
    html_parts = ["<div class='tl-sponsors'>"]
    for sp in sponsors:
        name = escape(sp.get("nome") or "")
        logo = sp.get("logo_url") or ""
        link = sp.get("link") or ""
        content = name
        if logo:
            content = f"<img src='{logo}' alt='{name}'>"
        if link:
            html_parts.append(f"<a href='{escape(link)}' target='_blank' rel='noopener'>{content}</a>")
        else:
            html_parts.append(f"<span>{content}</span>")
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


# ADMIN: interface para cadastro e manutenção de patrocinadores
def render_sponsors_admin() -> None:
    st.markdown("### Patrocinadores")
    try:
        sponsors = fetch_sponsors(include_inactive=True)
    except AppError as exc:
        md_box("error", str(exc))
        sponsors = []
    with st.expander("Adicionar novo patrocinador", expanded=False):
        new_name = st.text_input("Nome", key="sponsor_name_new")
        new_logo = st.text_input("URL do logo (PNG/JPG)", key="sponsor_logo_new")
        new_link = st.text_input("Link (opcional)", key="sponsor_link_new")
        new_order = st.number_input(
            "Ordem (controle de exibição)", value=0, step=1, format="%d", key="sponsor_order_new"
        )
        new_active = st.checkbox("Ativo", value=True, key="sponsor_active_new")
        if st.button("Adicionar", key="add_sponsor_btn"):
            try:
                payload = {
                    "nome": new_name.strip() or None,
                    "logo_url": new_logo.strip() or None,
                    "link": new_link.strip() or None,
                    "ordem": int(new_order),
                    "ativo": new_active,
                }
                insert_sponsor(payload)
                md_box("ok", "Patrocinador adicionado.")
                st.rerun()
            except AppError as exc:
                md_box("error", str(exc))

    if sponsors:
        for sp in sponsors:
            with st.expander(f"{sp.get('nome') or 'Patrocinador'}", expanded=False):
                name_val = st.text_input(
                    "Nome", sp.get("nome") or "", key=f"sponsor_edit_name_{sp['id']}"
                )
                logo_val = st.text_input(
                    "Logo URL", sp.get("logo_url") or "", key=f"sponsor_edit_logo_{sp['id']}"
                )
                link_val = st.text_input(
                    "Link", sp.get("link") or "", key=f"sponsor_edit_link_{sp['id']}"
                )
                order_val = st.number_input(
                    "Ordem", value=int(sp.get("ordem") or 0), step=1, format="%d", key=f"sponsor_edit_order_{sp['id']}"
                )
                active_val = st.checkbox(
                    "Ativo", value=bool(sp.get("ativo")), key=f"sponsor_edit_active_{sp['id']}"
                )
                col1, col2 = st.columns(2)
                if col1.button("Salvar alterações", key=f"sponsor_update_{sp['id']}"):
                    try:
                        payload = {
                            "nome": name_val.strip() or None,
                            "logo_url": logo_val.strip() or None,
                            "link": link_val.strip() or None,
                            "ordem": int(order_val),
                            "ativo": active_val,
                        }
                        update_sponsor(sp["id"], payload)
                        md_box("ok", "Patrocinador atualizado.")
                        st.rerun()
                    except AppError as exc:
                        md_box("error", str(exc))
                if col2.button("Apagar", key=f"sponsor_delete_{sp['id']}"):
                    try:
                        delete_sponsor(sp["id"])
                        md_box("ok", "Patrocinador removido.")
                        st.rerun()
                    except AppError as exc:
                        md_box("error", str(exc))
    else:
        st.info("Nenhum patrocinador cadastrado.")


# ADMIN: gerenciamento de chaves e jogos
def render_bracket_admin() -> None:
    st.markdown("### Chaves, Programação e Resultados")
    st.caption("Aqui você pode subir a chave pronta feita manualmente, importar programação em planilha/CSV e também cadastrar jogos individualmente.")
    try:
        events = fetch_events(admin=True)
    except AppError as exc:
        md_box("error", str(exc))
        events = []
    if not events:
        st.info("Nenhum evento encontrado. Primeiro crie o torneio em Eventos/Torneios.")
        return

    options = {
        f"{e.get('titulo') or 'Evento'} • {br_date(e.get('data_evento'))}": e.get("id")
        for e in events
    }
    selected_label = st.selectbox("Selecione o torneio/evento", list(options.keys()), key="bracket_event_select")
    selected_event_id = options.get(selected_label)
    if not selected_event_id:
        return

    aba_upload, aba_programacao, aba_manual, aba_resultados, aba_lista = st.tabs([
        "Upload de chaves prontas",
        "Programação por planilha",
        "Jogo manual",
        "Resultados ao vivo",
        "Ver / editar / apagar",
    ])

    with aba_upload:
        st.markdown("#### Upload de arquivo pronto")
        st.caption("Use esta área para subir uma chave pronta ou uma programação pronta em imagem/PDF. Ideal para arquivo feito manualmente fora do app e publicado no site.")
        tipo_arquivo_label = st.selectbox("Tipo do arquivo", ["Chave pronta", "Programação pronta"], key="upload_tipo_arquivo")
        tipo_arquivo = "programacao_arquivo" if tipo_arquivo_label == "Programação pronta" else "chave"
        c1, c2 = st.columns(2)
        titulo = c1.text_input("Título do arquivo", value="Chave principal", key="upload_chave_titulo")
        categoria_opcoes_upload = ["Todas as categorias"] + TOURNAMENT_CATEGORIES + ["Outra / personalizada"]
        categoria_upload_select = c2.selectbox(
            "Categoria / Classe",
            categoria_opcoes_upload,
            key="upload_chave_categoria_select",
            help="Escolha a categoria igual aparece na inscrição. Se for um arquivo geral, deixe Todas as categorias.",
        )
        categoria_upload_custom = c2.text_input(
            "Categoria personalizada",
            placeholder="Ex.: Duplas B",
            key="upload_chave_categoria_custom",
        ) if categoria_upload_select == "Outra / personalizada" else ""
        arquivo = st.file_uploader(
            "Escolha o arquivo",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            key="upload_chave_file",
        )
        ordem = st.number_input("Ordem de exibição", min_value=0, value=0, step=1, key="upload_chave_ordem")
        texto = st.text_area("Observação opcional", placeholder="Ex.: chave atualizada após sorteio", key="upload_chave_texto")
        if st.button("Salvar arquivo no site", use_container_width=True, key="btn_salvar_chave_upload"):
            if not arquivo:
                md_box("error", "Envie um arquivo antes de salvar.")
            else:
                try:
                    nome_arquivo, mime, conteudo_b64 = _file_to_base64(arquivo, max_mb=3.0)
                    categoria_final = ""
                    if categoria_upload_select == "Outra / personalizada":
                        categoria_final = categoria_upload_custom.strip()
                    elif categoria_upload_select != "Todas as categorias":
                        categoria_final = categoria_upload_select
                    insert_tournament_file({
                        "torneio_id": selected_event_id,
                        "tipo": tipo_arquivo,
                        "titulo": titulo.strip() or "Chave",
                        "categoria": categoria_final or None,
                        "arquivo_nome": nome_arquivo,
                        "mime_type": mime,
                        "arquivo_base64": conteudo_b64,
                        "texto": texto.strip() or None,
                        "ordem": int(ordem),
                        "ativo": True,
                    })
                    md_box("ok", "Arquivo enviado e publicado no evento.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        st.markdown("---")
        st.markdown("#### Arquivos já enviados")
        files = fetch_tournament_files(selected_event_id, tipo=None, include_inactive=True)
        if not files:
            st.info("Nenhum arquivo enviado ainda.")
        else:
            for f in files:
                with st.expander(f"{f.get('titulo') or 'Chave'} • {f.get('categoria') or 'Sem categoria'}", expanded=False):
                    st.write(f"Arquivo: **{f.get('arquivo_nome') or 'arquivo'}**")
                    st.write(f"Status: **{'ativo' if f.get('ativo') else 'inativo'}**")
                    col_a, col_b = st.columns(2)
                    ativo = col_a.checkbox("Ativo/publicado", value=bool(f.get("ativo")), key=f"file_active_{f['id']}")
                    nova_ordem = col_b.number_input("Ordem", value=int(f.get("ordem") or 0), step=1, key=f"file_order_{f['id']}")
                    if st.button("Salvar ajustes", key=f"file_update_{f['id']}"):
                        update_tournament_file(f["id"], {"ativo": ativo, "ordem": int(nova_ordem)})
                        md_box("ok", "Arquivo atualizado.")
                        st.rerun()
                    if st.button("Apagar arquivo", key=f"file_delete_{f['id']}"):
                        delete_tournament_file(f["id"])
                        md_box("ok", "Arquivo apagado.")
                        st.rerun()

    with aba_programacao:
        st.markdown("#### Importar programação por planilha")
        st.caption("Envie CSV ou XLSX com colunas como: data, hora, quadra, categoria, fase, jogador1, jogador2, status, resultado.")
        modelo = pd.DataFrame([
            {"data": "21/06/2026", "hora": "16:00", "quadra": "1", "categoria": "3ª Classe", "fase": "Oitavas", "jogador1": "João", "jogador2": "Pedro", "status": "agendado", "resultado": ""},
            {"data": "21/06/2026", "hora": "17:30", "quadra": "2", "categoria": "4ª Classe", "fase": "Oitavas", "jogador1": "Carlos", "jogador2": "Lucas", "status": "agendado", "resultado": ""},
        ])
        csv_modelo = modelo.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar modelo CSV", data=csv_modelo, file_name="modelo_programacao_torneio.csv", mime="text/csv", use_container_width=True)
        categoria_padrao_import = st.selectbox(
            "Categoria padrão para linhas sem categoria",
            ["Usar categoria da planilha"] + TOURNAMENT_CATEGORIES + ["Outra / personalizada"],
            key="programacao_categoria_padrao_import",
            help="Se a planilha já tiver a coluna categoria, ela será respeitada. Use isso apenas para completar linhas sem categoria.",
        )
        categoria_padrao_custom = st.text_input(
            "Categoria padrão personalizada",
            key="programacao_categoria_padrao_custom",
        ) if categoria_padrao_import == "Outra / personalizada" else ""
        prog_file = st.file_uploader("Enviar programação CSV/XLSX", type=["csv", "xlsx"], key="programacao_upload")
        substituir = st.checkbox("Apagar jogos/programação já cadastrados deste evento antes de importar", value=False, key="substituir_programacao")
        if prog_file is not None:
            try:
                df_prog = _read_schedule_upload(prog_file)
                st.markdown("Prévia da programação:")
                st.dataframe(df_prog.head(30), use_container_width=True, hide_index=True)
                matches_payload = _parse_schedule_dataframe(df_prog)
                categoria_padrao_final = ""
                if categoria_padrao_import == "Outra / personalizada":
                    categoria_padrao_final = categoria_padrao_custom.strip()
                elif categoria_padrao_import != "Usar categoria da planilha":
                    categoria_padrao_final = categoria_padrao_import
                if categoria_padrao_final:
                    for item in matches_payload:
                        if not item.get("categoria") or str(item.get("categoria")).strip() in {"Sem categoria", "sem categoria"}:
                            item["categoria"] = categoria_padrao_final
                st.caption(f"Jogos válidos detectados: {len(matches_payload)}")
                if st.button("Importar programação para o site", use_container_width=True, key="btn_importar_programacao_planilha"):
                    if not matches_payload:
                        md_box("error", "Nenhum jogo válido encontrado na planilha.")
                    else:
                        if substituir:
                            atuais = fetch_bracket_matches(selected_event_id)
                            delete_bracket_matches([x.get("id") for x in atuais if x.get("id")])
                        insert_bracket_matches(selected_event_id, matches_payload)
                        md_box("ok", f"Programação importada com {len(matches_payload)} jogos.")
                        st.rerun()
            except AppError as exc:
                md_box("error", str(exc))
            except Exception:
                md_box("error", "Não consegui ler essa planilha. Use o modelo CSV baixado acima.")

        st.markdown("---")
        st.markdown("#### Importar por texto rápido")
        st.caption("Formato novo: Data | Hora | Quadra | Categoria | Fase | Jogador 1 | Jogador 2. Também aceito o formato antigo com 6 campos.")
        exemplo = "21/06/2026 | 16:00 | 1 | 3ª Classe Masculina | Oitavas | João Silva | Pedro Santos"
        texto_prog = st.text_area("Cole a programação", placeholder=exemplo, key="programacao_texto")
        if st.button("Importar texto da programação", use_container_width=True, key="btn_importar_programacao_texto") and texto_prog.strip():
            matches_payload: list[dict[str, Any]] = []
            for idx, line in enumerate([x.strip() for x in texto_prog.splitlines() if x.strip()]):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 7:
                    raw_data, raw_hora, quadra, categoria_txt, fase, jogador1, jogador2 = parts[:7]
                elif len(parts) >= 6:
                    raw_data, raw_hora, quadra, fase, jogador1, jogador2 = parts[:6]
                    categoria_txt = "Sem categoria"
                else:
                    continue
                dt_iso = None
                try:
                    dt = pd.to_datetime(f"{raw_data} {raw_hora}", dayfirst=True, errors="coerce")
                    if not pd.isna(dt):
                        dt_iso = dt.isoformat()
                except Exception:
                    dt_iso = None
                matches_payload.append({
                    "categoria": categoria_txt or "Sem categoria",
                    "fase": fase,
                    "jogador1": jogador1,
                    "jogador2": jogador2,
                    "data_hora": dt_iso,
                    "quadra": quadra,
                    "status": "agendado",
                    "ordem": idx,
                })
            if matches_payload:
                insert_bracket_matches(selected_event_id, matches_payload)
                md_box("ok", f"{len(matches_payload)} jogos importados.")
                st.rerun()
            else:
                md_box("error", "Nenhuma linha válida encontrada. Use o formato indicado.")

    with aba_manual:
        st.markdown("#### Cadastrar jogo manual")
        col1, col2 = st.columns(2)
        categoria_val = col1.selectbox("Categoria", TOURNAMENT_CATEGORIES + ["Outra / personalizada"], key="single_categoria")
        categoria_custom = col1.text_input("Categoria personalizada", key="single_categoria_custom") if categoria_val == "Outra / personalizada" else ""
        fase_val = col1.text_input("Fase", placeholder="Ex.: Oitavas, Quartas, Semifinal, Final", key="single_fase")
        jogador1_val = col1.text_input("Jogador 1", key="single_jog1")
        jogador2_val = col1.text_input("Jogador 2", key="single_jog2")
        date_val = col2.date_input("Data", value=date.today(), key="single_date")
        time_val = col2.time_input("Hora", datetime.now().time(), key="single_time")
        quadra_val = st.text_input("Quadra", key="single_quadra")
        resultado_val = st.text_input("Resultado / placar", key="single_result")
        status_val = st.selectbox("Status", ["agendado", "concluido", "cancelado", "bye"], key="single_status")
        ordem_val = st.number_input("Ordem", value=0, step=1, key="single_ordem")
        if st.button("Cadastrar jogo", use_container_width=True, key="add_single_match"):
            try:
                data_hora_iso: Optional[str] = None
                if date_val and time_val:
                    try:
                        data_hora_iso = datetime.combine(date_val, time_val).isoformat()
                    except Exception:
                        data_hora_iso = None
                categoria_final = categoria_custom.strip() if categoria_val == "Outra / personalizada" else categoria_val
                payload = {
                    "categoria": categoria_final or "Sem categoria",
                    "fase": fase_val or None,
                    "jogador1": jogador1_val or None,
                    "jogador2": jogador2_val or None,
                    "data_hora": data_hora_iso,
                    "quadra": quadra_val or None,
                    "resultado": resultado_val or None,
                    "status": status_val or None,
                    "ordem": int(ordem_val),
                }
                insert_bracket_matches(selected_event_id, [payload])
                md_box("ok", "Jogo cadastrado.")
                st.rerun()
            except AppError as exc:
                md_box("error", str(exc))

    with aba_resultados:
        st.markdown("#### Editar resultados em tempo real")
        st.caption("Use esta área durante o torneio para colocar o placar e marcar o jogo como concluído. A área pública atualiza após salvar.")
        matches_live = fetch_bracket_matches(selected_event_id)
        if not matches_live:
            st.info("Nenhum jogo cadastrado para este evento.")
        else:
            df_live = _ensure_match_columns(pd.DataFrame(matches_live))
            categoria_filtro_live = st.selectbox(
                "Filtrar por categoria",
                _category_options_from_event(matches_live, fetch_tournament_files(selected_event_id, tipo=None, include_inactive=True)),
                key="live_result_category_filter",
            )
            df_live = pd.DataFrame(_filter_rows_by_category(df_live.to_dict("records"), categoria_filtro_live))
            if df_live.empty:
                st.info("Nenhum jogo encontrado para essa categoria.")
            else:
                df_live = _ensure_match_columns(df_live)
                df_live["_dt"] = pd.to_datetime(df_live["data_hora"], errors="coerce")
                df_live["_date_label"] = df_live["_dt"].dt.strftime("%d/%m/%Y")
                df_live["_date_label"] = df_live["_date_label"].fillna("Sem data definida")
                datas_live = ["Todas as datas"] + df_live["_date_label"].drop_duplicates().tolist()
                data_filtro_live = st.selectbox("Filtrar por data", datas_live, key="live_result_date_filter")
                if data_filtro_live != "Todas as datas":
                    df_live = df_live[df_live["_date_label"] == data_filtro_live]
                if df_live.empty:
                    st.info("Nenhum jogo encontrado nessa data.")
                else:
                    options_live = {
                        f"{row.get('_date_label') or ''} • {row.get('categoria') or ''} • {row.get('fase') or ''} • {row.get('jogador1') or 'A definir'} x {row.get('jogador2') or 'A definir'}": row.to_dict()
                        for _, row in df_live.sort_values(["_dt", "ordem"], na_position="last").iterrows()
                    }
                    selected_live_label = st.selectbox("Selecione o jogo", list(options_live.keys()), key="live_result_match_select")
                    selected_live = options_live[selected_live_label]
                    selected_live_id = selected_live.get("id")
                    st.markdown(
                        f"**{selected_live.get('jogador1') or 'A definir'} x {selected_live.get('jogador2') or 'A definir'}**  \n"
                        f"{selected_live.get('categoria') or ''} • {selected_live.get('fase') or ''} • Quadra {selected_live.get('quadra') or 'A definir'}"
                    )
                    live_status = st.selectbox(
                        "Status",
                        ["agendado", "concluido", "cancelado", "bye"],
                        index=["agendado", "concluido", "cancelado", "bye"].index(str(selected_live.get("status") or "agendado")) if str(selected_live.get("status") or "agendado") in ["agendado", "concluido", "cancelado", "bye"] else 0,
                        key="live_result_status",
                    )
                    live_resultado = st.text_input(
                        "Resultado / placar",
                        value=str(selected_live.get("resultado") or ""),
                        placeholder="Ex.: João venceu 6/3 6/4",
                        key="live_result_score",
                    )
                    if st.button("Salvar resultado agora", use_container_width=True, key="btn_save_live_result"):
                        try:
                            update_bracket_match(str(selected_live_id), {
                                "status": live_status,
                                "resultado": live_resultado.strip() or None,
                            })
                            md_box("ok", "Resultado atualizado. A área pública já buscará o dado salvo.")
                            st.rerun()
                        except AppError as exc:
                            md_box("error", str(exc))

    with aba_lista:
        st.markdown("#### Ver / editar / apagar jogos")
        st.caption("Mesmo que você importe uma programação por arquivo, aqui você consegue corrigir horário, quadra, fase, jogadores, status e resultado jogo por jogo, igual em um gerenciador de chaves.")
        matches = fetch_bracket_matches(selected_event_id)
        if not matches:
            st.info("Nenhum jogo cadastrado para este evento.")
        else:
            df = _ensure_match_columns(pd.DataFrame(matches))
            st.dataframe(clean_admin_dataframe(df), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### Editar resultado ou dados de um jogo")
            options_edit = {
                f"{row.get('categoria') or ''} • {row.get('fase') or ''} • {row.get('jogador1') or 'A definir'} x {row.get('jogador2') or 'A definir'} • {row.get('data_hora') or ''}": row.to_dict()
                for _, row in df.iterrows()
            }
            selected_edit_label = st.selectbox("Selecione o jogo para editar", list(options_edit.keys()), key="edit_match_select_v10")
            selected_match = options_edit[selected_edit_label]
            selected_match_id = selected_match.get("id")

            c1, c2 = st.columns(2)
            categorias_existentes = _category_options_from_event(matches, fetch_tournament_files(selected_event_id, tipo=None, include_inactive=True))
            categorias_opcoes = [c for c in categorias_existentes if c != "Todas as categorias"]
            for cat in TOURNAMENT_CATEGORIES:
                if cat not in categorias_opcoes:
                    categorias_opcoes.append(cat)
            if "Outra / personalizada" not in categorias_opcoes:
                categorias_opcoes.append("Outra / personalizada")
            current_cat = selected_match.get("categoria") or "Sem categoria"
            cat_index = categorias_opcoes.index(current_cat) if current_cat in categorias_opcoes else (len(categorias_opcoes)-1)
            edit_cat_select = c1.selectbox("Categoria", categorias_opcoes, index=cat_index, key="edit_match_categoria_select")
            edit_cat_custom = c1.text_input("Categoria personalizada", value=current_cat if edit_cat_select == "Outra / personalizada" else "", key="edit_match_categoria_custom") if edit_cat_select == "Outra / personalizada" else ""
            edit_fase = c2.text_input("Fase", value=str(selected_match.get("fase") or ""), key="edit_match_fase")

            c3, c4 = st.columns(2)
            edit_j1 = c3.text_input("Jogador 1", value=str(selected_match.get("jogador1") or ""), key="edit_match_jogador1")
            edit_j2 = c4.text_input("Jogador 2", value=str(selected_match.get("jogador2") or ""), key="edit_match_jogador2")

            parsed_dt = pd.to_datetime(selected_match.get("data_hora"), errors="coerce")
            default_date = parsed_dt.date() if not pd.isna(parsed_dt) else date.today()
            default_time = parsed_dt.time() if not pd.isna(parsed_dt) else datetime.now().time()
            c5, c6, c7 = st.columns(3)
            edit_date = c5.date_input("Data", value=default_date, key="edit_match_date")
            edit_time = c6.time_input("Hora", value=default_time, key="edit_match_time")
            edit_quadra = c7.text_input("Quadra", value=str(selected_match.get("quadra") or ""), key="edit_match_quadra")

            c8, c9, c10 = st.columns([1, 2, 1])
            status_options = ["agendado", "concluido", "cancelado", "bye"]
            current_status = str(selected_match.get("status") or "agendado")
            if current_status not in status_options:
                status_options.insert(0, current_status)
            edit_status = c8.selectbox("Status", status_options, index=status_options.index(current_status), key="edit_match_status")
            edit_resultado = c9.text_input("Resultado / placar", value=str(selected_match.get("resultado") or ""), key="edit_match_resultado")
            edit_ordem = c10.number_input("Ordem", value=int(selected_match.get("ordem") or 0), step=1, key="edit_match_ordem")

            col_save, col_delete = st.columns(2)
            if col_save.button("Salvar alterações do jogo", use_container_width=True, key="btn_save_match_edit_v10"):
                categoria_final = edit_cat_custom.strip() if edit_cat_select == "Outra / personalizada" else edit_cat_select
                try:
                    data_hora_iso = datetime.combine(edit_date, edit_time).isoformat()
                except Exception:
                    data_hora_iso = None
                try:
                    update_bracket_match(str(selected_match_id), {
                        "categoria": categoria_final or "Sem categoria",
                        "fase": edit_fase or None,
                        "jogador1": edit_j1 or None,
                        "jogador2": edit_j2 or None,
                        "data_hora": data_hora_iso,
                        "quadra": edit_quadra or None,
                        "resultado": edit_resultado or None,
                        "status": edit_status or None,
                        "ordem": int(edit_ordem),
                    })
                    md_box("ok", "Jogo atualizado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

            confirm_delete_single = col_delete.checkbox("Confirmo apagar este jogo", key="confirm_delete_single_match_v10")
            if col_delete.button("Apagar este jogo", use_container_width=True, disabled=not confirm_delete_single, key="btn_delete_single_match_v10"):
                try:
                    delete_bracket_matches([str(selected_match_id)])
                    md_box("ok", "Jogo apagado com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

            st.markdown("---")
            st.markdown("#### Apagar vários jogos")
            options_delete = {
                f"{row.get('categoria') or ''} • {row.get('fase') or ''} • {row.get('jogador1') or 'TBD'} x {row.get('jogador2') or 'TBD'} • {row.get('data_hora') or ''}": row.get("id")
                for _, row in df.iterrows()
            }
            selected_to_delete = st.multiselect("Selecionar jogos para apagar", list(options_delete.keys()), key="delete_matches_select")
            if st.button("Apagar jogos selecionados", use_container_width=True, key="btn_delete_matches"):
                ids = [options_delete[x] for x in selected_to_delete if options_delete.get(x)]
                if ids:
                    delete_bracket_matches(ids)
                    md_box("ok", "Jogos apagados.")
                    st.rerun()
                else:
                    md_box("warn", "Selecione pelo menos um jogo.")

# PUBLIC: mostra chaves enviadas, programação e resultados dentro da página do evento
def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _category_sort_key(cat: str) -> tuple[int, str]:
    clean = _clean_text(cat)
    return (CATEGORY_ORDER.get(clean, 999), clean.lower())


def _category_options_from_event(matches: list[dict[str, Any]], files: list[dict[str, Any]]) -> list[str]:
    found: set[str] = set()
    for f in files or []:
        cat = _clean_text(f.get("categoria"))
        if cat:
            found.add(cat)
    for m in matches or []:
        cat = _clean_text(m.get("categoria"))
        if cat:
            found.add(cat)
    # Mostra sempre as categorias oficiais iguais às da inscrição, mesmo que
    # ainda não exista chave/programação publicada para alguma delas.
    ordered = list(TOURNAMENT_CATEGORIES)
    extras = sorted([c for c in found if c not in ordered], key=lambda x: x.lower())
    return ["Todas as categorias"] + ordered + extras


def _row_matches_category(row: dict[str, Any], selected_category: str) -> bool:
    if selected_category == "Todas as categorias":
        return True
    cat = _clean_text(row.get("categoria"))
    if cat and cat == selected_category:
        return True
    # Compatibilidade com registros antigos, quando categoria estava misturada no campo fase.
    fase = _clean_text(row.get("fase")).lower()
    return bool(fase and selected_category.lower() in fase)


def _filter_rows_by_category(rows: list[dict[str, Any]], selected_category: str) -> list[dict[str, Any]]:
    return [r for r in rows or [] if _row_matches_category(r, selected_category)]


def _public_date_label(dt_value: Any) -> str:
    try:
        dt = pd.to_datetime(dt_value, errors="coerce")
        if pd.isna(dt):
            return "Sem data definida"
        weekday = WEEKDAY_LABELS[int(dt.weekday())] if 0 <= int(dt.weekday()) < len(WEEKDAY_LABELS) else ""
        return f"{weekday}, {dt.strftime('%d/%m/%Y')}" if weekday else dt.strftime("%d/%m/%Y")
    except Exception:
        return "Sem data definida"


def _date_options_from_matches(matches: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for m in matches or []:
        label = _public_date_label(m.get("data_hora"))
        if label not in labels:
            labels.append(label)
    # Ordena datas válidas e deixa "Sem data definida" por último
    def sort_key(label: str) -> tuple[int, str]:
        if label == "Sem data definida":
            return (1, label)
        return (0, label)
    labels = sorted(labels, key=sort_key)
    return ["Todas as datas"] + labels


def _filter_rows_by_public_date(rows: list[dict[str, Any]], selected_date_label: str) -> list[dict[str, Any]]:
    if selected_date_label == "Todas as datas":
        return rows or []
    return [r for r in rows or [] if _public_date_label(r.get("data_hora")) == selected_date_label]


def _ensure_match_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que a tabela de jogos tenha todas as colunas esperadas.

    Em alguns bancos já existentes, ou em importações antigas, certas colunas
    podem vir ausentes ou nulas. Se tentarmos ordenar/formatar por uma coluna
    que não existe, o Streamlit quebra a página pública inteira. Esta função
    padroniza os dados antes de montar Chaves, Programação e Resultados.
    """
    expected_defaults = {
        "fase": "A definir",
        "categoria": "Sem categoria",
        "jogador1": "A definir",
        "jogador2": "A definir",
        "data_hora": None,
        "quadra": "",
        "resultado": "",
        "status": "",
        "ordem": 0,
    }
    for column, default in expected_defaults.items():
        if column not in df.columns:
            df[column] = default
    return df


def _is_result_row(row: dict[str, Any]) -> bool:
    status = _clean_text(row.get("status")).lower()
    result = _clean_text(row.get("resultado"))
    finished_statuses = {"concluido", "concluído", "finalizado", "finalizada", "bye", "wo", "w.o", "w.o."}
    return bool(result) or status in finished_statuses


def _render_tournament_files(files: list[dict[str, Any]], empty_message: str) -> None:
    if not files:
        st.info(empty_message)
        return
    for f in files:
        titulo = escape(f.get("titulo") or "Arquivo")
        categoria = escape(f.get("categoria") or "")
        texto = escape(f.get("texto") or "")
        mime = f.get("mime_type") or ""
        b64 = f.get("arquivo_base64") or ""
        nome = f.get("arquivo_nome") or "arquivo"
        tipo_label = "Programação" if (f.get("tipo") == "programacao_arquivo") else "Chave"
        st.markdown("<div class='tl-upload-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='tl-upload-title'>{titulo}</div>", unsafe_allow_html=True)
        meta = " • ".join([x for x in [tipo_label, categoria or "", nome] if x])
        st.markdown(f"<div class='tl-upload-meta'>{meta}</div>", unsafe_allow_html=True)
        if texto:
            st.caption(texto)
        if b64 and mime.startswith("image/"):
            try:
                st.image(base64.b64decode(b64), use_container_width=True)
            except Exception:
                st.warning("Não foi possível mostrar esta imagem.")
        elif b64:
            try:
                data = base64.b64decode(b64)
                st.download_button(
                    "Baixar / abrir arquivo",
                    data=data,
                    file_name=nome,
                    mime=mime or "application/octet-stream",
                    use_container_width=True,
                    key=f"download_public_file_{f.get('id')}",
                )
            except Exception:
                st.warning("Não foi possível carregar este arquivo.")
        st.markdown("</div>", unsafe_allow_html=True)


def _render_bracket_blocks(matches: list[dict[str, Any]]) -> None:
    if not matches:
        return
    df = _ensure_match_columns(pd.DataFrame(matches))
    if "fase" not in df.columns:
        return
    df["_fase_ordem"] = df["fase"].fillna("A definir")
    df["_dt"] = pd.to_datetime(df["data_hora"], errors="coerce")
    fases = [x for x in df["_fase_ordem"].drop_duplicates().tolist() if str(x).strip()]
    if not fases:
        fases = ["Jogos"]
    cols = st.columns(min(len(fases), 4))
    for idx, fase in enumerate(fases):
        col = cols[idx % len(cols)]
        with col:
            st.markdown(f"<div class='tl-public-tabs-label'>{escape(str(fase))}</div>", unsafe_allow_html=True)
            phase_df = df[df["_fase_ordem"] == fase].sort_values(["_dt", "ordem"], na_position="last")
            for _, row in phase_df.iterrows():
                jogador1 = escape(row.get("jogador1") or "A definir")
                jogador2 = escape(row.get("jogador2") or "A definir")
                resultado = escape(row.get("resultado") or "")
                status = escape(row.get("status") or "")
                extra = resultado or status
                extra_html = f"<div class='tl-schedule-meta'>{extra}</div>" if extra else ""
                st.markdown(
                    f"<div class='tl-upload-card' style='padding:10px 12px;margin:8px 0;'>"
                    f"<div class='tl-schedule-main'>{jogador1}</div>"
                    f"<div class='tl-schedule-main' style='border-top:1px solid rgba(0,0,0,.08);padding-top:6px;margin-top:6px;'>{jogador2}</div>"
                    f"{extra_html}</div>",
                    unsafe_allow_html=True,
                )


def _render_schedule_rows(matches: list[dict[str, Any]], empty_message: str, show_results: bool = False) -> None:
    if not matches:
        st.info(empty_message)
        return
    df = _ensure_match_columns(pd.DataFrame(matches))
    df["_dt"] = pd.to_datetime(df["data_hora"], errors="coerce")
    df["_date_label"] = df["data_hora"].map(_public_date_label)
    df = df.sort_values(["_dt", "quadra", "ordem"], na_position="last")
    for date_label in df["_date_label"].drop_duplicates().tolist():
        st.markdown(f"<div class='tl-public-tabs-label'>{escape(str(date_label))}</div>", unsafe_allow_html=True)
        day_df = df[df["_date_label"] == date_label]
        for _, row in day_df.iterrows():
            horario = "A definir"
            if not pd.isna(row.get("_dt")):
                try:
                    horario = row.get("_dt").strftime("%H:%M")
                except Exception:
                    horario = "A definir"
            jogadores = f"{escape(row.get('jogador1') or 'A definir')} x {escape(row.get('jogador2') or 'A definir')}"
            categoria = escape(row.get("categoria") or "")
            fase = escape(row.get("fase") or "")
            quadra = escape(str(row.get("quadra") or ""))
            status = escape(row.get("status") or "")
            resultado = escape(row.get("resultado") or "")
            meta_parts = [x for x in [categoria, fase, f"Quadra {quadra}" if quadra else "", status] if x]
            meta = " • ".join(meta_parts)
            if show_results and resultado:
                meta += f" • Resultado: {resultado}"
            elif resultado:
                meta += f" • {resultado}"
            st.markdown(
                f"<div class='tl-schedule-row'><div class='tl-schedule-time'>{horario}</div>"
                f"<div><div class='tl-schedule-main'>{jogadores}</div>"
                f"<div class='tl-schedule-meta'>{meta}</div></div></div>",
                unsafe_allow_html=True,
            )


def render_event_public_tabs(
    event: dict[str, Any],
    pricing_options: list[dict[str, Any]],
    pix_name: str,
    pix_email: str,
    pix_phone: str,
    secretaria_nome: str,
    secretaria_whatsapp: str,
) -> None:
    event_id = str(event.get("id"))
    files = fetch_tournament_files(event_id, tipo=None, include_inactive=False)
    matches = fetch_bracket_matches(event_id)
    category_options = _category_options_from_event(matches, files)

    tab_insc, tab_chaves, tab_prog, tab_result = st.tabs(["Inscrição", "Chaves", "Programação", "Resultados"])

    with tab_insc:
        valor_padrao = float(event.get("valor_inscricao") or 0)
        if event.get("inscricoes_abertas", True):
            with st.form(f"form_evento_{event_id}", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome completo", key=f"ev_nome_{event_id}")
                whatsapp = c2.text_input("WhatsApp", key=f"ev_zap_{event_id}")
                categoria = st.selectbox("Categoria", TOURNAMENT_CATEGORIES, key=f"ev_cat_{event_id}")

                labels = [item["label"] for item in pricing_options]
                default_index = 0
                if valor_padrao:
                    default_index = min(
                        range(len(pricing_options)),
                        key=lambda idx: abs(valor_padrao - pricing_options[idx]["amount"]),
                    )
                selected_label = st.radio(
                    "Escolha sua condição para o torneio",
                    labels,
                    index=default_index,
                    key=f"ev_price_{event_id}",
                )
                selected_plan = next(item for item in pricing_options if item["label"] == selected_label)
                st.markdown(
                    f'<div class="tl-plan-inline">Valor selecionado: <strong>{money_br(selected_plan["amount"])}</strong></div>',
                    unsafe_allow_html=True,
                )
                submit = st.form_submit_button("Confirmar inscrição", use_container_width=True)

            if submit:
                if not nome.strip() or not whatsapp.strip():
                    md_box("error", "Preencha nome completo e WhatsApp.")
                else:
                    try:
                        if registration_exists(event_id, whatsapp, categoria):
                            md_box("warn", "Esse WhatsApp já está inscrito nesta categoria.")
                        elif tournament_category_count(event_id, categoria) >= TOURNAMENT_CATEGORY_LIMIT:
                            md_box("warn", f"Essa categoria já atingiu o limite de {TOURNAMENT_CATEGORY_LIMIT} inscritos.")
                        else:
                            payload = {
                                "evento_id": event.get("id"),
                                "evento_titulo": event.get("titulo") or "Evento",
                                "nome": nome.strip(),
                                "whatsapp": normalize_phone(whatsapp),
                                "categoria": categoria,
                                "tipo_inscricao": selected_plan["label"],
                                "valor": selected_plan["amount"],
                                "status_inscricao": "aguardando_pagamento",
                            }
                            insert_registration(payload)
                            st.session_state["tl_last_registration"] = {
                                "evento_titulo": payload["evento_titulo"],
                                "nome": payload["nome"],
                                "categoria": payload["categoria"],
                                "tipo_inscricao": payload["tipo_inscricao"],
                                "valor": payload["valor"],
                            }
                            flash_message("ok", f"Inscrição registrada com sucesso em {event.get('titulo')}.")
                            st.rerun()
                    except AppError as exc:
                        md_box("error", f"Não foi possível registrar a inscrição. {str(exc)}")
                    except Exception:
                        md_box("error", "Não foi possível registrar a inscrição agora.")
        else:
            md_box("warn", "Inscrições encerradas para este evento.")

    with tab_chaves:
        try:
            selected_category = st.selectbox("Escolha a categoria para ver a chave", category_options, key=f"public_chaves_cat_{event_id}")
            filtered_files = [f for f in files if f.get("tipo") == "chave" and _row_matches_category(f, selected_category)]
            filtered_matches = _filter_rows_by_category(matches, selected_category)
            _render_tournament_files(filtered_files, "Nenhuma chave em imagem/PDF publicada para esta categoria.")
            if filtered_matches:
                _render_bracket_blocks(filtered_matches)
            elif not filtered_files:
                st.info("A chave desta categoria ainda não foi publicada.")
        except Exception:
            st.info("Não foi possível carregar as chaves desta categoria agora. Confira se o schema complementar foi rodado.")

    with tab_prog:
        try:
            selected_category = st.selectbox("Escolha a categoria para ver a programação", category_options, key=f"public_programacao_cat_{event_id}")
            filtered_files = [f for f in files if f.get("tipo") == "programacao_arquivo" and _row_matches_category(f, selected_category)]
            filtered_matches = [m for m in _filter_rows_by_category(matches, selected_category) if not _is_result_row(m)]
            selected_date = st.selectbox("Escolha o dia/data", _date_options_from_matches(filtered_matches), key=f"public_programacao_data_{event_id}")
            filtered_matches = _filter_rows_by_public_date(filtered_matches, selected_date)
            _render_tournament_files(filtered_files, "Nenhum arquivo de programação publicado para esta categoria.")
            _render_schedule_rows(filtered_matches, "A programação desta categoria ainda não foi publicada.", show_results=False)
        except Exception:
            st.info("Não foi possível carregar a programação desta categoria agora. Confira se o schema complementar foi rodado.")

    with tab_result:
        try:
            selected_category = st.selectbox("Escolha a categoria para ver os resultados", category_options, key=f"public_resultados_cat_{event_id}")
            filtered_results = [m for m in _filter_rows_by_category(matches, selected_category) if _is_result_row(m)]
            selected_date = st.selectbox("Escolha o dia/data", _date_options_from_matches(filtered_results), key=f"public_resultados_data_{event_id}")
            filtered_results = _filter_rows_by_public_date(filtered_results, selected_date)
            _render_schedule_rows(filtered_results, "Nenhum resultado publicado para esta categoria ainda.", show_results=True)
        except Exception:
            st.info("Não foi possível carregar os resultados desta categoria agora. Confira se o schema complementar foi rodado.")


# Compatibilidade: esta função antiga agora chama a visualização por abas quando necessário.
def render_bracket_public(event_id: str) -> None:
    files = fetch_tournament_files(event_id, tipo=None, include_inactive=False)
    matches = fetch_bracket_matches(event_id)
    if not files and not matches:
        return
    category_options = _category_options_from_event(matches, files)
    selected_category = st.selectbox("Escolha a categoria", category_options, key=f"legacy_public_cat_{event_id}")
    _render_tournament_files([f for f in files if _row_matches_category(f, selected_category)], "Nenhum arquivo publicado para esta categoria.")
    _render_schedule_rows(_filter_rows_by_category(matches, selected_category), "Nenhum jogo publicado para esta categoria.")

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
        st.dataframe(clean_admin_dataframe(display_df), use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("error", str(exc))

def render_trial_requests_admin() -> None:
    st.markdown("### Aulas experimentais")
    try:
        rows = fetch_trial_requests()
        if not rows:
            st.info("Nenhuma solicitação de aula experimental registrada ainda.")
            return

        df = pd.DataFrame(rows)
        status_options = ["Todos"] + sorted([x for x in df["status"].dropna().unique().tolist()])
        c1, c2 = st.columns(2)
        status_filtro = c1.selectbox("Filtrar por status", status_options, key="trial_status_filter")
        busca = c2.text_input("Buscar por nome ou WhatsApp", key="trial_search")

        if status_filtro != "Todos":
            df = df[df["status"] == status_filtro]
        if busca.strip():
            termo = busca.strip().lower()
            df = df[
                df["nome"].fillna("").str.lower().str.contains(termo, na=False) |
                df["whatsapp"].fillna("").str.lower().str.contains(termo, na=False)
            ]

        if df.empty:
            st.info("Nenhuma solicitação encontrada com esse filtro.")
            return

        with st.expander("Gerenciar solicitação selecionada", expanded=False):
            options = {
                f"{row.get('nome','Aluno')} • {row.get('whatsapp','')} • {row.get('objetivo','')} • {row.get('status','')}": str(row.get("id"))
                for _, row in df.iterrows()
            }
            selected_label = st.selectbox("Selecionar solicitação", list(options.keys()), key="admin_select_trial")
            selected_id = options[selected_label]
            c3, c4 = st.columns(2)
            new_status = c3.selectbox("Status", ["novo", "contatado", "agendado", "concluido", "cancelado"], key="admin_trial_status")
            if c4.button("Atualizar status", use_container_width=True, key="btn_update_trial_status"):
                try:
                    update_trial_request(selected_id, {"status": new_status})
                    clear_caches()
                    md_box("ok", "Status da aula experimental atualizado.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

            confirm_delete = st.checkbox("Confirmo que desejo apagar esta solicitação", key="confirm_delete_trial")
            if st.button("Apagar solicitação selecionada", use_container_width=True, disabled=not confirm_delete, key="btn_delete_trial"):
                try:
                    delete_records_by_ids("aulas_experimentais", [selected_id])
                    clear_caches()
                    md_box("ok", "Solicitação apagada com sucesso.")
                    st.rerun()
                except AppError as exc:
                    md_box("error", str(exc))

        display_df = df.copy()
        if "created_at" in display_df.columns:
            display_df["created_at"] = display_df["created_at"].map(br_date)
        st.dataframe(clean_admin_dataframe(display_df), use_container_width=True, hide_index=True)
    except AppError as exc:
        md_box("error", str(exc))

def render_setup_message() -> None:
    md_box("warn", "Aplicativo em configuração. Verifique Secrets do Streamlit e rode o schema.sql mais novo no Supabase.")

def main() -> None:
    # Inject the base stylesheet first
    inject_css()
    # Override some styles with a lighter palette and extra classes
    inject_fresh_css()
    # Admin discreto pela sidebar, igual ao site oficial
    inject_official_admin_css()
    inject_admin_sidebar_fallback()
    render_header()
    render_navigation_router()
    admin_ok = render_admin_access()
    # Só mostra login na página se o botão nativo realmente não abrir a sidebar
    # e o fallback JS colocar admin_panel=1 na URL. No fluxo normal, o login
    # permanece discreto pela setinha/sidebar, igual ao site oficial.
    if admin_panel_query_requested():
        admin_ok = render_admin_login_public(admin_ok)

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
        tab_trial, tab_checkin, tab_makeup, tab_events, tab_finance = st.tabs(["Aula experimental", "Check-in das aulas", "Reposição de aula", "Eventos", "Financeiro"])
        with tab_trial:
            try:
                render_trial_request()
            except Exception:
                md_box("error", "Não foi possível carregar o agendamento agora.")
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

        # Login administrativo discreto igual ao site oficial:
        # somente pela seta/sidebar nativa do Streamlit.

        if admin_ok:
            render_admin_panel()
    except Exception:
        md_box("error", "Ocorreu um erro inesperado. Atualize a página e tente novamente.")

if __name__ == "__main__":
    main()
