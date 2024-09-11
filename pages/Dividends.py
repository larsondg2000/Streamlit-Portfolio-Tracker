import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime


def load_portfolio():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM stocks", conn)
    conn.close()
    return df


def get_dividend_info(ticker, shares):
    stock = yf.Ticker(ticker)
    info = stock.info
    if 'dividendRate' in info and info['dividendRate'] is not None:
        ex_date = info.get('exDividendDate')
        if ex_date:
            ex_date = datetime.fromtimestamp(ex_date).strftime('%m-%d-%Y')
        else:
            ex_date = 'N/A'
        return {
            'ticker': ticker,
            'shares': shares,
            'dividend_rate': info.get('dividendRate', 0),
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'payout_ratio': info.get('payoutRatio', 0) * 100 if info.get('payoutRatio') else 0,
            'ex_dividend_date': ex_date,
            'yearly_dividend_total': shares * info.get('dividendRate', 0)
        }
    return None


def main():
    st.set_page_config(layout="wide", page_title="Dividends", page_icon=":material/attach_money:")
    st.title(":rainbow[Dividend Tracker]")
    st.divider()

    # Load portfolio data
    portfolio = load_portfolio()

    # Get dividend information for each stock
    dividend_data = []
    for _, row in portfolio.iterrows():
        div_info = get_dividend_info(row['ticker'], row['shares'])
        if div_info:
            dividend_data.append(div_info)

    # Create DataFrame from dividend data
    if dividend_data:
        df = pd.DataFrame(dividend_data)

        # Display the dividend table
        st.subheader("My Dividend Stocks")

        # Modify Table Column Headings
        df.columns = ['Ticker', 'Shares', 'Dividend', 'Yield', 'Payout', 'Ex-Date', 'Total']

        # Format the DataFrame for display
        df['Shares'] = df['Shares'].apply(lambda x: f"{x:.2f}")
        df['Dividend'] = df['Dividend'].apply(lambda x: f"${x:.2f}")
        df['Yield'] = df['Yield'].apply(lambda x: f"{x:.2f}%")
        df['Payout'] = df['Payout'].apply(lambda x: f"{x:.2f}%")
        df['Total'] = df['Total'].apply(lambda x: f"${x:.2f}")

        # Change index to one
        df.index = range(1, len(df) + 1)

        col1, col2, col3 = st.columns([2.2, .8, 1.5])

        with col1:
            st.dataframe(df)

        with col2:
            # Display total yearly dividends and average yield
            st.write("")
            st.write("")
            total_yearly_dividends = df['Total'].apply(lambda x: float(x.replace('$', ''))).sum()
            st.write(f"Total Yearly Dividends: ")
            st.subheader(f":green[${total_yearly_dividends:.2f}]")
            df['Yield'] = df['Yield'].apply(lambda x: float(x.replace('%', '')))
            average_yield = df['Yield'].mean()
            # st.divider()
            st.write("")
            st.write("")
            st.write(f"Average Dividend Yield: ")
            st.subheader(f":green[{average_yield:.2f}%]")

        with col3:
            df['Total'] = df['Total'].apply(lambda x: float(x.replace('$', '')))
            fig2 = px.pie(df, values='Total', names='Ticker', title='Dividends by Stock')
            fig2.update_layout(
                title="                                    Dividends by Stock"
            )
            st.plotly_chart(fig2)

        st.divider()

        # convert payout ratio to float for chart
        df['Payout'] = df['Payout'].apply(lambda x: float(x.replace('%', '')))

        # Generate charts
        fig = make_subplots(rows=3, cols=1, subplot_titles=("Yearly Dividend Totals", "Dividend Yield", "Payout Ratio"))

        # Dividend totals vs. ticker
        fig.add_trace(
            go.Bar(x=df['Ticker'], y=df['Total'], name="Yearly Dividend Total"),
            row=1, col=1
        )

        # Dividend yield vs. ticker
        fig.add_trace(
            go.Bar(x=df['Ticker'], y=df['Yield'], name="Dividend Yield", marker_color='gray'),
            row=2, col=1
        )

        # Payout ratio vs. ticker (color-coded)
        colors = ['green' if x < 50 else 'yellow' if 50 <= x < 70 else 'red' for x in df['Payout']]
        fig.add_trace(
            go.Bar(x=df['Ticker'], y=df['Payout'], name="Payout Ratio", marker_color=colors),
            row=3, col=1
        )

        fig.update_layout(height=1200, title_text="Dividend Analysis", titlefont_size=26,)
        fig.update_xaxes(title_text="Ticker", row=3, col=1)
        fig.update_yaxes(title_text="Yearly Dividend Total ($)", row=1, col=1)
        fig.update_yaxes(title_text="Dividend Yield (%)", row=2, col=1)
        fig.update_yaxes(title_text="Payout Ratio (%)", row=3, col=1)

        st.plotly_chart(fig)
    else:
        st.write("No dividend-paying stocks found in your portfolio.")


if __name__ == "__main__":
    main()
