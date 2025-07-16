import pandas as pd
from scripts.data_prep import fill_missing, normalize_types

def test_fill_missing_and_normalize():
    df = pd.DataFrame([
        {"name": "Test", "rate": None, "term_months": None, "currency": "RUB", "min_amount": 1000}
    ])
    df['rate'] = 5.0

    df_filled = fill_missing(df)
    df_normalized = normalize_types(df_filled)

    assert df_normalized["rate"].notnull().all()
    assert df_normalized["term_months"].notnull().all()