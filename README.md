# ✈ TravelMind — Agent IA Planificateur de Voyage Autonome

> **Projet IA Générative — Master 2 SIAD, ISIMA 2025–2026**  
> Hamdadou Sarah & Moussi Dahbia — Encadré par Mr Issam Falih

---

## 🚀 Démarrage rapide

### 1. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement
```bash
cp .env.example .env
# Éditez .env et ajoutez votre clé API
```

### 3. Lancer l'application
```bash
streamlit run app.py
```

---

## 🔑 Configuration des APIs

| Variable | Description | Requis |
|----------|-------------|--------|
| `LLM_PROVIDER` | `groq` / `openai` / `anthropic` | ✅ |
| `GROQ_API_KEY` | Clé Groq (gratuit) | Si Groq |
| `OPENAI_API_KEY` | Clé OpenAI | Si OpenAI |
| `ANTHROPIC_API_KEY` | Clé Anthropic | Si Anthropic |
| `OPENWEATHER_API_KEY` | Clé OpenWeatherMap (optionnel) | ❌ |

> **Recommandation** : Groq est gratuit et très rapide (LLaMA 3.3 70B).  
> Obtenez une clé sur [console.groq.com](https://console.groq.com)

---

## 🧠 Techniques de Raisonnement

### Chain of Thought (CoT) — Phase 1
L'agent décompose le problème de planification en 6 questions structurées avant d'agir.
Visible dans l'onglet **Raisonnement** → Phase 1.

**Pourquoi ?** Éviter les erreurs de planification dues à un raisonnement incomplet.  
**Implémentation** : Prompt structuré forçant 6 étapes d'analyse (destination, manques, météo, activités, organisation, points d'attention).

### ReAct (Reason + Act) — Phase 2
Boucle itérative `THOUGHT → ACTION → INPUT → OBSERVATION` répétée jusqu'à 12 fois.

**Pourquoi ?** Permettre une adaptation dynamique : si la météo est mauvaise, l'agent ajuste les activités proposées.  
**Implémentation** : Parsing regex du format THOUGHT/ACTION/INPUT/OBSERVATION, dispatcher d'outils, contexte cumulatif.

---

## 🛠️ Les 4 Outils de l'Agent

| Outil | Description | API utilisée |
|-------|-------------|--------------|
| `get_weather` | Prévisions météo N jours | OpenWeatherMap / Simulation |
| `get_activities` | 12 activités adaptées au contexte | LLM |
| `get_travel_tips` | Conseils pratiques (visa, monnaie...) | LLM |
| `get_restaurants` | Guide gastronomique local | LLM |

---

## 💬 Mode Conversation Interactive (Nouveau)

Après la génération initiale, l'utilisateur peut **affiner l'itinéraire** en langage naturel :
- L'agent se base sur les données déjà collectées
- Pas besoin de tout régénérer
- 8 suggestions rapides disponibles
- Historique de la conversation affiché

---

## 📁 Structure du Projet

```
travelmind/
├── app.py                    # Interface Streamlit premium
├── requirements.txt
├── .env.example
├── agents/
│   └── travel_agent.py       # Logique CoT + ReAct + conversation
├── tools/
│   └── tools.py              # 4 outils spécialisés
└── utils/
    ├── llm_provider.py       # Abstraction OpenAI/Anthropic/Groq
    └── pdf_export.py         # Export PDF professionnel
```

---

## ✨ Fonctionnalités

- 🎨 **Interface dark premium** avec animations et design professionnel
- 🧠 **CoT visible** : raisonnement décomposé affiché en temps réel
- ⚡ **Trace ReAct** : chaque THOUGHT/ACTION/OBSERVATION visible
- 📊 **Graphiques interactifs** : météo, répartition activités (Plotly)
- 🎯 **Filtres activités** : par type (extérieur/intérieur) et budget
- 💬 **Mode conversation** : affinage interactif de l'itinéraire
- 🍽️ **Guide gastronomique** complet dédié
- 📄 **Export PDF** professionnel téléchargeable
- 🔄 **Multi-LLM** : Groq / OpenAI / Anthropic
