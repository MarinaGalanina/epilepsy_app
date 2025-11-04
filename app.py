import json
import numpy as np
import streamlit as st
import os
import sqlite3, uuid, time, json as _json
from typing import Dict, Any, List
from datetime import datetime
import requests

# ---------------------- ⚙️ HELPERS ----------------------

def read_secret(key: str, default=None):
    """Read secret from ENV, then st.secrets, else default."""
    if key in os.environ:
        return os.environ.get(key)
    try:
        return st.secrets[key]
    except Exception:
        return default

DB_PATH = os.environ.get("DB_PATH", "data.db")

def _now_iso():
    return datetime.utcnow().isoformat()

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())  # anonymous UID

# ---------------------- 💾 LOCAL DB ----------------------

@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        user_id TEXT NOT NULL,
        survey_version TEXT,
        path_id TEXT,
        q_idx INTEGER,
        answers_json TEXT,
        finished INTEGER,
        result_json TEXT
    )
    """)
    return conn

def save_locally(*, user_id, survey_version, path_id, q_idx, answers_dict, finished, result_dict=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO progress (created_at, user_id, survey_version, path_id, q_idx, answers_json, finished, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _now_iso(),
            user_id,
            survey_version,
            path_id,
            int(q_idx) if q_idx is not None else None,
            _json.dumps(answers_dict, ensure_ascii=False),
            1 if finished else 0,
            _json.dumps(result_dict, ensure_ascii=False) if result_dict is not None else None
        )
    )
    conn.commit()

# ---------------------- ☁️ REMOTE SAVE ----------------------

def save_remote(payload: dict):
    WEBHOOK_URL = read_secret("WEBHOOK_URL")
    if WEBHOOK_URL:
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            if r.status_code >= 300:
                st.warning(f"Webhook error {r.status_code}: {r.text}")
        except Exception as e:
            st.warning(f"Webhook save failed: {e}")

    SUPABASE_URL = read_secret("SUPABASE_URL")
    SUPABASE_KEY = read_secret("SUPABASE_KEY")
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            r = requests.post(
                f"{SUPABASE_URL}/rest/v1/progress",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=payload,
                timeout=8
            )
            if r.status_code not in (200, 201):
                st.warning(f"Supabase error {r.status_code}: {r.text}")
        except Exception as e:
            st.warning(f"Supabase save failed: {e}")

def autosave(*, finished=False, result=None):
    survey_version = survey.get("meta", {}).get("version", "unknown")
    path_id = st.session_state.selected_path_id
    q_idx = st.session_state.current_q_idx

    payload = {
        "created_at": _now_iso(),
        "user_id": st.session_state.user_id,
        "survey_version": survey_version,
        "path_id": path_id,
        "q_idx": q_idx,
        "finished": finished,
        "answers_json": st.session_state.answers,
        "result_json": result
    }

    save_locally(
        user_id=st.session_state.user_id,
        survey_version=survey_version,
        path_id=path_id,
        q_idx=q_idx,
        answers_dict=st.session_state.answers,
        finished=finished,
        result_dict=result
    )
    save_remote(payload)

# ---------------------- 🌐 PAGE CONFIG ----------------------

st.set_page_config(
    page_title="Ryzyko cech napadu (DEMO)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------- 💄 GLOBAL CSS ----------------------
st.markdown("""
<style>
/* schowaj chrome Streamlita, ale nie zmieniaj wysokości głównych kontenerów */
div[data-testid="stDecoration"],
header, div[data-testid="stHeader"], div[data-testid="stToolbar"],
footer, div[data-testid="stStatusWidget"] {
  display: none !important;
  visibility: hidden !important;
}

/* zostaw przełącznik sidebara i normalny flow */
div[data-testid="collapsedControl"] { display: flex !important; }

/* szerokość i pady treści */
div[data-testid="stAppViewContainer"] .block-container {
  max-width: 980px; padding-top: 12px; padding-bottom: 28px;
}

/* prosta karta logowania */
.login-card {
  border: 1px solid rgba(0,0,0,.08);
  border-radius: 14px;
  padding: 22px 22px 18px 22px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.06);
  background: var(--background-color);
}
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 AUTH ----------------------

