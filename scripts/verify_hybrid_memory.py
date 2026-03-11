import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.memory.api_schema import MemoryQueryRequest, MemorySearchRequest, MemoryStoreRequest
from core.memory.indexer import FAISSIndexer
from core.memory.ingest import MemoryIngester
from core.memory.llm_client import init_backends
from core.memory.rag_reasoner import RAGReasoner
from core.memory.retriever import MemoryRetriever
from core.memory.sqlite_manager import SQLiteManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify-memory")

async def verify_flow():
    # 1. Setup
    data_dir = project_root / "data" / "test_memory"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "test_app_state.db"
    index_path = data_dir / "test_index"

    if db_path.exists():
        db_path.unlink()
    if index_path.exists():
        import shutil
        shutil.rmtree(index_path)

    sqlite_manager = SQLiteManager(db_path=str(db_path))
    indexer = FAISSIndexer(index_path=str(index_path))

    # Initialize backends (mocking if necessary)
    # For testing, we might want to use a mock LLM client
    init_backends()

    ingester = MemoryIngester(indexer=indexer, sqlite_manager=sqlite_manager)
    retriever = MemoryRetriever(indexer=indexer, sqlite_manager=sqlite_manager)
    reasoner = RAGReasoner(retriever=retriever)

    # 2. Ingest
    logger.info("Ingesting test memory...")
    store_request = MemoryStoreRequest(
        transcript="I put my glasses on the bedside table next to the blue lamp.",
        summary="Glasses on bedside table",
        session_id="test-session-1",
        device_id="test-device-1"
    )

    ingest_response = await ingester.ingest(store_request)
    logger.info(f"Ingest response: {ingest_response}")

    # 3. Search
    logger.info("Searching for memory...")
    search_request = MemorySearchRequest(query="Where are my glasses?", k=1)
    search_response = await retriever.search(search_request)
    logger.info(f"Search results: {search_response.results}")

    if not search_response.results:
        logger.error("No search results found!")
        return False

    # 4. Reason
    logger.info("Querying RAG reasoner...")
    query_request = MemoryQueryRequest(query="Where did I leave my glasses?")
    query_response = await reasoner.query(query_request)
    logger.info(f"RAG response: {query_response.answer}")

    # 5. Cleanup
    logger.info("Verifying maintenance...")
    from core.memory.maintenance import MemoryMaintenance
    maintenance = MemoryMaintenance(indexer=indexer)
    # Note: MemoryMaintenance needs sqlite_manager too now

    # We'll fix maintenance.py next, but let's see it fail or partially work
    try:
        report = await maintenance.run()
        logger.info(f"Maintenance report: {report}")
    except Exception as e:
        logger.error(f"Maintenance failed as expected: {e}")

    return True

if __name__ == "__main__":
    asyncio.run(verify_flow())
