import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_processor import load_bank_data, get_summary_stats, get_monthly_summary, get_category_summary, analyze_spending_after_credit

# Page configuration
st.set_page_config(
    page_title="Bank Statement Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #FF6B6B 0%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border-left: 5px solid #FF6B6B;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stMetric {
        background-color: #ffffff;
        padding: 1.25rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid #e9ecef;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #2c3e50;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        font-weight: 600;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricDelta"] svg {
        display: none;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f8f9fa;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #FF6B6B 0%, #4ECDC4 100%);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">💰 Bank Statement Dashboard</h1>', unsafe_allow_html=True)

# File paths - Update these with your actual file paths
XLS_FILE = '/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/statment/Acct_Statement_XXXXXXXX7651_08022026.xls'
XLSX_FILE = '/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/statment/sbi online.xlsx'

# Load data with caching
@st.cache_data
def load_data():
    return load_bank_data(XLS_FILE, XLSX_FILE)

try:
    df = load_data()
    stats = get_summary_stats(df)
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Bank filter
    banks = ['All Banks'] + sorted(df['Bank'].unique().tolist())
    selected_bank = st.sidebar.selectbox("Select Bank", banks)
    
    # Month filter
    months = ['All Months'] + sorted(df['Month_name'].unique().tolist(), 
                                      key=lambda x: pd.to_datetime(x, format='%B %Y'))
    selected_month = st.sidebar.selectbox("Select Month", months)
    
    # Category filter
    categories = ['All Categories'] + sorted(df['Category'].unique().tolist())
    selected_category = st.sidebar.selectbox("Select Category", categories)
    
    # Amount range filter
    st.sidebar.subheader("Transaction Amount Range")
    min_amount = float(df['Debit'].min())
    max_amount = float(df['Debit'].max())
    amount_range = st.sidebar.slider(
        "Select Amount Range (₹)",
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount)
    )
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_bank != 'All Banks':
        filtered_df = filtered_df[filtered_df['Bank'] == selected_bank]
    
    if selected_month != 'All Months':
        filtered_df = filtered_df[filtered_df['Month_name'] == selected_month]
    
    if selected_category != 'All Categories':
        filtered_df = filtered_df[filtered_df['Category'] == selected_category]
    
    filtered_df = filtered_df[
        (filtered_df['Debit'] >= amount_range[0]) & 
        (filtered_df['Debit'] <= amount_range[1])
    ]
    
    # Summary metrics
    st.header("📊 Summary Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Transactions",
            f"{len(filtered_df):,}",
            delta=f"{len(filtered_df) - len(df):,}" if selected_bank != 'All Banks' or selected_month != 'All Months' else None
        )
    
    with col2:
        st.metric(
            "Total Spent",
            f"₹{filtered_df['Debit'].sum():,.2f}",
            delta=f"₹{filtered_df['Debit'].sum() - df['Debit'].sum():,.2f}" if selected_bank != 'All Banks' or selected_month != 'All Months' else None
        )
    
    with col3:
        st.metric(
            "Total Income",
            f"₹{filtered_df['Credit'].sum():,.2f}",
            delta=f"₹{filtered_df['Credit'].sum() - df['Credit'].sum():,.2f}" if selected_bank != 'All Banks' or selected_month != 'All Months' else None
        )
    
    with col4:
        net_change = filtered_df['Amount'].sum()
        st.metric(
            "Net Change",
            f"₹{net_change:,.2f}",
            delta=f"₹{net_change - df['Amount'].sum():,.2f}" if selected_bank != 'All Banks' or selected_month != 'All Months' else None,
            delta_color="normal" if net_change >= 0 else "inverse"
        )
    
    with col5:
        avg_trans = filtered_df[filtered_df['Debit'] > 0]['Debit'].mean()
        st.metric(
            "Avg Transaction",
            f"₹{avg_trans:,.2f}" if not pd.isna(avg_trans) else "₹0.00"
        )
    
    st.markdown("---")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Overview", 
        "💳 By Bank", 
        "📅 By Month", 
        "🏷️ By Category",
        "📋 Transactions",
        "💰 Credit Tracker"
    ])
    
    with tab1:
        st.header("Overview Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Monthly spending trend
            monthly_spending = filtered_df.groupby('Month_name')['Debit'].sum().reset_index()
            monthly_spending = monthly_spending.sort_values(
                'Month_name', 
                key=lambda x: pd.to_datetime(x, format='%B %Y')
            )
            
            fig_monthly = px.line(
                monthly_spending,
                x='Month_name',
                y='Debit',
                title='Monthly Spending Trend',
                markers=True,
                labels={'Month_name': 'Month', 'Debit': 'Amount (₹)'}
            )
            fig_monthly.update_traces(line_color='#FF6B6B', line_width=3, marker=dict(size=10, color='#FF6B6B'))
            fig_monthly.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        with col2:
            # Spending by bank pie chart
            bank_spending = filtered_df.groupby('Bank')['Debit'].sum().reset_index()
            
            fig_bank_pie = px.pie(
                bank_spending,
                values='Debit',
                names='Bank',
                title='Spending Distribution by Bank',
                color_discrete_map={'HDFC': '#FF6B6B', 'SBI': '#4ECDC4'}
            )
            fig_bank_pie.update_traces(marker=dict(line=dict(color='white', width=3)))
            fig_bank_pie.update_layout(height=400)
            st.plotly_chart(fig_bank_pie, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Income vs Spending
            monthly_summary = filtered_df.groupby('Month_name').agg({
                'Debit': 'sum',
                'Credit': 'sum'
            }).reset_index()
            monthly_summary = monthly_summary.sort_values(
                'Month_name',
                key=lambda x: pd.to_datetime(x, format='%B %Y')
            )
            
            fig_income_vs_spending = go.Figure()
            fig_income_vs_spending.add_trace(go.Bar(
                x=monthly_summary['Month_name'],
                y=monthly_summary['Debit'],
                name='Spending',
                marker_color='#FF6B6B'
            ))
            fig_income_vs_spending.add_trace(go.Bar(
                x=monthly_summary['Month_name'],
                y=monthly_summary['Credit'],
                name='Income',
                marker_color='#4ECDC4'
            ))
            fig_income_vs_spending.update_layout(
                title='Income vs Spending by Month',
                barmode='group',
                height=400,
                xaxis_title='Month',
                yaxis_title='Amount (₹)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_income_vs_spending, use_container_width=True)
        
        with col4:
            # Top categories
            category_spending = filtered_df[filtered_df['Debit'] > 0].groupby('Category')['Debit'].sum().reset_index()
            category_spending = category_spending.sort_values('Debit', ascending=True).tail(10)
            
            # Vibrant gradient colors
            colors_gradient = ['#4ECDC4', '#45B7D1', '#5DADE2', '#6C7AE0', '#7B68EE', 
                             '#9B59B6', '#C39BD3', '#E8DAEF', '#FFA07A', '#FF6B6B']
            
            fig_categories = px.bar(
                category_spending,
                x='Debit',
                y='Category',
                orientation='h',
                title='Top Spending Categories',
                labels={'Debit': 'Amount (₹)', 'Category': 'Category'}
            )
            fig_categories.update_traces(marker_color=colors_gradient[:len(category_spending)])
            fig_categories.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_categories, use_container_width=True)
    
    with tab2:
        st.header("Bank-wise Analysis")
        
        # Bank comparison
        bank_stats = filtered_df.groupby('Bank').agg({
            'Debit': 'sum',
            'Credit': 'sum',
            'Amount': 'sum',
            'Date': 'count'
        }).reset_index()
        bank_stats.columns = ['Bank', 'Total Spent', 'Total Income', 'Net Change', 'Transactions']
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Bank Comparison")
            st.dataframe(
                bank_stats.style.format({
                    'Total Spent': '₹{:,.2f}',
                    'Total Income': '₹{:,.2f}',
                    'Net Change': '₹{:,.2f}',
                    'Transactions': '{:,}'
                }),
                hide_index=True,
                use_container_width=True
            )
        
        with col2:
            # Monthly spending by bank
            monthly_bank = filtered_df.groupby(['Month_name', 'Bank'])['Debit'].sum().reset_index()
            monthly_bank = monthly_bank.sort_values(
                'Month_name',
                key=lambda x: pd.to_datetime(x, format='%B %Y')
            )
            
            fig_bank_monthly = px.bar(
                monthly_bank,
                x='Month_name',
                y='Debit',
                color='Bank',
                title='Monthly Spending by Bank',
                barmode='group',
                labels={'Month_name': 'Month', 'Debit': 'Amount (₹)'},
                color_discrete_map={'HDFC': '#FF6B6B', 'SBI': '#4ECDC4'}
            )
            fig_bank_monthly.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bank_monthly, use_container_width=True)
        
        # Transaction count by bank
        st.subheader("Transaction Count by Bank")
        transaction_count = filtered_df.groupby(['Month_name', 'Bank']).size().reset_index(name='Count')
        transaction_count = transaction_count.sort_values(
            'Month_name',
            key=lambda x: pd.to_datetime(x, format='%B %Y')
        )
        
        fig_trans_count = px.line(
            transaction_count,
            x='Month_name',
            y='Count',
            color='Bank',
            markers=True,
            title='Transaction Count Trend',
            labels={'Month_name': 'Month', 'Count': 'Number of Transactions'}
        )
        fig_trans_count.update_layout(height=400)
        st.plotly_chart(fig_trans_count, use_container_width=True)
    
    with tab3:
        st.header("Monthly Analysis")
        
        # Monthly summary table
        monthly_summary = filtered_df.groupby('Month_name').agg({
            'Debit': 'sum',
            'Credit': 'sum',
            'Amount': 'sum',
            'Date': 'count'
        }).reset_index()
        monthly_summary.columns = ['Month', 'Total Spent', 'Total Income', 'Net Change', 'Transactions']
        monthly_summary = monthly_summary.sort_values(
            'Month',
            key=lambda x: pd.to_datetime(x, format='%B %Y')
        )
        
        st.subheader("Monthly Summary")
        st.dataframe(
            monthly_summary.style.format({
                'Total Spent': '₹{:,.2f}',
                'Total Income': '₹{:,.2f}',
                'Net Change': '₹{:,.2f}',
                'Transactions': '{:,}'
            }).background_gradient(subset=['Net Change'], cmap='RdYlGn'),
            hide_index=True,
            use_container_width=True
        )
        
        # Balance trend
        st.subheader("Balance Trend Over Time")
        balance_trend = filtered_df.groupby(['Date', 'Bank'])['Balance'].last().reset_index()
        
        fig_balance = px.line(
            balance_trend,
            x='Date',
            y='Balance',
            color='Bank',
            title='Account Balance Trend',
            labels={'Date': 'Date', 'Balance': 'Balance (₹)'}
        )
        fig_balance.update_layout(height=400)
        st.plotly_chart(fig_balance, use_container_width=True)
    
    with tab4:
        st.header("Category-wise Spending Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Category spending pie chart
            category_data = filtered_df[filtered_df['Debit'] > 0].groupby('Category')['Debit'].sum().reset_index()
            category_data = category_data.sort_values('Debit', ascending=False)
            
            fig_cat_pie = px.pie(
                category_data,
                values='Debit',
                names='Category',
                title='Spending by Category'
            )
            fig_cat_pie.update_layout(height=400)
            st.plotly_chart(fig_cat_pie, use_container_width=True)
        
        with col2:
            # Category spending table
            st.subheader("Category Breakdown")
            category_data['Percentage'] = (category_data['Debit'] / category_data['Debit'].sum() * 100).round(2)
            
            st.dataframe(
                category_data.style.format({
                    'Debit': '₹{:,.2f}',
                    'Percentage': '{:.2f}%'
                }),
                hide_index=True,
                use_container_width=True
            )
        
        # Monthly category trends
        st.subheader("Category Spending Trend")
        monthly_category = filtered_df[filtered_df['Debit'] > 0].groupby(['Month_name', 'Category'])['Debit'].sum().reset_index()
        monthly_category = monthly_category.sort_values(
            'Month_name',
            key=lambda x: pd.to_datetime(x, format='%B %Y')
        )
        
        fig_cat_trend = px.bar(
            monthly_category,
            x='Month_name',
            y='Debit',
            color='Category',
            title='Monthly Spending by Category',
            labels={'Month_name': 'Month', 'Debit': 'Amount (₹)'}
        )
        fig_cat_trend.update_layout(height=500, barmode='stack')
        st.plotly_chart(fig_cat_trend, use_container_width=True)
    
    with tab5:
        st.header("Transaction Details")
        
        # Search functionality
        search_term = st.text_input("🔍 Search transactions", placeholder="Search by description...")
        
        if search_term:
            display_df = filtered_df[
                filtered_df['Description'].str.contains(search_term, case=False, na=False)
            ].copy()
        else:
            display_df = filtered_df.copy()
        
        # Sort options
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            sort_by = st.selectbox(
                "Sort by",
                ['Date', 'Debit', 'Credit', 'Balance', 'Bank', 'Category']
            )
        with col2:
            sort_order = st.radio("Order", ['Descending', 'Ascending'])
        with col3:
            rows_to_show = st.selectbox("Rows per page", [25, 50, 100, 'All'])
        
        # Apply sorting
        ascending = True if sort_order == 'Ascending' else False
        display_df = display_df.sort_values(by=sort_by, ascending=ascending)
        
        # Format for display
        display_df_formatted = display_df.copy()
        display_df_formatted['Date'] = display_df_formatted['Date'].dt.strftime('%d-%b-%Y')
        display_df_formatted['Description'] = display_df_formatted['Description'].str[:80]
        
        # Select columns to display
        columns_to_show = ['Date', 'Bank', 'Description', 'Category', 'Debit', 'Credit', 'Balance']
        
        # Show data
        if rows_to_show == 'All':
            st.dataframe(
                display_df_formatted[columns_to_show].style.format({
                    'Debit': '₹{:,.2f}',
                    'Credit': '₹{:,.2f}',
                    'Balance': '₹{:,.2f}'
                }),
                use_container_width=True,
                height=600
            )
        else:
            st.dataframe(
                display_df_formatted[columns_to_show].head(rows_to_show).style.format({
                    'Debit': '₹{:,.2f}',
                    'Credit': '₹{:,.2f}',
                    'Balance': '₹{:,.2f}'
                }),
                use_container_width=True,
                height=600
            )
        
        # Download options
        st.subheader("📥 Export Data")
        col1, col2 = st.columns(2)
        
        with col1:
            # Download filtered data as CSV
            csv = display_df[columns_to_show].to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="bank_transactions.csv",
                mime="text/csv"
            )
        
        with col2:
            # Summary statistics
            st.metric("Filtered Transactions", f"{len(display_df):,}")
    
    with tab6:
        st.header("💰 Credit Amount Tracker")
        st.markdown("""
        Track how a specific credit amount was spent across both banks over time.
        Useful for understanding how large deposits (salary, bonuses, etc.) are utilized.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Date input
            credit_date_input = st.date_input(
                "Credit Date",
                value=pd.to_datetime("2025-11-24"),
                min_value=df['Date'].min().date(),
                max_value=df['Date'].max().date()
            )
        
        with col2:
            # Amount input
            credit_amount_input = st.number_input(
                "Credit Amount (₹)",
                min_value=0.0,
                value=397000.0,
                step=1000.0,
                help="Enter the credit amount you want to track"
            )
        
        if st.button("🔍 Analyze Spending", type="primary"):
            analysis = analyze_spending_after_credit(
                df, 
                credit_date_input, 
                credit_amount_input,
                tolerance=5000
            )
            
            if analysis is None:
                st.error(f"❌ No credit transaction found on {credit_date_input} with amount close to ₹{credit_amount_input:,.2f}")
                st.info("Try adjusting the date or amount, or check your transaction history.")
            else:
                # Store in session state
                st.session_state['credit_analysis'] = analysis
        
        # Display analysis if available
        if 'credit_analysis' in st.session_state:
            analysis = st.session_state['credit_analysis']
            
            st.success(f"✅ Found credit of ₹{analysis['credit_amount']:,.2f} on {analysis['credit_date'].strftime('%d %B %Y')} in {analysis['credit_bank']} bank")
            
            # Key metrics with custom styling
            st.subheader("📊 Summary")
            
            # Custom CSS for metrics
            st.markdown("""
                <style>
                [data-testid="stMetricValue"] {
                    font-size: 28px;
                    font-weight: bold;
                }
                [data-testid="stMetricLabel"] {
                    font-size: 16px;
                    font-weight: 600;
                }
                </style>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "💰 Original Credit",
                    f"₹{analysis['credit_amount']:,.2f}"
                )
            
            with col2:
                spent_pct = (analysis['total_spent']/analysis['credit_amount']*100)
                st.metric(
                    "💸 Total Spent",
                    f"₹{analysis['total_spent']:,.2f}",
                    delta=f"{spent_pct:.1f}% of credit",
                    delta_color="inverse"
                )
            
            with col3:
                income_pct = (analysis['total_additional_income']/analysis['credit_amount']*100)
                st.metric(
                    "💵 Additional Income",
                    f"₹{analysis['total_additional_income']:,.2f}",
                    delta=f"+{income_pct:.1f}%" if income_pct > 0 else "No additional income"
                )
            
            with col4:
                remaining_pct = (analysis['remaining']/analysis['credit_amount']*100)
                if analysis['remaining'] >= 0:
                    st.metric(
                        "✅ Current Position",
                        f"₹{analysis['remaining']:,.2f}",
                        delta=f"Surplus {remaining_pct:.1f}%",
                        delta_color="normal"
                    )
                else:
                    st.metric(
                        "⚠️ Current Position",
                        f"₹{analysis['remaining']:,.2f}",
                        delta=f"Deficit {abs(remaining_pct):.1f}%",
                        delta_color="inverse"
                    )
            
            # Time period
            st.info(f"📅 Analysis period: {analysis['days_elapsed']} days ({analysis['credit_date'].strftime('%d %b %Y')} to today)")
            
            st.markdown("---")
            
            # Spending breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Spending by Bank")
                fig_bank = px.bar(
                    analysis['spending_by_bank'],
                    x='Bank',
                    y='Total Spent',
                    color='Bank',
                    text='Total Spent',
                    title='How much was spent in each bank',
                    color_discrete_map={'HDFC': '#FF6B6B', 'SBI': '#4ECDC4'}
                )
                fig_bank.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
                fig_bank.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_bank, use_container_width=True)
                
                # Bank details table
                st.dataframe(
                    analysis['spending_by_bank'].style.format({
                        'Total Spent': '₹{:,.2f}',
                        'Total Income': '₹{:,.2f}',
                        'Transaction Count': '{:,}'
                    }),
                    hide_index=True,
                    use_container_width=True
                )
            
            with col2:
                st.subheader("Spending by Category")
                category_df = analysis['spending_by_category'].reset_index()
                category_df.columns = ['Category', 'Amount']
                category_df['Percentage'] = (category_df['Amount'] / category_df['Amount'].sum() * 100).round(1)
                
                # Vibrant color palette
                colors_category = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', 
                                  '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2']
                
                fig_category = px.pie(
                    category_df,
                    values='Amount',
                    names='Category',
                    title='Where did the money go?',
                    hole=0.4,
                    color_discrete_sequence=colors_category
                )
                fig_category.update_traces(textposition='inside', textinfo='percent+label',
                                          textfont_size=12, marker=dict(line=dict(color='white', width=2)))
                fig_category.update_layout(height=400)
                st.plotly_chart(fig_category, use_container_width=True)
                
                # Category details
                st.dataframe(
                    category_df.style.format({
                        'Amount': '₹{:,.2f}',
                        'Percentage': '{:.1f}%'
                    }),
                    hide_index=True,
                    use_container_width=True
                )
            
            # Daily spending trend
            st.subheader("📈 Daily Spending Trend")
            
            fig_daily = px.line(
                analysis['daily_spending'],
                x='Date',
                y='Debit',
                color='Bank',
                title='Daily spending pattern since credit',
                markers=True,
                labels={'Date': 'Date', 'Debit': 'Amount Spent (₹)'},
                color_discrete_map={'HDFC': '#FF6B6B', 'SBI': '#4ECDC4'}
            )
            fig_daily.update_traces(line=dict(width=3), marker=dict(size=8))
            fig_daily.update_layout(height=400, hovermode='x unified',
                                   plot_bgcolor='rgba(0,0,0,0)',
                                   paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_daily, use_container_width=True)
            
            # Monthly breakdown
            st.subheader("📅 Monthly Spending Breakdown")
            
            # Sort months chronologically
            monthly_data = analysis['spending_by_month'].copy()
            monthly_data['Month_Date'] = pd.to_datetime(monthly_data['Month_Year'], format='%B %Y')
            monthly_data = monthly_data.sort_values('Month_Date')
            
            fig_monthly = px.bar(
                monthly_data,
                x='Month_Year',
                y='Debit',
                color='Bank',
                title='Monthly spending by bank',
                barmode='group',
                labels={'Month_Year': 'Month', 'Debit': 'Amount (₹)'},
                color_discrete_map={'HDFC': '#FF6B6B', 'SBI': '#4ECDC4'}
            )
            fig_monthly.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)',
                                     paper_bgcolor='rgba(0,0,0,0)')
            fig_monthly.update_traces(marker_line_width=1.5, marker_line_color='white')
            st.plotly_chart(fig_monthly, use_container_width=True)
            
            # Top expenses
            st.subheader("💸 Top 20 Expenses Since Credit")
            
            top_exp_display = analysis['top_expenses'].copy()
            top_exp_display['Date'] = top_exp_display['Date'].dt.strftime('%d-%b-%Y')
            top_exp_display['Description'] = top_exp_display['Description'].str[:70]
            
            st.dataframe(
                top_exp_display.style.format({
                    'Debit': '₹{:,.2f}'
                }).background_gradient(subset=['Debit'], cmap='Reds'),
                hide_index=True,
                use_container_width=True,
                height=400
            )
            
            # Download option for this analysis
            st.subheader("📥 Export Analysis")
            col1, col2 = st.columns(2)
            
            with col1:
                # Download transactions since credit
                csv_transactions = analysis['transactions'].to_csv(index=False)
                st.download_button(
                    label=f"Download All Transactions Since {analysis['credit_date'].strftime('%d %b %Y')}",
                    data=csv_transactions,
                    file_name=f"transactions_after_{analysis['credit_date'].strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Download summary
                summary_data = {
                    'Metric': [
                        'Original Credit',
                        'Total Spent',
                        'Additional Income',
                        'Current Position',
                        'Days Elapsed',
                        'Average Daily Spending'
                    ],
                    'Value': [
                        f"₹{analysis['credit_amount']:,.2f}",
                        f"₹{analysis['total_spent']:,.2f}",
                        f"₹{analysis['total_additional_income']:,.2f}",
                        f"₹{analysis['remaining']:,.2f}",
                        analysis['days_elapsed'],
                        f"₹{analysis['total_spent']/max(analysis['days_elapsed'], 1):,.2f}"
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                csv_summary = summary_df.to_csv(index=False)
                st.download_button(
                    label="Download Summary Report",
                    data=csv_summary,
                    file_name=f"spending_summary_{analysis['credit_date'].strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: #666;'>
            <p>Dashboard showing {len(df):,} transactions from {stats['date_range'][0].strftime('%d %b %Y')} 
            to {stats['date_range'][1].strftime('%d %b %Y')}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

except FileNotFoundError as e:
    st.error(f"❌ Error: Could not find the bank statement files. Please check the file paths.")
    st.code(f"XLS_FILE = {XLS_FILE}\nXLSX_FILE = {XLSX_FILE}")
    st.info("Update the file paths at the top of the script with your actual file locations.")

except Exception as e:
    st.error(f"❌ An error occurred: {str(e)}")
    st.exception(e)