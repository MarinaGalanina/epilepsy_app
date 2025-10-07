import json
import numpy as np
import streamlit as st
import os

# ---------------------- 🔒 LOGOWANIE ----------------------

def check_access() -> bool:
    """Prosty system logowania oparty na ACCESS_CODE (z secrets lub ENV)."""
    st.sidebar.markdown("### 🔒 Dostęp")

    # Odczyt kodu z konfiguracji (Streamlit Secrets lub zmienna środowiskowa)
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")

    if not ACCESS_CODE:
        st.sidebar.error("Brak ustawionego ACCESS_CODE w Secrets/ENV.")
        st.stop()

    # Przechowywanie statusu logowania w sesji
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    # Formularz logowania
    if not st.session_state.auth_ok:
        with st.sidebar.form("login_form", clear_on_submit=False):
            code = st.text_input("Wpisz kod dostępu", type="password")
            submitted = st.form_submit_button("Zaloguj")

        if submitted:
            if code == ACCESS_CODE:
                st.session_state.auth_ok = True
                st.sidebar.success("Zalogowano ✅")
            else:
                st.sidebar.error("Błędny kod ❌")

    # Wylogowanie
    if st.session_state.auth_ok:
        if st.sidebar.button("Wyloguj"):
            st.session_state.auth_ok = False
            st.experimental_rerun()
        return True

    # Jeśli użytkownik nie jest zalogowany, zatrzymujemy działanie aplikacji
    st.stop()


# ---------------------- ⚙️ USTAWIENIA STRONY ----------------------

st.set_page_config(page_title="Ryzyko cech napadu (DEMO)", page_icon="🧠")

# Zatrzymaj aplikację, jeśli użytkownik nie wpisał poprawnego kodu
if not check_access():
    st.stop()


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
