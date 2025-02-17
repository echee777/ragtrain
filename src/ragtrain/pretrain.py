"""
Usage:

# Run with defaults (all files in data/training_data
python -m ragtrain.pretrain

# Run with custom pretrain docs file
python -m ragtrain.pretrain config/pretrain_docs.yaml

# With additional custom base directory
python -m ragtrain.pretrain config/pretrain_docs.yaml --base-dir <custom training_data dir>
"""

import argparse
import yaml
import logging
from pathlib import Path
from typing import List

from ragtrain.training_manager import TrainingManager
from ragtrain.document_store import FileSystemDocumentStore
from ragtrain.embeddings import get_default_embeddings_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> List[str]:
    """Load document URLs from YAML config"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if not isinstance(config.get('documents'), list):
        raise ValueError("Config must contain 'documents' list")

    return config['documents']


def setup_training(base_dir: Path) -> TrainingManager:
    """Setup training infrastructure

    Args:
        base_dir: Base directory for document and vector stores

    Returns:
        Configured TrainingManager
    """
    # Create and return training manager
    return TrainingManager(
        embeddings_manager=get_default_embeddings_manager(),
        document_store=FileSystemDocumentStore(base_dir / "documents")
    )


def main():
    parser = argparse.ArgumentParser(description='Pre-train on document URLs from config')
    parser.add_argument('--config',
                        type=str,
                        default='../data/training_data/pretrain_docs.yaml',
                        help='Path to YAML config file with document URLs')
    parser.add_argument('--base-dir',
                        type=str,
                        default='../data/training_data',
                        help='Base directory for document and vector stores')
    parser.add_argument('--force',
                        action='store_true',
                        help='Force reprocessing of existing documents')
    args = parser.parse_args()

    try:
        # Load document URLs
        doc_urls = load_config(args.config)
        logger.info(f"Loaded {len(doc_urls)} document URLs from config")

        # Setup infrastructure
        base_dir = Path(args.base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        training_manager = setup_training(base_dir)
        logger.info("Training infrastructure setup complete")

        # Process each document
        for url in doc_urls:
            try:
                logger.info(f"Processing document: {url}")
                doc_hash = training_manager.process_document(url, force_reprocess=args.force)
                logger.info(f"Successfully processed document {url} (hash: {doc_hash})")
            except Exception as e:
                logger.error(f"Failed to process document {url}: {str(e)}")
                continue

        logger.info("Pre-training complete")

    except Exception as e:
        logger.error(f"Pre-training failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
