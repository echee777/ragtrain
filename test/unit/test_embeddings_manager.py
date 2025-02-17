import pytest
import numpy as np
from ragtrain.embeddings import (
    EmbeddingsManager, ChromaVectorStore,
    GeneralEmbedder, SubjectDomain, EmbeddingMatch, BiobertEmbedder
)


@pytest.fixture
def vector_store():
    store = ChromaVectorStore(collection_name="test_collection", get_or_create=True)
    yield store
    store.clear()
    store.reset()


@pytest.fixture
def embedders():
    biology_embedder = BiobertEmbedder()
    general_embedder = GeneralEmbedder()

    # Start embedders
    # In real life you would start() just-in-time
    biology_embedder.start()
    general_embedder.start()

    yield {
        "biology": biology_embedder,
        "general": general_embedder
    }

    # Stop embedders
    biology_embedder.stop()
    general_embedder.stop()


@pytest.fixture
def manager(vector_store, embedders):
    manager = EmbeddingsManager(vector_store)
    manager.register_embedder(SubjectDomain.BIOLOGY, embedders["biology"])
    manager.register_embedder(SubjectDomain.GENERAL, embedders["general"])
    return manager


def test_write_and_read_embeddings(manager):
    """Test basic writing and reading of embeddings"""
    # Create some test documents
    texts = [
        "The cell is the basic unit of life",
        "DNA contains genetic information",
        "Proteins are made of amino acids"
    ]

    # Create embeddings
    manager.create_embeddings(texts, SubjectDomain.BIOLOGY)

    # Search for similar embeddings
    query = "What is the role of DNA in cells?"
    results = manager.get_top_k_embeddings(k=2, domain=SubjectDomain.BIOLOGY, question=query)

    # Verify results
    assert len(results) == 2
    assert isinstance(results[0], EmbeddingMatch)
    assert results[0].content in texts
    assert isinstance(results[0].score, float)


def test_top_k_search(manager):
    """Test searching for top k embeddings"""
    # Create test documents
    texts = [
        "Document 1: Biology is the science of life",
        "Document 2: More biology",
        "Document 3: Even more biology",
        "Document 4: Final biology document"
    ]

    # Create embeddings
    manager.create_embeddings(texts, SubjectDomain.BIOLOGY)

    # Search for top 2 results
    results = manager.get_top_k_embeddings(
        k=2,
        domain=SubjectDomain.BIOLOGY,
        question="What is biology?"
    )

    # Verify we get exactly k results and they're ordered by score
    assert len(results) == 2
    assert results[0].score >= results[1].score


def test_best_embedder_selection(manager, embedders):
    """Test selection of the best embedder for a question"""
    # Biology-related question
    biology_question = "What is the structure of DNA in cells?"
    embedder = manager.get_best_embedder(biology_question)
    assert embedder == embedders["biology"]

    # General question
    general_question = "What is the weather like today?"
    embedder = manager.get_best_embedder(general_question)
    assert embedder == embedders["general"]


def test_vector_store_clear(vector_store):
    """Test that vector store clear works properly"""
    # Add some embeddings
    texts = ["test1", "test2"]
    embeddings = np.random.rand(2, 768).tolist()  # Generate 768-dimensional embeddings
    vector_store.add_embeddings(texts, embeddings)

    # Clear the store
    vector_store.clear()

    # Search should return empty results
    results = vector_store.search(embeddings[0], k=1)
    assert len(results) == 0


def test_embedder_memory_management():
    """Test embedder start/stop functionality"""
    embedder = GeneralEmbedder()

    # Initially not loaded
    assert not embedder.is_loaded

    # Should raise error when trying to embed before starting
    with pytest.raises(RuntimeError):
        embedder.embed("test text")

    # Start embedder
    embedder.start()
    assert embedder.is_loaded

    # Should work after starting
    embeddings = embedder.embed("test text")

    # Stop embedder
    embedder.stop()
    assert not embedder.is_loaded

    # Should raise error after stopping
    with pytest.raises(RuntimeError):
        embedder.embed("test text")


def test_biobert_embedder():
    """Test BioBERT embedder functionality"""
    embedder = BiobertEmbedder()

    # Test start/stop
    assert not embedder.is_loaded
    embedder.start()
    assert embedder.is_loaded

    # Test single embedding
    text = "The protein kinase regulates cell division."
    embedding = embedder.embed(text)
    assert len(embedding) == 768  # BioBERT base has 768 dimensions

    # Test batch embedding
    texts = [
        "The DNA double helix contains genetic information.",
        "Enzymes catalyze biochemical reactions."
    ]
    embeddings = embedder.embed_batch(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768

    # Verify keywords are biology-related
    keywords = embedder.get_keywords()
    assert len(keywords) > 0
    assert "DNA" in keywords
    assert "protein" in keywords

    # Test stop
    embedder.stop()
    assert not embedder.is_loaded
    assert embedder.model is None
    assert embedder.tokenizer is None



def test_invalid_search_k(manager):
    """Test searching with invalid k values"""
    texts = ["test document"]
    manager.create_embeddings(texts, SubjectDomain.BIOLOGY)

    # Search with k=0 should return empty list
    results = manager.get_top_k_embeddings(
        k=0,
        domain=SubjectDomain.BIOLOGY,
        question="test"
    )
    assert len(results) == 0

    # Search with k larger than number of documents
    results = manager.get_top_k_embeddings(
        k=10,
        domain=SubjectDomain.BIOLOGY,
        question="test"
    )
    assert len(results) == 1  # Should only return available documents