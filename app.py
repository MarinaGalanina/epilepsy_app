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


# ---------------------- 🧩 INTERFEJS (WIZARD) ----------------------

st.set_page_config(page_title="Ryzyko cech napadu (DEMO)", page_icon="🧠", layout="wide")  # szerzej

# init session state
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "step" not in st.session_state:
    st.session_state.step = 0
if "current_path" not in st.session_state:
    st.session_state.current_path = None

# wybór ścieżki jako „pigułki” (poziomo, w main – lepsza ergonomia)
st.markdown("### Wybór ścieżki (typ incydentu)")
labels = list(path_labels.keys())
cols = st.columns(len(labels))
clicked = None
for i, lbl in enumerate(labels):
    with cols[i]:
        if st.button(lbl, use_container_width=True):
            clicked = lbl

# ustaw aktualną ścieżkę przy pierwszym wyborze lub kliknięciu
if st.session_state.current_path is None:
    st.session_state.current_path = labels[0]
if clicked:
    st.session_state.current_path = clicked
    st.session_state.step = 0  # reset kroków

path_id = path_labels[st.session_state.current_path]
path = paths[path_id]
questions = path["questions"]
n = len(questions)

st.markdown(f"#### Ścieżka: {st.session_state.current_path}")
st.progress((st.session_state.step+1)/n, text=f"Krok {st.session_state.step+1} z {n}")

# przygotuj słownik odpowiedzi dla tej ścieżki
st.session_state.answers.setdefault(path_id, {})

# RENDER 1 PYTANIE
q = questions[st.session_state.step]
qid = q["id"]
label = q["text"]

# pokaż kompaktowo w formularzu (mniej migotania UI)
with st.form(f"qform_{qid}", clear_on_submit=False):
    if q["type"] == "tri":
        default = st.session_state.answers[path_id].get(qid, "nie")
        ans = st.selectbox(label, ["nie", "tak", "nie wiem"], index=["nie","tak","nie wiem"].index(default))
    elif q["type"] == "select":
        options = [opt["label"] for opt in q["options"]]
        default = st.session_state.answers[path_id].get(qid, options[0])
        ans = st.selectbox(label, options, index=options.index(default))
    else:
        ans = st.text_input(label, value=st.session_state.answers[path_id].get(qid, ""))

    nav_col1, nav_col2, nav_col3 = st.columns([1,1,2])
    with nav_col1:
        back = st.form_submit_button("⬅ Wstecz", disabled=st.session_state.step == 0)
    with nav_col2:
        next_ = st.form_submit_button("Dalej ➡")
    with nav_col3:
        finish = st.form_submit_button("✅ Zakończ i oblicz", disabled=st.session_state.step != n-1)

# zapisz odpowiedź bieżącego pytania
st.session_state.answers[path_id][qid] = ans

# nawigacja
if back:
    st.session_state.step = max(0, st.session_state.step - 1)
    st.experimental_rerun()
elif next_:
    st.session_state.step = min(n-1, st.session_state.step + 1)
    st.experimental_rerun()

# ---------------------- 🔢 OBLICZANIE WYNIKU PO ZAKOŃCZENIU ----------------------

def compute_score(path_obj, answers_dict):
    score = 0.0
    max_score = 0.0
    for qq in path_obj["questions"]:
        qid = qq["id"]
        if qq["type"] == "tri":
            max_score += float(qq.get("weight_yes", 0))
            v = answers_dict.get(qid)
            if v == "tak":
                score += float(qq.get("weight_yes", 0))
            elif v == "nie wiem":
                score += float(qq.get("weight_maybe", 0))
        elif qq["type"] == "select":
            opt_weights = [float(opt.get("weight", 0)) for opt in qq.get("options", [])]
            max_score += max(opt_weights) if opt_weights else 0.0
            chosen = answers_dict.get(qid)
            for opt in qq.get("options", []):
                if opt["label"] == chosen:
                    score += float(opt.get("weight", 0))
                    break
    if max_score == 0:
        return 0.0, 0.0, 0.0
    ratio = score / max_score
    import numpy as np
    logit = (ratio - 0.5) * 6.0
    prob = 1.0 / (1.0 + np.exp(-logit))
    return prob, score, max_score

if finish:
    prob, score, max_score = compute_score(path, st.session_state.answers[path_id])

    st.divider()
    st.subheader("Wynik (DEMO)")
    c1, c2, c3, c4 = st.columns([1,1,1,2])

    with c1:
        st.metric("Szacowane ryzyko", f"{prob*100:.0f}%")
    with c2:
        st.write("**Suma punktów**")
        st.write(f"{score:.1f} / {max_score:.1f}")
    with c3:
        if prob < 0.3: level = "niskie"
        elif prob < 0.7: level = "umiarkowane"
        else: level = "wysokie"
        st.metric("Poziom", level)
    with c4:
        if st.button("🔁 Wypełnij ponownie", use_container_width=True):
            st.session_state.step = 0
            st.session_state.answers[path_id] = {}
            st.experimental_rerun()

    with st.expander("Podgląd odpowiedzi (debug)"):
        st.json(st.session_state.answers[path_id])

st.caption("Wersja: " + survey["meta"]["version"])
