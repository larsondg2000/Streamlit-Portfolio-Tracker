import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
import plotly.express as px


def load_portfolio():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM stocks", conn)
    conn.close()
    return df


def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.info['currentPrice']
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
    st.header(":rainbow[Portfolio Analysis]", divider='rainbow')
    st.write("")

    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = load_portfolio()

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

    # Calculate individual sharp ratio
    sharp_individual = (returns_df.mean() / returns_df.std()) * np.sqrt(250)

    # Get values to calculate portfolio Sharpe Ratio
    shares_df = risk_df.filter(["ticker", "shares"])
    shares_df.set_index("ticker", inplace=True)
    prices_df = df_prices.copy()

    # Multiply prices by shares to get total value
    for ticker in shares_df.index:
        if ticker in prices_df.columns:
            prices_df[ticker] = prices_df[ticker] * shares_df.loc[ticker, "shares"]

    # Add a new column that sums each row
    prices_df['Total Value'] = prices_df.iloc[:, 1:].sum(axis=1)

    # Add new column for daily return
    prices_df["return"] = prices_df['Total Value'].pct_change().fillna(0) * 100

    # Calculate Sharpe Ratio
    sharpe_ratio = ((prices_df["return"].mean() / prices_df["return"].std()) * np.sqrt(250)).round(3)

    # Calculate 5 year cum return
    cum_return = ((prices_df['Total Value'].iloc[-1] - prices_df['Total Value'].iloc[0]) /
                  prices_df['Total Value'].iloc[0] * 100)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.subheader("Annual Portfolio Risk")
        st.subheader(f":blue[{sd_p_annual / 100:.3f}]")
    with col2:
        st.subheader("Portfolio Sharpe Ratio")
        st.subheader(f":blue[{sharpe_ratio}]")
    with col3:
        st.subheader("5-Year Cumulative Return")
        st.subheader(f":blue[{cum_return:.2f}%]")
    
    st.divider()

    # Sort the risk values
    sorted_risks = individual_risks.sort_values(ascending=False)
    sorted_risks.index.name = 'Ticker'
    sorted_risks.columns = ['Risk']

    # Plot risk
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
    data = {"Risk": individual_risks,
            "Sharp Ratio": sharp_individual}
    df_test = pd.DataFrame(data)
    st.table(df_test.sort_values(by='Risk', ascending=False).T)

    # Sort and plot Sharp
    sorted_sharp = sharp_individual.sort_values(ascending=False)
    sorted_sharp.index.name = 'Ticker'
    sorted_sharp.columns = ['Sharp']

    # Plot risk
    fig = px.line(sorted_sharp, markers=True)
    fig.update_layout(height=600,
                      title="Sharpe Ratio by Stock",
                      xaxis_title="Stock Ticker",
                      yaxis_title="Sharpe",
                      titlefont_size=26,
                      title_font_color="white",
                      showlegend=False)
    fig.update_traces(line_color='purple')
    st.plotly_chart(fig)


    st.subheader("Risk Explained", divider='rainbow')

    col1, col2, col3 = st.columns([2, 1, 2])
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
        st.image("risk_formulas.png", width=500)

    st.header("")

    st.subheader("Sharpe Ratio Explained", divider='rainbow')

    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown("The Sharpe ratio is a measure of risk-adjusted return, comparing an investment's excess "
                    "return to its volatility. It helps investors understand the return of an investment compared "
                    "to its risk, providing a way to compare different investments on a risk-adjusted basis.")
        st.write("")
        st.markdown('''
        **Sharpe Ratio Calculation**:
        - Calculates the average return of the portfolio over the risk-free rate.
        - Determines the standard deviation of the portfolio returns.
        - Divides the excess return by the standard deviation to get the Sharpe ratio.
        - A higher Sharpe ratio indicates better risk-adjusted performance.
        ''')

    with col2:
        st.write("")

    with col3:
        st.image("sharp.png", width=300)

    rainbow_divider = """
      <hr style="height:5px;border:none;background:linear-gradient(to right, red, orange, 
      yellow, green, blue, indigo, violet);">
      """
    st.markdown(rainbow_divider, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
