import pytest
from pathlib import Path
import tempfile
import shutil

from ragtrain.document_store import FileSystemDocumentStore



@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def doc_store(temp_dir):
    """Create document store instance using temp directory"""
    return FileSystemDocumentStore(temp_dir)


def test_store_and_retrieve_document(doc_store):
    """Test basic document storage and retrieval"""
    doc_hash = "123abc"
    content = "Test document content"

    # Store document
    stored_path = doc_store.store_document(doc_hash, content)
    assert stored_path.exists()
    assert stored_path.parent.name == doc_hash

    # Retrieve document
    retrieved = doc_store.get_document(doc_hash)
    assert retrieved == content


def test_store_with_custom_filename(doc_store):
    """Test storing document with custom filename"""
    doc_hash = "456def"
    content = "Custom filename content"
    filename = "custom.txt"

    stored_path = doc_store.store_document(doc_hash, content, filename)
    assert stored_path.name == filename

    retrieved = doc_store.get_document(doc_hash, filename)
    assert retrieved == content


def test_delete_document(doc_store):
    """Test document deletion"""
    doc_hash = "789ghi"
    content = "Document to delete"

    # Store and verify
    doc_store.store_document(doc_hash, content)
    assert doc_hash in doc_store.list_documents()

    # Delete and verify
    doc_store.delete_document(doc_hash)
    assert doc_hash not in doc_store.list_documents()

    # Check directory is gone
    doc_dir = doc_store.base_dir / doc_hash
    assert not doc_dir.exists()


def test_list_documents(doc_store):
    """Test listing all documents"""
    hashes = ["abc123", "def456", "ghi789"]
    content = "Test content"

    # Store multiple documents
    for doc_hash in hashes:
        doc_store.store_document(doc_hash, content)

    # List and verify
    stored_hashes = doc_store.list_documents()
    assert set(stored_hashes) == set(hashes)


def test_get_nonexistent_document(doc_store):
    """Test error when getting non-existent document"""
    with pytest.raises(FileNotFoundError):
        doc_store.get_document("nonexistent")


def test_delete_nonexistent_document(doc_store):
    """Test error when deleting non-existent document"""
    with pytest.raises(FileNotFoundError):
        doc_store.delete_document("nonexistent")


def test_multiple_files_same_hash(doc_store):
    """Test storing multiple files under same hash"""
    doc_hash = "multi123"
    content1 = "First file content"
    content2 = "Second file content"

    # Store two files under same hash
    doc_store.store_document(doc_hash, content1, "file1.txt")
    doc_store.store_document(doc_hash, content2, "file2.txt")

    # Retrieve and verify both files
    retrieved1 = doc_store.get_document(doc_hash, "file1.txt")
    retrieved2 = doc_store.get_document(doc_hash, "file2.txt")

    assert retrieved1 == content1
    assert retrieved2 == content2


def test_unicode_content(doc_store):
    """Test handling of Unicode content"""
    doc_hash = "unicode123"
    content = "Unicode content: 你好, שָׁלוֹם, مرحبا"

    # Store and retrieve
    doc_store.store_document(doc_hash, content)
    retrieved = doc_store.get_document(doc_hash)

    assert retrieved == content
