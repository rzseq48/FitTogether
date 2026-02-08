import pandas as pd
import numpy as np

def load_bank_data(xls_file, xlsx_file):
    """Load and process bank statement data from HDFC and SBI"""
    
    # Read with correct header rows
    df_hdfc = pd.read_excel(xls_file, header=20)
    df_sbi = pd.read_excel(xlsx_file, header=17)
    
    # Clean up - remove separator rows and NaN rows
    df_hdfc = df_hdfc[~df_hdfc['Date'].astype(str).str.contains('\*', na=False)]
    df_hdfc = df_hdfc.dropna(how='all')
    
    # Remove footer/summary rows
    df_hdfc = df_hdfc[~df_hdfc['Date'].astype(str).str.contains('STATEMENT SUMMARY|Opening Balance|Closing Balance', case=False, na=False)]
    df_sbi = df_sbi[~df_sbi['Date'].astype(str).str.contains('STATEMENT SUMMARY|Opening Balance|Closing Balance', case=False, na=False)]
    
    df_sbi = df_sbi.dropna(how='all')
    
    # Rename columns to standard names
    hdfc_rename = {
        'Date': 'Date',
        'Narration': 'Description', 
        'Withdrawal Amt.': 'Debit',
        'Deposit Amt.': 'Credit',
        'Closing Balance': 'Balance',
        'Chq./Ref.No.': 'Reference'
    }
    
    sbi_rename = {
        'Date': 'Date',
        'Details': 'Description',
        'Debit': 'Debit', 
        'Credit': 'Credit',
        'Balance': 'Balance',
        'Ref No/Cheque No': 'Reference'
    }
    
    df_hdfc = df_hdfc.rename(columns=hdfc_rename)
    df_sbi = df_sbi.rename(columns=sbi_rename)
    
    # Add bank identifier
    df_hdfc['Bank'] = 'HDFC'
    df_sbi['Bank'] = 'SBI'
    
    # Select only needed columns
    cols = ['Date', 'Description', 'Debit', 'Credit', 'Balance', 'Bank', 'Reference']
    df_hdfc = df_hdfc[cols]
    df_sbi = df_sbi[cols]
    
    # Combine
    df_combined = pd.concat([df_hdfc, df_sbi], ignore_index=True)
    
    # Clean up amounts - remove commas and convert to numeric
    df_combined['Debit'] = df_combined['Debit'].astype(str).str.replace(',', '').replace('nan', '0')
    df_combined['Credit'] = df_combined['Credit'].astype(str).str.replace(',', '').replace('nan', '0')
    df_combined['Balance'] = df_combined['Balance'].astype(str).str.replace(',', '')
    
    df_combined['Debit'] = pd.to_numeric(df_combined['Debit'], errors='coerce').fillna(0)
    df_combined['Credit'] = pd.to_numeric(df_combined['Credit'], errors='coerce').fillna(0)
    df_combined['Balance'] = pd.to_numeric(df_combined['Balance'], errors='coerce')
    
    # Create net amount column (Credit - Debit)
    df_combined['Amount'] = df_combined['Credit'] - df_combined['Debit']
    
    # Convert date - try different formats for HDFC (DD/MM/YY) and SBI (DD/MM/YYYY)
    def parse_date(date_str):
        if pd.isna(date_str):
            return pd.NaT
        date_str = str(date_str).strip()
        
        # Try different date formats
        for fmt in ['%d/%m/%y', '%d/%m/%Y', '%d-%m-%Y', '%d-%m-%y']:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except:
                continue
        return pd.NaT
    
    df_combined['Date'] = df_combined['Date'].apply(parse_date)
    
    # Remove rows where date parsing failed or date is before 2020
    df_combined = df_combined.dropna(subset=['Date'])
    df_combined = df_combined[df_combined['Date'] >= '2020-01-01']
    
    # Sort by date
    df_combined = df_combined.sort_values('Date').reset_index(drop=True)
    
    # Add derived columns
    df_combined['Month'] = df_combined['Date'].dt.to_period('M')
    df_combined['Month_str'] = df_combined['Date'].dt.strftime('%b-%y')
    df_combined['Year'] = df_combined['Date'].dt.year
    df_combined['Month_name'] = df_combined['Date'].dt.strftime('%B %Y')
    
    # Categorize transactions
    df_combined['Category'] = df_combined['Description'].apply(categorize_transaction)
    
    return df_combined


