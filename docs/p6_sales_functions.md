# P6 intelligent sales functions

P6 keeps natural-language interpretation separate from business execution. A validated
`QueryPlan` is translated into controlled repository filters; no model-generated SQL is
accepted. SQLAlchemy binds all values as parameters.

## Product search

`ProductSearchTool.search` is the primary `QueryPlan` adapter. It supports category, brand,
price bounds, DZD/DA normalization, stock, numeric RAM/storage/screen/refresh-rate constraints,
sorting, and limits. `search_filters` additionally accepts controlled exact textual
specifications such as `processor`. An absent result is reported as `no_results`; invalid or
unsupported constraints are reported as `invalid_filters`. Unknown prices and stock values
are never treated as zero or available.

## Comparison

`ProductComparisonTool` resolves IDs, exact/partial catalog names, or `last_product_ids`.
Ambiguous and missing references are returned explicitly. Rows contain catalog values only;
missing cells use `N/A`. The tool does not calculate an overall winner. Promotion rows contain
only active offers eligible for the compared product.

## Recommendations

`RecommendationService` first invokes the same hard-constraint search. Eligible candidates
are ranked deterministically with weights: price 0.35, requested specification coverage 0.45,
and known in-stock availability 0.20. Scores are normalized to `[0, 1]`, rounded to four
decimal places, and tied by product ID. The response includes reasons and missing relevant
specifications. No LLM participates in scoring.

## Promotions

`PromotionsTool` uses `PromotionRepository` with an inclusive UTC calendar-date policy.
Expired, future, and unknown-validity records are excluded. Global, category, and
product-specific eligibility is evaluated without modifying prices or assuming that offers
can be combined. Missing descriptions or conditions are reported through
`incomplete_promotion_ids`.

## Graph boundary

`build_sales_functions_graph` is the deterministic P6 subgraph. It routes the existing enum
values `product_search`, `comparison`, `recommendation`, and `promotion_search`, runs the
matching business function, and validates evidence identifiers before ending. The repository
does not yet contain the P5 conversational graph, checkpointer, chat endpoint, or LLM response
composition node; those concerns are intentionally not fabricated inside P6.
