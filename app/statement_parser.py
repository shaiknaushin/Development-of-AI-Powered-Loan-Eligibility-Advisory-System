import pdfplumber
import pandas as pd
import re
from datetime import datetime, timedelta

def analyze_bank_statement(pdf_path: str) -> dict:
    """
    Extracts transactions from a bank statement PDF and calculates key financial metrics,
    including a check for recent missed EMI payments.
    """
    transactions = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table(table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines"})
                if table:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    transactions.append(df)
    except Exception as e:
        print(f"Error parsing bank statement PDF: {e}")
        return {}

    if not transactions:
        print("Could not find any transaction tables in the bank statement.")
        return {}

    full_statement = pd.concat(transactions, ignore_index=True)
    
    full_statement.columns = [str(col).lower().replace(' ', '_') for col in full_statement.columns]
    rename_map = {
        'txn_date': 'date', 'transaction_date': 'date',
        'narration': 'description', 'particulars': 'description',
        'withdrawal_amt.': 'debit', 'withdrawal': 'debit',
        'deposit_amt.': 'credit', 'deposit': 'credit',
        'balance': 'balance'
    }
    full_statement.rename(columns=rename_map, inplace=True)
    
    if 'debit' not in full_statement.columns or 'credit' not in full_statement.columns or 'date' not in full_statement.columns:
        print("Could not find essential Date, Debit, or Credit columns.")
        return {}

    for col in ['debit', 'credit', 'balance']:
        if col in full_statement.columns:
            full_statement[col] = pd.to_numeric(full_statement[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # This is the fix for the UserWarning.
    full_statement['date'] = pd.to_datetime(full_statement['date'], errors='coerce', dayfirst=True)
    full_statement.dropna(subset=['date'], inplace=True)

    # --- NEW: EMI Payment History Analysis ---
    emi_debits = full_statement[full_statement['description'].str.contains('emi|loan|instalment', case=False, na=False)]
    
    today = datetime.now()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    two_months_ago_start = (last_month_start - timedelta(days=1)).replace(day=1)

    paid_last_month = not emi_debits[(emi_debits['date'] >= last_month_start) & (emi_debits['date'] < this_month_start)].empty
    paid_two_months_ago = not emi_debits[(emi_debits['date'] >= two_months_ago_start) & (emi_debits['date'] < last_month_start)].empty

    missed_emis = not (paid_last_month and paid_two_months_ago)
    
    average_balance = full_statement['balance'].mean() if 'balance' in full_statement.columns else 0
    bounced_checks_count = full_statement['description'].str.contains('bounce|dishonor|insufficient', case=False).sum()
    monthly_credits = full_statement.groupby(pd.to_datetime(full_statement['date'], errors='coerce').dt.to_period('M'))['credit'].sum()
    estimated_salary = monthly_credits[monthly_credits > 10000].median() if not monthly_credits.empty else 0

    return {
        "average_balance": float(average_balance),
        "estimated_salary": float(estimated_salary),
        "bounced_checks_count": int(bounced_checks_count),
        "missed_recent_emis": bool(missed_emis)
    }

