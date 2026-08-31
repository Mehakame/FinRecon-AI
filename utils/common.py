from pathlib import Path
from typing import Any, Tuple


def source_name(source: Any) -> str:
    if isinstance(source, (str, Path)):
        return Path(source).name
    return getattr(source, "name", "uploaded_file")


def source_bytes(source: Any) -> bytes:
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    if hasattr(source, "getvalue"):
        return source.getvalue()
    if hasattr(source, "read"):
        pos = None
        try:
            pos = source.tell()
        except Exception:
            pass
        data = source.read()
        if pos is not None:
            try:
                source.seek(pos)
            except Exception:
                pass
        return data
    raise TypeError("Unsupported file source")
