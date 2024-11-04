import streamlit as st
import yfinance as yf
import boto3
import json
import requests
import pandas as pd
import plotly.graph_objects as go
import requests
from textblob import TextBlob

# Configuration des clés d'API et AWS S3
news_api_key = "ddd73f9423ad41c2aff5090e8493c142"
s3 = boto3.client('s3', region_name='us-west-2')

# Configuration de la page
st.set_page_config(page_title="Tableau de Bord Financier Intelligent", layout="wide")

# Fonction de chargement des données KPI
@st.cache_data
def get_kpi_data(symbol):
    ticker = yf.Ticker(symbol)
    kpi_data = ticker.history(period="5y")
    kpi_data['NET_CHANGE'] = kpi_data['Close'].pct_change() * 100
    kpi_data.index = kpi_data.index.tz_localize(None)  # Supprime les informations de fuseau horaire
    return kpi_data

# Fonction pour obtenir les rapports financiers
def get_financial_reports(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.balance_sheet, ticker.financials, ticker.cashflow

# Simulation de scénario
def simulate_scenario(revenue_growth, cost_growth, margin):
    revenue_projection = [100 * (1 + revenue_growth)**i for i in range(5)]
    cost_projection = [80 * (1 + cost_growth)**i for i in range(5)]
    profit_projection = [(r - c) * margin for r, c in zip(revenue_projection, cost_projection)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(5)), y=revenue_projection, mode='lines+markers', name="Revenus"))
    fig.add_trace(go.Scatter(x=list(range(5)), y=cost_projection, mode='lines+markers', name="Coûts"))
    fig.add_trace(go.Scatter(x=list(range(5)), y=profit_projection, mode='lines+markers', name="Profit"))
    fig.update_layout(title="Projection Financière", height=300, margin=dict(l=10, r=10, t=30, b=10))
    return fig

# Fonction pour obtenir les scores ESG
def get_esg_scores(symbol):
    ticker = yf.Ticker(symbol)
    esg_data = ticker.sustainability
    if esg_data is not None:
        return {
            'Environment': esg_data.loc['environmentScore'].values[0] if 'environmentScore' in esg_data.index else None,
            'Social': esg_data.loc['socialScore'].values[0] if 'socialScore' in esg_data.index else None,
            'Governance': esg_data.loc['governanceScore'].values[0] if 'governanceScore' in esg_data.index else None
        }
    return {'Environment': None, 'Social': None, 'Governance': None}

# Analyse de sentiment
def get_sentiment(query):
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&apiKey={news_api_key}"
    response = requests.get(url)
    articles = response.json().get('articles', [])
    sentiments = [TextBlob(article['description']).sentiment.polarity for article in articles if article['description']]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    s3.put_object(
        Bucket='tableau-de-bord-datathon',
        Key=f'Sentiment/{query}_news_sentiment.json',
        Body=json.dumps({'sentiment': avg_sentiment})
    )
    return avg_sentiment

# Affichage principal
st.title("Tableau de Bord Financier Intelligent")

# Paramètres utilisateur dans la barre latérale
symbol = st.sidebar.text_input("Entrez le symbole boursier :", value="AAPL").upper()

if symbol:
    kpi_data = get_kpi_data(symbol)
    
    # Bloc KPI
    latest_price = kpi_data['Close'].iloc[-1]
    volume = kpi_data['Volume'].iloc[-1]
    net_change = kpi_data['NET_CHANGE'].iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Prix actuel", f"${latest_price:.2f}")
    col2.metric("Volume", f"{volume:,.0f}")
    col3.metric("Variation", f"{net_change:.2f}%")

    # Affichage des rapports financiers
    st.subheader("📊 Rapports Financiers")
    balance_sheet, income_statement, cashflow = get_financial_reports(symbol)
    col1, col2, col3 = st.columns(3)
    col1.write("Bilan")
    col1.dataframe(balance_sheet)
    col2.write("Compte de Résultat")
    col2.dataframe(income_statement)
    col3.write("Flux de Trésorerie")
    col3.dataframe(cashflow)

    # Simulation de scénario
    st.subheader("📈 Simulation de Scénario")
    col1, col2, col3 = st.columns(3)
    revenue_growth = col1.slider("Croissance des Revenus (%)", 0.01, 0.2, 0.05)
    cost_growth = col2.slider("Croissance des Coûts (%)", 0.01, 0.2, 0.05)
    margin = col3.slider("Marge Bénéficiaire", 0.1, 0.5, 0.2)
    st.plotly_chart(simulate_scenario(revenue_growth, cost_growth, margin), use_container_width=True)

    # Bloc Score ESG
    st.subheader("🌍 Score ESG")
    esg_scores = get_esg_scores(symbol)
    col1, col2, col3 = st.columns(3)
    col1.metric("Environnement", esg_scores.get('Environment', 'N/A'))
    col2.metric("Social", esg_scores.get('Social', 'N/A'))
    col3.metric("Gouvernance", esg_scores.get('Governance', 'N/A'))

    # Sentiment des actualités
    st.subheader("📰 Sentiment des Actualités")
    sentiment = round(get_sentiment(symbol)*100)
    st.metric("Sentiment moyen", f"{sentiment}%")

    # Affichage de la DataFrame filtrée
    st.write("**Données Filtrées :**")
    st.dataframe(kpi_data)
