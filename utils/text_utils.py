import re
from difflib import SequenceMatcher
from typing import Any

BUSINESS_SUFFIXES = [
    "private limited", "pvt ltd", "pvt", "limited", "ltd", "llp",
    "incorporated", "inc", "corporation", "corp", "company", "co",
]


def compact_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def normalize_vendor(value: Any) -> str:
    text = str(value or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    for suffix in BUSINESS_SUFFIXES:
        text = re.sub(rf"\b{re.escape(suffix)}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def vendor_similarity(a: Any, b: Any) -> tuple[float, bool]:
    a = normalize_vendor(a)
    b = normalize_vendor(b)
    if not a:
        return 0.0, False
    if not b:
        return 0.0, True
    if a == b:
        return 100.0, True
    if a in b or b in a:
        return 95.0, True
    aw, bw = set(a.split()), set(b.split())
    word_score = len(aw & bw) / max(len(aw), len(bw)) * 100 if aw and bw else 0.0
    char_score = SequenceMatcher(None, a, b).ratio() * 100
    return round(max(word_score, char_score), 2), True
