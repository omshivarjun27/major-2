import asyncio
import logging
import shutil
from pathlib import Path

from core.memory.api_schema import MemorySearchRequest, MemoryStoreRequest
from core.memory.embeddings import AudioEmbedder, MockTextEmbedder, MultimodalFuser
from core.memory.indexer import MockFAISSIndexer
from core.memory.ingest import MemoryIngester
from core.memory.retriever import MemoryRetriever
from core.memory.sqlite_manager import SQLiteManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-memory-integration")

async def run_test():
    # Cleanup previous test data
    data_dir = Path("./data/test_memory")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = str(data_dir / "test_app_state.db")
    index_path = str(data_dir / "test_index")

    logger.info("Initializing components...")
    sqlite = SQLiteManager(db_path=db_path)
    # Use Mock indexer and embedder for testing without heavy deps
    indexer = MockFAISSIndexer(index_path=index_path, dimension=384)
    text_embedder = MockTextEmbedder(dimension=384)
    audio_embedder = AudioEmbedder(text_embedder=text_embedder, enabled=True)
    fuser = MultimodalFuser(text_embedder=text_embedder, audio_embedder=audio_embedder)

    ingester = MemoryIngester(
        indexer=indexer,
        sqlite_manager=sqlite,
        text_embedder=text_embedder,
        fuser=fuser
    )

    retriever = MemoryRetriever(
        indexer=indexer,
        sqlite_manager=sqlite,
        text_embedder=text_embedder
    )

    # 1. Ingest some memories
    logger.info("Ingesting memories...")
    memories = [
        {"transcript": "I put my blue keys on the kitchen table", "session_id": "session_1", "user_label": "Keys location"},
        {"transcript": "The weather is sunny today", "session_id": "session_1"},
        {"transcript": "I need to buy milk and eggs", "session_id": "session_2", "user_label": "Shopping list"},
        {"transcript": "My doctor appointment is at 3pm tomorrow", "session_id": "session_2"}
    ]

    ids = []
    for mem in memories:
        request = MemoryStoreRequest(**mem)
        response = await ingester.ingest(request, consent_given=True)
        logger.info(f"Stored memory: {response.summary} (ID: {response.id})")
        ids.append(response.id)

    # 2. Search memories
    logger.info("Searching memories...")

    # Search for keys
    search_request = MemorySearchRequest(query="Where are my keys?", k=2)
    results = await retriever.search(search_request)

    logger.info("Search results for 'Where are my keys?':")
    for hit in results.results:
        logger.info(f" - [{hit.score:.4f}] {hit.summary} (ID: {hit.id}, label: {hit.user_label})")

    assert len(results.results) > 0
    assert "keys" in results.results[0].summary.lower()

    # 3. Filter by session
    logger.info("Searching with session filter (session_2)...")
    search_request_filtered = MemorySearchRequest(query="shopping", k=2, session_id="session_2")
    results_filtered = await retriever.search(search_request_filtered)

    logger.info("Filtered search results:")
    for hit in results_filtered.results:
        logger.info(f" - [{hit.score:.4f}] {hit.summary} (ID: {hit.id})")

    for hit in results_filtered.results:
        # Verify it's from session_2
        mem_record = retriever.get_memory(hit.id)
        assert mem_record.session_id == "session_2"

    # 4. Get recent memories
    logger.info("Getting recent memories...")
    recent = retriever.get_recent_memories(hours=1, limit=10)
    logger.info(f"Found {len(recent)} recent memories")
    assert len(recent) == 4

    logger.info("Integration test PASSED!")

if __name__ == "__main__":
    asyncio.run(run_test())
