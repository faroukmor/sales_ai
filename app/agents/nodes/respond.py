"""Evidence validation and deterministic response-composition nodes."""

from langchain_core.messages import AIMessage, RemoveMessage

from app.agents.state import (
    ExecutionStatus,
    ExecutionStep,
    SalesAgentState,
    StateError,
)
from app.services.evidence_validator import EvidenceValidationError, EvidenceValidator
from app.services.response_composer import ResponseComposer


def validate_chat_evidence_node(
    validator: EvidenceValidator, state: SalesAgentState
) -> SalesAgentState:
    try:
        evidence = validator.validate(state)
    except EvidenceValidationError:
        return {
            "status": ExecutionStatus.FAILED,
            "current_step": ExecutionStep.VALIDATE_EVIDENCE,
            "evidence": [],
            "errors": [
                *state.get("errors", []),
                StateError(
                    code="insufficient_evidence",
                    message="Business results could not be grounded safely.",
                    step=ExecutionStep.VALIDATE_EVIDENCE,
                ),
            ],
        }
    return {"evidence": evidence, "current_step": ExecutionStep.VALIDATE_EVIDENCE}


def compose_response_node(
    composer: ResponseComposer,
    state: SalesAgentState,
    *,
    max_history_messages: int,
) -> SalesAgentState:
    answer, _status = composer.compose(state)
    assistant_message = AIMessage(content=answer)
    messages = state.get("messages", [])
    excess = max(0, len(messages) + 1 - max_history_messages)
    removals = [
        RemoveMessage(id=message.id)
        for message in messages[:excess]
        if message.id is not None
    ]
    return {
        "answer": answer,
        "messages": [*removals, assistant_message],
        "current_step": ExecutionStep.COMPOSE_RESPONSE,
    }
