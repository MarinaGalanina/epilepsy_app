import json
import numpy as np
import streamlit as st
import os
from typing import Dict, Any, List
import sqlite3, uuid, time, json as _json
from datetime import datetime
import requests


if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())  # anonimowy UIDs


@st.cache_resource
def get_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        user_id TEXT NOT NULL,
        survey_version TEXT,
        path_id TEXT,
        q_idx INTEGER,
        answers_json TEXT,      -- pełny słownik odpowiedzi (draft)
        finished INTEGER,       -- 0/1
        result_json TEXT        -- wynik końcowy (jeśli finished=1)
    )
    """)
    return conn

def _now_iso():
    return datetime.utcnow().isoformat()

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

# --- [4] OPCJONALNY EXPORT DO CHMURY (Supabase REST lub dowolny webhook) ---
def save_remote(payload: dict):
    WEBHOOK_URL = st.secrets.get("WEBHOOK_URL")
    if WEBHOOK_URL:
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            if r.status_code >= 300:
                st.warning(f"Webhook error {r.status_code}: {r.text}")
        except Exception as e:
            st.warning(f"Webhook save failed: {e}")

    SUPABASE_URL = st.secrets.get("SUPABASE_URL")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            r = requests.post(
                f"{SUPABASE_URL}/rest/v1/progress",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    # poproś o zwrotkę – łatwiej debugować
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
        # 👇 nazwy muszą zgadzać się z kolumnami w tabeli
        "answers_json": st.session_state.answers,
        "result_json": result
    }

    # lokalny zapis — jak było
    save_locally(
        user_id=st.session_state.user_id,
        survey_version=survey_version,
        path_id=path_id,
        q_idx=q_idx,
        answers_dict=st.session_state.answers,
        finished=finished,
        result_dict=result
    )

    # chmura
    save_remote(payload)
# ---------------------- ⚙️ USTAWIENIA STRONY ----------------------
st.set_page_config(
    page_title="Ryzyko cech napadu (DEMO)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------- ✨ GLOBALNY STYL — BEZ CZERWIENI, BEZ BIAŁEJ "PIGUŁY" ----------------------
st.markdown("""
<style>
/* 1) Header/toolbar/status/badges */
div[data-testid="stDecoration"],
header, div[data-testid="stHeader"], div[data-testid="stToolbar"],
div[class*="viewerBadge_"], a[data-testid="viewer-badge"],
div[data-testid="stStatusWidget"], [data-testid="stAppStatusWidget"],
[data-testid="stAppStatusContainer"], header[role="banner"], div[role="banner"] {
  display: none !important; visibility: hidden !important;
}

/* 2) „White egg” (toggle sidebara) */
div[data-testid="collapsedControl"] { display: none !important; }

/* 3) Kontener: pełna szerokość, brak twardego max-width */
div[data-testid="stAppViewContainer"] .block-container {
  padding-top: 12px; padding-bottom: 28px; max-width: 980px;
}

/* 4) Selectbox – pewne targetowanie (różne wersje Streamlit) */
div[role="combobox"] {
  border-radius: 14px !important;
  border: 1px solid rgba(0,0,0,.12) !important;
  background: rgba(0,0,0,.02) !important;
}

