import pytest
from ragtrain.embeddings import ChromaVectorStore
from ragtrain.embeddings.vector_store import EmbeddingMatch


@pytest.fixture
def vector_store():
    store = ChromaVectorStore(collection_name="test_collection")  # in-memory for tests
    yield store
    store.clear()


def test_add_and_search_embeddings(vector_store):
    """Test basic adding embeddings and searching"""
    texts = ["test1", "test2"]
    embeddings = [
        [1.0, 0.0, 0.0],  # Simple test vectors
        [0.0, 1.0, 0.0]
    ]

    vector_store.add_embeddings(texts, embeddings)

    # Search with first vector
    results = vector_store.search([1.0, 0.0, 0.0], k=1)
    assert len(results) == 1
    assert results[0].content == "test1"
    assert isinstance(results[0], EmbeddingMatch)


def test_search_with_metadata(vector_store):
    """Test searching with metadata"""
    texts = ["test1", "test2"]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0]
    ]
    metadata = [
        {"type": "doc1"},
        {"type": "doc2"}
    ]

    vector_store.add_embeddings(texts, embeddings, metadata)

    results = vector_store.search([1.0, 0.0, 0.0], k=1)
    assert results[0].metadata["type"] == "doc1"


def test_empty_search(vector_store):
    """Test searching when store is empty"""
    results = vector_store.search([1.0, 0.0, 0.0], k=1)
    assert len(results) == 0


def test_clear(vector_store):
    """Test clearing the store"""
    texts = ["test1"]
    embeddings = [[1.0, 0.0, 0.0]]

    vector_store.add_embeddings(texts, embeddings)
    vector_store.clear()

    results = vector_store.search([1.0, 0.0, 0.0], k=1)
    assert len(results) == 0


def test_invalid_k(vector_store):
    """Test searching with invalid k values"""
    texts = ["test1"]
    embeddings = [[1.0, 0.0, 0.0]]
    vector_store.add_embeddings(texts, embeddings)

    # k <= 0 should return empty list
    results = vector_store.search([1.0, 0.0, 0.0], k=0)
    assert len(results) == 0

    results = vector_store.search([1.0, 0.0, 0.0], k=-1)
    assert len(results) == 0


def test_chroma_persistence(tmp_path):
    """Test persistence to disk"""
    # Create store with persistence
    persist_dir = str(tmp_path / "chroma")
    store = ChromaVectorStore(
        collection_name="test_persist",
        persist_directory=persist_dir
    )

    # Add some data
    texts = ["test1"]
    embeddings = [[1.0, 0.0, 0.0]]
    store.add_embeddings(texts, embeddings)

    # Create new store with same persist directory
    store2 = ChromaVectorStore(
        collection_name="test_persist",
        persist_directory=persist_dir,
        get_or_create=True,
    )

    # Verify data is still there
    results = store2.search([1.0, 0.0, 0.0], k=1)
    assert len(results) == 1
    assert results[0].content == "test1"
