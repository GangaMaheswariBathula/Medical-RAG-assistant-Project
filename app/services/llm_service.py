"""All Groq / LLM logic lives here."""
from app.config import get_settings
from app.exceptions import ConfigError
from app.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    def __init__(self):
        from langchain_groq import ChatGroq

        s = get_settings()
        if not s.groq_api_key:
            raise ConfigError("GROQ_API_KEY is not set")
        self._llm = ChatGroq(  # one reusable client
            model=s.llm_model,
            temperature=s.temperature,
            max_tokens=s.max_tokens,
            api_key=s.groq_api_key,
        )

    def generate(self, messages) -> str:
        return self._llm.invoke(messages).content
