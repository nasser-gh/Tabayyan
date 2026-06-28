"""Fast recall regression: checksum/format types must survive formatting noise."""
import random

from tabayyan import DetectionEngine, EntityType
from tests.synthetic import make_iban, make_national_id

engine = DetectionEngine()
_AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _recall(make, target, embed, n=60, seed=5):
    rng = random.Random(seed)
    hits = sum(target in {m.entity_type for m in engine.scan(embed(rng, make(rng)))}
               for _ in range(n))
    return hits / n


def test_national_id_recall_under_arabic_digits_and_noise():
    def embed(rng, v):
        v = v.translate(_AR) if rng.random() < 0.5 else v
        return f"{rng.choice(['ref:', '  ', 'الرقم: '])}{v}{rng.choice(['.', ' تم', ''])}"
    assert _recall(lambda r: make_national_id(r, "1"),
                   EntityType.SAUDI_NATIONAL_ID, embed) == 1.0


def test_iban_recall_with_and_without_spaces():
    def embed(rng, v):
        if rng.random() < 0.5:
            v = " ".join(v[i:i+4] for i in range(0, len(v), 4))
        return f"account {v}."
    assert _recall(make_iban, EntityType.SAUDI_IBAN, embed) == 1.0
