"""
agents/travel_agent.py
TravelMind - Chain of Thought + ReAct + conversation
"""
import re
from utils.llm_provider import call_llm
from tools.tools import (
    get_weather, get_activities, get_travel_tips,
    get_restaurants, dispatch_tool, TOOLS_DESCRIPTION
)

MAX_ITER = 10

SYSTEM_PROMPT = """Tu es TravelMind, agent expert en planification de voyages.
Tu utilises la méthode ReAct. Format STRICT:

THOUGHT: [ta réflexion]
ACTION: [nom_outil]
INPUT: [paramètres]

Quand tu as fini de collecter, génère l'itinéraire complet avec:
FINISH: [itinéraire Markdown jour par jour, Matin/Après-midi/Soirée]

{tools}

Règles: commence par get_weather. Réponds TOUJOURS en français.
"""


def run_cot_phase(destination, days, travelers, interests, budget):
    interests_str = ", ".join(interests) if interests else "général"
    prompt = f"""Planifie un voyage à {destination}, {days} jours, {travelers} voyageur(s).
Intérêts: {interests_str}. Budget: {budget}.

Chain of Thought - réponds étape par étape:
1. Analyse de {destination}: spécificités, culture, climat général
2. Informations à collecter (météo, activités, gastronomie, conseils)
3. Comment adapter le programme selon la météo prévue
4. Activités adaptées aux intérêts: {interests_str}
5. Organisation optimale des {days} jours (géographie, rythme, thèmes)
6. Conseils pratiques essentiels pour ce voyage"""

    return call_llm(
        [{"role": "user", "content": prompt}],
        system="Tu es expert en voyages. Décompose ta réflexion étape par étape.",
        max_tokens=1500, temperature=0.6
    )


def run_react_loop(destination, days, travelers, interests, budget, cot_analysis, callback=None):
    """
    Boucle ReAct + appel direct des outils si le LLM ne les appelle pas.
    Garantit que weather, activities, tips, restaurants sont TOUJOURS remplis.
    """
    interests_str = ", ".join(interests) if interests else "général"

    user_content = f"""Destination: {destination} | Durée: {days} jours | Voyageurs: {travelers}
Intérêts: {interests_str} | Budget: {budget}

Analyse préalable:
{cot_analysis[:800]}

Utilise les 4 outils dans l'ordre: get_weather → get_activities → get_restaurants → get_travel_tips
Puis génère l'itinéraire complet avec FINISH:"""

    messages = [{"role": "user", "content": user_content}]
    steps = []
    weather_data = activities_data = tips_data = restaurants_data = final_itinerary = ""
    tools_called = set()

    for iteration in range(MAX_ITER):
        response = call_llm(
            messages,
            system=SYSTEM_PROMPT.format(tools=TOOLS_DESCRIPTION),
            max_tokens=3000, temperature=0.7,
        )
        messages.append({"role": "assistant", "content": response})

        # FINISH ?
        if "FINISH:" in response:
            m = re.search(r"FINISH:\s*(.*)", response, re.DOTALL)
            if m:
                final_itinerary = m.group(1).strip()
            step = {"iteration": iteration+1, "type": "FINISH",
                    "thought": _extract(response, "THOUGHT"), "content": "Itinéraire généré ✅"}
            steps.append(step)
            if callback: callback(step)
            break

        thought = _extract(response, "THOUGHT")
        action  = _extract(response, "ACTION")
        inp     = _extract(response, "INPUT")

        if action:
            obs = dispatch_tool(action.strip(), inp.strip() if inp else "")
            a = action.strip()
            if "get_weather"     in a: weather_data      = obs; tools_called.add("weather")
            elif "get_activities" in a: activities_data   = obs; tools_called.add("activities")
            elif "get_travel_tips" in a: tips_data        = obs; tools_called.add("tips")
            elif "get_restaurants" in a: restaurants_data = obs; tools_called.add("restaurants")

            step = {"iteration": iteration+1, "type": "REACT", "thought": thought,
                    "action": a, "input": inp.strip() if inp else "",
                    "observation": obs[:400] + ("..." if len(obs)>400 else "")}
            steps.append(step)
            if callback: callback(step)
            messages.append({"role": "user",
                             "content": f"OBSERVATION {a}: {obs}\nContinue avec les outils restants ou génère FINISH."})
        else:
            # Pas d'action parsée - pousser le LLM à continuer
            step = {"iteration": iteration+1, "type": "THOUGHT",
                    "thought": thought or response[:200], "action": None, "input": None, "observation": None}
            steps.append(step)
            if callback: callback(step)
            missing = _missing_tools(tools_called)
            if missing:
                messages.append({"role": "user",
                                 "content": f"Tu n'as pas encore utilisé: {missing}. Utilise-les puis génère FINISH:"})
            else:
                messages.append({"role": "user",
                                 "content": "Tu as toutes les données. Génère maintenant l'itinéraire avec FINISH:"})

    # ── Garantie : appel direct si le LLM a raté des outils ──────────────────
    if not weather_data:
        weather_data = get_weather(destination, min(days, 7))
        _add_fallback_step(steps, "get_weather", weather_data)

    if not activities_data:
        w_summary = weather_data.split("\n")[1] if "\n" in weather_data else weather_data
        activities_data = get_activities(destination, w_summary, interests_str, budget)
        _add_fallback_step(steps, "get_activities", activities_data)

    if not restaurants_data:
        restaurants_data = get_restaurants(destination, budget, interests_str)
        _add_fallback_step(steps, "get_restaurants", restaurants_data)

    if not tips_data:
        tips_data = get_travel_tips(destination)
        _add_fallback_step(steps, "get_travel_tips", tips_data)

    # ── Si pas d'itinéraire généré, le générer maintenant ────────────────────
    if not final_itinerary:
        final_itinerary = _generate_itinerary_directly(
            destination, days, travelers, interests_str, budget,
            weather_data, activities_data, restaurants_data, tips_data
        )

    return {
        "itinerary": final_itinerary,
        "steps": steps,
        "weather_data": weather_data,
        "activities_data": activities_data,
        "tips_data": tips_data,
        "restaurants_data": restaurants_data,
    }


