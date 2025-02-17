import pytest
from unittest.mock import Mock, patch
from transformers import PreTrainedTokenizerBase

from ragtrain.training_manager import TrainingManager
from ragtrain.types import SubjectDomain
from ragtrain.document_store import DocumentStore
from ragtrain.embeddings.manager import EmbeddingsManager


class MockTokenizer:
    """Mock HuggingFace tokenizer for testing"""

    def __init__(self):
        # Special tokens similar to BERT
        self.cls_token_id = 101
        self.sep_token_id = 102
        self.pad_token_id = 0

        # Token ID mapping for consistency
        self._token_map = {}
        self._next_token_id = 200

    def _get_token_id(self, word: str) -> int:
        """Get consistent token ID for a word"""
        if word not in self._token_map:
            self._token_map[word] = self._next_token_id
            self._next_token_id += 1
        return self._token_map[word]

    def encode(self, text: str, add_special_tokens: bool = True, **kwargs) -> list:
        """Mock encode that mimics BERT-like tokenization with consistent IDs"""
        # Simple word-based tokenization for testing
        words = text.split()
        # Convert to token IDs using consistent mapping
        token_ids = [self._get_token_id(word) for word in words]

        if add_special_tokens:
            token_ids = [self.cls_token_id] + token_ids + [self.sep_token_id]

        return token_ids

    def decode(self, token_ids: list, skip_special_tokens: bool = False, **kwargs) -> str:
        """Mock decode that converts token IDs back to text"""
        if skip_special_tokens:
            token_ids = [t for t in token_ids if t not in
                         {self.cls_token_id, self.sep_token_id, self.pad_token_id}]

        # Convert back to words using reverse token mapping
        reverse_map = {v: k for k, v in self._token_map.items()}
        words = [reverse_map.get(t, f"<unk{t}>") for t in token_ids]
        return " ".join(words)


class MockEmbedder:
    """Mock embedder for testing"""

    def __init__(self):
        self.tokenizer = MockTokenizer()

    def get_tokenizer(self) -> PreTrainedTokenizerBase:
        return self.tokenizer

    def embed_text(self, text: str) -> list:
        return [0.1] * 10  # Fixed size mock embedding


@pytest.fixture
def mock_embeddings_manager():
    manager = Mock(spec=EmbeddingsManager)

    # Configure get_subject_domain to return BIOLOGY
    manager.get_subject_domain.return_value = SubjectDomain.BIOLOGY

    # Configure get_best_embedder to return our mock embedder
    embedder = MockEmbedder()
    manager.get_best_embedder.return_value = embedder

    return manager


@pytest.fixture
def mock_document_store():
    store = Mock(spec=DocumentStore)
    return store


@pytest.fixture
def training_manager(mock_embeddings_manager, mock_document_store):
    return TrainingManager(
        embeddings_manager=mock_embeddings_manager,
        document_store=mock_document_store,
        max_chunk_tokens=10  # Small value for testing
    )


def test_chunking_with_special_tokens(training_manager, tmp_path):
    """Test chunking with special tokens handling"""
    # Create document slightly larger than chunk size
    content = "This is a test document that should be split into chunks"
    doc_path = tmp_path / "test.txt"
    doc_path.write_text(content)

    # Process document
    doc_hash = training_manager.process_document(str(doc_path))

    # Get chunks that were processed
    create_embeddings_calls = training_manager.embeddings_manager.create_embeddings.call_args_list

    # Get tokenizer
    tokenizer = training_manager.embeddings_manager.get_best_embedder().get_tokenizer()

    # Verify each chunk
    for call in create_embeddings_calls:
        chunks, _ = call[0]
        for chunk in chunks:
            # Check tokens without special tokens
            token_ids = tokenizer.encode(chunk, add_special_tokens=False)
            assert len(token_ids) <= training_manager.max_chunk_tokens, \
                f"Chunk has {len(token_ids)} tokens (excluding special tokens), limit is {training_manager.max_chunk_tokens}"


def test_chunking_overlap(training_manager, tmp_path):
    """Test that chunks have proper overlap"""
    # Create document with repeating pattern to ensure overlap
    repeated_text = "alpha beta gamma delta " * 10
    doc_path = tmp_path / "test.txt"
    doc_path.write_text(repeated_text)

    # Process document
    doc_hash = training_manager.process_document(str(doc_path))

    # Get all chunks
    create_embeddings_calls = training_manager.embeddings_manager.create_embeddings.call_args_list
    all_chunks = []
    for call in create_embeddings_calls:
        chunks, _ = call[0]
        all_chunks.extend(chunks)

    if len(all_chunks) > 1:
        tokenizer = training_manager.embeddings_manager.get_best_embedder().get_tokenizer()

        for i in range(len(all_chunks) - 1):
            # Get tokens without special tokens
            curr_tokens = tokenizer.encode(all_chunks[i], add_special_tokens=False)
            next_tokens = tokenizer.encode(all_chunks[i + 1], add_special_tokens=False)

            # Check overlap
            curr_end = set(curr_tokens[-3:])  # Last few tokens of current chunk
            next_start = set(next_tokens[:3])  # First few tokens of next chunk

            overlap = curr_end.intersection(next_start)
            assert len(overlap) > 0, (
                f"No overlap found between chunks:\n"
                f"Chunk {i} end: {tokenizer.decode(list(curr_end))}\n"
                f"Chunk {i + 1} start: {tokenizer.decode(list(next_start))}"
            )


def test_empty_document(training_manager, tmp_path):
    """Test handling of empty document"""
    doc_path = tmp_path / "empty.txt"
    doc_path.write_text("")

    doc_hash = training_manager.process_document(str(doc_path))
    assert training_manager.embeddings_manager.create_embeddings.call_count == 0


def test_exact_chunk_size(training_manager, tmp_path):
    """Test document exactly at chunk size"""
    # Create document with exactly max_chunk_tokens words
    words = " ".join([f"word{i}" for i in range(training_manager.max_chunk_tokens)])
    doc_path = tmp_path / "exact.txt"
    doc_path.write_text(words)

    doc_hash = training_manager.process_document(str(doc_path))

    create_embeddings_calls = training_manager.embeddings_manager.create_embeddings.call_args_list
    chunks = create_embeddings_calls[-1][0][0]
    assert len(chunks) == 1  # Should be exactly one chunk


@patch('requests.get')
def test_remote_document(mock_get, training_manager):
    """Test processing remote document"""
    mock_response = Mock()
    mock_response.text = "This is a remote document"
    mock_get.return_value = mock_response

    doc_hash = training_manager.process_document("http://example.com/doc.txt")

    mock_get.assert_called_once_with("http://example.com/doc.txt")
    assert training_manager.document_store.store_document.called
    assert training_manager.embeddings_manager.create_embeddings.called


def test_error_handling(training_manager):
    """Test error handling for various scenarios"""
    # Invalid URL
    with pytest.raises(ValueError):
        training_manager.process_document("invalid://example.com")

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        training_manager.process_document("nonexistent.txt")