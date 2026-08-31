import io
from typing import Any, Dict, List, Tuple

import pandas as pd

from utils.common import source_bytes, source_name
from utils.data_cleaner import header_score, normalize_transactions
from utils.pdf_parser import parse_bank_pdf


def _read_csv(data: bytes) -> pd.DataFrame:
    best, best_score = None, -1
    for skip in range(0, 10):
        for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
            try:
                df = pd.read_csv(io.BytesIO(data), encoding=encoding, skiprows=skip)
            except Exception:
                continue
            if df.empty:
                continue
            score = header_score(df)
            if score > best_score:
                best, best_score = df, score
            if score >= 3:
                return df
    if best is not None:
        return best
    raise ValueError("CSV could not be parsed")


def _read_excel(data: bytes) -> pd.DataFrame:
    best, best_score = None, -1
    for skip in range(0, 10):
        try:
            df = pd.read_excel(io.BytesIO(data), skiprows=skip)
        except Exception:
            continue
        if df.empty:
            continue
        score = header_score(df)
        if score > best_score:
            best, best_score = df, score
        if score >= 3:
            return df
    if best is not None:
        return best
    raise ValueError("Excel statement could not be parsed")


def parse_bank_source(source: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    name = source_name(source)
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    data = source_bytes(source)
    if extension == "csv":
        raw = _read_csv(data)
    elif extension in {"xlsx", "xls"}:
        raw = _read_excel(data)
    elif extension == "pdf":
        raw = parse_bank_pdf(source)
    else:
        raise ValueError(f"{name}: unsupported bank format. Use CSV, XLSX, XLS, or text PDF")
    normalized, mapping = normalize_transactions(raw, source_name=name)
    return normalized, {"file": name, **mapping}


def ingest_bank_statements(sources: List[Any]) -> Dict[str, Any]:
    frames, mappings, errors = [], [], []
    for source in sources:
        try:
            frame, mapping = parse_bank_source(source)
            frames.append(frame)
            mappings.append(mapping)
        except Exception as exc:
            errors.append({"file": source_name(source), "error": str(exc)})
    if not frames:
        detail = "; ".join(f"{x['file']}: {x['error']}" for x in errors)
        raise ValueError(f"No bank statements could be processed. {detail}")
    combined = pd.concat(frames, ignore_index=True)
    return {"transactions": combined, "mappings": mappings, "errors": errors}
