import json
import numpy as np
import streamlit as st
import os

# ---------------------- ⚙️ USTAWIENIA STRONY ----------------------
st.set_page_config(
    page_title="Ryzyko cech napadu (DEMO)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"  # ukryj sidebar do czasu logowania
)

# ---------------------- 🔒 LOGOWANIE (center + bez st.rerun) ----------------------
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
        code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed")
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

st.sidebar.success("Zalogowano ✅")
if st.sidebar.button("Wyloguj"):
    st.session_state.auth_ok = False

# ---------------------- 🧠 GŁÓWNA CZĘŚĆ APLIKACJI ----------------------
st.title("🧠 Szacowanie ryzyka cech napadów – DEMO")
st.caption("Narzędzie edukacyjne. Nie służy do diagnozy. "
           "W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112.")

# ---------------------- 📄 WCZYTANIE ANKIETY ----------------------
@st.cache_data
def load_survey(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

survey = load_survey("survey.json")
paths = {p["id"]: p for p in survey["paths"]}
path_labels = {p["label"]: p["id"] for p in survey["paths"]}

# ---------------------- 🧩 INTERFEJS ----------------------
st.sidebar.header("Wybór ścieżki (typ incydentu)")
chosen_label = st.sidebar.radio("Typ incydentu:", list(path_labels.keys()))
path_id = path_labels[chosen_label]
path = paths[path_id]

st.header(f"Ścieżka: {chosen_label}")
st.write("Odpowiedz na poniższe pytania. Jeśli nie jesteś pewna/pewien, wybierz „nie wiem”.")

# ---------------------- 🔢 OBLICZANIE WYNIKU ----------------------
responses = {}
max_score = 0.0
score = 0.0

def tri_widget(key, label):
    return st.selectbox(label, ["nie", "tak", "nie wiem"], key=key)

def handle_question(q):
    global max_score, score
    qtype = q["type"]
    if qtype == "tri":
        ans = tri_widget(q["id"], q["text"])
        responses[q["id"]] = ans
        max_score += float(q.get("weight_yes", 0))
        if ans == "tak":
            score += float(q.get("weight_yes", 0))
        elif ans == "nie wiem":
            score += float(q.get("weight_maybe", 0))
    elif qtype == "select":
        labels = [opt["label"] for opt in q["options"]]
        ans = st.selectbox(q["text"], labels, key=q["id"])
        responses[q["id"]] = ans
        opt_weights = [float(opt.get("weight", 0)) for opt in q["options"]]
        max_score += max(opt_weights) if opt_weights else 0.0
        for opt in q["options"]:
            if opt["label"] == ans:
                score += float(opt.get("weight", 0))
                break

for q in path["questions"]:
    handle_question(q)

st.divider()

# ---------------------- 📊 WYNIK ----------------------
if max_score == 0:
    prob = 0.0
else:
    ratio = score / max_score
    logit = (ratio - 0.5) * 6.0
    prob = 1.0 / (1.0 + np.exp(-logit))

st.subheader("Wynik (DEMO)")
col1, col2, col3 = st.columns(3)
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

st.caption("Wersja: " + survey["meta"]["version"])
