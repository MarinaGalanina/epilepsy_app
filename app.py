import json
import numpy as np
import streamlit as st
import os
from typing import Dict, Any, List

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

st.markdown("""
<style>
/* Sekcja centralna na pełną wysokość okna */
.center-stage {
  min-height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

/* Węższa kolumna na środku, żeby nie „pływało” na ultra-szerokich ekranach */
.center-narrow {
  width: min(900px, 92vw);
}

/* Karta pytania – lekko unieś i zrób neutralną ramkę */
.q-card {
  border:1px solid rgba(0,0,0,.10);
  border-radius: 14px;
  padding: 16px 18px;
  background: transparent;
  box-shadow: none;
}
.q-title { font-size:1.08rem; font-weight:700; margin:0 0 .35rem 0; }

/* Pasek postępu/kropki */
.progress-dots { display:flex; gap:6px; flex-wrap:wrap; margin:10px 0 6px 0; justify-content:center; }
.dot { width:10px; height:10px; border-radius:50%; background:rgba(0,0,0,.15); }
.dot.on { background:rgba(0,0,0,.45); }
.badge { display:inline-flex; align-items:center; gap:.5rem; padding:.25rem .7rem;
  border-radius:999px; background:rgba(0,0,0,.06); font-size:.85rem; }
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
        if st.session_state.current_q_idx + 1 >= nq:
            score, max_score, prob = compute_scores(st.session_state.answers, path)
            st.session_state.result = {"score": score, "max_score": max_score, "prob": prob}
            st.session_state.finished = True
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
        level = "niskie" if prob < 0.3 else ("umiarkowane" if prob < 0.7 else "wysokie")
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

    st.info("To narzędzie ma charakter edukacyjny i nie zastępuje ostatecznej diagnozy.")
    if st.button("Zacznij od nowa"):
        st.session_state.current_q_idx = 0
        st.session_state.answers = {}
        st.session_state.finished = False
        st.session_state.result = None
        st.rerun()

st.caption("Wersja: " + survey.get("meta", {}).get("version", "unknown"))
