"""
tools/tools.py
Outils disponibles pour l'agent TravelMind.
"""
import os
import json
import random
import requests
from datetime import datetime, timedelta
from utils.llm_provider import call_llm

OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY", "")


# ─────────────────────────────────────────────
# OUTIL 1 : Météo
# ─────────────────────────────────────────────

def get_weather(destination: str, days: int = 7) -> str:
    """Récupère les prévisions météo pour la destination."""
    days = min(int(days), 7)

    if OPENWEATHER_KEY:
        try:
            geo_url = "http://api.openweathermap.org/geo/1.0/direct"
            geo_r = requests.get(geo_url, params={"q": destination, "limit": 1, "appid": OPENWEATHER_KEY}, timeout=5)
            geo_data = geo_r.json()
            if geo_data:
                lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
                fc_url = "http://api.openweathermap.org/data/2.5/forecast"
                fc_r = requests.get(fc_url, params={
                    "lat": lat, "lon": lon, "appid": OPENWEATHER_KEY,
                    "units": "metric", "lang": "fr", "cnt": days * 8
                }, timeout=5)
                fc_data = fc_r.json()
                return _parse_openweather(fc_data, days)
        except Exception:
            pass

    # Mode simulation
    return _simulate_weather(destination, days)


def _parse_openweather(data: dict, days: int) -> str:
    daily = {}
    for item in data.get("list", []):
        date = item["dt_txt"][:10]
        if date not in daily:
            daily[date] = []
        daily[date].append(item)

    lines = []
    for i, (date, items) in enumerate(list(daily.items())[:days]):
        temps = [x["main"]["temp"] for x in items]
        desc = items[len(items)//2]["weather"][0]["description"]
        hum = items[len(items)//2]["main"]["humidity"]
        rain = sum(x.get("rain", {}).get("3h", 0) for x in items)
        lines.append(
            f"{date}: {desc}, min {min(temps):.0f}°C / max {max(temps):.0f}°C, "
            f"humidité {hum}%, pluie {rain:.1f}mm"
        )
    return "\n".join(lines)


def _simulate_weather(destination: str, days: int) -> str:
    descriptions = [
        ("ensoleillé ☀️", 28, 22, 45, 0),
        ("partiellement nuageux ⛅", 24, 17, 60, 0),
        ("nuageux 🌥️", 20, 14, 70, 2),
        ("légère pluie 🌦️", 18, 13, 80, 8),
        ("orageux ⛈️", 16, 12, 85, 15),
        ("très ensoleillé 🌞", 32, 24, 35, 0),
    ]
    lines = ["[Simulation - clé API météo absente]"]
    base = datetime.now()
    for i in range(days):
        d = base + timedelta(days=i)
        desc, tmax, tmin, hum, rain = random.choice(descriptions)
        tmax += random.randint(-3, 3)
        tmin += random.randint(-2, 2)
        lines.append(
            f"{d.strftime('%Y-%m-%d')}: {desc}, min {tmin}°C / max {tmax}°C, "
            f"humidité {hum}%, pluie {rain}mm"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────
# OUTIL 2 : Activités
# ─────────────────────────────────────────────

def get_activities(destination: str, weather_summary: str, interests: str = "", budget: str = "moyen") -> str:
    """Génère des suggestions d'activités adaptées au contexte."""
    prompt = f"""Tu es un expert en tourisme. Pour une visite à {destination}, météo prévue: {weather_summary}.
Intérêts du voyageur: {interests or 'général'}. Budget: {budget}.

Propose exactement 12 activités variées (extérieur ET intérieur) adaptées à la météo.
Format JSON STRICT:
{{
  "activites": [
    {{"nom": "...", "type": "exterieur|interieur|culture|gastronomie|sport|shopping", 
      "duree": "2h", "cout": "gratuit|€|€€|€€€", "description": "...", "conseil": "...",
      "emoji": "🏛️"}}
  ]
}}
Réponds UNIQUEMENT avec le JSON, sans aucun texte autour."""

    raw = call_llm([{"role": "user", "content": prompt}], max_tokens=2000, temperature=0.8)
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return raw.strip()
    except Exception:
        return raw


# ─────────────────────────────────────────────
# OUTIL 3 : Conseils pratiques
# ─────────────────────────────────────────────

def get_travel_tips(destination: str) -> str:
    """Génère des conseils pratiques structurés pour la destination."""
    prompt = f"""Tu es un expert voyageur. Donne des informations pratiques pour {destination}.
Format JSON STRICT:
{{
  "visa": "...",
  "monnaie": "...",
  "langue": "...",
  "transport_local": "...",
  "securite": "...",
  "meilleure_periode": "...",
  "budget_moyen_jour": "...",
  "urgences": "...",
  "cuisine_locale": "...",
  "decalage_horaire": "..."
}}
Réponds UNIQUEMENT avec le JSON."""

    raw = call_llm([{"role": "user", "content": prompt}], max_tokens=1000)
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return raw.strip()
    except Exception:
        return raw


# ─────────────────────────────────────────────
# OUTIL 4 : Restaurants
# ─────────────────────────────────────────────

def get_restaurants(destination: str, budget: str = "moyen", cuisine_pref: str = "") -> str:
    """Recommande des types de restaurants et plats locaux."""
    prompt = f"""Expert gastronomique pour {destination}. Budget voyageur: {budget}. Préférences: {cuisine_pref or 'ouvert à tout'}.
Format JSON STRICT:
{{
  "plats_incontournables": ["...", "..."],
  "restaurants": [
    {{"nom_type": "...", "specialite": "...", "budget_moyen": "...", "conseil": "...", "emoji": "🍜"}}
  ],
  "marches_street_food": "...",
  "boissons_locales": ["...", "..."],
  "erreurs_a_eviter": "..."
}}
Réponds UNIQUEMENT avec le JSON."""

    raw = call_llm([{"role": "user", "content": prompt}], max_tokens=1200)
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return raw.strip()
    except Exception:
        return raw


# ─────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: str) -> str:
    """Dispatcher central des outils."""
    parts = [p.strip() for p in tool_input.split("|")]

    if tool_name == "get_weather":
        dest = parts[0]
        days = int(parts[1]) if len(parts) > 1 else 7
        return get_weather(dest, days)

    elif tool_name == "get_activities":
        dest = parts[0]
        weather = parts[1] if len(parts) > 1 else ""
        interests = parts[2] if len(parts) > 2 else ""
        budget = parts[3] if len(parts) > 3 else "moyen"
        return get_activities(dest, weather, interests, budget)

    elif tool_name == "get_travel_tips":
        return get_travel_tips(parts[0])

    elif tool_name == "get_restaurants":
        dest = parts[0]
        budget = parts[1] if len(parts) > 1 else "moyen"
        cuisine = parts[2] if len(parts) > 2 else ""
        return get_restaurants(dest, budget, cuisine)

    else:
        return f"Outil inconnu: {tool_name}"


TOOLS_DESCRIPTION = """
Outils disponibles:
1. get_weather: Prévisions météo. Input: "destination | nombre_jours"
2. get_activities: Suggestions d'activités. Input: "destination | résumé_météo | intérêts | budget"
3. get_travel_tips: Conseils pratiques (visa, monnaie, etc.). Input: "destination"
4. get_restaurants: Recommandations gastronomiques. Input: "destination | budget | préférences_cuisine"
"""