def run_followup(original_result, follow_up_request, destination, days, travelers, interests, budget, callback=None):
    """Affine l'itinéraire selon la demande. Réutilise toutes les données collectées."""
    interests_str = ", ".join(interests) if interests else "général"

    context = f"""Tu es TravelMind. Tu as déjà toutes les données pour {destination}.

MÉTÉO DISPONIBLE:
{original_result.get('weather_data', '')}

ACTIVITÉS DISPONIBLES (JSON):
{original_result.get('activities_data', '')[:800]}

GASTRONOMIE DISPONIBLE (JSON):
{original_result.get('restaurants_data', '')[:600]}

CONSEILS DISPONIBLES (JSON):
{original_result.get('tips_data', '')[:600]}

ITINÉRAIRE ACTUEL:
{original_result.get('itinerary', '')[:1500]}

Voyageurs: {travelers} | Budget: {budget} | Intérêts: {interests_str}

NOUVELLE DEMANDE DE L'UTILISATEUR: {follow_up_request}

Génère DIRECTEMENT un itinéraire amélioré qui tient compte de cette demande.
Commence par FINISH: suivi de l'itinéraire Markdown complet jour par jour."""

    messages = [{"role": "user", "content": context}]
    final_itinerary = ""
    followup_steps = []

    for iteration in range(5):
        response = call_llm(
            messages,
            system="Tu es TravelMind, expert en voyages. Réponds en français.",
            max_tokens=3500, temperature=0.7,
        )
        messages.append({"role": "assistant", "content": response})

        if "FINISH:" in response:
            m = re.search(r"FINISH:\s*(.*)", response, re.DOTALL)
            if m:
                final_itinerary = m.group(1).strip()
            followup_steps.append({"iteration": iteration+1, "type": "FINISH",
                                   "thought": "Itinéraire affiné", "content": "✅"})
            if callback: callback(followup_steps[-1])
            break

        action = _extract(response, "ACTION")
        inp    = _extract(response, "INPUT")
        if action:
            obs = dispatch_tool(action.strip(), inp.strip() if inp else "")
            followup_steps.append({"iteration": iteration+1, "type": "REACT",
                                   "thought": _extract(response, "THOUGHT"),
                                   "action": action.strip(), "input": inp or "",
                                   "observation": obs[:300]})
            if callback: callback(followup_steps[-1])
            messages.append({"role": "user", "content": f"OBSERVATION: {obs}\nMaintenant génère FINISH:"})
        else:
            # Réponse directe longue sans tag FINISH — on la prend quand même
            if len(response.strip()) > 300:
                final_itinerary = response.strip()
                followup_steps.append({"iteration": iteration+1, "type": "FINISH",
                                       "thought": "Réponse directe", "content": "✅"})
                if callback: callback(followup_steps[-1])
                break
            messages.append({"role": "user",
                             "content": "Génère maintenant l'itinéraire amélioré avec FINISH:"})

    updated = dict(original_result)
    updated["itinerary"]      = final_itinerary or original_result.get("itinerary", "")
    updated["steps"]          = original_result.get("steps", []) + followup_steps
    updated["followup_steps"] = followup_steps
    return updated


# ── Helpers privés ────────────────────────────────────────────────────────────

def _extract(text, tag):
    pattern = rf"{tag}:\s*(.*?)(?=\n(?:THOUGHT|ACTION|INPUT|OBSERVATION|FINISH):|$)"
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _missing_tools(called):
    all_tools = {"weather", "activities", "restaurants", "tips"}
    missing = all_tools - called
    names = {"weather": "get_weather", "activities": "get_activities",
             "restaurants": "get_restaurants", "tips": "get_travel_tips"}
    return ", ".join(names[t] for t in missing)


def _add_fallback_step(steps, tool_name, observation):
    n = len(steps) + 1
    steps.append({
        "iteration": n, "type": "REACT",
        "thought": f"Appel direct de {tool_name} (fallback)",
        "action": tool_name, "input": "auto",
        "observation": observation[:300] + ("..." if len(observation) > 300 else ""),
    })


def _generate_itinerary_directly(destination, days, travelers, interests_str, budget,
                                  weather, activities, restaurants, tips):
    prompt = f"""Génère un itinéraire complet pour {destination}, {days} jours, {travelers} voyageur(s).
Budget: {budget}. Intérêts: {interests_str}.

Données météo:
{weather[:500]}

Activités disponibles (extrait):
{activities[:400]}

Gastronomie (extrait):
{restaurants[:300]}

Conseils pratiques (extrait):
{tips[:300]}

Génère un itinéraire DÉTAILLÉ jour par jour avec sections Matin / Après-midi / Soirée / Budget du jour.
Utilise le format Markdown avec ## Jour X - Titre."""

    return call_llm(
        [{"role": "user", "content": prompt}],
        system="Tu es expert en voyages. Génère un itinéraire détaillé et pratique en français.",
        max_tokens=3500, temperature=0.7
    )