def categorize_transaction(desc):
    """Categorize transaction based on description"""
    desc = str(desc).upper()
    if any(word in desc for word in ['SWIGGY', 'ZOMATO', 'UBER EATS', 'RESTAURANT', 'FOOD', 'ARYAAS', 'KITCHEN']):
        return 'Food & Dining'
    elif any(word in desc for word in ['EMI', 'LOAN']):
        return 'EMI/Loans'
    elif any(word in desc for word in ['AMAZON', 'FLIPKART', 'SHOPPING', 'LULU', 'MALL']):
        return 'Shopping'
    elif any(word in desc for word in ['NETFLIX', 'PRIME', 'HOTSTAR', 'SPOTIFY', 'PLAY', 'GOOGLE PLAY']):
        return 'Entertainment'
    elif any(word in desc for word in ['UBER', 'OLA', 'RAPIDO', 'PETROL', 'FUEL']):
        return 'Transport'
    elif any(word in desc for word in ['ATM', 'CASH']):
        return 'Cash Withdrawal'
    elif any(word in desc for word in ['TRANSFER', 'TFR']):
        return 'Transfers'
    else:
        return 'Others'


def get_summary_stats(df):
    """Calculate summary statistics"""
    stats = {
        'total_transactions': len(df),
        'total_spent': df['Debit'].sum(),
        'total_income': df['Credit'].sum(),
        'net_change': df['Amount'].sum(),
        'avg_transaction': df[df['Debit'] > 0]['Debit'].mean(),
        'date_range': (df['Date'].min(), df['Date'].max())
    }
    return stats


def get_monthly_summary(df):
    """Get monthly summary by bank"""
    monthly = df.groupby(['Month_name', 'Bank']).agg({
        'Debit': 'sum',
        'Credit': 'sum',
        'Amount': 'sum',
        'Date': 'count'
    }).round(2)
    monthly.columns = ['Total Spent', 'Total Income', 'Net', 'Transaction Count']
    return monthly.reset_index()


def get_category_summary(df):
    """Get spending by category"""
    category_df = df[df['Debit'] > 0].groupby('Category')['Debit'].sum().sort_values(ascending=False)
    return category_df.reset_index()


def analyze_spending_after_credit(df, credit_date, credit_amount=None, tolerance=1000):
    """
    Analyze how money was spent after a specific credit transaction
    
    Parameters:
    - df: DataFrame with all transactions
    - credit_date: Date of the credit (as string or datetime)
    - credit_amount: Optional - amount of credit to track (will find closest match if not exact)
    - tolerance: Tolerance for matching credit amount (default 1000)
    
    Returns:
    - Dictionary with analysis results
    """
    credit_date = pd.to_datetime(credit_date)
    
    # Find the specific credit transaction
    if credit_amount:
        # Find credit on that date with amount close to specified
        credits_on_date = df[(df['Date'].dt.date == credit_date.date()) & 
                            (df['Credit'] > 0) & 
                            (abs(df['Credit'] - credit_amount) <= tolerance)]
    else:
        # Find all credits on that date
        credits_on_date = df[(df['Date'].dt.date == credit_date.date()) & (df['Credit'] > 0)]
    
    if len(credits_on_date) == 0:
        return None
    
    # Get the credit transaction details
    credit_transaction = credits_on_date.iloc[0]
    actual_credit_amount = credit_transaction['Credit']
    credit_bank = credit_transaction['Bank']
    
    # Get all transactions after this credit
    transactions_after = df[df['Date'] >= credit_date].copy()
    
    # Calculate spending by bank
    spending_by_bank = transactions_after.groupby('Bank').agg({
        'Debit': 'sum',
        'Credit': 'sum',
        'Date': 'count'
    }).reset_index()
    spending_by_bank.columns = ['Bank', 'Total Spent', 'Total Income', 'Transaction Count']
    
    # Calculate spending by category
    spending_by_category = transactions_after[transactions_after['Debit'] > 0].groupby('Category')['Debit'].sum().sort_values(ascending=False)
    
    # Calculate spending by month
    transactions_after['Month_Year'] = transactions_after['Date'].dt.strftime('%B %Y')
    spending_by_month = transactions_after.groupby(['Month_Year', 'Bank'])['Debit'].sum().reset_index()
    
    # Calculate daily spending trend
    daily_spending = transactions_after.groupby([transactions_after['Date'].dt.date, 'Bank'])['Debit'].sum().reset_index()
    daily_spending.columns = ['Date', 'Bank', 'Debit']
    
    # Get top expenses
    top_expenses = transactions_after[transactions_after['Debit'] > 0].nlargest(20, 'Debit')[
        ['Date', 'Bank', 'Description', 'Category', 'Debit']
    ]
    
    # Calculate running balance (how much is left)
    total_spent = transactions_after['Debit'].sum()
    total_additional_income = transactions_after[transactions_after['Date'] > credit_date]['Credit'].sum()
    remaining = actual_credit_amount - total_spent + total_additional_income
    
    return {
        'credit_amount': actual_credit_amount,
        'credit_date': credit_date,
        'credit_bank': credit_bank,
        'total_spent': total_spent,
        'total_additional_income': total_additional_income,
        'remaining': remaining,
        'spending_by_bank': spending_by_bank,
        'spending_by_category': spending_by_category,
        'spending_by_month': spending_by_month,
        'daily_spending': daily_spending,
        'top_expenses': top_expenses,
        'transactions': transactions_after,
        'days_elapsed': (pd.Timestamp.now() - credit_date).days
    }