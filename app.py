import json
import numpy as np
import streamlit as st
import os
from typing import Dict, Any, List

# ---------------------- ⚙️ PAGE SETUP ----------------------
st.set_page_config(
    page_title="Ryzyko cech napadu (DEMO)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None,
)

# ---------------------- 🎨 GLOBAL / KILL WHITE BARS ----------------------
st.markdown("""
<style>
:root { --radius: 14px; }

/* 0) Kill Streamlit white decorations/badges/header/status */
div[data-testid="stDecoration"],
section[data-testid="stDecoration"],
div[data-testid="stHeader"],
header, div[role="banner"],
div[class*="viewerBadge_"],
a[data-testid="viewer-badge"],
[data-testid="stAppStatusWidget"],
[data-testid="stStatusWidget"],
[data-testid="stStatusContainer"],
button[kind="header"] { display:none !important; visibility:hidden !important; }

/* 1) Full-bleed app, remove default paddings/gaps */
html, body, [data-testid="stAppViewContainer"] { background: var(--background-color) !important; }
div[data-testid="stAppViewContainer"] > .main { padding: 0 !important; }
div[data-testid="stAppViewContainer"] .block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { border-right: 1px solid rgba(0,0,0,.06); }

/* 2) A subtle content wrapper with our own spacing */
.app-wrap { padding: 12px 20px 28px 20px; max-width: 1024px; margin: 0 auto; }

/* 3) Top hero/header band */
.hero {
  display:flex; align-items:center; gap:14px;
  padding: 10px 0 6px 0; border-bottom:1px solid rgba(0,0,0,.06);
}
.hero .title { font-weight:800; letter-spacing:.3px; font-size:1.35rem; margin:0; }
.hero .cap { opacity:.85; font-size:.92rem; }

/* 4) Sticky progress strip (no white gaps) */
.progress-wrap { position:sticky; top:0; z-index:5; backdrop-filter:saturate(180%) blur(6px); background:color-mix(in oklab, var(--background-color) 92%, black 0%); border-bottom:1px solid rgba(0,0,0,.06); }
.progress-inner { max-width:1024px; margin:0 auto; padding: 8px 20px; }
.progress-bar { height:6px; width:100%; background: rgba(0,0,0,.08); border-radius:999px; overflow:hidden; }
.progress-fill { height:100%; width:0%; border-radius:999px; background: rgba(0,0,0,.35); transition: width .25s ease; }
.progress-meta { display:flex; gap:10px; align-items:center; margin-top:6px; font-size:.88rem; opacity:.9; }
.dotline { display:flex; gap:6px; flex-wrap:wrap; }
.dot { width:8px; height:8px; border-radius:50%; background: rgba(0,0,0,.18); }
.dot.on { background: rgba(0,0,0,.45); }

/* 5) Question card — flat, neutral (no white pills) */
.q-card {
  border:1px solid rgba(0,0,0,.10);
  border-radius: var(--radius);
  padding: 16px;
  background: transparent;
  box-shadow: none;
}
.q-title { font-size:1.06rem; font-weight:700; margin:0 0 .5rem 0; }

/* 6) Choice grid & neutral buttons */
.choice-grid { display:grid; grid-template-columns: 1fr; gap:10px; margin-top:.4rem; }
@media (min-width:560px){ .choice-grid { grid-template-columns: repeat(3, 1fr); } }
.stButton>button {
  border-radius: var(--radius);
  font-weight: 700;
  padding: 0.9rem 1rem;
  border: 1px solid rgba(0,0,0,.12);
  background: rgba(0,0,0,.03);
  color: inherit;
}
.stButton>button:hover { background: rgba(0,0,0,.06); border-color: rgba(0,0,0,.16); }
.stButton>button:focus { outline: 2px solid rgba(0,0,0,.18); }

/* 7) Neutral select */
div[data-baseweb="select"] > div {
  border-radius: var(--radius);
  border-color: rgba(0,0,0,.12);
  background: rgba(0,0,0,.02);
}

/* 8) Login card */
.auth-card {
  width: min(94vw, 420px);
  background: var(--background-color);
  border-radius: 18px;
  padding: 28px 28px 22px 28px;
  box-shadow: 0 12px 30px rgba(0,0,0,0.08);
  text-align: center;
  animation: fadeIn .25s ease-out;
  margin: auto;
}
.auth-title { margin: 6px 0 2px 0; font-weight: 800; font-size:1.1rem; }
.auth-sub   { opacity: .85; margin-bottom: 14px; }
@keyframes fadeIn { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }

/* 9) Tiny polish on metrics/json/expander */
[data-testid="stMetricValue"] { font-weight:800; }

/* 10) Remove extra top spacing on login view */
.login-center { height: 100vh; display: flex; align-items: center; justify-content: center; padding: 0 !important; margin: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 LOGIN ----------------------
def check_access() -> bool:
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")
    if not ACCESS_CODE:
        st.warning("Brak ustawionego ACCESS_CODE w Secrets/ENV. Skontaktuj się z administratorem.")
        st.stop()

    if st.session_state.get("auth_ok", False):
        return True

    # Centered login without any white bars
    st.markdown('<div class="login-center">', unsafe_allow_html=True)
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.image("https://img.icons8.com/color/96/brain.png", width=76)
    st.markdown('<div class="auth-title">Szacowanie ryzyka cech napadów</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Wpisz kod dostępu, aby kontynuować</div>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed")
        submitted = st.form_submit_button("Zaloguj", use_container_width=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    if submitted:
        if code == ACCESS_CODE:
            st.session_state.auth_ok = True
        else:
            st.warning("Niepoprawny kod. Spróbuj ponownie.")

    st.stop()

if not check_access():
    st.stop()

# ---------------------- 🔁 LOGOUT ----------------------
st.sidebar.success("Zalogowano")
if st.sidebar.button("Wyloguj"):
    st.session_state.auth_ok = False

# ---------------------- 📄 LOAD SURVEY ----------------------
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

# ---------------------- 🧠 HERO ----------------------
st.markdown('<div class="app-wrap">', unsafe_allow_html=True)
st.markdown(f"""
<div class="hero">
  <img src="https://img.icons8.com/color/48/brain.png" width="36" height="36" alt="">
  <div>
    <p class="title">Szacowanie ryzyka cech napadów — DEMO</p>
    <p class="cap">Narzędzie edukacyjne. Nie służy do diagnozy. W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------- 🧩 PATH PICKER ----------------------
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

# ---------------------- 🔢 SCORING ----------------------
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
    ratio = (score / max_score) if max_score else 0.0
    logit = (ratio - 0.5) * 6.0
    prob = 1.0 / (1.0 + np.exp(-logit))
    return score, max_score, prob

# ---------------------- 🔁 PROGRESS (sticky, no white gaps) ----------------------
q_idx = st.session_state.current_q_idx if nq else 0
pct = int((q_idx / max(nq, 1)) * 100)

# Build dots line
dots_html = "".join([f'<span class="dot{" on" if i<q_idx else ""}"></span>' for i in range(nq)])

st.markdown(f"""
<div class="progress-wrap">
  <div class="progress-inner">
    <div class="progress-bar" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{pct}">
      <div class="progress-fill" style="width:{pct}%;"></div>
    </div>
    <div class="progress-meta">
      <span>Pytanie {min(q_idx+1, max(nq,1))} z {nq if nq else 1}</span>
      <div class="dotline" aria-label="postęp pytań">{dots_html}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------- 🗳️ QUESTION ----------------------
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

# ---------------------- 📊 RESULT ----------------------
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
            "path_label": [k for k,v in path_labels.items() if v==st.session_state.selected_path_id][0],
            "version": survey["meta"].get("version", "unknown"),
            "responses": st.session_state.answers,
            "score": score, "max_score": max_score, "probability": prob
        }
        st.json(pretty)
        st.download_button(
            "Pobierz podsumowanie (JSON)",
            data=json.dumps(prety := pretty, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="wynik_ankiety.json", mime="application/json"
        )

    st.info("To narzędzie ma charakter edukacyjny i nie zastępuje ostatecznej diagnozy.")
    if st.button("Zacznij od nowa"):
        st.session_state.current_q_idx = 0
        st.session_state.answers = {}
        st.session_state.finished = False
        st.session_state.result = None
        st.rerun()

st.caption("Wersja: " + survey["meta"].get("version", "unknown"))
st.markdown('</div>', unsafe_allow_html=True)  # .app-wrap
