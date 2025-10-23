import pandas as pd

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    A simple data preprocessor.
    In a real-world scenario, this would handle missing values,
    feature scaling, and more complex encoding.
    """
    # For now, we just ensure the necessary columns exist
    # and handle potential NaNs from the database.
    df = df.dropna(subset=['monthly_income', 'loan_amount', 'approved'])

    # Example of a more complex feature: debt-to-income ratio
    # This requires 'monthly_debt', which we don't have, but shows the concept.
    # df['dti'] = df['monthly_debt'] / df['monthly_income']
    
    return df
