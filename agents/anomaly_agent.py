import pandas as pd

from utils.text_utils import normalize_vendor


def detect_duplicates(transactions_df: pd.DataFrame) -> pd.DataFrame:
    if transactions_df is None or transactions_df.empty:
        return pd.DataFrame()
    df = transactions_df.copy()
    df["vendor_norm"] = df["vendor"].apply(normalize_vendor)
    df["date_norm"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["amount_norm"] = df["absolute_amount"].round(2)
    mask = df.duplicated(subset=["date_norm", "vendor_norm", "amount_norm"], keep=False)
    cols = ["transaction_key", "source_bank", "date", "vendor", "amount", "transaction_id"]
    return df.loc[mask, cols].reset_index(drop=True) if mask.any() else pd.DataFrame(columns=cols)


def detect_amount_anomalies(transactions_df: pd.DataFrame) -> pd.DataFrame:
    if transactions_df is None or transactions_df.empty or len(transactions_df) < 5:
        return pd.DataFrame()
    df = transactions_df.copy()
    values = df["absolute_amount"].dropna()
    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    iqr = q3 - q1
    if iqr <= 0:
        return pd.DataFrame()
    lower, upper = max(0.0, q1 - 1.5 * iqr), q3 + 1.5 * iqr
    result = df[(df["absolute_amount"] < lower) | (df["absolute_amount"] > upper)].copy()
    if result.empty:
        return pd.DataFrame()
    result["lower_limit"] = lower
    result["upper_limit"] = upper
    result["reason"] = "Transaction amount is outside the normal IQR range"
    return result[["transaction_key", "source_bank", "date", "vendor", "amount", "lower_limit", "upper_limit", "reason"]].reset_index(drop=True)


def analyze_transactions(transactions_df: pd.DataFrame) -> dict:
    duplicates = detect_duplicates(transactions_df)
    anomalies = detect_amount_anomalies(transactions_df)
    return {
        "duplicates": duplicates,
        "anomalies": anomalies,
        "duplicate_count": len(duplicates),
        "anomaly_count": len(anomalies),
    }
