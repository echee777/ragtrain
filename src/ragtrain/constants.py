import os
from pathlib import Path

# Get the directory containing this test file
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = CURRENT_DIR / ".." / ".." / "data"
TEMPLATE_DIR = DATA_DIR / "prompt_templates"
TRAINING_DATA = DATA_DIR / "training_data"
DOCUMENTS_DIR = TRAINING_DATA / "documents"
EMBEDDINGS_DIR = TRAINING_DATA / "embeddings"
DOWNLOADS_DIR = TRAINING_DATA / "downloads"