/* 5) Przyciski – focus bardziej dostępny */
.stButton>button:focus-visible {
  outline: 3px solid rgba(0,0,0,.35) !important;
  outline-offset: 2px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 LOGOWANIE (Twoje – bez zmian) ----------------------
def check_access() -> bool:
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")
    if not ACCESS_CODE:
        st.warning("Brak ustawionego ACCESS_CODE w Secrets/ENV. Skontaktuj się z administratorem.")
        st.stop()

    if st.session_state.get("auth_ok", False):
        return True

    st.markdown("""
    <style>
    div[data-testid="stAppViewContainer"] > .main {
        height: 100vh; display: flex; align-items: center; justify-content: center;
        padding-top: 0 !important; padding-bottom: 0 !important;
    }
    .auth-card {
        width: min(94vw, 420px); background: var(--background-color);
        border-radius: 18px; padding: 28px 28px 22px 28px;
        box-shadow: 0 12px 30px rgba(0,0,0,0.08); text-align: center;
        animation: fadeIn .25s ease-out;
    }
    .auth-title { margin: 6px 0 2px 0; font-weight: 700; }
    .auth-sub   { opacity: .8; margin-bottom: 14px; }
    @keyframes fadeIn { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.image("https://img.icons8.com/color/96/brain.png", width=76)
    st.markdown('<div class="auth-title"> Szacowanie ryzyka cech napadów</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Wpisz kod dostępu, aby kontynuować</div>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed")
        submitted = st.form_submit_button("Zaloguj", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if code == ACCESS_CODE:
            st.session_state.auth_ok = True
        else:
            st.warning("Niepoprawny kod. Spróbuj ponownie.")

    st.stop()

if not check_access():
    st.stop()

# ---------------------- 🔁 Wylogowanie ----------------------
st.sidebar.success("Zalogowano")
if st.sidebar.button("Wyloguj"):
    st.session_state.auth_ok = False
    st.rerun()

# ---------------------- 🧠 Tytuł i disclaimer ----------------------
st.title("🧠 Szacowanie ryzyka cech napadów – DEMO")
st.caption("Narzędzie edukacyjne. Nie służy do diagnozy. W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112.")

# ---------------------- 📄 WCZYTANIE ANKIETY ----------------------
@st.cache_data
def load_survey(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

try:
    survey = load_survey("survey.json")
except FileNotFoundError:
    st.warning("Nie znaleziono pliku survey.json. Upewnij się, że plik istnieje w katalogu aplikacji.")
    st.stop()

paths: Dict[str, Dict[str, Any]] = {p["id"]: p for p in survey["paths"]}
path_labels: Dict[str, str] = {p["label"]: p["id"] for p in survey["paths"]}

# ---------------------- 🧭 STAN ----------------------
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

# ---------------------- 🧩 WYBÓR ŚCIEŻKI ----------------------
st.sidebar.header("Wybór ścieżki (typ incydentu)")
if st.session_state.finished:
    st.sidebar.info("Wynik obliczony. Aby zacząć od nowa, kliknij „Zacznij od nowa”.")
    st.sidebar.write(f"Wybrana ścieżka: **{[k for k,v in path_labels.items() if v==st.session_state.selected_path_id][0]}**")
else:
    chosen_label = st.sidebar.radio("Typ incydentu:", list(path_labels.keys()))
    selected_path_id = path_labels[chosen_label]
    if selected_path_id != st.session_state.selected_path_id:
        st.session_state.selected_path_id = selected_path_id
        st.session_state.current_q_idx = 0
        st.session_state.answers = {}
        st.session_state.finished = False
        st.session_state.result = None

path = paths[st.session_state.selected_path_id]
questions: List[Dict[str, Any]] = path.get("questions", [])
nq = len(questions)

# ---------------------- 🔢 OCENA ----------------------
def compute_scores(answers: Dict[str, Any], path: Dict[str, Any]):
    score = 0.0
    max_score = 0.0
    for q in path["questions"]:
        qid = q["id"]; qtype = q.get("type")
        if qtype == "tri":
            max_score += float(q.get("weight_yes", 0))
            a = answers.get(qid)
            if a == "tak":
                score += float(q.get("weight_yes", 0))
            elif a == "nie wiem":
                score += float(q.get("weight_maybe", 0))
        elif qtype == "select":
            weights = [float(opt.get("weight", 0)) for opt in q.get("options", [])]
            max_score += max(weights) if weights else 0.0
            chosen = answers.get(qid)
            for opt in q.get("options", []):
                if opt["label"] == chosen:
                    score += float(opt.get("weight", 0))
                    break
    if max_score == 0:
        prob = 0.0
    else:
        ratio = score / max_score
        logit = (ratio - 0.5) * 6.0
        prob = 1.0 / (1.0 + np.exp(-logit))
    return score, max_score, prob

# ---------------------- 🧱 NAGŁÓWEK + PROGRES ----------------------
label_text = [k for k,v in path_labels.items() if v==st.session_state.selected_path_id][0]
st.header(f"Ścieżka: {label_text}")
if nq == 0:
    st.warning("Brak pytań w tej ścieżce.")
else:
    q_idx = st.session_state.current_q_idx
    st.progress(int((q_idx / max(nq,1)) * 100))
    dots = "".join([f'<span class="dot{" on" if i<=q_idx else ""}"></span>' for i in range(nq)])
    st.markdown(f'<div class="progress-dots" aria-label="postęp pytań">{dots}</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="badge">Pytanie {q_idx + 1} z {nq}</span>', unsafe_allow_html=True)

# ---------------------- 🗳️ WYBÓR — AUTO-ADVANCE, NEUTRALNY LOOK ----------------------
def tri_buttons(qid: str):
    st.markdown('<div class="choice-grid">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)
    return clicked

if not st.session_state.finished and nq > 0:
    q = questions[st.session_state.current_q_idx]
    st.markdown('<div class="q-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="q-title">{q["text"]}</div>', unsafe_allow_html=True)

    answer_clicked = None
    if q["type"] == "tri":
        answer_clicked = tri_buttons(q["id"])
    elif q["type"] == "select":
        labels = [opt["label"] for opt in q.get("options", [])]
        val = st.selectbox("", ["-- wybierz --"] + labels, index=0, key=f"sel_{q['id']}")
        if val != "-- wybierz --":
            answer_clicked = val

    st.markdown('</div>', unsafe_allow_html=True)

    if answer_clicked is not None:
        st.session_state.answers[q["id"]] = answer_clicked

        # >>> AUTOSAVE DRAFT po odpowiedzi <<<
        autosave(finished=False, result=None)

        if st.session_state.current_q_idx + 1 >= nq:
            score, max_score, prob = compute_scores(st.session_state.answers, path)
            st.session_state.result = {"score": score, "max_score": max_score, "prob": prob}
            st.session_state.finished = True

            # >>> AUTOSAVE WYNIK KOŃCOWY <<<
            autosave(finished=True, result=st.session_state.result)

            st.rerun()
        else:
            st.session_state.current_q_idx += 1
            st.rerun()

st.divider()

# ---------------------- 📊 WYNIK – READ-ONLY ----------------------
if st.session_state.finished and st.session_state.result:
    res = st.session_state.result
    score, max_score, prob = res["score"], res["max_score"], res["prob"]

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Szacowane ryzyko", f"{prob * 100:.0f}%")
    with c2:
        st.write("**Suma punktów**")
        st.write(f"{score:.1f} / {max_score:.1f}")
    with c3:
        level = "niskie" if prob < 0.3 else ("umiarkowane" if prob < 0.6 else "wysokie")
        st.metric("Poziom", level)

    with st.expander("Zobacz podsumowanie (read-only)"):
        pretty = {
            "path_label": label_text,
            "version": survey.get("meta", {}).get("version", "unknown"),
            "responses": st.session_state.answers,
            "score": score, "max_score": max_score, "probability": prob
        }
        st.json(pretty)
        st.download_button(
            "Pobierz podsumowanie (JSON)",
            data=json.dumps(pretty, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="wynik_ankiety.json", mime="application/json"
        )

    #st.info("To narzędzie ma charakter edukacyjny i nie zastępuje ostatecznej diagnozy.")
    center_col = st.columns([1, 1, 1])[1]
    with center_col:
        if st.button("Zacznij od nowa"):
            autosave(finished=False, result={"event": "reset"})  # opcjonalny log
            st.session_state.current_q_idx = 0
            st.session_state.answers = {}
            st.session_state.finished = False
            st.session_state.result = None
            st.rerun()

st.caption("Wersja: " + survey.get("meta", {}).get("version", "unknown"))
