# services/chat_service.py
import logging

from core.exceptions import GeantError
from models.chat_response import ChatResponse
from models.evidence import EvidenceBundle
from models.query_plan import Intent, QueryPlan

logger = logging.getLogger(__name__)

# أي نيات تحتاج صياغة LLM؟ (بيانات، وليست منطقًا). البحث والمقارنة بلا LLM.
_GENERATE_FOR = frozenset({Intent.EXPLANATION})


class ChatService:
    """ينسّق دورة الطلب فقط. كل التفاصيل في المكونات التي يستلمها من الخارج."""

    def __init__(self, analyzer, handlers: dict, builder, generator, validator):
        self._analyzer = analyzer
        self._handlers = handlers
        self._builder = builder
        self._generator = generator
        self._validator = validator

    def handle_message(self, message: str, session_id: str | None = None) -> ChatResponse:
        # session_id محجوز لـ ConversationManager (Phase 6) ولا يُستخدم الآن.
        plan = self._analyzer.analyze(message)

        if plan.intent is Intent.UNKNOWN or plan.missing_info:
            return self._builder.needs_clarification(plan)

        handler = self._handlers.get(plan.intent)
        if handler is None:
            return self._builder.unsupported(plan)

        try:
            bundle = handler.handle(plan)
            generated = None
            if plan.intent in _GENERATE_FOR and bundle.chunks:
                generated = self._generate_checked(plan, bundle)
            return self._builder.build(plan, bundle, generated)
        except GeantError as exc:
            logger.warning("Request failed (%s): %s", type(exc).__name__, exc)
            return self._builder.error(plan)

    def _generate_checked(self, plan: QueryPlan, bundle: EvidenceBundle) -> str | None:
        """يولّد ثم يفحص الأرقام. أي فشل في الفحص يُعامل كأن الأدلة لا تكفي."""
        chunks = list(bundle.chunks)
        text = self._generator.generate(plan.message, chunks, plan.language)
        if text is None:
            return None
        result = self._validator.validate(text, [sc.chunk.text for sc in chunks])
        if not result.ok:
            logger.info("Discarded generated answer; unsupported numbers: %s",
                        result.unsupported_numbers)
            return None
        return text
