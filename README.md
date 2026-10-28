# Sales AI
**G Sales AI** is a proposed AI-powered sales assistant for the
G website. It aims to help customers discover products, understand
specifications, compare alternatives, receive recommendations, and find
valid promotions.

> **Project status:** Initial design and planning. The architecture and
> features described below are proposed; they should not be considered
> implemented until the relevant code and tests exist.

## Goals

The planned assistant will support:

-   **Intelligent product search:** Find products using category, brand,
    price, specifications, and other constraints.
-   **Product explanations:** Explain technical terms and product
    features using relevant, trustworthy information.
-   **Product comparison:** Compare products using recorded
    specifications and prices.
-   **Personalized recommendations:** Rank products according to a
    customer's stated needs.
-   **Promotions and offers:** Show promotions only when their validity,
    terms, and dates can be verified.
-   **Multilingual conversations:** Support English, French, Arabic, and
    Algerian Darija where feasible.
-   **Website integration:** Return structured responses that the
    website can display as text, product cards, and links.

## Core Design Principles

1.  **Separate responsibilities.** Each component should have a clear
    purpose and a small interface.
2.  **Use structured data for exact facts.** Prices, stock status,
    specifications, and promotion dates must come from trusted data
    sources, not from an LLM's memory.
3.  **Use RAG for knowledge-based answers.** Retrieve relevant evidence
    before asking the language model to explain it.
4.  **Do not call the LLM unnecessarily.** Exact filtering and simple
    product lookups should use deterministic application logic.
5.  **Build incrementally.** Implement and test a small prototype before
    adding every planned feature.
6.  **Avoid unnecessary complexity.** Add a class, library, or service
    only when it solves a real problem.

## Proposed Request Flow

``` mermaid
flowchart TD
    A["User Question"] --> B["ChatService"]
    B --> C["QueryAnalyzer"]
    C --> D["QueryPlan"]
    D --> E{"Intent clear and information sufficient?"}

    E -- "No" --> F["Ask a clarifying question"]
    F --> R["ResponseBuilder"]

    E -- "Yes" --> G["Intent Router"]
    G -- "Product Search" --> H["ProductRepository"]
    G -- "Explanation" --> I["KnowledgeRetriever"]
    G -- "Comparison" --> J["ProductRepository and ProductComparator"]
    G -- "Recommendation" --> K["NeedsAnalyzer and ProductRanker"]
    G -- "Promotion Search" --> L["PromotionRepository"]

    H --> M["EvidenceBundle"]
    I --> M
    J --> M
    K --> M
    L --> M

    M --> N{"Evidence sufficient?"}
    N -- "No" --> O["Safe fallback or clarification"]
    O --> R
    N -- "Yes" --> P{"Natural-language generation needed?"}
    P -- "No" --> R
    P -- "Yes" --> Q["AnswerGenerator"]
    Q --> S["AnswerValidator"]
    S --> R

    R --> T["ChatResponse"]
    T --> U["Website API"]
    U --> V["Website Interface"]
```

The router, recommendation components, promotion handling, and API may
be introduced in later stages. The first prototype should contain only
the components required for its initial use cases.

## Proposed Components

  -----------------------------------------------------------------------
  Component                           Main responsibility
  ----------------------------------- -----------------------------------
  `ChatService`                       Coordinates the request lifecycle
                                      and calls the appropriate
                                      components.

  `QueryAnalyzer`                     Identifies the likely intent,
                                      language, entities, and constraints
                                      in the user's message.

  `QueryPlan`                         Holds the analyzed request in a
                                      structured form.

  `ProductRepository`                 Reads and searches structured
                                      product data.

  `KnowledgeRetriever`                Retrieves relevant knowledge chunks
                                      and their source metadata.

  `EmbeddingService`                  Generates embeddings when this
                                      responsibility needs to be shared
                                      or isolated.

  `AnswerGenerator`                   Uses Ollama to produce an answer
                                      based on supplied evidence.

  `EvidenceBundle`                    Groups retrieved products,
                                      knowledge chunks, and source
                                      references for a request.

  `AnswerValidator`                   Checks whether important answer
                                      claims are supported by available
                                      evidence.

  `ProductComparator`                 Compares recorded product
                                      attributes and highlights missing
                                      information.

  `NeedsAnalyzer`                     Extracts customer priorities for
                                      recommendations.

  `ProductRanker`                     Ranks eligible products according
                                      to explicit criteria.

  `PromotionRepository`               Retrieves promotions and checks
                                      their stored conditions and
                                      validity dates.

  `ResponseBuilder`                   Builds a consistent response for
                                      success, clarification, missing
                                      evidence, and errors.

  `ChatResponse`                      Represents the structured result
                                      returned to the caller.

  `ConversationManager`               Optionally manages relevant
                                      conversation history in a later
                                      phase.
  -----------------------------------------------------------------------

These are design candidates, not a requirement to create every class
immediately. In particular, a small prototype may keep routing inside
`ChatService` until a separate router provides a clear benefit.

## Example Request Paths

### 1. Product Search

