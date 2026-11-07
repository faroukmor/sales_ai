from decimal import Decimal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph.message import add_messages

from app.agents.state import (
    ExecutionStatus,
    ExecutionStep,
    SalesAgentState,
    StateError,
    create_initial_state,
)
from app.schemas.query_plan import Intent, Language, QueryPlan


def make_query_plan(message: str) -> QueryPlan:
    return QueryPlan(
        original_message=message,
        intent=Intent.PRODUCT_SEARCH,
        language=Language.EN,
        category="laptop",
        brand=None,
        min_price=None,
        max_price=Decimal("150000"),
        currency="DZD",
        in_stock_only=True,
        specification_constraints=[],
        product_refs=[],
        needs_clarification=False,
        missing_info=[],
        clarification_question=None,
    )


def test_initializes_english_message() -> None:
    state = create_initial_state("Find me a laptop")

    assert isinstance(state["messages"][0], HumanMessage)
    assert state["messages"][0].content == "Find me a laptop"
    assert state["status"] is ExecutionStatus.READY
    assert state["current_step"] is ExecutionStep.INITIALIZED
    assert state["session_id"]


def test_initializes_french_message_without_normalizing_it() -> None:
    text = "Je cherche un téléphone à moins de 80 000 DA"
    assert create_initial_state(text)["messages"][0].content == text


def test_preserves_arabic_and_darija_unicode() -> None:
    text = "عطيني تلفاز مليح ما يفوتش 10 ملاين"
    assert create_initial_state(text)["messages"][0].content == text


def test_preserves_known_session_and_optional_user_id() -> None:
    state = create_initial_state("hello", session_id="session-42", user_id="user-7")
    assert state["session_id"] == "session-42"
    assert state["user_id"] == "user-7"


def test_empty_products_is_distinct_from_missing_products() -> None:
    state = create_initial_state("find laptops")
    assert "products" not in state

    searched_state: SalesAgentState = {**state, "products": []}
    assert "products" in searched_state
    assert searched_state["products"] == []


def test_query_plan_is_compatible_with_state() -> None:
    plan = make_query_plan("Find a laptop")
    state: SalesAgentState = {**create_initial_state(plan.original_message), "query_plan": plan}
    assert state["query_plan"] is plan
    assert state["query_plan"].max_price == Decimal("150000")


def test_add_messages_reducer_appends_and_replaces_by_id() -> None:
    initial = [HumanMessage(content="hello", id="message-1")]
    appended = add_messages(initial, [AIMessage(content="Hi!", id="message-2")])
    replaced = add_messages(appended, [HumanMessage(content="bonjour", id="message-1")])

    assert [message.content for message in replaced] == ["bonjour", "Hi!"]


def test_partial_updates_do_not_require_unrelated_keys() -> None:
    update: SalesAgentState = {
        "status": ExecutionStatus.RUNNING,
        "current_step": ExecutionStep.SEARCH_PRODUCTS,
    }
    assert set(update) == {"status", "current_step"}


def test_error_and_status_have_controlled_serializable_values() -> None:
    error = StateError(
        code="catalog_unavailable",
        message="Catalog could not be reached",
        step=ExecutionStep.SEARCH_PRODUCTS,
        retryable=True,
    )
    state: SalesAgentState = {"status": ExecutionStatus.FAILED, "errors": [error]}

    assert state["status"].value == "failed"
    assert error.model_dump(mode="json")["step"] == "search_products"


def test_conversation_states_are_isolated() -> None:
    first = create_initial_state("first")
    second = create_initial_state("second")
    first["errors"].append(
        StateError(code="test", message="test error", step=ExecutionStep.ANALYZE_REQUEST)
    )
    first["last_product_ids"].append(1)

    assert first["session_id"] != second["session_id"]
    assert second["errors"] == []
    assert second["last_product_ids"] == []


def test_langgraph_checkpoint_round_trip() -> None:
    plan = make_query_plan("Find a laptop")
    state: SalesAgentState = {**create_initial_state(plan.original_message), "query_plan": plan}
    serializer = JsonPlusSerializer()

    type_name, payload = serializer.dumps_typed(state)
    restored = serializer.loads_typed((type_name, payload))

    assert restored["messages"][0].content == plan.original_message
    assert restored["query_plan"] == plan
    assert restored["status"] is ExecutionStatus.READY


def test_initializer_has_no_shared_mutable_defaults() -> None:
    first = create_initial_state("one", session_id="one")
    second = create_initial_state("two", session_id="two")

    assert first["messages"] is not second["messages"]
    assert first["errors"] is not second["errors"]
    assert first["missing_info"] is not second["missing_info"]
    assert first["last_product_ids"] is not second["last_product_ids"]
