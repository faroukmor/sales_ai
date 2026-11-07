"""Restricted serializer configuration for trusted application checkpoint types."""

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


def chat_checkpoint_serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("app.schemas.query_plan", "Intent"),
            ("app.schemas.query_plan", "Language"),
            ("app.schemas.query_plan", "QueryPlan"),
            ("app.schemas.query_plan", "QuerySpecificationConstraint"),
            ("app.schemas.query_plan", "SpecificationOperator"),
            ("app.schemas.product", "ProductRead"),
            ("app.schemas.product", "ProductSpecRead"),
            ("app.schemas.promotion", "PromotionRead"),
            ("app.schemas.sales_functions", "RecommendationItem"),
            ("app.agents.state", "ExecutionStatus"),
            ("app.agents.state", "ExecutionStep"),
            ("app.agents.state", "StateError"),
            ("app.agents.state", "EvidenceItem"),
            ("app.agents.state", "ComparisonValue"),
            ("app.agents.state", "ComparisonRow"),
            ("app.agents.state", "ProductComparison"),
        ]
    )