def check_access() -> bool:
    # Bypass tylko jeśli DISABLE_AUTH ustawione
    if os.environ.get("DISABLE_AUTH", "").lower() in {"1", "true", "yes"}:
        return True

    if st.session_state.get("auth_ok", False):
        return True

    ACCESS_CODE = read_secret("ACCESS_CODE", None) or "demo"

    # odstęp od góry
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)

    # centrum strony: 3 kolumny, środkowa z kartą logowania
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container(border=False):
            st.markdown("<div class='login-card'>", unsafe_allow_html=True)
            st.markdown("### Szacowanie ryzyka cech napadów")
            st.caption("Wpisz kod dostępu, aby kontynuować:")

            with st.form("login_form", clear_on_submit=False):
                code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed", key="login_code")
                submitted = st.form_submit_button("Zaloguj", use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if code == ACCESS_CODE:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.warning("Niepoprawny kod. Spróbuj ponownie.")

    st.stop()

if not check_access():
    st.stop()

# ---------------------- 🔁 GÓRNY PRZYCISK (po prawej) ----------------------
st.sidebar.success("Zalogowano")

# jeden wiersz z dwoma małymi kolumnami po prawej
_spacer, col_reset, col_logout = st.columns([8, 1, 1])

with col_reset:
    if st.button("Zacznij od nowa", key="reset_btn_top", use_container_width=True):
        autosave(finished=False, result={"event": "reset"})
        st.session_state.current_q_idx = 0
        st.session_state.answers = {}
        st.session_state.finished = False
        st.session_state.result = None
        st.rerun()

with col_logout:
    if st.button("Wyloguj", key="logout_btn_top", use_container_width=True):
        st.session_state.auth_ok = False
        st.rerun()

# ---------------------- 📄 LOAD SURVEY ----------------------

@st.cache_data
def load_survey(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

try:
    survey = load_survey("survey.json")
except FileNotFoundError:
    st.warning("Nie znaleziono pliku survey.json.")
    st.stop()

if not survey.get("paths"):
    st.warning("Brak zdefiniowanych ścieżek w survey.json.")
    st.stop()

paths: Dict[str, Dict[str, Any]] = {p["id"]: p for p in survey["paths"]}
path_labels: Dict[str, str] = {p["label"]: p["id"] for p in survey["paths"]}
labels_list: List[str] = list(path_labels.keys())

# ---------------------- 🧭 STATE ----------------------
def _init_state():
    if "selected_path_id" not in st.session_state:
        st.session_state.selected_path_id = list(path_labels.values())[0]
    if "current_q_idx" not in st.session_state:
        st.session_state.current_q_idx = 0
    if "answers" not in st.session_state:
        st.session_state.answers: Dict[str, Any] = {}
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "result" not in st.session_state:
        st.session_state.result = None
_init_state()

def _current_label() -> str:
    return [k for k, v in path_labels.items() if v == st.session_state.selected_path_id][0]

# ---------------------- 🧩 PATH PICKER ----------------------
cur_label = _current_label()
if st.session_state.current_q_idx == 0 and not st.session_state.finished:
    top_choice = st.selectbox(
        "Typ incydentu",
        labels_list,
        index=labels_list.index(cur_label),
        key="top_select"
    )
else:
    # tylko wyświetl nazwę bez możliwości zmiany
    st.markdown(f"**Typ incydentu:** {cur_label}")
    top_choice = cur_label

st.sidebar.header("Wybór ścieżki")
if st.session_state.finished:
    st.sidebar.info("Wynik obliczony. Aby zacząć od nowa, kliknij „Zacznij od nowa” na dole ekranu wyników.")
    sidebar_choice = cur_label
else:
    sidebar_choice = st.sidebar.radio(
        "Typ incydentu:",
        labels_list,
        index=labels_list.index(cur_label),
        key="sidebar_radio"
    )

new_label = top_choice if top_choice != cur_label else sidebar_choice
if new_label != cur_label:
    st.session_state.selected_path_id = path_labels[new_label]
    st.session_state.current_q_idx = 0
    st.session_state.answers = {}
    st.session_state.finished = False
    st.session_state.result = None

# Refresh path data
path = paths[st.session_state.selected_path_id]
questions: List[Dict[str, Any]] = path.get("questions", [])
nq = len(questions)
label_text = _current_label()

# ---------------------- 🔢 SCORING ----------------------
def _tri_weights(q: Dict[str, Any]):
    """Return (yes, maybe, no) weights; missing = 0.
       Questions without weights don't affect score."""
    return (
        float(q.get("weight_yes", 0) or 0),
        float(q.get("weight_maybe", 0) or 0),
        float(q.get("weight_no", 0) or 0),
    )

def compute_scores(answers: Dict[str, Any], path: Dict[str, Any]):
    score = 0.0
    max_score = 0.0

    for q in path.get("questions", []):
        if q.get("noscore", False):
            continue

        qtype = q.get("type")
        qid = q.get("id")

        if qtype == "tri":
            w_yes, w_maybe, w_no = _tri_weights(q)
            per_q_max = max(w_yes, w_maybe, w_no)
            max_score += per_q_max
            a = answers.get(qid)
            if a == "tak":
                score += w_yes
            elif a == "nie wiem":
                score += w_maybe
            elif a == "nie":
                score += w_no

        elif qtype == "select":
            opts = q.get("options", [])
            opt_weights = [float(o.get("weight", 0) or 0) for o in opts]
            per_q_max = max(opt_weights) if opt_weights else 0.0
            max_score += per_q_max
            chosen = answers.get(qid)
            if chosen is not None:
                for o in opts:
                    if o.get("label") == chosen:
                        score += float(o.get("weight", 0) or 0)
                        break

    if max_score <= 0:
        prob = 0.0
    else:
        ratio = score / max_score
        logit = (ratio - 0.5) * 6.0
        prob = 1.0 / (1.0 + np.exp(-logit))

    return score, max_score, prob

# ---------------------- 🧱 UI ----------------------
st.header(f"Ścieżka: {label_text}")

if nq == 0:
    st.warning("Brak pytań w tej ścieżce.")
else:
    q_idx = st.session_state.current_q_idx
    st.progress(int((q_idx / max(nq, 1)) * 100))
    st.markdown(f"Pytanie {q_idx + 1} z {nq}")

def tri_buttons(qid: str):
    cols = st.columns(3)
    clicked = None
    with cols[0]:
        if st.button("Nie", key=f"btn_{qid}_nie", use_container_width=True):
            clicked = "nie"
    with cols[1]:
        if st.button("Tak", key=f"btn_{qid}_tak", use_container_width=True):
            clicked = "tak"
    with cols[2]:
        if st.button("Nie wiem", key=f"btn_{qid}_niewiem", use_container_width=True):
            clicked = "nie wiem"
    return clicked

# ---------------------- PYTANIA I ODPOWIEDZI ----------------------
if not st.session_state.finished and nq > 0:
    q_idx = st.session_state.current_q_idx
    q = questions[q_idx]

    q_title = q.get("text", "Pytanie")
    st.markdown(f"### {q_title}")

    answer_clicked = None

    # --- przyciski typu TAK / NIE / NIE WIEM ---
    if q.get("type") == "tri":
        cols = st.columns(3)
        with cols[0]:
            if st.button("Nie", key=f"btn_{q['id']}_nie", use_container_width=True):
                answer_clicked = "nie"
        with cols[1]:
            if st.button("Tak", key=f"btn_{q['id']}_tak", use_container_width=True):
                answer_clicked = "tak"
        with cols[2]:
            if st.button("Nie wiem", key=f"btn_{q['id']}_niewiem", use_container_width=True):
                answer_clicked = "nie wiem"

    # --- pytania z wyborem z listy ---
    elif q.get("type") == "select":
        labels = [opt["label"] for opt in q.get("options", [])]
        val = st.selectbox(
            "",
            ["-- wybierz --"] + labels,
            index=0,
            key=f"sel_{q['id']}"
        )
        if val != "-- wybierz --":
            answer_clicked = val

    # --- zapis i przejście dalej ---
    if answer_clicked is not None:
        st.session_state.answers[q["id"]] = answer_clicked
        autosave(finished=False, result=None)

        if st.session_state.current_q_idx + 1 >= nq:
            score, max_score, prob = compute_scores(st.session_state.answers, path)
            st.session_state.result = {
                "score": score,
                "max_score": max_score,
                "prob": prob
            }
            st.session_state.finished = True
            autosave(finished=True, result=st.session_state.result)
            st.rerun()
        else:
            st.session_state.current_q_idx += 1
            st.rerun()

    # --- NAWIGACJA W TYŁ ---
    st.divider()
    if st.button("← Wstecz", key=f"back_{q_idx}", disabled=(q_idx == 0)):
        st.session_state.current_q_idx = max(0, q_idx - 1)
        st.rerun()

st.divider()

# ---------------------- 📊 RESULT ----------------------
if st.session_state.finished and st.session_state.result:
    res = st.session_state.result
    score, max_score, prob = res["score"], res["max_score"], res["prob"]

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Szacowane ryzyko", f"{prob * 100:.0f}%")
    with c2: st.metric("Suma punktów", f"{score:.1f} / {max_score:.1f}")
    with c3:
        level = "niskie" if prob < 0.3 else ("umiarkowane" if prob < 0.6 else "wysokie")
        st.metric("Poziom", level)

    with st.expander("Zobacz szczegóły"):
        pretty = {
            "path_label": label_text,
            "version": survey.get("meta", {}).get("version", "unknown"),
            "responses": st.session_state.answers,
            "score": score, "max_score": max_score, "probability": prob
        }
        st.json(pretty)
        st.download_button(
            "Pobierz wynik (JSON)",
            data=json.dumps(pretty, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="wynik_ankiety.json",
            mime="application/json"
        )

    # przycisk tylko NA DOLE, po PRAWEJ
    right_spacer, right_btn = st.columns([0.8, 0.2])
    with right_btn:
        if st.button("Zacznij od nowa", key="reset_btn_bottom", use_container_width=True):
            autosave(finished=False, result={"event": "reset"})
            st.session_state.current_q_idx = 0
            st.session_state.answers = {}
            st.session_state.finished = False
            st.session_state.result = None
            st.rerun()

# ---------------------- 📝 FOOTER ----------------------
st.caption("Wersja: " + survey.get("meta", {}).get("version", "unknown"))
st.caption(survey.get("meta", {}).get("disclaimer", ""))
