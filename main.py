# main.py: نقطة التركيب (composition root) وواجهة سطر أوامر للتجربة اليدوية
import argparse
import logging
from pathlib import Path

from core.config import DB_PATH, KNOWLEDGE_DIR
from db.database import connect, init_schema
from handlers.comparison_handler import ComparisonHandler
from handlers.explanation_handler import ExplanationHandler
from handlers.search_handler import SearchHandler
from models.query_plan import Intent
from rag.embedding_service import EmbeddingService
from rag.knowledge_ingestor import KnowledgeIngestor
from rag.knowledge_retriever import KnowledgeRetriever
from repositories.product_repository import ProductRepository
from services.answer_generator import AnswerGenerator
from services.answer_validator import AnswerValidator
from services.chat_service import ChatService
from services.product_comparator import ProductComparator
from services.query_analyzer import QueryAnalyzer
from services.response_builder import ResponseBuilder


def build_chat_service(conn) -> ChatService:
    embedder = EmbeddingService()
    products = ProductRepository(conn)
    handlers = {
        Intent.PRODUCT_SEARCH: SearchHandler(products),
        Intent.COMPARISON: ComparisonHandler(products, ProductComparator()),
        Intent.EXPLANATION: ExplanationHandler(KnowledgeRetriever(conn, embedder)),
    }
    return ChatService(
        analyzer=QueryAnalyzer(known_brands=products.list_brands()),
        handlers=handlers,
        builder=ResponseBuilder(),
        generator=AnswerGenerator(),
        validator=AnswerValidator(),
    )


def print_response(response) -> None:
    print(f"\n[{response.status.value}] {response.answer}")
    for p in response.products:
        stock = {True: "in stock", False: "out of stock", None: "stock unknown"}[p.in_stock]
        price = f"{p.price:g} {p.currency}" if p.price is not None else "price not recorded"
        print(f"  - {p.name} | {price} | {stock}")
    for s in response.sources:
        print(f"  source: {s.label}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Géant Sales AI (prototype CLI)")
    parser.add_argument("--ingest", nargs="?", const=str(KNOWLEDGE_DIR), metavar="FOLDER",
                        help="embed .txt/.md files into the knowledge base, then exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    conn = connect(DB_PATH)
    try:
        init_schema(conn)
        if args.ingest:
            report = KnowledgeIngestor(conn, EmbeddingService()).add_directory(Path(args.ingest))
            for name, count in report.items():
                print(f"{name}: {count} chunk(s)")
            return
        service = build_chat_service(conn)
        print("Géant Sales AI. Type 'exit' to quit.")
        while True:
            message = input("you> ").strip()
            if message.lower() in {"exit", "quit"}:
                break
            if message:
                print_response(service.handle_message(message))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
