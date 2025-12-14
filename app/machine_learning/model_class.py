from transformers import BertModel
from torch.nn import Module, Dropout, Linear
import os

class DetoxClass(Module):
    def __init__(self):
        super().__init__()

        BASE_DIR = os.path.dirname(__file__)
        LOCAL_BERT = os.path.join(BASE_DIR, "model_hub", "pretrained", "bert-base-uncased")

        self.l1 = BertModel.from_pretrained(
            LOCAL_BERT,
            local_files_only=True   # 🔥 prevents trying to download from internet
        )

        self.l2 = Dropout(0.3)
        self.l3 = Linear(768, 6)

    def forward(self, ids, mask, token_type_ids):
        _, pooled = self.l1(
            ids,
            attention_mask=mask,
            token_type_ids=token_type_ids,
            return_dict=False
        )
        x = self.l2(pooled)
        return self.l3(x)
