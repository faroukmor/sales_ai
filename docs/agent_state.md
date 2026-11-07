# Sales agent state contract

`SalesAgentState` is a `TypedDict(total=False)`. Nodes return partial dictionaries and must
not copy the complete state. Missing result keys mean “not processed”; present empty lists
mean “processed successfully with no results.” `messages` is the only reducer-managed key
and uses LangGraph's `add_messages` reducer.

The state contains Pydantic read/value schemas, not SQLAlchemy objects. It must never contain
database sessions, repositories, LLM clients, credentials, exceptions, or a second copy of
the transcript. LangGraph's checkpoint serializer supports the LangChain messages, Pydantic
models, enums, dates, and decimals used here.

## Key ownership

| Node | Required inputs | Owned outputs | Expected recorded errors |
|---|---|---|---|
| `analyze_request` | `messages` | `query_plan`, `intent`, `language`, `missing_info`, `status`, `current_step`, `errors` | invalid input, structured-output/validation failure, model unavailable |
| `route_intent` | `query_plan`, `intent`, `missing_info` | `status`, `current_step` | unsupported or inconsistent intent |
| `search_products` | `query_plan` | `products`, `promotions`, `last_product_ids`, `current_step`, `errors` | invalid filters, catalog unavailable |
| `compare_products` | `query_plan`, `products` and/or `last_product_ids` | `comparison`, `evidence`, `current_step`, `errors` | too few/resolvable products, incompatible data |
| `retrieve_knowledge` | `query_plan` | `evidence`, `current_step`, `errors` | retrieval unavailable, no relevant evidence |
| `rank_recommendations` | `query_plan`, `products` | `recommendations`, `products`, `last_product_ids`, `evidence`, `current_step`, `errors` | insufficient candidates, ranking failure |
| `lookup_promotions` | `query_plan` | `promotions`, `evidence`, `current_step`, `errors` | unknown/ambiguous product, ineligible offer |
| `validate_evidence` | `evidence`; relevant business result | `evidence`, `status`, `current_step`, `errors` | unsupported claim, stale/malformed source |
| `compose_response` | `messages`, `query_plan`; validated route outputs | `answer`, `messages`, `status`, `current_step`, `errors` | generation failure, insufficient grounded data |
| `clarify` | `messages`, `missing_info`; optionally `query_plan` | `answer`, `messages`, `status`, `current_step`, `errors` | missing clarification question/context |

Each node appends a safe `StateError` by returning a newly built `errors` list because no
error reducer is defined. A successful node writes an empty owned collection when it ran and
found nothing; it does not invent catalog data. Nodes should set `FAILED` only for terminal
failures and `NEEDS_CLARIFICATION` only when user input is required.

## Keys

Conversation keys are `messages`, `session_id`, and optional `user_id`. Understanding keys
are `query_plan`, `intent`, `language`, and `missing_info`. Business keys are `products`,
`comparison`, `promotions`, `recommendations`, and `evidence`. Response/execution keys are
`answer`, `status`, `errors`, `current_step`, and `last_product_ids`.
