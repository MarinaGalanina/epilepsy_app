import json
import numpy as np
import streamlit as st
import os
from typing import Dict, Any

# ---------------------- ⚙️ USTAWIENIA STRONY ----------------------
st.set_page_config(
    page_title="Ryzyko cech napadu (DEMO)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------- 🔒 LOGOWANIE (center + without st.rerun) ----------------------
def show_centered_login():
    """Render a centered login card and handle authentication in session_state."""
    # CSS: center main container and style the auth card (keeps it in same position)
    st.markdown(
        """
        <style>
        /* Center the app main area vertically & horizontally */
        div[data-testid="stAppViewContainer"] > .main {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        .auth-card {
            width: min(92vw, 460px);
            background: var(--background-color);
            border-radius: 14px;
            padding: 28px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            text-align: center;
            animation: fadeIn .22s ease-out;
        }
        .auth-title { margin: 6px 0 2px 0; font-weight: 700; font-size:20px; }
        .auth-sub   { opacity: .85; margin-bottom: 12px; font-size:13px; color: var(--secondary-text-color); }
        .auth-note  { margin-top:10px; font-size:12px; color:var(--secondary-text-color); }
        .auth-btn button { width: 100%; height: 44px; font-weight: 700; }
        @keyframes fadeIn { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.image("https://img.icons8.com/color/96/brain.png", width=72)
    st.markdown('<div class="auth-title">🧠 Szacowanie ryzyka cech napadów</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-sub">Prosimy o podanie kodu dostępu, aby uzyskać dostęp do narzędzia. '
        'Aplikacja jest demonstracyjna i nie zastępuje opinii medycznej.</div>',
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        # keep label hidden for compact look; but accessible to screen readers
        code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed", placeholder="Wpisz kod dostępu")
        submitted = st.form_submit_button("Zaloguj")

    st.markdown('<div class="auth-note">Kontakt do administratora: admin@example.com</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # check secrets/env
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")
    if not ACCESS_CODE:
        st.error("Brak ustawionego ACCESS_CODE w Secrets/ENV. Skontaktuj się z administratorem.", icon="⚠️")
        return False

    if submitted:
        if code == ACCESS_CODE:
            st.session_state.auth_ok = True
            # small confirmation to proceed
            st.experimental_rerun()
        else:
            st.error("Błędny kod. Spróbuj ponownie.", icon="❌")
    return False


def check_access_centered() -> bool:
    """Return True if user authenticated, otherwise show centered login and return False."""
    if st.session_state.get("auth_ok", False):
        return True
    return show_centered_login()


# ---------------------- ⛔️ Strażnik logowania ----------------------
if not check_access_centered():
    # stop further rendering for non-authenticated users
    st.stop()

# ---------------------- Sidebar utilities ----------------------
st.sidebar.success("Zalogowano ✅")
if st.sidebar.button("Wyloguj"):
    st.session_state.auth_ok = False
    st.experimental_rerun()

# ---------------------- 🧠 GŁÓWNA CZĘŚĆ APLIKACJI ----------------------
st.title("🧠 Szacowanie ryzyka cech napadów – DEMO")
st.caption(
    "Narzędzie edukacyjne. Nie służy do diagnozy. "
    "W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112."
)

# ---------------------- 📄 WCZYTANIE ANKIETY ----------------------
@st.cache_data
def load_survey(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

try:
    survey = load_survey("survey.json")
except FileNotFoundError:
    st.error("Nie znaleziono pliku survey.json. Upewnij się, że plik istnieje i aplikacja ma do niego dostęp.", icon="🚫")
    st.stop()

paths = {p["id"]: p for p in survey["paths"]}
path_labels = {p["label"]: p["id"] for p in survey["paths"]}

# ---------------------- INITIALIZE SESSION STATE FOR QUESTION FLOW ----------------------
if "selected_path_id" not in st.session_state:
    st.session_state.selected_path_id = list(path_labels.values())[0]
if "current_q_idx" not in st.session_state:
    st.session_state.current_q_idx = 0
if "responses" not in st.session_state:
    st.session_state.responses = {}  # qid -> answer
if "finished" not in st.session_state:
    st.session_state.finished = False
if "computed_result" not in st.session_state:
    st.session_state.computed_result = None

# ---------------------- 🧩 INTERFEJS (select path on sidebar) ----------------------
st.sidebar.header("Wybór ścieżki (typ incydentu)")
chosen_label = st.sidebar.radio("Typ incydentu:", list(path_labels.keys()))
selected_path_id = path_labels[chosen_label]
# if user changes path, reset progress
if selected_path_id != st.session_state.selected_path_id:
    st.session_state.selected_path_id = selected_path_id
    st.session_state.current_q_idx = 0
    st.session_state.responses = {}
    st.session_state.finished = False
    st.session_state.computed_result = None

path = paths[st.session_state.selected_path_id]
st.header(f"Ścieżka: {chosen_label}")
st.write("Odpowiedz na poniższe pytania. Jeśli nie jesteś pewna/pewien, wybierz „nie wiem”.\n\n"
         "Pytania pojawiają się jedno po drugim. Możesz wrócić do poprzedniego pytania i zmienić odpowiedź zanim zobaczysz wynik.")

# ---------------------- Question helper functions ----------------------
def tri_widget(qid: str, label: str, value=None):
    opts = ["nie", "tak", "nie wiem"]
    # use radio for quick keyboard navigation
    return st.radio(label, opts, index=opts.index(value) if value in opts else 0, key=f"tri_{qid}")

def select_widget(qid: str, label: str, options, value=None):
    # provide a placeholder to force explicit selection for new answers
    choices = ["-- wybierz --"] + options
    default_index = choices.index(value) if value in choices else 0
    sel = st.selectbox(label, choices, index=default_index, key=f"sel_{qid}")
    return sel if sel != "-- wybierz --" else None

def compute_scores(responses: Dict[str, Any], path: Dict[str, Any]):
    """Given the responses mapping, compute score, max_score, and probability."""
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
            # find max option weight
            opt_weights = [float(opt.get("weight", 0)) for opt in q.get("options", [])]
            max_score += max(opt_weights) if opt_weights else 0.0
            chosen_label = responses.get(qid)
            for opt in q.get("options", []):
                if opt["label"] == chosen_label:
                    score += float(opt.get("weight", 0))
                    break
    if max_score == 0:
        prob = 0.0
    else:
        ratio = score / max_score
        logit = (ratio - 0.5) * 6.0
        prob = 1.0 / (1.0 + np.exp(-logit))
    return score, max_score, prob

# ---------------------- Single-question flow ----------------------
questions = path["questions"]
n_questions = len(questions)
q_idx = st.session_state.current_q_idx
q = questions[q_idx]

# show progress
progress_pct = int((q_idx / n_questions) * 100)
st.progress(progress_pct)
st.markdown(f"**Pytanie {q_idx + 1} z {n_questions}**")

# display question form (so keyboard Enter submits)
with st.form(f"question_form_{q_idx}"):
    # show question text
    st.write(q["text"])
    # prefill from saved responses if present
    prev_answer = st.session_state.responses.get(q["id"])
    answer = None
    if q["type"] == "tri":
        answer = tri_widget(q["id"], "", value=prev_answer)
    elif q["type"] == "select":
        opts = [opt["label"] for opt in q.get("options", [])]
        answer = select_widget(q["id"], "", opts, value=prev_answer)
    # buttons
    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        prev_clicked = st.form_submit_button("◀ Poprzednie")
    with col_next:
        next_clicked = st.form_submit_button("Dalej ▶")

# handle navigation logic
if prev_clicked:
    if q_idx > 0:
        st.session_state.current_q_idx -= 1
    st.experimental_rerun()

if next_clicked:
    # validate answer (require selection)
    if answer is None:
        st.warning("Proszę wybrać odpowiedź, zanim przejdziesz dalej.")
    else:
        # store
        st.session_state.responses[q["id"]] = answer
        # if last question -> compute result
        if q_idx + 1 >= n_questions:
            score, max_score, prob = compute_scores(st.session_state.responses, path)
            st.session_state.computed_result = {"score": score, "max_score": max_score, "prob": prob}
            st.session_state.finished = True
            st.experimental_rerun()
        else:
            st.session_state.current_q_idx += 1
            st.experimental_rerun()

st.divider()

# ---------------------- 📊 WYNIK (only after finishing) ----------------------
if st.session_state.finished and st.session_state.computed_result is not None:
    res = st.session_state.computed_result
    prob = res["prob"]
    score = res["score"]
    max_score = res["max_score"]

    st.subheader("Wynik (DEMO)")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("Szacowane ryzyko", f"{prob * 100:.0f}%")
    with col2:
        st.write("**Suma punktów**")
        st.write(f"{score:.1f} / {max_score:.1f}")
    with col3:
        if prob < 0.3:
            level = "niskie"
        elif prob < 0.7:
            level = "umiarkowane"
        else:
            level = "wysokie"
        st.metric("Poziom", level)

    st.caption("Wersja: " + survey["meta"].get("version", "unknown"))
    st.markdown("---")
    st.info(
        "To narzędzie ma charakter wyłącznie edukacyjny. Jeśli występują objawy lub wątpliwości — skontaktuj się z lekarzem.",
        icon="ℹ️"
    )

    # allow restart or review
    rcol1, rcol2 = st.columns([1, 1])
    with rcol1:
        if st.button("Powrót do początku"):
            st.session_state.current_q_idx = 0
            st.session_state.responses = {}
            st.session_state.finished = False
            st.session_state.computed_result = None
            st.experimental_rerun()
    with rcol2:
        if st.button("Zobacz / edytuj odpowiedzi"):
            # let user walk through questions again starting from first unanswered
            st.session_state.current_q_idx = 0
            st.session_state.finished = False
            st.session_state.computed_result = None
            st.experimental_rerun()
else:
    # show a subtle hint how many answered and how many left
    answered = len([k for k in st.session_state.responses.keys()])
    st.caption(f"Odpowiedziano: {answered} / {n_questions}. Po przejściu przez wszystkie pytania zobaczysz wynik.")