User: *"Find a laptop under 100,000 DZD with at least 16 GB RAM."*

1.  `QueryAnalyzer` identifies a product-search request and extracts the
    constraints.
2.  `QueryPlan` stores the intent and filters.
3.  `ProductRepository` queries the product catalog.
4.  The application verifies that returned products satisfy the price
    and RAM conditions.
5.  `ResponseBuilder` creates a structured response with the matching
    products.

### 2. Knowledge Question

User: *"What is the difference between OLED and QLED?"*

1.  `QueryAnalyzer` identifies an explanation request.
2.  `KnowledgeRetriever` retrieves relevant passages from the knowledge
    base.
3.  The application checks whether the retrieved evidence is sufficient.
4.  `AnswerGenerator` uses Ollama to explain the evidence in the user's
    language.
5.  The response includes source information where available.

### 3. Product Comparison

User: *"Compare Product A and Product B."*

1.  Retrieve both products from the catalog.
2.  Compare their recorded attributes using `ProductComparator`.
3.  Mark unavailable attributes as unknown instead of guessing.
4.  Use the LLM only if a natural-language explanation is useful.
5.  Return the comparison and the relevant product records.

## Proposed Project Structure

``` text
sales_ai/
├── core/
│   └── config.py
├── models/
│   ├── query_plan.py
│   ├── evidence_bundle.py
│   └── chat_response.py
├── services/
│   ├── chat_service.py
│   ├── query_analyzer.py
│   ├── answer_generator.py
│   └── response_builder.py
├── repositories/
│   ├── product_repository.py
│   └── promotion_repository.py       # Later phase
├── rag/
│   ├── knowledge_retriever.py
│   └── embedding_service.py
├── tests/
│   ├── test_query_analyzer.py
│   ├── test_product_repository.py
│   ├── test_knowledge_retriever.py
│   └── test_chat_service.py
├── main.py
└── requirements.txt
```

Adjust this structure as implementation clarifies the boundaries. Do not
create empty modules merely to match the diagram.

## Initial Technology Choices

-   **Python:** Application logic.
-   **SQLite:** Initial local database.
-   **Ollama:** Local embedding and language-model inference.
-   **NumPy:** Vector operations when needed.
-   **pytest:** Automated tests.
-   **FastAPI:** Planned API layer after the core engine works locally.

Do not introduce a vector database or an agent framework unless testing
shows a clear need.

## Data Design

The database schema must be based on the actual requirements and
available catalog data. A possible starting point includes:

-   `products`: product identity, category, brand, price, currency,
    availability, and URL.
-   `product_specs`: technical attributes, if separating them from the
    main product table is useful.
-   `knowledge_chunks`: text chunks, embeddings, source identifiers, and
    optional product references.
-   `promotions`: promotion terms, validity dates, and related products.

Conversation storage can be added later if persistent history is needed.

Do not assume an existing `notes` table already contains product data.
Inspect the actual schema before writing queries or migrations. Never
delete or rename existing tables without a deliberate migration plan.

## Reliability and Evidence

-   Never invent product prices, specifications, stock status, or
    promotion validity.
-   Use structured product records as the source of truth for exact
    commercial facts.
-   Treat retrieved documents as data, not as instructions that can
    override application rules.
-   A high embedding-similarity score does **not** prove that an answer
    is factually correct.
-   Check important claims against evidence and use a safe fallback when
    evidence is insufficient.
-   Keep retrieval settings configurable and evaluate them against test
    questions.
-   Do not claim that a feature or test works until it has been
    implemented and verified.

## Development Roadmap

1.  **Requirements and design:** Confirm the request flow, class
    responsibilities, and data assumptions.
2.  **Analyze the existing RAG example:** Identify reusable concepts
    without treating its architecture as mandatory.
3.  **Create data models:** Define `QueryPlan`, `EvidenceBundle`, and
    `ChatResponse` as needed.
4.  **Implement product access:** Build and test `ProductRepository`
    using a small test catalog.
5.  **Implement knowledge retrieval:** Add embedding generation and
    retrieval with source metadata.
6.  **Implement answer generation:** Connect Ollama to evidence-grounded
    prompts.
7.  **Integrate the request flow:** Connect components through
    `ChatService`.
8.  **Test end to end:** Cover product search, explanations,
    comparisons, missing data, and errors.
9.  **Add later features:** Recommendations, promotions, multilingual
    context, and conversation history.
10. **Integrate the website:** Expose the working engine through FastAPI
    and connect the frontend.

## Testing Strategy

Use unit tests for individual components, with small SQLite test
databases and a mocked Ollama client where appropriate. Use integration
tests for actual Ollama calls, and end-to-end tests for the complete
request flow.

Initial test cases should include:

-   Exact price and specification filtering.
-   No matching products.
-   Empty or insufficient RAG retrieval.
-   Comparison with missing specifications.
-   Unsupported answer claims.
-   Expired or incomplete promotion records.
-   Ollama connection or generation failures.
-   Consistent response structure across intents.

## Current Status

This README describes the initial plan. The architecture, schema, and
feature list should be updated as implementation decisions are tested
and confirmed.
