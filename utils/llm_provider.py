"""
utils/llm_provider.py
Abstraction multi-LLM : OpenAI / Anthropic / Groq
"""
import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()


def call_llm(messages: list, system: str = "", max_tokens: int = 4096, temperature: float = 0.7) -> str:
    """Appel unifié au LLM selon le fournisseur configuré."""
    if PROVIDER == "openai":
        return _call_openai(messages, system, max_tokens, temperature)
    elif PROVIDER == "anthropic":
        return _call_anthropic(messages, system, max_tokens, temperature)
    elif PROVIDER == "groq":
        return _call_groq(messages, system, max_tokens, temperature)
    else:
        raise ValueError(f"Fournisseur LLM inconnu: {PROVIDER}")


def _call_openai(messages, system, max_tokens, temperature):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content


def _call_anthropic(messages, system, max_tokens, temperature):
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or "Tu es un assistant de voyage expert.",
        messages=messages,
    )
    return response.content[0].text


def _call_groq(messages, system, max_tokens, temperature):
    from openai import OpenAI
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY est manquante. Créez un fichier .env avec:\n"
            "LLM_PROVIDER=groq\n"
            "GROQ_API_KEY=gsk_..."
        )
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content


def get_provider_info() -> dict:
    return {
        "openai": {"name": "OpenAI GPT-4o", "color": "#10a37f", "icon": "🟢"},
        "anthropic": {"name": "Anthropic Claude", "color": "#d4763b", "icon": "🟠"},
        "groq": {"name": "Groq LLaMA 3.3", "color": "#f55036", "icon": "🔴"},
    }.get(PROVIDER, {"name": PROVIDER, "color": "#888", "icon": "🤖"})
