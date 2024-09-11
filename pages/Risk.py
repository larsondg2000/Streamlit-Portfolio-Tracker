import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def load_portfolio():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM stocks", conn)
    conn.close()
    return df


def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d").Close.iloc[0]
        return price
    except IndexError:
        # Handle the case where the history data is empty
        print(f"No historical data available for ticker: {ticker}")
        return None
    except Exception as e:
        # Handle any other exceptions
        print(f"An error occurred: {e}")
        return None


def main():
    st.set_page_config(layout="wide", page_title="Risk Analysis", page_icon=":material/analytics:")
    st.title(":rainbow[Portfolio Risk Analysis]")
    st.divider()

    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = load_portfolio()

    # Load portfolio data
    portfolio = load_portfolio()

    # Get weights list for individual stocks (Portfolio %)
    risk_df = st.session_state.portfolio.copy()
    risk_df['Current Price'] = risk_df['ticker'].apply(get_current_price)
    risk_df['Total Value'] = risk_df['shares'] * risk_df['Current Price']
    total_portfolio_value = risk_df['Total Value'].sum()
    risk_df['Portfolio %'] = (risk_df['Total Value'] / total_portfolio_value) * 100
    weights_list = risk_df['Portfolio %'].tolist()

    # Create list of stocks (tickers)
    stock_list = risk_df['ticker'].tolist()

    # Get historical stock price data for the last 5 years
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365 * 5)).strftime('%Y-%m-%d')

    data = {}

    for stock in stock_list:
        ticker = yf.Ticker(stock)
        history = ticker.history(start=start_date, end=end_date)
        data[stock] = history['Close']

    df_prices = pd.DataFrame(data)
    df_prices.index = df_prices.index.tz_localize(None)
    df_prices.bfill(inplace=True)

    # Calculate percent change and covariance matrix from price history
    returns_df = df_prices.pct_change(1)
    vcv_matrix = returns_df.cov()

    # Calculate variance and standard deviation
    var_p = np.dot(np.transpose(weights_list), np.dot(vcv_matrix, weights_list))
    sd_p = np.sqrt(var_p)

    # Get annual portfolio and individual stock risks
    sd_p_annual = sd_p * np.sqrt(250)
    individual_risks = np.std(returns_df, axis=0, ddof=1) * np.sqrt(250)

    # Sort the risk values
    sorted_risks = individual_risks.sort_values(ascending=False)
    sorted_risks.index.name = 'Ticker'
    sorted_risks.columns = ['Risk']

    st.subheader("Annual Portfolio Risk")
    st.subheader(f":blue[{sd_p_annual / 100:.3f}]")
    st.divider()

    fig = px.line(sorted_risks, markers=True)
    fig.update_layout(height=600,
                      title="Risk by Stock",
                      xaxis_title="Stock Ticker",
                      yaxis_title="Risk",
                      titlefont_size=26,
                      title_font_color="white",
                      showlegend=False)
    st.plotly_chart(fig)

    # Display risks as a row under the chart
    data = {"Risk": individual_risks}
    df_test = pd.DataFrame(data)
    st.table(df_test.sort_values(by='Risk', ascending=False).T)

    rainbow_divider = """
    <hr style="height:10px;border:none;background:linear-gradient(to right, red, orange, 
    yellow, green, blue, indigo, violet);">
    """
    st.markdown(rainbow_divider, unsafe_allow_html=True)

    st.subheader("Risk Calculation Explained")

    col1, col2, col3 = st.columns([2, .3, 2])
    with col1:
        st.markdown("This assesses the risk associated with individual stocks and the overall portfolio by calculating "
                    "key statistical measures such as variance, standard deviation, covariance, and weighted return. "
                    "It utilizes historical data from Yahoo Finance and performs quantitative risk analysis.")
        st.write("")
        st.markdown('''
                 **Risk Calculation**:
                 - Uses 5-year daily returns and generates a covariance matrix.
                 - Calculates portfolio variance and standard deviation on a daily and annual basis.
                 - Determines individual stock risks and aggregates them to evaluate overall portfolio risk.
                 ''')
    with col2:
        st.write("")
    with col3:
        st.image("risk_formulas.png")


if __name__ == "__main__":
    main()
