import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stocks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ticker TEXT NOT NULL,
                  shares REAL NOT NULL,
                  cost_basis REAL NOT NULL)''')
    conn.commit()
    conn.close()


def load_portfolio():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM stocks", conn)
    conn.close()
    return df


def save_stock(ticker, account, shares, cost_basis):
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()

    # Add the 'account' column if it doesn't exist
    # c.execute("ALTER TABLE stocks ADD COLUMN account TEXT")

    c.execute("INSERT INTO stocks (ticker, account, shares, cost_basis) VALUES (?, ?, ?, ?)",
              (ticker, account, shares, cost_basis))
    conn.commit()
    conn.close()


def update_stock(id, account, shares, cost_basis):
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    if shares > 0:
        c.execute("UPDATE stocks SET account = ?, shares = ?, cost_basis = ? WHERE id = ?",
                  (account, shares, cost_basis, id))
    else:
        c.execute("DELETE FROM stocks WHERE id = ?", (id,))
    conn.commit()
    conn.close()


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
    st.set_page_config(layout="wide", page_title="Portfolio Tracker", page_icon=":material/trending_up:")

    st.header(":rainbow[Stock Portfolio Tracker]", divider='rainbow')
    st.write("")

    init_db()

    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = load_portfolio()

    account_options = ['Webull', 'Fidelity', 'HSA']

    # Create a new DataFrame for display
    display_df = st.session_state.portfolio.copy()
    display_df['Current Price'] = display_df['ticker'].apply(get_current_price)
    display_df['Total Value'] = display_df['shares'] * display_df['Current Price']
    total_portfolio_value = display_df['Total Value'].sum()
    display_df['Portfolio %'] = (display_df['Total Value'] / total_portfolio_value) * 100
    display_df['Gain/Loss'] = display_df['Total Value'] - (display_df['cost_basis'] * display_df['shares'])
    display_df['Gain/Loss %'] = (display_df['Gain/Loss'] / (display_df['cost_basis'] * display_df['shares'])) * 100

    # Sort the DataFrame by Total Value, from highest to lowest
    display_df = display_df.sort_values('Total Value', ascending=False)

    # Format the DataFrame for display
    display_df['Shares'] = display_df['shares'].apply(lambda x: f"{x:.2f}")
    display_df['Cost Basis'] = display_df['cost_basis'].apply(lambda x: f"${x:.2f}")
    display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"${x:.2f}" if x else "N/A")
    display_df['Total Value'] = display_df['Total Value'].apply(lambda x: f"${x:.2f}")
    display_df['Portfolio %'] = display_df['Portfolio %'].apply(lambda x: f"{x:.2f}%")
    display_df['Gain/Loss'] = display_df['Gain/Loss'].apply(lambda x: f"${x:.2f}")
    display_df['Gain/Loss %'] = display_df['Gain/Loss %'].apply(lambda x: f"{x:.2f}%")

    # Reorder and rename columns
    display_df = display_df[['ticker', 'account', 'Shares', 'Cost Basis', 'Current Price', 'Total Value', 'Portfolio %',
                             'Gain/Loss', 'Gain/Loss %']]
    display_df.columns = ['Ticker', 'Account', 'Shares', 'Cost Basis', 'Current Price', 'Total Value', 'Portfolio %',
                          'Gain/Loss', 'Gain/Loss %']

    # Display total portfolio value and total gain/loss
    total_value = display_df['Total Value'].apply(lambda x: float(x.replace('$', ''))).sum()
    total_cost = (st.session_state.portfolio['cost_basis'] * st.session_state.portfolio['shares']).sum()
    total_gain_loss = total_value - total_cost
    total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0

    # Create a DataFrame for charts
    chart_df = display_df.copy()
    chart_df['Total Value'] = chart_df['Total Value'].apply(lambda x: float(x.replace('$', '').replace(',', '')))
    chart_df['Gain/Loss'] = chart_df['Gain/Loss'].apply(lambda x: float(x.replace('$', '').replace(',', '')))
    chart_df['Gain/Loss %'] = chart_df['Gain/Loss %'].apply(lambda x: float(x.replace('%', '')))

    # Portfolio Summary section
    st.subheader(":blue[Portfolio Summary]")

    col1, col2, col3 = st.columns([3, 1, 3])

    with col1:
        fig2 = px.pie(chart_df, values='Total Value', names='Ticker', title='Portfolio Composition')
        fig2.update_layout(
            title=""
        )
        st.plotly_chart(fig2)

    with col2:
        st.write("")

    with col3:
        st.write(f"Total Portfolio Value: ")
        st.subheader(f":green[${total_value:.2f}]")
        st.divider()
        st.write(f"Total Gain/Loss: ")
        st.subheader(f":green[${total_gain_loss:.2f}]")
        st.divider()
        st.write("Percent Gain/Loss: ")
        st.subheader(f":green[{total_gain_loss_percent:.2f}%]")

    st.divider()

    st.subheader(":blue[My Stocks]")

    # Set index start to 1 and display "My Stocks"" table
    display_df.index = range(1, len(display_df)+1)
    # sorted_df = display_df.sort_values(by='Total Value', ascending=False)
    st.table(display_df)

    # Collapsible section for adding new stock
    with st.expander("Add New Stock"):
        with st.form("add_stock_form"):
            ticker = st.text_input("Stock Ticker (e.g., MSFT)").upper()
            account = st.selectbox("Account", account_options)
            shares = st.number_input("Number of Shares", min_value=0.01, step=0.01)
            cost_basis = st.number_input("Cost Basis per Share", min_value=0.01, step=0.01)

            submitted = st.form_submit_button("Add Stock")
            if submitted:
                print(account)
                save_stock(ticker, account, shares, cost_basis)
                st.session_state.portfolio = load_portfolio()
                st.success(f"Added {ticker} to your {account} portfolio!")

    # Edit my stocks functionality in an expander
    with st.expander("Edit Portfolio"):
        st.subheader("Edit Your Holdings")
        for index, row in st.session_state.portfolio.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                st.write(row['ticker'])
            with col2:
                account = st.selectbox(f"Account for {row['ticker']}", account_options,
                                       index=account_options.index(row['account']), key=f"account_{row['id']}")
            with col3:
                shares = st.number_input(f"Shares {row['ticker']}", value=row['shares'], key=f"shares_{row['id']}")
            with col4:
                cost_basis = st.number_input(f"Cost Basis {row['ticker']}", value=row['cost_basis'],
                                             key=f"cost_{row['id']}")
            with col5:
                if st.button("Update", key=f"update_{row['id']}"):
                    update_stock(row['id'], account, shares, cost_basis)
                    st.session_state.portfolio = load_portfolio()
                    if shares > 0:
                        st.success(f"Updated {row['ticker']} in your portfolio!")
                    else:
                        st.success(f"Removed {row['ticker']} from your portfolio!")
                    st.success(f"Updated {row['ticker']} in your portfolio!")
                    st.rerun()

    st.divider()

    # Bar charts showing total Gain and Gain Percentage by Ticker
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                         subplot_titles=('Total Gain/Loss by Ticker', 'Gain/Loss Percentage by Ticker'))

    # Total Gain/Loss bar chart
    fig1.add_trace(
        go.Bar(
            x=chart_df['Ticker'],
            y=chart_df['Gain/Loss'],
            name='Total Gain/Loss',
            marker_color=['red' if x < 0 else 'green' for x in chart_df['Gain/Loss']]
        ),
        row=1, col=1
    )

    # Gain/Loss Percentage bar chart
    fig1.add_trace(
        go.Bar(
            x=chart_df['Ticker'],
            y=chart_df['Gain/Loss %'],
            name='Gain/Loss %',
            marker_color=['red' if x < 0 else 'green' for x in chart_df['Gain/Loss %']]
        ),
        row=2, col=1
    )

    fig1.update_layout(height=1200,
                       title_text="Portfolio Performance by Ticker",
                       titlefont_size=26,
                       title_font_color="white",
                       showlegend=False,
                       xaxis_showticklabels=True
                       )
    # fig1.update_xaxes(title_text="Ticker", row=1, col=1)
    # fig1.update_xaxes(title_text="Ticker", row=2, col=1)
    fig1.update_yaxes(title_text="Total Gain/Loss ($)", row=1, col=1)
    fig1.update_yaxes(title_text="Gain/Loss %", row=2, col=1)

    st.plotly_chart(fig1)

    # Streamlit logo
    logo_url = "https://streamlit.io/images/brand/streamlit-logo-primary-colormark-darktext.png"
    st.image(logo_url, width=100)

    rainbow_divider = """
    <hr style="height:10px;border:none;background:linear-gradient(to right, red, orange, 
    yellow, green, blue, indigo, violet);">
    """
    st.markdown(rainbow_divider, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
