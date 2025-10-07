import json
import numpy as np
import streamlit as st
import os
from datetime import datetime

# ---------------------- ⚙️ USTAWIENIA STRONY ----------------------
st.set_page_config(
    page_title="Ryzyko cech napadu (DEMO)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------- 🔧 STYLE (bez białych marginesów) ----------------------
st.markdown("""
<style>
div[data-testid="stDecoration"],
header [data-testid="stDecoration"],
section[data-testid="stDecoration"],
div[data-testid="stHeader"], header, div[data-testid="stToolbar"],
div[class*="viewerBadge_"], a[data-testid="viewer-badge"],
button[kind="header"], div[data-testid="stStatusWidget"] { display:none !important; }

html, body { margin:0 !important; padding:0 !important; }
div[data-testid="stAppViewContainer"] { padding-top:0 !important; margin-top:0 !important; }
div[data-testid="stAppViewContainer"] > .main { padding-top:0 !important; padding-bottom:1rem !important; }
.block-container { padding-top:0 !important; }

/* karty i badge */
.card { background:#fff; border-radius:16px; padding:20px; box-shadow:0 8px 24px rgba(0,0,0,.06); }
.badge { display:inline-block; padding:.25rem .6rem; border-radius:999px; font-size:.85rem; font-weight:600; }
.badge-low{ background:#ecfdf5; color:#065f46; }
.badge-mid{ background:#fffbeb; color:#92400e; }
.badge-high{ background:#fef2f2; color:#991b1b; }

/* ——— login centrowany ——— */
div[data-testid="stAppViewContainer"] > .main {
  height: auto;
}
.auth-card{
  width: min(94vw, 420px);
  background: #fff;
  border-radius: 18px;
  padding: 28px 28px 22px;
  box-shadow: 0 12px 30px rgba(0,0,0,.08);
  text-align:center;
  animation: fadeIn .25s ease-out;
}
@keyframes fadeIn{from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:translateY(0);}}
.auth-emoji{ font-size:56px; line-height:1; margin-bottom:6px; user-select:none; }
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 LOGOWANIE (IDENTYCZNE) ----------------------
def check_access() -> bool:
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")
    if not ACCESS_CODE:
        st.error("Brak ustawionego ACCESS_CODE w Secrets/ENV."); st.stop()

    if st.session_state.get("auth_ok", False):
        return True

    # Centrowany login
    st.markdown('<div style="min-height:100vh; display:flex; align-items:center; justify-content:center;">', unsafe_allow_html=True)
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-emoji">🧠</div>', unsafe_allow_html=True)
    st.markdown("### Szacowanie ryzyka cech napadów")
    st.write("Wpisz kod dostępu, aby kontynuować")
    with st.form("login_form", clear_on_submit=False):
        code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed")
        ok = st.form_submit_button("Zaloguj", use_container_width=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    if ok:
        if code == ACCESS_CODE:
            st.session_state.auth_ok = True
            return True
        else:
            st.error("Błędny kod ❌")

    st.stop()

if not check_access():
    st.stop()

# ---------------------- 📄 WCZYTANIE ANKIETY ----------------------
@st.cache_data
def load_survey(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

survey = load_survey("survey.json")
paths = {p["id"]: p for p in survey["paths"]}
path_labels = {p["label"]: p["id"] for p in survey["paths"]}

# ---------------------- 🧭 SESSION STATE ----------------------
def _init_state():
    st.session_state.setdefault("screen", "questions")   # "questions" | "result"
    st.session_state.setdefault("chosen_path_id", list(paths.keys())[0] if paths else None)
    st.session_state.setdefault("step", 0)               # index pytania
    st.session_state.setdefault("responses", {})         # {q_id: answer}

_init_state()

# ---------------------- 🧠 SIDEBAR ----------------------
with st.sidebar:
    st.success("Zalogowano ✅")
    if st.button("Wyloguj"):
        st.session_state.clear()
        st.session_state.auth_ok = False
        st.rerun()

    st.header("Wybór ścieżki")
    labels_list = list(path_labels.keys())
    current_label = [k for k,v in path_labels.items() if v == st.session_state.chosen_path_id][0]
    new_label = st.radio("Typ incydentu:", labels_list, index=labels_list.index(current_label))

    new_path_id = path_labels[new_label]
    if new_path_id != st.session_state.chosen_path_id:
        st.session_state.chosen_path_id = new_path_id
        st.session_state.step = 0
        st.session_state.responses = {}
        st.session_state.screen = "questions"

# ---------------------- 🔢 LOGIKA OBLICZEŃ ----------------------
def compute_score_and_prob(path_def, responses):
    max_score = 0.0
    score = 0.0
    for q in path_def["questions"]:
        qtype = q["type"]
        if qtype == "tri":
            ans = responses.get(q["id"])
            max_score += float(q.get("weight_yes", 0))
            if ans == "tak":
                score += float(q.get("weight_yes", 0))
            elif ans == "nie wiem":
                score += float(q.get("weight_maybe", 0))
        elif qtype == "select":
            labels = [opt["label"] for opt in q["options"]]
            opt_weights = [float(opt.get("weight", 0)) for opt in q["options"]]
            max_score += max(opt_weights) if opt_weights else 0.0
            ans = responses.get(q["id"])
            if ans in labels:
                idx = labels.index(ans)
                score += float(q["options"][idx].get("weight", 0))
    if max_score <= 0:
        return 0.0, 0.0, 0.0
    ratio = score / max_score
    logit = (ratio - 0.5) * 6.0
    prob = 1.0 / (1.0 + np.exp(-logit))
    return score, max_score, prob

def risk_label(prob):
    if prob < 0.3:
        return "niskie", "badge-low"
    elif prob < 0.7:
        return "umiarkowane", "badge-mid"
    return "wysokie", "badge-high"

def tri_widget(key, label, value=None):
    idx = {"nie":0, "tak":1, "nie wiem":2}.get(value, 0)
    return st.selectbox(label, ["nie", "tak", "nie wiem"], index=idx, key=key)

def handle_question(q, existing_value):
    if q["type"] == "tri":
        return tri_widget(q["id"], q["text"], existing_value)
    elif q["type"] == "select":
        labels = [opt["label"] for opt in q["options"]]
        default_idx = labels.index(existing_value) if existing_value in labels else 0
        return st.selectbox(q["text"], labels, index=default_idx, key=q["id"])
    else:
        st.warning(f"Nieznany typ pytania: {q['type']}")
        return None

# ---------------------- 🖥️ EKRAN 1: ANKIETA ----------------------
path = paths[st.session_state.chosen_path_id]
questions = path["questions"]
total_steps = len(questions)

st.markdown("### 🧠 Szacowanie ryzyka cech napadów – DEMO")
st.caption("Narzędzie edukacyjne. Nie służy do diagnozy. W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112.")
st.divider()

if st.session_state.screen == "questions":
    if total_steps == 0:
        st.info("Dla tej ścieżki nie zdefiniowano pytań.")
    else:
        idx = st.session_state.step
        st.progress(idx / total_steps, text=f"Krok {idx} z {total_steps}")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(f"Pytanie {idx+1} z {total_steps}")
        q = questions[idx]
        prev = st.session_state.responses.get(q["id"])
        ans = handle_question(q, prev)

        col_prev, col_mid, col_next = st.columns([1,6,2])
        with col_prev:
            if st.button("← Wstecz", use_container_width=True, disabled=(idx == 0)):
                st.session_state.step = max(0, idx-1)
                st.rerun()
        with col_next:
            label = "Zakończ i pokaż wynik" if idx == total_steps-1 else "Dalej →"
            if st.button(label, use_container_width=True):
                if ans is not None:
                    st.session_state.responses[q["id"]] = ans
                if idx < total_steps-1:
                    st.session_state.step = idx+1
                else:
                    st.session_state.screen = "result"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Opcje"):
            if st.button("Wyczyść odpowiedzi i zacznij od nowa"):
                st.session_state.responses = {}
                st.session_state.step = 0
                st.session_state.screen = "questions"
                st.rerun()

# ---------------------- 🧾 EKRAN 2: WYNIK ----------------------
if st.session_state.screen == "result":
    score, max_score, prob = compute_score_and_prob(path, st.session_state.responses)
    level, cls = risk_label(prob)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Wynik (DEMO)")
    st.markdown(f"<span class='badge {cls}'>Poziom ryzyka: {level}</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Szacowane ryzyko", f"{prob*100:.0f}%")
    with c2: st.metric("Suma punktów", f"{score:.1f} / {max_score:.1f}")
    with c3: st.metric("Ścieżka", path["label"])

    st.markdown("#### Rekomendacje (informacyjne)")
    if prob >= 0.7:
        st.warning("Wysokie ryzyko cech napadu. Skontaktuj się niezwłocznie z lekarzem lub zadzwoń na 112 w razie niepokojących objawów.")
    elif prob >= 0.3:
        st.info("Umiarkowane ryzyko. Rozważ konsultację lekarską i obserwację objawów.")
    else:
        st.success("Niskie ryzyko na podstawie udzielonych odpowiedzi. W razie wątpliwości skontaktuj się z lekarzem.")

    # Pobierz podsumowanie
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": survey["meta"]["version"],
        "path_id": path["id"],
        "path_label": path["label"],
        "responses": st.session_state.responses,
        "score": round(score, 3),
        "max_score": round(max_score, 3),
        "risk_probability": round(float(prob), 4),
        "risk_level": level
    }
    st.download_button(
        "Pobierz podsumowanie (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"wynik_{path['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True
    )

    col_a, col_b, col_c = st.columns([1,1,1])
    with col_a:
        if st.button("Edytuj odpowiedzi", use_container_width=True):
            # wróć do ostatniego pytania, gdzie nie ma odpowiedzi (lub do końca)
            unanswered = [i for i, q in enumerate(questions) if q["id"] not in st.session_state.responses]
            st.session_state.step = unanswered[0] if unanswered else len(questions)-1
            st.session_state.screen = "questions"
            st.rerun()
    with col_b:
        if st.button("Wypełnij ponownie", use_container_width=True):
            st.session_state.responses = {}
            st.session_state.step = 0
            st.session_state.screen = "questions"
            st.rerun()
    with col_c:
        if st.button("Zmień ścieżkę", use_container_width=True):
            st.session_state.step = 0
            st.session_state.screen = "questions"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Wersja: " + survey["meta"]["version"])
