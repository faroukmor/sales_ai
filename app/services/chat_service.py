"""Application service for one checkpointed chat turn."""

from __future__ import annotations

from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.orm import Session

from app.agents.chat_graph import build_chat_graph
from app.agents.nodes.sales import SalesFunctionTools
from app.agents.state import SalesAgentState
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.chat_response import ChatRequest, ChatResponse
from app.schemas.query_plan import Intent
from app.services.evidence_validator import EvidenceValidator
from app.services.intent_parser import IntentParser
from app.services.recommendation import RecommendationService
from app.services.response_composer import ResponseComposer
from app.tools.product_comparison import ProductComparisonTool
from app.tools.product_search import ProductSearchTool
from app.tools.promotions import PromotionsTool


class ChatService:
    def __init__(
        self,
        session: Session,
        parser: IntentParser,
        checkpointer: BaseCheckpointSaver,
        *,
        max_history_messages: int = 30,
    ) -> None:
        products = ProductRepository(session)
        promotions = PromotionRepository(session)
        tools = SalesFunctionTools(
            search=ProductSearchTool(products),
            comparison=ProductComparisonTool(products, promotions),
            recommendations=RecommendationService(products),
            promotions=PromotionsTool(promotions, products),
        )
        self._graph = build_chat_graph(
            parser,
            tools,
            checkpointer=checkpointer,
            max_history_messages=max_history_messages,
        )
        self._composer = ResponseComposer()
        self._evidence = EvidenceValidator()

    def chat(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid4())
        config = {"configurable": {"thread_id": session_id}}
        state = self._graph.invoke(
            {
                "messages": [HumanMessage(content=request.message)],
                "session_id": session_id,
            },
            config=config,
        )
        typed_state: SalesAgentState = state
        plan = typed_state["query_plan"]
        answer, status = self._composer.compose(typed_state)
        sources = self._evidence.validate(typed_state)

        products = typed_state.get("products", []) if plan.intent in {
            Intent.PRODUCT_SEARCH,
            Intent.COMPARISON,
            Intent.RECOMMENDATION,
        } else []
        return ChatResponse(
            session_id=session_id,
            answer=answer,
            status=status,
            intent=plan.intent,
            language=plan.language,
            products=products,
            comparison=(
                typed_state.get("comparison") if plan.intent is Intent.COMPARISON else None
            ),
            recommendations=(
                typed_state.get("recommendations", [])
                if plan.intent is Intent.RECOMMENDATION
                else []
            ),
            promotions=(
                typed_state.get("promotions", [])
                if plan.intent is Intent.PROMOTION_SEARCH
                else []
            ),
            sources=sources,
        )
