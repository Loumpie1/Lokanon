"""gbert-base bringt nur vocab.txt mit; transformers 5 baut daraus keinen Tokenizer mehr. Einmalig einen
schnellen WordPiece-Tokenizer erzeugen und unter daten/tokenizer ablegen (trainieren.py lädt ihn von dort).

    python experimente/zweitpruefer/tokenizer_bauen.py
"""
from pathlib import Path

from huggingface_hub import snapshot_download
from tokenizers import BertWordPieceTokenizer
from transformers import PreTrainedTokenizerFast

ZIEL = Path(__file__).resolve().parent / "daten/tokenizer"

vocab = Path(snapshot_download("deepset/gbert-base", allow_patterns=["vocab.txt"])) / "vocab.txt"
roh = BertWordPieceTokenizer(str(vocab), lowercase=False, strip_accents=False, clean_text=True,
                             handle_chinese_chars=True)
tok = PreTrainedTokenizerFast(tokenizer_object=roh, unk_token="[UNK]", sep_token="[SEP]", pad_token="[PAD]",
                              cls_token="[CLS]", mask_token="[MASK]", model_max_length=512)
tok.save_pretrained(ZIEL)
print(tok.tokenize("Herr Brüggemann von der Spedition Nolte GmbH"))
print(tok("Person: Koch", "Herr «Koch» kam.")["input_ids"])
