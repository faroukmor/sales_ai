# services/answer_generator.py
from typing import Sequence

from core.config import LLM_MODEL, NUM_PREDICT, OLLAMA_HOST, OLLAMA_TIMEOUT_SECONDS, TEMPERATURE
from core.exceptions import GenerationError
from models.chunk import ScoredChunk

NO_ANSWER_TOKEN = "NO_ANSWER"
_LANGUAGE_NAMES = {"en": "English", "fr": "French", "ar": "Arabic"}

_SYSTEM_TEMPLATE = """You are a sales assistant for an online electronics store.
Answer the customer's question using ONLY the sources below.

Rules:
- Use only facts stated in the sources. Do not add outside knowledge.
- Do not mention prices, stock, discounts or dates: those come from the product database, not from you.
- Do not write source labels or citations in your answer.
- {language_rule}
- If the sources do not contain the answer, reply with exactly: {no_answer}

Sources:
{sources}"""


class AnswerGenerator:
    """يصوغ إجابة نصية من أدلة معطاة عبر Ollama. لا يستعلم القاعدة ولا يختار منتجات."""

    def __init__(self, client=None, model: str = LLM_MODEL,
                 temperature: float = TEMPERATURE, num_predict: int = NUM_PREDICT):
        if client is None:
            import ollama
            client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT_SECONDS)
        self._client = client
        self._model = model
        self._options = {"temperature": temperature, "num_predict": num_predict}

    def generate(self, question: str, chunks: Sequence[ScoredChunk],
                 language: str = "unknown") -> str | None:
        """يرجع الإجابة، أو None إن قال النموذج إن الأدلة لا تكفي."""
        if not chunks:
            return None
        messages = [
            {"role": "system", "content": self._system_prompt(chunks, language)},
            {"role": "user", "content": question},
        ]
        try:
            response = self._client.chat(model=self._model, messages=messages, options=self._options)
            text = response["message"]["content"]
        except Exception as exc:
            raise GenerationError(f"LLM request failed (model={self._model}): {exc}") from exc

        text = (text or "").strip()
        if not text:
            raise GenerationError("LLM returned an empty answer")
        if NO_ANSWER_TOKEN in text.upper():
            return None
        return text

    @staticmethod
    def _system_prompt(chunks: Sequence[ScoredChunk], language: str) -> str:
        # تسميات حرفية (A, B, ...) بدل الأرقام حتى لا تختلط بأرقام الحقائق في الفحص اللاحق
        sources = "\n\n".join(
            f"Source {chr(ord('A') + i)}: {sc.chunk.text}" for i, sc in enumerate(chunks[:26])
        )
        name = _LANGUAGE_NAMES.get(language)
        language_rule = (
            f"Reply in {name}." if name
            else "Reply in the same language as the customer's question."
        )
        return _SYSTEM_TEMPLATE.format(
            language_rule=language_rule, no_answer=NO_ANSWER_TOKEN, sources=sources
        )
