import os
import httpx
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from datetime import datetime


PROVIDERS: dict[str, dict] = {
    "cerebras": {"label": "Cerebras · gpt-oss-120b", "env": "CEREBRAS_API_KEY"},
    "openai":   {"label": "OpenAI · gpt-4.1-mini",   "env": "OPENAI_API_KEY"},
    "google":   {"label": "Google · gemini-2.5-flash","env": "GOOGLE_API_KEY"},
    "groq":     {"label": "Groq · llama-3.3-70b",    "env": "groq_api_key"},
}


def get_model(provider: str):
    if provider == "openai":
        return ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    elif provider == "google":
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    elif provider == "groq":
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("groq_api_key"),
            http_client=httpx.Client(verify=False),
        )
    else:  # cerebras (default)
        return ChatOpenAI(
            model="gpt-oss-120b",
            base_url="https://api.cerebras.ai/v1",
            api_key=os.getenv("CEREBRAS_API_KEY"),
            http_client=httpx.Client(verify=False),
        )


def is_configured(provider: str) -> bool:
    return bool(os.getenv(PROVIDERS[provider]["env"]))


def check_api_key(provider: str) -> dict:
    """
    Probe the provider with a minimal 1-token call.
    Only called on explicit user action — never called automatically.

    Returns:
        {
            "status":     "active" | "invalid_key" | "no_credits" | "no_key" | "error",
            "message":    str,
            "checked_at": "HH:MM" string,
        }
    """
    if not is_configured(provider):
        return {
            "status": "no_key",
            "message": "API key not set in .env",
            "checked_at": datetime.now().strftime("%H:%M"),
        }

    try:
        # Instantiate with max_tokens=1 to minimise cost
        if provider == "openai":
            model = ChatOpenAI(
                model="gpt-4.1-mini", max_tokens=1,
                http_client=httpx.Client(verify=False),
            )
        elif provider == "google":
            model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", max_output_tokens=1)
        elif provider == "groq":
            model = ChatGroq(
                model="llama-3.3-70b-versatile", max_tokens=1,
                api_key=os.getenv("groq_api_key"),
                http_client=httpx.Client(verify=False),
            )
        else:  # cerebras
            model = ChatOpenAI(
                model="gpt-oss-120b", max_tokens=1,
                base_url="https://api.cerebras.ai/v1",
                api_key=os.getenv("CEREBRAS_API_KEY"),
                http_client=httpx.Client(verify=False),
            )

        model.invoke([HumanMessage(content="hi")])
        return {
            "status": "active",
            "message": "Active",
            "checked_at": datetime.now().strftime("%H:%M"),
        }

    except Exception as e:
        err = str(e).lower()
        if any(t in err for t in ("401", "authentication", "invalid api key",
                                   "incorrect api key", "unauthorized", "invalid_api_key")):
            status, message = "invalid_key", "Invalid API key"
        elif any(t in err for t in ("403", "permission denied", "forbidden")):
            status, message = "invalid_key", "Permission denied — check key"
        elif any(t in err for t in ("429", "quota", "rate limit", "rate_limit",
                                     "insufficient_quota", "billing", "exceeded", "credit")):
            status, message = "no_credits", "Quota exceeded / no credits"
        else:
            status, message = "error", str(e)[:100]

        return {
            "status": status,
            "message": message,
            "checked_at": datetime.now().strftime("%H:%M"),
        }


class UsageTracker(BaseCallbackHandler):
    """Captures total token usage across every LLM call in a chain invocation."""

    def __init__(self):
        self.total_tokens = 0

    def on_llm_end(self, response, **kwargs):
        for gen_list in response.generations:
            for gen in gen_list:
                if hasattr(gen, "message") and hasattr(gen.message, "usage_metadata"):
                    meta = gen.message.usage_metadata or {}
                    self.total_tokens += meta.get("total_tokens", 0)
