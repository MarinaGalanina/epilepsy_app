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

# ---------------------- 🎨 GLOBAL STYLES (no top ghost gaps) ----------------------
st.markdown("""
<style>
/* Hide Streamlit chrome we don't want */
div[data-testid="stDecoration"],
header [data-testid="stDecoration"],
section[data-testid="stDecoration"],
div[data-testid="stHeader"], header, div[data-testid="stToolbar"],
div[class*="viewerBadge_"], a[data-testid="viewer-badge"],
button[kind="header"], div[data-testid="stStatusWidget"] { display:none !important; }

/* Remove mysterious top spacing */
html, body { margin:0 !important; padding:0 !important; }
div[data-testid="stAppViewContainer"] { padding-top:0 !important; margin-top:0 !important; }
div[data-testid="stAppViewContainer"] > .main { padding-top:0 !important; padding-bottom:1.25rem !important; }
.block-container { padding-top:0 !important; }

/* Card helpers */
.card {
  background: var(--background-color, #fff);
  border-radius: 16px;
  padding: 20px 20px 16px;
  box-shadow: 0 8px 24px rgba(0,0,0,.06);
}
.badge {
  display:inline-block; padding:.25rem .6rem; border-radius:999px; font-size:.85rem;
  background:#eef2ff; color:#3730a3; font-weight:600;
}
.badge-low    { background:#ecfdf5; color:#065f46; }
.badge-mid    { background:#fffbeb; color:#92400e; }
.badge-high   { background:#fef2f2; color:#991b1b; }
.subtle { color:rgba(0,0,0,.6); }

/* Center the login card perfectly */
.full-center {
  min-height: 100vh;
  display:flex; align-items:center; justify-content:center;
}
.auth-card { width:min(94vw, 420px); }
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 LOGOWANIE ----------------------
def check_access() -> bool:
    ACCESS_CODE = st.secrets.get("ACCESS_CODE") or os.environ.get("ACCESS_CODE")
    if not ACCESS_CODE:
        st.error("Brak ustawionego ACCESS_CODE w Secrets/ENV.")
        st.stop()

    if st.session_state.get("auth_ok", False):
        return True

    # Centered login card
    with st.container():
        st.markdown('<div class="full-center">', unsafe_allow_html=True)
        st.markdown('<div class="card auth-card">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:56px; line-height:1; user-select:none; text-align:center;">🧠</div>', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-top:6px;'>Szacowanie ryzyka cech napadów</h3>", unsafe_allow_html=True)
        st.markdown("<p class='subtle' style='text-align:center; margin:-6px 0 12px'>Wpisz kod dostępu, aby kontynuować</p>", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            code = st.text_input("Kod dostępu", type="password", label_visibility="collapsed")
            colA, colB = st.columns([1,1])
            with colA: pass
            with colB:
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
@st.cache_data(show_spinner=False)
def load_survey(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

survey = load_survey("survey.json")
paths = {p["id"]: p for p in survey["paths"]}
path_labels = {p["label"]: p["id"] for p in survey["paths"]}

# ---------------------- 🧭 SESSION STATE ----------------------
def _init_state():
    st.session_state.setdefault("chosen_path_id", None)
    st.session_state.setdefault("step", 0)              # question index
    st.session_state.setdefault("responses", {})        # {q_id: "tak/nie/nie wiem" or option label}
    st.session_state.setdefault("finished", False)

_init_state()

# ---------------------- 🧠 SIDEBAR ----------------------
with st.sidebar:
    st.success("Zalogowano ✅")
    if st.button("Wyloguj"):
        st.session_state.auth_ok = False
        st.rerun()

    st.header("Wybór ścieżki")
    chosen_label = st.radio("Typ incydentu:", list(path_labels.keys()),
                            index= list(path_labels.keys()).index(next(iter(path_labels))) if st.session_state.chosen_path_id is None else
                                   list(path_labels.keys()).index([k for k,v in path_labels.items() if v==st.session_state.chosen_path_id][0]))
    new_path_id = path_labels[chosen_label]

    # If path changed, reset wizard
    if new_path_id != st.session_state.chosen_path_id:
        st.session_state.chosen_path_id = new_path_id
        st.session_state.step = 0
        st.session_state.responses = {}
        st.session_state.finished = False

# ---------------------- 🧩 WIZARD UTILS ----------------------
def tri_widget(key, label, value=None):
    return st.selectbox(
        label,
        ["nie", "tak", "nie wiem"],
        key=key,
        index={"nie":0, "tak":1, "nie wiem":2}.get(value, 0)
    )

def handle_question(q, existing_value):
    qtype = q["type"]
    if qtype == "tri":
        return tri_widget(q["id"], q["text"], existing_value)
    elif qtype == "select":
        labels = [opt["label"] for opt in q["options"]]
        default_idx = 0
        if existing_value in labels:
            default_idx = labels.index(existing_value)
        return st.selectbox(q["text"], labels, index=default_idx, key=q["id"])
    else:
        st.warning(f"Nieznany typ pytania: {qtype}")
        return None

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

# ---------------------- 🖥️ MAIN VIEW ----------------------
path = paths[st.session_state.chosen_path_id]
questions = path["questions"]
total_steps = len(questions)

st.markdown("### 🧠 Szacowanie ryzyka cech napadów – DEMO")
st.caption("Narzędzie edukacyjne. Nie służy do diagnozy. W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112.")

# Progress
if not st.session_state.finished and total_steps > 0:
    progress = (st.session_state.step) / total_steps
    st.progress(progress, text=f"Krok {st.session_state.step} z {total_steps}")

st.divider()

# ---------------------- 🔄 WIZARD: QUESTIONS ----------------------
if not st.session_state.finished:

    if total_steps == 0:
        st.info("Dla tej ścieżki nie zdefiniowano pytań.")
    else:
        idx = st.session_state.step
        if idx == 0:
            st.markdown(f"<span class='badge'>Ścieżka: {path['label']}</span>", unsafe_allow_html=True)

        if idx < total_steps:
            q = questions[idx]
            with st.container():
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.subheader(f"Pytanie {idx+1} z {total_steps}")
                existing = st.session_state.responses.get(q["id"])
                ans = handle_question(q, existing)

                # Navigation buttons
                col_prev, col_sp, col_next = st.columns([1,6,2])
                with col_prev:
                    if st.button("← Wstecz", use_container_width=True, disabled=(idx == 0)):
                        st.session_state.step = max(0, idx-1)
                        st.rerun()
                with col_next:
                    label = "Zakończ" if idx == total_steps-1 else "Dalej →"
                    if st.button(label, use_container_width=True):
                        # Save response
                        if ans is not None:
                            st.session_state.responses[q["id"]] = ans
                        # Move forward or finish
                        if idx < total_steps-1:
                            st.session_state.step = idx+1
                        else:
                            st.session_state.finished = True
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

            # Quick save exit
            with st.expander("Opcje zapisu"):
                st.write("Twoje odpowiedzi są zapisywane w bieżącej sesji.")
                if st.button("Wyczyść odpowiedzi i zacznij od nowa"):
                    st.session_state.responses = {}
                    st.session_state.step = 0
                    st.session_state.finished = False
                    st.rerun()

        else:
            # Safety: if step somehow overshoots
            st.session_state.finished = True
            st.rerun()

# ---------------------- ✅ RESULTS ----------------------
if st.session_state.finished:
    score, max_score, prob = compute_score_and_prob(path, st.session_state.responses)
    level, level_class = risk_label(prob)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Wynik (DEMO)")
    st.markdown(f"<span class='badge {level_class}'>Poziom ryzyka: {level}</span>", unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Szacowane ryzyko", f"{prob*100:.0f}%")
    with c2:
        st.metric("Suma punktów", f"{score:.1f} / {max_score:.1f}")
    with c3:
        st.metric("Ścieżka", path["label"])

    st.markdown("#### Rekomendacje (informacyjne)")
    if prob >= 0.7:
        st.warning("Wysokie ryzyko cech napadu. Skontaktuj się niezwłocznie z lekarzem lub służbami ratunkowymi (112) w przypadku niepokojących objawów.")
    elif prob >= 0.3:
        st.info("Umiarkowane ryzyko. Rozważ konsultację lekarską i obserwację objawów.")
    else:
        st.success("Niskie ryzyko na podstawie udzielonych odpowiedzi. W razie wątpliwości skontaktuj się z lekarzem.")

    # Download summary
    result_payload = {
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
        data=json.dumps(result_payload, ensure_ascii=False, indent=2),
        file_name=f"wynik_{path['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True
    )

    col_again1, col_again2 = st.columns([1,1])
    with col_again1:
        if st.button("Wypełnij ponownie", use_container_width=True):
            st.session_state.step = 0
            st.session_state.responses = {}
            st.session_state.finished = False
            st.rerun()
    with col_again2:
        if st.button("Zmień ścieżkę", use_container_width=True):
            st.session_state.step = 0
            st.session_state.responses = {}
            st.session_state.finished = False
            # keep chosen_path_id; user can switch in sidebar
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Wersja: " + survey["meta"]["version"])
