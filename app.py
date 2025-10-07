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
    initial_sidebar_state="collapsed"  # ukryj sidebar do czasu logowania
)

# ---------------------- 🔧 GLOBALNY STYL (subtelny, nowoczesny) ----------------------
st.markdown("""
<style>
/* Delikatne wyrównanie typografii i komponentów */
:root {
  --radius: 14px;
}
div[data-testid="stAppViewContainer"] .block-container {
  padding-top: 16px;
  padding-bottom: 32px;
}
section[tabindex="0"] { outline: none; }
.stButton>button, .stDownloadButton>button {
  border-radius: var(--radius);
  font-weight: 600;
}
.stAlert {
  border-radius: var(--radius);
}
.stProgress > div > div > div {
  border-radius: 999px;
}
div[data-baseweb="select"] > div {
  border-radius: var(--radius);
}
.stRadio > div { gap: 10px; }
hr { margin: 10px 0 2px 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 LOGOWANIE (TA SAMA FUNKCJA – NIE ZMIENIAM) ----------------------
def check_access() -> bool:
    """
    Ekran logowania wyświetlany dokładnie na środku ekranu.
    Wymaga ACCESS_CODE w st.secrets lub zmiennej środowiskowej.
    """
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")
    if not ACCESS_CODE:
        st.error("Brak ustawionego ACCESS_CODE w Secrets/ENV.")
        st.stop()

    # status sesji
    auth_ok = st.session_state.get("auth_ok", False)
    if auth_ok:
        return True

    # CSS: centrowanie głównego kontenera, bez dziwnych marginesów
    st.markdown(
        """
        <style>
        /* uderzamy w główny kontener widoku */
        div[data-testid="stAppViewContainer"] > .main {
            height: 100vh;
            display: flex;
            align-items: center;          /* pion */
            justify-content: center;       /* poziom */
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        .auth-card {
            width: min(94vw, 420px);
            background: var(--background-color);
            border-radius: 18px;
            padding: 28px 28px 22px 28px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.08);
            text-align: center;
            animation: fadeIn .25s ease-out;
        }
        .auth-title { margin: 6px 0 2px 0; font-weight: 700; }
        .auth-sub   { opacity: .8; margin-bottom: 14px; }
        .auth-btn button { width: 100%; height: 42px; font-weight: 600; }
        @keyframes fadeIn { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
        </style>
        """,
        unsafe_allow_html=True
    )

    # środkowa karta logowania (bez callbacków)
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.image("https://img.icons8.com/color/96/brain.png", width=76)
    st.markdown('<div class="auth-title"> Szacowanie ryzyka cech napadów</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Wpisz kod dostępu, aby kontynuować</div>', unsafe_allow_html=True)

    # używamy formy – submit = naturalny rerender (bez st.rerun)
    with st.form("login_form", clear_on_submit=False):
        code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed", placeholder="••••••")
        submitted = st.form_submit_button("Zaloguj", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if code == ACCESS_CODE:
            st.session_state.auth_ok = True   # kolejny rerender pokaże aplikację
        else:
            st.error("Błędny kod ❌")

    st.stop()  # dopóki nie zalogowany – nic dalej się nie renderuje

# ---------------------- ⛔️ Strażnik logowania ----------------------
if not check_access():
    st.stop()

# ---------------------- 🔁 Wylogowanie ----------------------
st.sidebar.success("Zalogowano ✅")
if st.sidebar.button("Wyloguj"):
    st.session_state.auth_ok = False

# ---------------------- 🧠 GŁÓWNA CZĘŚĆ APLIKACJI ----------------------
st.title("🧠 Szacowanie ryzyka cech napadów – DEMO")
st.caption("Narzędzie edukacyjne. Nie służy do diagnozy. "
           "W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112.")

# ---------------------- 📄 WCZYTANIE ANKIETY ----------------------
@st.cache_data
def load_survey(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

try:
    survey = load_survey("survey.json")
except FileNotFoundError:
    st.error("Nie znaleziono pliku survey.json. Upewnij się, że plik istnieje w katalogu aplikacji.", icon="🚫")
    st.stop()

paths: Dict[str, Dict[str, Any]] = {p["id"]: p for p in survey["paths"]}
path_labels: Dict[str, str] = {p["label"]: p["id"] for p in survey["paths"]}

# ---------------------- 🧭 STAN SESJI (przepływ pytań) ----------------------
def _init_state():
    if "selected_path_id" not in st.session_state:
        st.session_state.selected_path_id = list(path_labels.values())[0]
    if "current_q_idx" not in st.session_state:
        st.session_state.current_q_idx = 0
    if "responses" not in st.session_state:
        st.session_state.responses: Dict[str, Any] = {}
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "result" not in st.session_state:
        st.session_state.result = None

_init_state()

# ---------------------- 🧩 WYBÓR ŚCIEŻKI ----------------------
st.sidebar.header("Wybór ścieżki (typ incydentu)")
chosen_label = st.sidebar.radio("Typ incydentu:", list(path_labels.keys()))
selected_path_id = path_labels[chosen_label]

# Reset postępu przy zmianie ścieżki
if selected_path_id != st.session_state.selected_path_id:
    st.session_state.selected_path_id = selected_path_id
    st.session_state.current_q_idx = 0
    st.session_state.responses = {}
    st.session_state.finished = False
    st.session_state.result = None

path = paths[st.session_state.selected_path_id]
questions: List[Dict[str, Any]] = path["questions"]
nq = len(questions)

# ---------------------- 🔢 NARZĘDZIA OCENY ----------------------
def compute_scores(responses: Dict[str, Any], path: Dict[str, Any]):
    score = 0.0
    max_score = 0.0
    for q in path["questions"]:
        qid = q["id"]
        qtype = q.get("type")
        if qtype == "tri":
            max_score += float(q.get("weight_yes", 0))
            ans = responses.get(qid)
            if ans == "tak":
                score += float(q.get("weight_yes", 0))
            elif ans == "nie wiem":
                score += float(q.get("weight_maybe", 0))
        elif qtype == "select":
            opt_weights = [float(opt.get("weight", 0)) for opt in q.get("options", [])]
            max_score += max(opt_weights) if opt_weights else 0.0
            chosen = responses.get(qid)
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

# ---------------------- 🧱 NAGŁÓWEK ŚCIEŻKI ----------------------
st.header(f"Ścieżka: {chosen_label}")
st.write("Odpowiadaj na pytania po kolei. Jeśli nie jesteś pewna/pewien, wybierz „nie wiem”. "
         "Wynik zobaczysz po udzieleniu odpowiedzi na wszystkie pytania.")

# ---------------------- 📈 PROGRES ----------------------
q_idx = st.session_state.current_q_idx
progress = int((q_idx / max(nq, 1)) * 100)
st.progress(progress)
st.markdown(f"**Pytanie {q_idx + 1} z {nq}**" if nq else "**Brak pytań w tej ścieżce.**")

# ---------------------- 🗳️ WIDGETY PYTAŃ ----------------------
def tri_widget(qid: str, prev=None):
    opts = ["nie", "tak", "nie wiem"]
    idx = opts.index(prev) if prev in opts else 0
    return st.radio("", opts, index=idx, key=f"tri_{qid}", horizontal=True)

def select_widget(qid: str, options: List[str], prev=None):
    choices = ["-- wybierz --"] + options
    idx = choices.index(prev) if prev in choices else 0
    val = st.selectbox("", choices, index=idx, key=f"sel_{qid}")
    return None if val == "-- wybierz --" else val

# ---------------------- 🎛️ FORMULARZ JEDNO-PYTANIE-NA-RAZ ----------------------
if not st.session_state.finished and nq > 0:
    q = questions[q_idx]
    st.write(q["text"])

    with st.form(f"qform_{q_idx}"):
        prev = st.session_state.responses.get(q["id"])
        answer = None
        if q["type"] == "tri":
            answer = tri_widget(q["id"], prev=prev)
        elif q["type"] == "select":
            labels = [opt["label"] for opt in q.get("options", [])]
            answer = select_widget(q["id"], labels, prev=prev)

        c1, c2, c3 = st.columns([1, 1, 2])
        prev_btn = c1.form_submit_button("◀ Poprzednie")
        next_btn = c2.form_submit_button("Dalej ▶")
        # podpowiedź sterowania
        with c3:
            st.caption("Wskazówka: używaj Tab/Shift+Tab do nawigacji, Enter aby zatwierdzić.")

    if prev_btn:
        if q_idx > 0:
            st.session_state.current_q_idx -= 1
        st.rerun()

    if next_btn:
        if answer is None:
            st.warning("Wybierz odpowiedź, zanim przejdziesz dalej.")
        else:
            st.session_state.responses[q["id"]] = answer
            if q_idx + 1 >= nq:
                # policz wynik
                score, max_score, prob = compute_scores(st.session_state.responses, path)
                st.session_state.result = {"score": score, "max_score": max_score, "prob": prob}
                st.session_state.finished = True
                st.rerun()
            else:
                st.session_state.current_q_idx += 1
                st.rerun()

st.divider()

# ---------------------- 📊 WYNIK (po zakończeniu) ----------------------
if st.session_state.finished and st.session_state.result:
    res = st.session_state.result
    score, max_score, prob = res["score"], res["max_score"], res["prob"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Szacowane ryzyko", f"{prob * 100:.0f}%")
    with col2:
        st.write("**Suma punktów**")
        st.write(f"{score:.1f} / {max_score:.1f}")
    with col3:
        level = "niskie" if prob < 0.3 else ("umiarkowane" if prob < 0.7 else "wysokie")
        st.metric("Poziom", level)

    # 🔽 Podsumowanie odpowiedzi + eksport JSON
    with st.expander("Zobacz swoje odpowiedzi"):
        pretty = {
            "path_label": chosen_label,
            "version": survey["meta"].get("version", "unknown"),
            "responses": st.session_state.responses,
            "score": score,
            "max_score": max_score,
            "probability": prob
        }
        st.json(pretty)
        st.download_button(
            "Pobierz podsumowanie (JSON)",
            data=json.dumps(pretty, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="wynik_ankiety.json",
            mime="application/json"
        )

    st.info("To narzędzie ma charakter edukacyjny i nie zastępuje porady lekarskiej.", icon="ℹ️")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("🔁 Zacznij od nowa"):
            st.session_state.current_q_idx = 0
            st.session_state.responses = {}
            st.session_state.finished = False
            st.session_state.result = None
            st.rerun()
    with r2:
        if st.button("✏️ Edytuj odpowiedzi"):
            st.session_state.current_q_idx = 0
            st.session_state.finished = False
            st.session_state.result = None
            st.rerun()

st.caption("Wersja: " + survey["meta"].get("version", "unknown"))
