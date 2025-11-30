from pathlib import Path
from transformers import BertTokenizer
from torch.utils.data import DataLoader
from .data_class import DetoxDataset

# parameters for data loader
MAX_LEN = 200
BATCH_SIZE = 8

# build correct local path (relative to this file)
BASE_DIR = Path(__file__).resolve().parent
PRETRAINED_DIR = BASE_DIR / "model_hub" / "pretrained" / "bert-base-uncased"

# global tokenizer instance
tokenizer = None


def load_tokeninzer() -> None:
    """Loads BERT Tokenizer from local folder only."""
    global tokenizer

    if not PRETRAINED_DIR.exists():
        raise RuntimeError(f"BERT folder not found at: {PRETRAINED_DIR}")

    tokenizer = BertTokenizer.from_pretrained(
        PRETRAINED_DIR,
        local_files_only=True
    )


def data_loader(data) -> DataLoader:
    """Creates and returns a DataLoader for inference."""
    if tokenizer is None:
        raise RuntimeError("Tokenizer not loaded. Call load_tokeninzer() first.")

    inference_set = DetoxDataset(data, tokenizer, MAX_LEN)

    inference_params = {
        'batch_size': BATCH_SIZE,
        'shuffle': False,
        'num_workers': 0
    }

    return DataLoader(inference_set, **inference_params)