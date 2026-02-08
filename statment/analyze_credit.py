"""
Analyze how the ₹397,000 credit on November 24, 2025 was spent
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from data_processor import load_bank_data, analyze_spending_after_credit

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 12)

# File paths
XLS_FILE = '/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/statment/hdfc_6_months.xls'
XLSX_FILE = '/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/statment/sbi online.xlsx'

# Load data
print("Loading bank statements...")
df = load_bank_data(XLS_FILE, XLSX_FILE)
print(f"✓ Loaded {len(df):,} transactions")

# Analyze the specific credit
credit_date = "2025-11-24"
credit_amount = 397000

print(f"\n{'='*80}")
print(f"ANALYZING CREDIT OF ₹{credit_amount:,} ON {credit_date}")
print(f"{'='*80}\n")

analysis = analyze_spending_after_credit(df, credit_date, credit_amount, tolerance=5000)

if analysis is None:
    print(f"❌ No credit found on {credit_date} with amount ~₹{credit_amount:,}")
else:
    # Print summary
    print(f"✓ Found credit: ₹{analysis['credit_amount']:,.2f} in {analysis['credit_bank']} bank")
    print(f"  Date: {analysis['credit_date'].strftime('%d %B %Y')}")
    print(f"  Days elapsed: {analysis['days_elapsed']} days")
    print(f"\n{'='*80}")
    print(f"SPENDING SUMMARY")
    print(f"{'='*80}")
    print(f"Original Credit:        ₹{analysis['credit_amount']:>15,.2f}")
    print(f"Total Spent:            ₹{analysis['total_spent']:>15,.2f} ({analysis['total_spent']/analysis['credit_amount']*100:.1f}%)")
    print(f"Additional Income:      ₹{analysis['total_additional_income']:>15,.2f}")
    print(f"Current Position:       ₹{analysis['remaining']:>15,.2f}")
    print(f"Average Daily Spending: ₹{analysis['total_spent']/max(analysis['days_elapsed'], 1):>15,.2f}")
    
    # Spending by bank
    print(f"\n{'='*80}")
    print(f"SPENDING BY BANK")
    print(f"{'='*80}")
    for _, row in analysis['spending_by_bank'].iterrows():
        percentage = (row['Total Spent'] / analysis['total_spent'] * 100) if analysis['total_spent'] > 0 else 0
        print(f"{row['Bank']:10s} ₹{row['Total Spent']:>12,.2f} ({percentage:>5.1f}%) - {int(row['Transaction Count']):,} transactions")
    
    # Spending by category
    print(f"\n{'='*80}")
    print(f"SPENDING BY CATEGORY")
    print(f"{'='*80}")
    category_df = analysis['spending_by_category'].reset_index()
    category_df.columns = ['Category', 'Amount']
    for _, row in category_df.iterrows():
        percentage = (row['Amount'] / analysis['total_spent'] * 100) if analysis['total_spent'] > 0 else 0
        print(f"{row['Category']:20s} ₹{row['Amount']:>12,.2f} ({percentage:>5.1f}%)")
    
    # Top 10 expenses
    print(f"\n{'='*80}")
    print(f"TOP 10 LARGEST EXPENSES")
    print(f"{'='*80}")
    top_10 = analysis['top_expenses'].head(10).copy()
    top_10['Date'] = top_10['Date'].dt.strftime('%d-%b-%Y')
    top_10['Description'] = top_10['Description'].str[:60]
    print(top_10[['Date', 'Bank', 'Category', 'Debit', 'Description']].to_string(index=False))
    
    # Create visualizations
    print(f"\n{'='*80}")
    print("CREATING VISUALIZATIONS...")
    print(f"{'='*80}\n")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f'Spending Analysis: ₹{analysis["credit_amount"]:,.0f} Credit on {analysis["credit_date"].strftime("%d %b %Y")}', 
                 fontsize=16, fontweight='bold')
    
    # 1. Spending by bank
    bank_data = analysis['spending_by_bank']
    colors_bank = ['#004c8c', '#00a4e4']
    axes[0, 0].bar(bank_data['Bank'], bank_data['Total Spent'], color=colors_bank)
    axes[0, 0].set_title('Spending by Bank', fontweight='bold')
    axes[0, 0].set_ylabel('Amount (₹)')
    for i, v in enumerate(bank_data['Total Spent']):
        axes[0, 0].text(i, v, f'₹{v:,.0f}', ha='center', va='bottom')
    
    # 2. Category breakdown
    category_data = analysis['spending_by_category'].head(8)
    axes[0, 1].pie(category_data.values, labels=category_data.index, autopct='%1.1f%%', startangle=90)
    axes[0, 1].set_title('Spending by Category (Top 8)', fontweight='bold')
    
    # 3. Daily spending trend
    daily_data = analysis['daily_spending']
    for bank in daily_data['Bank'].unique():
        bank_data = daily_data[daily_data['Bank'] == bank]
        axes[0, 2].plot(bank_data['Date'], bank_data['Debit'], marker='o', label=bank, linewidth=2)
    axes[0, 2].set_title('Daily Spending Trend', fontweight='bold')
    axes[0, 2].set_xlabel('Date')
    axes[0, 2].set_ylabel('Amount (₹)')
    axes[0, 2].legend()
    axes[0, 2].tick_params(axis='x', rotation=45)
    axes[0, 2].grid(True, alpha=0.3)
    
    # 4. Monthly spending by bank
    monthly_data = analysis['spending_by_month'].copy()
    monthly_data['Month_Date'] = pd.to_datetime(monthly_data['Month_Year'], format='%B %Y')
    monthly_data = monthly_data.sort_values('Month_Date')
    
    months = monthly_data['Month_Year'].unique()
    x = range(len(months))
    width = 0.35
    
    hdfc_amounts = []
    sbi_amounts = []
    for month in months:
        hdfc_val = monthly_data[(monthly_data['Month_Year'] == month) & (monthly_data['Bank'] == 'HDFC')]['Debit'].sum()
        sbi_val = monthly_data[(monthly_data['Month_Year'] == month) & (monthly_data['Bank'] == 'SBI')]['Debit'].sum()
        hdfc_amounts.append(hdfc_val)
        sbi_amounts.append(sbi_val)
    
    axes[1, 0].bar([i - width/2 for i in x], hdfc_amounts, width, label='HDFC', color='#004c8c')
    axes[1, 0].bar([i + width/2 for i in x], sbi_amounts, width, label='SBI', color='#00a4e4')
    axes[1, 0].set_title('Monthly Spending by Bank', fontweight='bold')
    axes[1, 0].set_xlabel('Month')
    axes[1, 0].set_ylabel('Amount (₹)')
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(months, rotation=45, ha='right')
    axes[1, 0].legend()
    
    # 5. Cumulative spending
    daily_cumulative = analysis['daily_spending'].copy()
    daily_cumulative = daily_cumulative.sort_values('Date')
    daily_cumulative['Cumulative'] = daily_cumulative.groupby('Bank')['Debit'].cumsum()
    
    for bank in daily_cumulative['Bank'].unique():
        bank_cum = daily_cumulative[daily_cumulative['Bank'] == bank]
        axes[1, 1].plot(bank_cum['Date'], bank_cum['Cumulative'], label=bank, linewidth=2.5)
    
    axes[1, 1].axhline(y=analysis['credit_amount'], color='red', linestyle='--', label='Original Credit', linewidth=2)
    axes[1, 1].set_title('Cumulative Spending Over Time', fontweight='bold')
    axes[1, 1].set_xlabel('Date')
    axes[1, 1].set_ylabel('Cumulative Amount (₹)')
    axes[1, 1].legend()
    axes[1, 1].tick_params(axis='x', rotation=45)
    axes[1, 1].grid(True, alpha=0.3)
    
    # 6. Money flow summary
    flow_data = {
        'Category': ['Original\nCredit', 'Total\nSpent', 'Additional\nIncome', 'Current\nPosition'],
        'Amount': [analysis['credit_amount'], -analysis['total_spent'], 
                   analysis['total_additional_income'], analysis['remaining']],
        'Color': ['green', 'red', 'green', 'blue' if analysis['remaining'] >= 0 else 'red']
    }
    
    for i, (cat, amt, col) in enumerate(zip(flow_data['Category'], flow_data['Amount'], flow_data['Color'])):
        axes[1, 2].bar(i, amt, color=col, alpha=0.7)
        axes[1, 2].text(i, amt, f'₹{abs(amt):,.0f}', ha='center', 
                       va='bottom' if amt > 0 else 'top', fontweight='bold')
    
    axes[1, 2].set_title('Money Flow Summary', fontweight='bold')
    axes[1, 2].set_xticks(range(4))
    axes[1, 2].set_xticklabels(flow_data['Category'])
    axes[1, 2].set_ylabel('Amount (₹)')
    axes[1, 2].axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    axes[1, 2].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('credit_analysis_nov24.png', dpi=300, bbox_inches='tight')
    print("✓ Saved visualization: credit_analysis_nov24.png")
    plt.show()
    
    # Export detailed report
    print(f"\n{'='*80}")
    print("EXPORTING DETAILED REPORT...")
    print(f"{'='*80}\n")
    
    # Save transactions to CSV
    analysis['transactions'].to_csv('transactions_after_nov24_credit.csv', index=False)
    print("✓ Saved: transactions_after_nov24_credit.csv")
    
    # Save summary report
    summary_report = {
        'Metric': [
            'Credit Date',
            'Credit Amount',
            'Credit Bank',
            'Days Elapsed',
            'Total Spent',
            'Percentage Spent',
            'Additional Income',
            'Current Position',
            'Average Daily Spending',
            'HDFC Spending',
            'SBI Spending',
            'Top Category',
            'Top Category Amount'
        ],
        'Value': [
            analysis['credit_date'].strftime('%d %B %Y'),
            f"₹{analysis['credit_amount']:,.2f}",
            analysis['credit_bank'],
            f"{analysis['days_elapsed']} days",
            f"₹{analysis['total_spent']:,.2f}",
            f"{analysis['total_spent']/analysis['credit_amount']*100:.1f}%",
            f"₹{analysis['total_additional_income']:,.2f}",
            f"₹{analysis['remaining']:,.2f}",
            f"₹{analysis['total_spent']/max(analysis['days_elapsed'], 1):,.2f}",
            f"₹{analysis['spending_by_bank'][analysis['spending_by_bank']['Bank']=='HDFC']['Total Spent'].sum():,.2f}",
            f"₹{analysis['spending_by_bank'][analysis['spending_by_bank']['Bank']=='SBI']['Total Spent'].sum():,.2f}",
            analysis['spending_by_category'].index[0],
            f"₹{analysis['spending_by_category'].iloc[0]:,.2f}"
        ]
    }
    summary_df = pd.DataFrame(summary_report)
    summary_df.to_csv('spending_summary_nov24_credit.csv', index=False)
    print("✓ Saved: spending_summary_nov24_credit.csv")
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE!")
    print(f"{'='*80}\n")