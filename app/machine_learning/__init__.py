"""Machine learning modules helping to predict classes."""

import os

# paths
pretrained_path = os.path.join(os.path.dirname(__file__), "model_hub/pretrained/bert-base-uncased")
fine_tuned_path = os.path.join(os.path.dirname(__file__), "model_hub/fine_tuned/toxic_model.pth")

# useful functions for easy access
from .data_loader import load_tokeninzer
from .make_predictions import predict, load_model