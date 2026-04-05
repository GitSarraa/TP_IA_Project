"""
app.py — TravelMind : Interface Streamlit Premium
Agent IA Planificateur de Voyage (ReAct + Chain of Thought)
"""
import streamlit as st
import json, time, re
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="TravelMind AI", page_icon="✈️",
                   layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS — définis EN PREMIER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_json_safe(raw: str) -> dict | list | None:
    """Parse JSON en nettoyant les blocs ```json``` si présents."""
    if not raw:
        return None
    text = raw.strip()
    # Supprimer les balises ```json ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        return None


def parse_weather(raw: str):
    """Retourne (cards_html, df_list). Robuste même si format varie."""
    emoji_map = {
        "très ensoleillé": "🌞", "ensoleillé": "☀️", "soleil": "☀️", "clair": "🌤️",
        "partiellement nuageux": "⛅", "nuageux": "🌥️", "couvert": "☁️",
        "légère pluie": "🌦️", "pluie": "🌧️", "averse": "🌦️",
        "orage": "⛈️", "orageux": "⛈️", "neige": "❄️", "brouillard": "🌫️",
    }
    lines = [l for l in raw.split("\n") if l.strip() and not l.startswith("[")]
    df_list, cards = [], []

    for line in lines[:14]:
        try:
            idx = line.index(":")
            date_str = line[:idx].strip()
            rest     = line[idx+1:].strip()

            tmin = int(m.group(1)) if (m := re.search(r"min\s*([-\d]+)", rest)) else None
            tmax = int(m.group(1)) if (m := re.search(r"max\s*([-\d]+)", rest)) else None
            hum  = m.group(1) if (m := re.search(r"humidité\s*(\d+)%", rest)) else "?"
            desc = rest.split(",")[0].strip()

            emoji = "🌤️"
            for k in sorted(emoji_map, key=len, reverse=True):
                if k in desc.lower():
                    emoji = emoji_map[k]; break

            try:
                label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%a %d/%m")
            except Exception:
                label = date_str

            cards.append(f"""
<div class="wcard">
  <div class="wdate">{label}</div>
  <div class="wemoji">{emoji}</div>
  <div class="wtemp">{tmax if tmax is not None else "?"}° / {tmin if tmin is not None else "?"}°</div>
  <div class="wdesc">{desc[:28]}</div>
  <div class="wdetail">💧 {hum}%</div>
</div>""")

            if tmin is not None and tmax is not None:
                df_list.append({"date": label, "tmin": tmin, "tmax": tmax})
        except Exception:
            continue

    html = '<div class="weather-row">' + "".join(cards) + "</div>" if cards else ""
    return html, df_list


def render_step(s: dict) -> str:
    t = s.get("type","")
    i = s.get("iteration","?")
    if t == "FINISH":
        return (f'<div class="scard sfinish"><span class="slabel">✅ ÉTAPE {i} — FINISH</span>'
                f'<div class="scontent">{s.get("content","Itinéraire généré")}</div></div>')
    elif t == "REACT":
        obs = (s.get("observation") or "")[:250]
        return (f'<div class="scard sthought"><span class="slabel">💭 THOUGHT — Étape {i}</span>'
                f'<div class="scontent">{s.get("thought","")}</div></div>'
                f'<div class="scard saction"><span class="slabel">⚡ ACTION</span>'
                f'<code class="stool">{s.get("action","")}</code>'
                f'<div class="scontent mono">Input: {s.get("input","")}</div></div>'
                f'<div class="scard sobs"><span class="slabel">👁️ OBSERVATION</span>'
                f'<div class="scontent">{obs}{"…" if len(s.get("observation",""))>250 else ""}</div></div>')
    else:
        return (f'<div class="scard sthought"><span class="slabel">💭 THOUGHT</span>'
                f'<div class="scontent">{s.get("thought","")}</div></div>')


# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;600&display=swap');
html,body,[data-testid="stAppViewContainer"]{background:#080c1a!important}
[data-testid="stAppViewContainer"]>.main{
  background:linear-gradient(135deg,#080c1a 0%,#0d1526 60%,#080c1a 100%)!important;
  font-family:'DM Sans',sans-serif}
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#0a0f1e,#0d1530)!important;
  border-right:1px solid rgba(255,215,0,.15)!important}
[data-testid="stSidebar"] *{color:#e8eaf6!important}
[data-testid="stSidebar"] label{color:rgba(180,200,255,.8)!important;font-size:.85rem!important}

/* Hero */
.hero{background:linear-gradient(135deg,#0d1530,#1a2545,#0d1530);
  border:1px solid rgba(255,215,0,.2);border-radius:20px;
  padding:2.5rem 3rem;text-align:center;margin-bottom:1.5rem}
.hero h1{font-family:'Playfair Display',serif;font-size:3rem;font-weight:900;margin:0;
  background:linear-gradient(135deg,#ffd700,#fff8dc,#ffd700);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero p{color:rgba(180,200,255,.75);font-size:1rem;margin:.4rem 0 1rem;
  text-transform:uppercase;letter-spacing:2px}
.badges{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.badge{background:rgba(255,215,0,.08);border:1px solid rgba(255,215,0,.25);
  color:#ffd700;padding:3px 14px;border-radius:50px;font-size:.76rem;font-weight:600;letter-spacing:1px}

/* Métriques */
.mgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem}
.mcard{background:linear-gradient(135deg,#0d1530,#131f40);border:1px solid rgba(255,215,0,.12);
  border-radius:14px;padding:1.2rem;text-align:center;transition:.2s}
.mcard:hover{transform:translateY(-3px);border-color:rgba(255,215,0,.35)}
.mnum{font-family:'Playfair Display',serif;font-size:2rem;color:#ffd700;font-weight:700;line-height:1}
.mlabel{color:rgba(180,200,255,.55);font-size:.75rem;text-transform:uppercase;letter-spacing:1.5px;margin-top:.3rem}
.micon{font-size:1.5rem;margin-bottom:.4rem}

/* Section title */
.stitle{font-family:'Playfair Display',serif;font-size:1.4rem;color:#e2e8f0;
  margin:1.5rem 0 1rem;display:flex;align-items:center;gap:10px}
.stitle::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,rgba(255,215,0,.3),transparent)}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;
  border-radius:12px;padding:4px;gap:4px;border:1px solid rgba(255,215,0,.1)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:rgba(180,200,255,.5)!important;
  border-radius:8px!important;font-family:'DM Sans',sans-serif!important;
  font-size:.87rem!important;padding:8px 18px!important;border:none!important}
.stTabs [aria-selected="true"]{background:rgba(255,215,0,.14)!important;color:#ffd700!important}

/* Buttons */
.stButton>button{background:linear-gradient(135deg,#ffd700,#f59e0b)!important;
  color:#080c1a!important;font-weight:700!important;border:none!important;
  border-radius:12px!important;padding:.65rem 1.8rem!important;
  font-family:'DM Sans',sans-serif!important;transition:.2s!important}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 25px rgba(255,215,0,.3)!important}

/* Inputs */
.stTextInput>div>div>input,.stTextArea>div>div>textarea{
  background:rgba(255,255,255,.05)!important;border:1px solid rgba(255,215,0,.2)!important;
  border-radius:10px!important;color:#e2e8f0!important}
.stSelectbox>div>div{background:rgba(255,255,255,.05)!important;
  border:1px solid rgba(255,215,0,.2)!important;border-radius:10px!important}

/* Météo */
.weather-row{display:flex;gap:.7rem;flex-wrap:wrap;padding:.5rem 0}
.wcard{min-width:115px;background:linear-gradient(180deg,#0d1530,#131f40);
  border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:1rem;text-align:center;flex-shrink:0}
.wdate{font-size:.7rem;color:rgba(180,200,255,.5);text-transform:uppercase;letter-spacing:1px}
.wemoji{font-size:1.9rem;margin:.4rem 0}
.wtemp{font-family:'Playfair Display',serif;font-size:1.25rem;color:#ffd700;font-weight:700}
.wdesc{font-size:.73rem;color:rgba(180,200,255,.6);margin-top:.2rem}
.wdetail{font-size:.7rem;color:rgba(180,200,255,.4);margin-top:.15rem}

/* Activités grid */
.agrid{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-top:1rem}
.acard{background:linear-gradient(135deg,#0d1530,#131f40);border:1px solid rgba(255,255,255,.08);
  border-radius:14px;padding:1.2rem;transition:.2s}
.acard:hover{transform:translateY(-3px);border-color:rgba(255,215,0,.3)}
.aemoji{font-size:1.9rem}
.aname{font-weight:600;color:#e2e8f0;margin:.4rem 0 .2rem;font-size:.93rem}
.adesc{font-size:.8rem;color:rgba(180,200,255,.6);line-height:1.5}
.aconseil{font-size:.77rem;color:rgba(255,215,0,.6);margin-top:.5rem;font-style:italic}
.atags{display:flex;gap:5px;margin-top:.6rem;flex-wrap:wrap}
.tag{font-size:.68rem;padding:2px 8px;border-radius:50px;font-weight:600}
.tg{background:rgba(52,211,153,.12);color:#34d399;border:1px solid rgba(52,211,153,.25)}
.tb{background:rgba(96,165,250,.12);color:#60a5fa;border:1px solid rgba(96,165,250,.25)}
.tt{background:rgba(251,191,36,.12);color:#fbbf24;border:1px solid rgba(251,191,36,.25)}

/* Tips grid */
.tgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:.8rem;margin-top:1rem}
.tcard{background:linear-gradient(135deg,#0d1530,#131f40);border:1px solid rgba(255,255,255,.07);
  border-radius:12px;padding:1rem 1.2rem}
.ttitle{font-size:.75rem;color:rgba(180,200,255,.5);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:.35rem}
.tval{color:#e2e8f0;font-size:.88rem;line-height:1.5}

/* Gastro */
.gcard{background:linear-gradient(135deg,#0d1530,#131f40);border:1px solid rgba(255,255,255,.07);
  border-radius:14px;padding:1.2rem;margin-bottom:.9rem}

/* Itinéraire */
.itin{background:linear-gradient(135deg,#0a0f1e,#0d1530);border:1px solid rgba(255,255,255,.06);
  border-radius:16px;padding:2rem}
.itin h1,.itin h2,.itin h3{color:#ffd700!important}
.itin p,.itin li{color:#cbd5e1;line-height:1.8}

/* ReAct steps */
.scard{border-radius:10px;padding:.9rem 1.2rem;margin-bottom:.7rem;border-left:4px solid}
.sthought{background:rgba(96,165,250,.07);border-left-color:#60a5fa}
.saction{background:rgba(251,191,36,.07);border-left-color:#fbbf24}
.sobs{background:rgba(52,211,153,.07);border-left-color:#34d399}
.sfinish{background:rgba(167,139,250,.08);border-left-color:#a78bfa}
.slabel{font-size:.7rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;display:block;margin-bottom:.35rem}
.scontent{font-size:.88rem;color:#cbd5e1;line-height:1.6}
.stool{background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.25);color:#fbbf24;
  padding:2px 10px;border-radius:50px;font-size:.78rem;display:inline-block;margin-bottom:.3rem}
.mono{font-family:monospace;font-size:.8rem!important}

/* Chat */
.chat-box{background:linear-gradient(135deg,#0a0f1e,#0d1530);border:1px solid rgba(255,215,0,.12);
  border-radius:16px;padding:1.4rem;margin-bottom:1rem}
.chat-u{background:rgba(255,215,0,.07);border:1px solid rgba(255,215,0,.18);
  border-radius:12px 12px 4px 12px;padding:.75rem 1rem;margin:.5rem 0 .5rem auto;
  color:#ffd700;font-size:.88rem;max-width:80%;text-align:right}
.chat-a{background:rgba(96,165,250,.07);border:1px solid rgba(96,165,250,.18);
  border-radius:12px 12px 12px 4px;padding:.75rem 1rem;margin:.5rem 0;
  color:#cbd5e1;font-size:.88rem;max-width:80%}
.chat-who{font-size:.68rem;color:rgba(180,200,255,.4);letter-spacing:1px;font-weight:700;margin-bottom:.2rem}

/* Scrollbar */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-thumb{background:rgba(255,215,0,.3);border-radius:2px}

/* Info/warning overrides */
.stAlert{border-radius:10px!important}
</style>
""", unsafe_allow_html=True)

# ── Imports métier ─────────────────────────────────────────────────────────────
from agents.travel_agent import run_cot_phase, run_react_loop, run_followup
from utils.pdf_export import generate_pdf
from utils.llm_provider import get_provider_info

# ── Session state ──────────────────────────────────────────────────────────────
for k,v in {"result":None,"cot":None,"steps":[],"convo":[],"followup_txt":"",
             "gen_time":None,"dest":"","days":5,"travelers":2,
             "interests":["Culture & Musées","Gastronomie"],"budget":"50-100€ (Modéré)"}.items():
    if k not in st.session_state: st.session_state[k]=v

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    pinfo = get_provider_info()
    st.markdown(f"""
    <div style="text-align:center;padding:1.2rem 0 .8rem">
      <div style="font-family:'Playfair Display',serif;font-size:1.9rem;font-weight:900;
           background:linear-gradient(135deg,#ffd700,#fff8dc);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent">✈ TravelMind</div>
      <div style="color:rgba(180,200,255,.45);font-size:.7rem;letter-spacing:2px;text-transform:uppercase;margin-top:3px">Agent IA Planificateur</div>
    </div>
    <div style="background:rgba(255,215,0,.05);border:1px solid rgba(255,215,0,.15);
         border-radius:10px;padding:.65rem 1rem;margin-bottom:1rem;text-align:center">
      <div style="font-size:.68rem;color:rgba(180,200,255,.4);text-transform:uppercase;letter-spacing:1px">Modèle actif</div>
      <div style="color:#ffd700;font-weight:600;font-size:.85rem;margin-top:2px">{pinfo['icon']} {pinfo['name']}</div>
    </div>
    <hr style="border:none;border-top:1px solid rgba(255,215,0,.1);margin:.8rem 0">
    """, unsafe_allow_html=True)

    st.markdown("### 🗺️ Paramètres")
    dest = st.text_input("📍 Destination", value=st.session_state.dest or "Tokyo, Japon")
    c1,c2 = st.columns(2)
    with c1: days = st.number_input("📅 Jours", 1, 30, st.session_state.days)
    with c2: travelers = st.number_input("👥 Pers.", 1, 20, st.session_state.travelers)
    interests = st.multiselect("🎯 Intérêts",
        ["Culture & Musées","Gastronomie","Nature","Plages","Architecture",
         "Nightlife","Shopping","Sport","Histoire","Art","Bien-être","Famille","Romantique"],
        default=st.session_state.interests)
    budget = st.select_slider("💰 Budget/pers/jour",
        ["<50€ (Éco)","50-100€ (Modéré)","100-200€ (Confort)",">200€ (Luxe)"],
        value=st.session_state.budget)
    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,.05);margin:.8rem 0'>",
                unsafe_allow_html=True)
    show_react = st.toggle("🔍 Trace ReAct en direct", value=True)
    show_cot   = st.toggle("🧠 Afficher raisonnement CoT", value=True)
    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,.05);margin:.8rem 0'>",
                unsafe_allow_html=True)
    go_btn = st.button("🚀 Lancer la planification", use_container_width=True)
    if st.session_state.result:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Nouveau voyage", use_container_width=True):
            for k in ["result","cot","steps","convo","gen_time"]:
                st.session_state[k] = None if k not in ["steps","convo"] else []
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# HERO + MÉTRIQUES
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <h1>✈ TravelMind</h1>
  <p>Agent IA Planificateur de Voyage Autonome</p>
  <div class="badges">
    <span class="badge">⚡ ReAct</span>
    <span class="badge">🧠 Chain of Thought</span>
    <span class="badge">🛠️ 4 Outils</span>
    <span class="badge">💬 Conversation</span>
    <span class="badge">📄 PDF</span>
  </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.result:
    r = st.session_state.result
    n_react = sum(1 for s in r.get("steps",[]) if s.get("type")=="REACT")
    gt = st.session_state.gen_time or 0
    st.markdown(f"""<div class="mgrid">
      <div class="mcard"><div class="micon">📍</div><div class="mnum">{st.session_state.days}</div><div class="mlabel">Jours planifiés</div></div>
      <div class="mcard"><div class="micon">🔄</div><div class="mnum">{n_react}</div><div class="mlabel">Actions ReAct</div></div>
      <div class="mcard"><div class="micon">⏱️</div><div class="mnum">{gt:.0f}s</div><div class="mlabel">Temps génération</div></div>
      <div class="mcard"><div class="micon">💬</div><div class="mnum">{len(st.session_state.convo)//2}</div><div class="mlabel">Échanges</div></div>
    </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION
# ═══════════════════════════════════════════════════════════════════════════════
if go_btn:
    if not dest:
        st.error("⚠️ Saisissez une destination.")
    else:
        # Sauvegarder
        st.session_state.update(dest=dest, days=days, travelers=travelers,
                                interests=interests, budget=budget,
                                steps=[], convo=[], result=None)

        # Phase CoT
        if show_cot:
            st.markdown('<div class="stitle">🧠 Phase 1 — Chain of Thought</div>', unsafe_allow_html=True)
            with st.spinner("Décomposition du problème..."):
                cot = run_cot_phase(dest, days, travelers, interests, budget)
            st.session_state.cot = cot
            with st.expander("📋 Voir l'analyse complète", expanded=True):
                st.markdown(f'<div style="color:#cbd5e1;line-height:1.8;font-size:.9rem">{cot}</div>',
                            unsafe_allow_html=True)
        else:
            with st.spinner("Analyse..."):
                cot = run_cot_phase(dest, days, travelers, interests, budget)
            st.session_state.cot = cot

        # Phase ReAct
        st.markdown('<div class="stitle">⚡ Phase 2 — Boucle ReAct</div>', unsafe_allow_html=True)
        ph = st.empty()
        live_steps = []

        def cb(step):
            live_steps.append(step)
            st.session_state.steps = list(live_steps)
            if show_react:
                ph.markdown("".join(render_step(s) for s in live_steps), unsafe_allow_html=True)

        t0 = time.time()
        with st.spinner("🌍 L'agent planifie..."):
            result = run_react_loop(dest, days, travelers, interests, budget, cot, callback=cb)

        st.session_state.gen_time = time.time() - t0
        st.session_state.result   = result
        st.session_state.convo    = [
            {"role":"user",    "content": f"Planifie {dest} pour {days} jours."},
            {"role":"assistant","content": result.get("itinerary","")[:400]},
        ]
        st.success(f"✅ Terminé en {st.session_state.gen_time:.1f}s !")
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# RÉSULTATS
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.result:
    r    = st.session_state.result
    dest = st.session_state.dest
    days = st.session_state.days
    trav = st.session_state.travelers
    bud  = st.session_state.budget
    ints = st.session_state.interests

    tabs = st.tabs(["🗓️ Itinéraire","🌤️ Météo","🎯 Activités",
                    "🍽️ Gastronomie","📋 Conseils","🧠 Raisonnement",
                    "💬 Conversation","📄 Export PDF"])

    # ── 0 ITINÉRAIRE ──────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown('<div class="stitle">🗓️ Votre Itinéraire</div>', unsafe_allow_html=True)
        itin = r.get("itinerary","")
        if itin:
            st.markdown('<div class="itin">', unsafe_allow_html=True)
            st.markdown(itin)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Itinéraire non généré — relancez la planification.")

    # ── 1 MÉTÉO ───────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown('<div class="stitle">🌤️ Prévisions Météo</div>', unsafe_allow_html=True)
        wraw = r.get("weather_data","")
        if not wraw:
            st.warning("Données météo manquantes.")
        else:
            cards_html, df_list = parse_weather(wraw)
            if cards_html:
                st.markdown(cards_html, unsafe_allow_html=True)
            else:
                st.info("Format météo non reconnu — données brutes :")
                st.code(wraw)

            if df_list:
                df = pd.DataFrame(df_list)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["date"], y=df["tmax"], name="Max",
                    line=dict(color="#ffd700",width=3), mode="lines+markers",
                    marker=dict(size=9,color="#ffd700")))
                fig.add_trace(go.Scatter(x=df["date"], y=df["tmin"], name="Min",
                    line=dict(color="#60a5fa",width=2,dash="dot"), mode="lines+markers",
                    marker=dict(size=6,color="#60a5fa"),
                    fill="tonexty", fillcolor="rgba(96,165,250,0.07)"))
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,21,48,0.5)",
                    font=dict(color="#cbd5e1"), legend=dict(bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(gridcolor="rgba(255,255,255,.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,.05)",title="°C"),
                    margin=dict(t=10,b=30,l=30,r=10), height=280)
                st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("🔍 Données brutes", expanded=False):
                st.code(wraw)

    # ── 2 ACTIVITÉS ───────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown('<div class="stitle">🎯 Activités Recommandées</div>', unsafe_allow_html=True)
        araw = r.get("activities_data","")
        if not araw:
            st.warning("Données activités manquantes.")
        else:
            adata = parse_json_safe(araw)
            if adata is None:
                st.error("Impossible de lire les activités (JSON invalide).")
                st.code(araw[:500])
            else:
                acts = adata.get("activites", []) if isinstance(adata, dict) else []
                if not acts:
                    st.info("Aucune activité dans la réponse.")
                    st.code(araw[:300])
                else:
                    # Filtres
                    all_types = sorted({a.get("type","autre") for a in acts})
                    all_couts = sorted({a.get("cout","?") for a in acts})
                    cf1, cf2 = st.columns(2)
                    with cf1:
                        f_type = st.multiselect("Filtrer par type", all_types, key="ftype")
                    with cf2:
                        f_cout = st.multiselect("Filtrer par budget", all_couts, key="fcout")
                    filtered = [a for a in acts
                                if (not f_type or a.get("type") in f_type)
                                and (not f_cout or a.get("cout") in f_cout)]
                    st.markdown(f"**{len(filtered)} activité(s) affichée(s)**")
                    html = '<div class="agrid">'
                    for a in filtered:
                        html += f"""<div class="acard">
                          <div class="aemoji">{a.get('emoji','🏙️')}</div>
                          <div class="aname">{a.get('nom','')}</div>
                          <div class="adesc">{a.get('description','')}</div>
                          <div class="aconseil">💡 {a.get('conseil','')}</div>
                          <div class="atags">
                            <span class="tag tg">{a.get('cout','')}</span>
                            <span class="tag tb">⏱ {a.get('duree','')}</span>
                            <span class="tag tt">{a.get('type','')}</span>
                          </div></div>"""
                    html += '</div>'
                    st.markdown(html, unsafe_allow_html=True)
                    # Donut
                    type_c = {}
                    for a in acts: type_c[a.get("type","autre")] = type_c.get(a.get("type","autre"),0)+1
                    fig2 = go.Figure(go.Pie(
                        labels=list(type_c.keys()), values=list(type_c.values()), hole=.6,
                        marker_colors=["#ffd700","#60a5fa","#34d399","#f87171","#a78bfa","#fb923c"]))
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#cbd5e1"),
                        legend=dict(bgcolor="rgba(0,0,0,0)"),height=250,margin=dict(t=5,b=5),
                        annotations=[dict(text="Types",x=.5,y=.5,font_size=12,showarrow=False,font_color="#ffd700")])
                    c1,c2 = st.columns([1,2])
                    with c1: st.plotly_chart(fig2, use_container_width=True)
                    with c2:
                        st.markdown("**Répartition**")
                        for t,c in type_c.items():
                            st.progress(c/len(acts), text=f"{t}: {c}")

    # ── 3 GASTRONOMIE ─────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown('<div class="stitle">🍽️ Guide Gastronomique</div>', unsafe_allow_html=True)
        rraw = r.get("restaurants_data","")
        if not rraw:
            st.warning("Données gastronomie manquantes.")
        else:
            rdata = parse_json_safe(rraw)
            if rdata is None:
                st.error("JSON gastronomie invalide.")
                st.code(rraw[:400])
            else:
                c1,c2 = st.columns(2)
                with c1:
                    plats = rdata.get("plats_incontournables",[])
                    if plats:
                        st.markdown('<div class="gcard"><div class="ttitle">🍜 Plats incontournables</div>',
                                    unsafe_allow_html=True)
                        for p in plats: st.markdown(f"• {p}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    boissons = rdata.get("boissons_locales",[])
                    if boissons:
                        st.markdown(f'<div class="gcard"><div class="ttitle">🥂 Boissons locales</div>'
                                    f'<div class="tval">{", ".join(boissons)}</div></div>',
                                    unsafe_allow_html=True)
                with c2:
                    sf = rdata.get("marches_street_food","")
                    if sf:
                        st.markdown(f'<div class="gcard"><div class="ttitle">🏪 Street food & Marchés</div>'
                                    f'<div class="tval">{sf}</div></div>', unsafe_allow_html=True)
                    err = rdata.get("erreurs_a_eviter","")
                    if err:
                        st.markdown(f'<div class="gcard"><div class="ttitle">⚠️ Erreurs à éviter</div>'
                                    f'<div class="tval">{err}</div></div>', unsafe_allow_html=True)
                restos = rdata.get("restaurants",[])
                if restos:
                    st.markdown('<div class="stitle" style="font-size:1.1rem">🍴 Restaurants</div>',
                                unsafe_allow_html=True)
                    rhtml = '<div class="agrid">'
                    for rr in restos:
                        rhtml += f"""<div class="acard">
                          <div class="aemoji">{rr.get('emoji','🍽️')}</div>
                          <div class="aname">{rr.get('nom_type','')}</div>
                          <div class="adesc">{rr.get('specialite','')}</div>
                          <div class="aconseil">💡 {rr.get('conseil','')}</div>
                          <div class="atags"><span class="tag tg">{rr.get('budget_moyen','')}</span></div>
                        </div>"""
                    rhtml += '</div>'
                    st.markdown(rhtml, unsafe_allow_html=True)

    # ── 4 CONSEILS ────────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown('<div class="stitle">📋 Conseils Pratiques</div>', unsafe_allow_html=True)
        traw = r.get("tips_data","")
        if not traw:
            st.warning("Données conseils manquantes.")
        else:
            tdata = parse_json_safe(traw)
            if tdata is None:
                st.error("JSON conseils invalide.")
                st.code(traw[:400])
            else:
                icons = {"visa":"🛂","monnaie":"💵","langue":"🗣️","transport_local":"🚇",
                         "securite":"🛡️","meilleure_periode":"📅","budget_moyen_jour":"💰",
                         "urgences":"🚨","cuisine_locale":"🍜","decalage_horaire":"🕐"}
                html = '<div class="tgrid">'
                for k,v in tdata.items():
                    if isinstance(v, str):
                        html += (f'<div class="tcard">'
                                 f'<div class="ttitle">{icons.get(k,"ℹ️")} {k.replace("_"," ").title()}</div>'
                                 f'<div class="tval">{v}</div></div>')
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)

    # ── 5 RAISONNEMENT ────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown('<div class="stitle">🧠 Transparence du Raisonnement</div>', unsafe_allow_html=True)
        if st.session_state.cot:
            with st.expander("📋 Phase 1 — Chain of Thought", expanded=False):
                st.markdown(f'<div style="color:#cbd5e1;line-height:1.8;font-size:.9rem">'
                            f'{st.session_state.cot}</div>', unsafe_allow_html=True)
        steps = r.get("steps",[])
        if steps:
            st.markdown("**Phase 2 — Trace ReAct**")
            for s in steps:
                if s.get("type")=="REACT":
                    with st.expander(f"Étape {s['iteration']} — {s.get('action','')}"):
                        st.markdown(render_step(s), unsafe_allow_html=True)
                else:
                    st.markdown(render_step(s), unsafe_allow_html=True)
        else:
            st.info("Aucune trace disponible.")

    # ── 6 CONVERSATION ────────────────────────────────────────────────────────
    with tabs[6]:
        st.markdown('<div class="stitle">💬 Affiner avec l\'Agent</div>', unsafe_allow_html=True)
        st.markdown("""<div style="background:rgba(96,165,250,.06);border:1px solid rgba(96,165,250,.2);
            border-radius:10px;padding:.9rem 1.1rem;margin-bottom:1rem;font-size:.87rem;color:rgba(180,200,255,.75)">
            💡 <b style="color:#60a5fa">Mode conversation</b> — L'agent utilise les données déjà collectées
            (météo, activités, gastronomie, conseils) pour affiner votre itinéraire sans tout régénérer.</div>""",
            unsafe_allow_html=True)

        # Suggestions rapides
        SUGS = [
            "Rends l'itinéraire plus romantique",
            "Plus d'activités gratuites",
            "Concentre-toi sur la gastronomie",
            "Alternatives par mauvais temps",
            "Optimise les trajets",
            "Version famille avec enfants",
            "Plus de culture et musées",
            "Activités sportives et aventure",
        ]
        st.markdown("**Suggestions rapides :**")
        cols = st.columns(4)
        for i,s in enumerate(SUGS):
            with cols[i%4]:
                if st.button(s, key=f"sg{i}", use_container_width=True):
                    st.session_state.followup_txt = s
                    st.rerun()

        # Historique
        if st.session_state.convo:
            st.markdown('<div class="chat-box">', unsafe_allow_html=True)
            st.markdown('<div class="ttitle" style="color:#ffd700;font-size:.85rem;margin-bottom:.8rem">💬 Historique</div>',
                        unsafe_allow_html=True)
            for msg in st.session_state.convo:
                if msg["role"]=="user":
                    st.markdown(f'<div><div class="chat-who">👤 VOUS</div>'
                                f'<div class="chat-u">{msg["content"][:250]}</div></div>',
                                unsafe_allow_html=True)
                else:
                    preview = msg["content"][:250]+("…" if len(msg["content"])>250 else "")
                    st.markdown(f'<div><div class="chat-who">✈️ TRAVELMIND</div>'
                                f'<div class="chat-a">{preview}</div></div>',
                                unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Zone de saisie
        txt = st.text_area("✍️ Votre demande à l'agent",
                           value=st.session_state.followup_txt,
                           placeholder="Ex: Ajoute une journée de repos, plus d'activités culturelles, propose des alternatives végétariennes...",
                           height=95, key="ftxt")

        sc1, sc2 = st.columns([3,1])
        with sc1: send = st.button("📤 Envoyer à l'agent", use_container_width=True)
        with sc2:
            if st.button("🗑️ Effacer", use_container_width=True):
                st.session_state.followup_txt = ""
                st.rerun()

        if send and txt.strip():
            with st.spinner("🤖 L'agent affine votre itinéraire..."):
                updated = run_followup(
                    original_result=r,
                    follow_up_request=txt.strip(),
                    destination=dest, days=days, travelers=trav,
                    interests=ints, budget=bud,
                )
            st.session_state.result = updated
            st.session_state.convo.append({"role":"user",    "content": txt.strip()})
            st.session_state.convo.append({"role":"assistant","content": updated.get("itinerary","")[:400]})
            st.session_state.followup_txt = ""
            st.success("✅ Itinéraire mis à jour ! Consultez l'onglet **Itinéraire**.")
            st.rerun()

    # ── 7 EXPORT PDF ──────────────────────────────────────────────────────────
    with tabs[7]:
        st.markdown('<div class="stitle">📄 Export PDF Professionnel</div>', unsafe_allow_html=True)
        st.info(f"📍 **{dest}** — {days} jours — {trav} voyageur(s) — {bud}")
        if r.get("itinerary"):
            if st.button("🖨️ Générer le PDF"):
                with st.spinner("Génération PDF..."):
                    pdf_bytes = generate_pdf(r["itinerary"], dest, days, trav, bud)
                st.download_button("⬇️ Télécharger le PDF", pdf_bytes,
                                   f"TravelMind_{dest.replace(' ','_')}_{days}j.pdf",
                                   "application/pdf", use_container_width=True)
        else:
            st.warning("Aucun itinéraire disponible pour l'export.")

# ── État initial ───────────────────────────────────────────────────────────────
else:
    st.markdown("""
    <div style="text-align:center;padding:3rem 2rem">
      <div style="font-size:4rem;margin-bottom:1.2rem">🌍</div>
      <div style="font-family:'Playfair Display',serif;font-size:1.7rem;color:#ffd700;margin-bottom:.8rem">
        Prêt à explorer le monde ?</div>
      <div style="color:rgba(180,200,255,.6);font-size:.95rem;max-width:480px;margin:0 auto;line-height:1.8">
        Configurez votre voyage dans le panneau de gauche et cliquez sur
        <strong style="color:#ffd700">Lancer la planification</strong>.
      </div>
    </div>
    """, unsafe_allow_html=True)
    popular = [("🗼","Paris, France","Mode, gastronomie, culture"),
               ("🗾","Tokyo, Japon","Technologie, temples, cuisine"),
               ("🗽","New York, USA","Architecture, musées, nightlife"),
               ("🏛️","Rome, Italie","Histoire, art, gastronomie"),
               ("🌴","Bali, Indonésie","Nature, bien-être, plages"),
               ("🏙️","Dubaï, EAU","Luxe, architecture, shopping")]
    st.markdown('<div class="stitle">✨ Destinations Populaires</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i,(em,name,desc) in enumerate(popular):
        with cols[i%3]:
            st.markdown(f'<div class="acard" style="text-align:center">'
                        f'<div style="font-size:2.4rem">{em}</div>'
                        f'<div class="aname">{name}</div>'
                        f'<div class="adesc">{desc}</div></div>', unsafe_allow_html=True)
