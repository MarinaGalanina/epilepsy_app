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

# 🔧 Usuń dekoracje i górne odstępy UI Streamlita (żeby nic nie „wystawało” nad loginem)
st.markdown("""
<style>
/* dekoracyjna pigułka / header / toolbar / badge */
div[data-testid="stDecoration"],
header [data-testid="stDecoration"],
section[data-testid="stDecoration"],
div[data-testid="stHeader"], header, div[data-testid="stToolbar"],
div[class*="viewerBadge_"], a[data-testid="viewer-badge"],
button[kind="header"], div[data-testid="stStatusWidget"] { display:none !important; }

/* wyzeruj górne odstępy kontenera aplikacji */
div[data-testid="stAppViewContainer"] { padding-top:0 !important; margin-top:0 !important; }
div[data-testid="stAppViewContainer"] > .main { padding-top:0 !important; padding-bottom:0 !important; }
.block-container { padding-top:0 !important; }

/* jednolite tło, żeby nic nie „przebijało” */
html, body, [data-testid="stAppViewContainer"] {
  background: var(--background-color, #ffffff) !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 LOGOWANIE (center + bez st.rerun) ----------------------
def check_access() -> bool:
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")
    if not ACCESS_CODE:
        st.error("Brak ustawionego ACCESS_CODE w Secrets/ENV."); st.stop()

    if st.session_state.get("auth_ok", False):
        return True

    # Dokładne centrowanie karty logowania
    st.markdown("""
    <style>
      div[data-testid="stAppViewContainer"] > .main {
        height: 100vh;                   /* pełny viewport */
        display: flex;
        align-items: center;             /* pion */
        justify-content: center;         /* poziom */
      }
      .auth-card{
        width: min(94vw, 420px);
        background: var(--background-color, #ffffff);
        border-radius: 18px;
        padding: 28px 28px 22px;
        box-shadow: 0 12px 30px rgba(0,0,0,.08);
        text-align:center;
        animation: fadeIn .25s ease-out;
      }
      @keyframes fadeIn{from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:translateY(0);}}
      .auth-emoji{
        font-size: 56px; line-height: 1; margin-bottom: 6px;
        user-select:none;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    # 👉 ZAMIANA obrazka z białym tłem na czyste emoji (brak „białego jajka”)
    st.markdown('<div class="auth-emoji">🧠</div>', unsafe_allow_html=True)
    st.markdown("### Szacowanie ryzyka cech napadów")
    st.write("Wpisz kod dostępu, aby kontynuować")
    with st.form("login_form", clear_on_submit=False):
        code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed")
        ok = st.form_submit_button("Zaloguj", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if ok:
        if code == ACCESS_CODE:
            st.session_state.auth_ok = True   # kolejny render pokaże appkę
        else:
            st.error("Błędny kod ❌")

    st.stop()


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
