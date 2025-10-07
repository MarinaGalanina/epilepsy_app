
import json
import numpy as np
import streamlit as st

st.set_page_config(page_title="Ryzyko cech napadu (DEMO)", page_icon="🧠")
st.title("🧠 Szacowanie ryzyka cech napadów – DEMO")
st.caption("Narzędzie edukacyjne. Nie służy do diagnozy. W razie niepokojących objawów skontaktuj się z lekarzem lub dzwoń na 112.")

@st.cache_data
def load_survey(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

survey = load_survey("survey.json")

paths = {p["id"]: p for p in survey["paths"]}
path_labels = {p["label"]: p["id"] for p in survey["paths"]}

st.sidebar.header("Wybór ścieżki (typ incydentu)")
chosen_label = st.sidebar.radio("Typ incydentu:", list(path_labels.keys()))
path_id = path_labels[chosen_label]
path = paths[path_id]

st.header(f"Ścieżka: {chosen_label}")
st.write("Odpowiedz na poniższe pytania. Jeśli nie jesteś pewna/pewien, wybierz „nie wiem”.")

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
        # Max score is weight_yes
        max_score += float(q.get("weight_yes", 0))
        if ans == "tak":
            score += float(q.get("weight_yes", 0))
        elif ans == "nie wiem":
            score += float(q.get("weight_maybe", 0))
        # else: +0
    elif qtype == "select":
        labels = [opt["label"] for opt in q["options"]]
        ans = st.selectbox(q["text"], labels, key=q["id"])
        responses[q["id"]] = ans
        # Max score is the maximum option weight
        opt_weights = [float(opt.get("weight", 0)) for opt in q["options"]]
        max_score += max(opt_weights) if opt_weights else 0.0
        # Add chosen option weight
        for opt in q["options"]:
            if opt["label"] == ans:
                score += float(opt.get("weight", 0))
                break

for q in path["questions"]:
    handle_question(q)

st.divider()

if max_score == 0:
    prob = 0.0
else:
    # Pseudo-probability via logistic transform to keep 0–100 range smooth
    ratio = score / max_score  # 0..1
    logit = (ratio - 0.5) * 6.0  # scale
    prob = 1.0 / (1.0 + np.exp(-logit))

st.subheader("Wynik (DEMO)")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Szacowane ryzyko", f"{prob*100:.0f}%")
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


