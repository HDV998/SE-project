from pathlib import Path
from transformers import BertTokenizer, BertModel

# path where your model is stored in the repo
# match this with your screenshot: model_hub/pretrained/bert-base-uncased
MODEL_DIR = Path(__file__).resolve().parent / "model_hub" / "pretrained" / "bert-base-uncased"

if MODEL_DIR.exists():
    # ✅ Use local files only (Render & localhost)
    tokenizer = BertTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    model = BertModel.from_pretrained(MODEL_DIR, local_files_only=True)
else:
    # 🔁 First-time download (only happens on your machine)
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertModel.from_pretrained("bert-base-uncased")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(MODEL_DIR)
    model.save_pretrained(MODEL_DIR)
