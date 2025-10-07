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

# ---------------------- ✨ GLOBALNY, RESPONSYWNY STYL ----------------------
st.markdown("""
<style>
:root { --radius: 16px; }
div[data-testid="stAppViewContainer"] .block-container { padding-top: 16px; padding-bottom: 28px; }
.stButton>button, .stDownloadButton>button { border-radius: var(--radius); font-weight: 700; padding: 0.8rem 1rem; }
.stAlert { border-radius: var(--radius); }
.stProgress > div > div > div { border-radius: 999px; }
.step-chip { display:inline-flex; align-items:center; gap:.5rem; padding:.25rem .7rem; border-radius:999px; background:rgba(0,0,0,.06); font-size:.85rem; }
.q-card { border:1px solid rgba(0,0,0,.08); border-radius: var(--radius); padding: 18px; box-shadow: 0 8px 24px rgba(0,0,0,.04); background: var(--background-color); }
.q-title { font-size:1.05rem; font-weight:700; margin-bottom:.25rem; }
.q-help { opacity:.8; font-size:.9rem; margin-bottom:.75rem; }
.btn-grid { display:grid; grid-template-columns: 1fr; gap:10px; }
@media (min-width: 520px){ .btn-grid{ grid-template-columns: repeat(3, 1fr);} }
.choice-btn { width:100%; height:58px; border-radius: var(--radius); font-weight:800; }
.navbar { display:flex; gap:10px; justify-content:space-between; margin-top:8px; }
.navbar > * { flex: 1; }
hr { margin: 8px 0 4px 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------- 🔒 LOGOWANIE (NIE ZMIENIAMY – JAK WYSŁAŁAŚ) ----------------------
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

# ---------------------- 🔁 Wylogowanie ----------------------
st.sidebar.success("Zalogowano ✅")
if st.sidebar.button("Wyloguj"):
    st.session_state.auth_ok = False

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
    st.error("Nie znaleziono pliku survey.json. Upewnij się, że plik istnieje w katalogu aplikacji.", icon="🚫")
    st.stop()

paths: Dict[str, Dict[str, Any]] = {p["id"]: p for p in survey["paths"]}
path_labels: Dict[str, str] = {p["label"]: p["id"] for p in survey["paths"]}

# ---------------------- 🧭 STAN SESJI ----------------------
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
    st.sidebar.info("Wynik został obliczony. Aby rozpocząć nowy przebieg, kliknij „Zacznij od nowa”.")
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

# ---------------------- 🧱 NAGŁÓWEK ŚCIEŻKI ----------------------
label_text = [k for k,v in path_labels.items() if v==st.session_state.selected_path_id][0]
st.header(f"Ścieżka: {label_text}")
if nq == 0:
    st.warning("Brak pytań w tej ścieżce.")
else:
    q_idx = st.session_state.current_q_idx
    st.progress(int((q_idx / nq) * 100))
    st.markdown(f'<span class="step-chip">Pytanie {q_idx + 1} z {nq}</span>', unsafe_allow_html=True)

# ---------------------- 🗳️ NOWOCZESNY, DOTYKOWY WYBÓR ----------------------
def _render_choice_buttons(options: List[str], qid: str):
    # Siatka 3 przycisków – pełna szerokość na mobile, 3 kolumny na desktopie
    st.markdown('<div class="btn-grid">', unsafe_allow_html=True)
    cols = st.columns(3) if len(options) == 3 else st.columns(len(options))
    clicked_val = None
    for i, opt in enumerate(options):
        with cols[i]:
            if st.button(opt.capitalize(), key=f"btn_{qid}_{opt}", use_container_width=True, type="primary" if opt=="tak" else "secondary"):
                clicked_val = opt
    st.markdown('</div>', unsafe_allow_html=True)
    return clicked_val

# ---------------------- 🎛️ PRZEPŁYW – JEDNO PYTANIE NA EKRANIE ----------------------
if not st.session_state.finished and nq > 0:
    q = questions[q_idx]
    with st.container():
        st.markdown('<div class="q-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="q-title">{q["text"]}</div>', unsafe_allow_html=True)

        answer_clicked = None
        if q["type"] == "tri":
            # nowoczesny wybór: duże przyciski
            answer_clicked = _render_choice_buttons(["nie", "tak", "nie wiem"], q["id"])
        elif q["type"] == "select":
            # select – też nowocześnie, pełna szerokość
            labels = [opt["label"] for opt in q.get("options", [])]
            val = st.selectbox("",
                               ["-- wybierz --"] + labels,
                               index=0,
                               key=f"sel_{q['id']}")
            if val != "-- wybierz --":
                answer_clicked = val

        # Nawigacja – wróć (tylko przed zakończeniem)
        st.markdown('<div class="navbar">', unsafe_allow_html=True)
        prev_col, next_col = st.columns(2)
        with prev_col:
            if st.button("◀ Poprzednie", use_container_width=True, disabled=(q_idx == 0)):
                st.session_state.current_q_idx -= 1
                st.rerun()
        with next_col:
            # „Dalej” aktywne tylko jeśli mamy odpowiedź (dla select) – dla tri niepotrzebne, bo klik przenosi od razu
            need_next = (q["type"] == "select")
            st.button("Dalej ▶", use_container_width=True, disabled=need_next and (answer_clicked is None), key="next_btn_dummy")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # logika: kliknięcie odpowiedzi zapisuje i przechodzi dalej
    if answer_clicked is not None:
        st.session_state.answers[q["id"]] = answer_clicked
        if q_idx + 1 >= nq:
            score, max_score, prob = compute_scores(st.session_state.answers, path)
            st.session_state.result = {"score": score, "max_score": max_score, "prob": prob}
            st.session_state.finished = True  # 🔒 blokada edycji po zakończeniu
            st.rerun()
        else:
            st.session_state.current_q_idx += 1
            st.rerun()

st.divider()

# ---------------------- 📊 WYNIK – BEZ MOŻLIWOŚCI EDYCJI ----------------------
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

    # Podsumowanie (read-only) + eksport JSON
    with st.expander("Zobacz podsumowanie (read-only)"):
        pretty = {
            "path_label": label_text,
            "version": survey["meta"].get("version", "unknown"),
            "responses": st.session_state.answers,  # tylko do wglądu
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

    # Tylko restart – brak edycji odpowiedzi po zakończeniu
    if st.button("🔁 Zacznij od nowa"):
        st.session_state.current_q_idx = 0
        st.session_state.answers = {}
        st.session_state.finished = False
        st.session_state.result = None
        st.rerun()

st.caption("Wersja: " + survey["meta"].get("version", "unknown"))
