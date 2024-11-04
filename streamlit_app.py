import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from textblob import TextBlob
import boto3
import json
import datetime

# Configuration de la page
st.set_page_config(page_title="Tableau de Bord Financier Intelligent", layout="wide")

# Configuration des services AWS
s3 = boto3.client('s3', region_name='us-west-2')
bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')

# Clé API NewsAPI
YOUR_NEWS_API_KEY = "ddd73f9423ad41c2aff5090e8493c142"

# Fonction pour récupérer les scores ESG
def get_esg_scores(symbol):
    ticker = yf.Ticker(symbol)
    esg_data = ticker.sustainability
    if esg_data is not None:
        esg_scores = {
            'Environment': esg_data.loc['environmentScore'].values[0],
            'Social': esg_data.loc['socialScore'].values[0],
            'Governance': esg_data.loc['governanceScore'].values[0]
        }
    else:
        esg_scores = {'Environment': None, 'Social': None, 'Governance': None}
    return esg_scores

# Fonction de chargement des données KPI, avec moyenne annuelle
@st.cache_data
def get_kpi_data(symbol):
    ticker = yf.Ticker(symbol)
    kpi_data = ticker.history(period="5y")
    kpi_data['Year'] = kpi_data.index.year
    kpi_data = kpi_data.groupby('Year').mean()  # Moyenne annuelle
    kpi_data['NET_CHANGE'] = kpi_data['Close'].pct_change() * 100
    return kpi_data

# Fonction pour afficher les KPI en barres par année
def plot_kpi_barchart(kpi_data):
    fig = go.Figure()
    metrics = ['Close', 'Volume', 'Open', 'High']
    for i, metric in enumerate(metrics):
        fig.add_trace(go.Bar(
            x=kpi_data.index,
            y=kpi_data[metric],
            name=metric,
            marker_color=f"rgba({(i+1)*50}, {(i+1)*30}, 150, 0.6)"
        ))
    fig.update_layout(barmode='group', title="KPI Annuel", xaxis_title="Année", yaxis_title="Valeur")
    st.plotly_chart(fig)

# Fonction pour afficher les scores ESG
def plot_esg_scores(esg_scores):
    fig = go.Figure()
    for category, score in esg_scores.items():
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=score if score is not None else 0,
            title={'text': category},
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "green" if score and score > 50 else "red"}}
        ))
    fig.update_layout(title="Scores ESG")
    st.plotly_chart(fig)

# Fonction pour obtenir un résumé critique des rapports financiers via AWS Bedrock
def get_financial_report_summary(symbol):
    prompt = f"Analyser les rapports financiers de {symbol}. Inclure les points clés, les chiffres importants, et les 'non-dits'. Lire entre les lignes."
    try:
        response = bedrock.invoke_model(
            modelId='amazon.titan-tg1-large',  # Remplacez par le modèle disponible
            body=json.dumps({"inputText": prompt}),
            contentType='application/json',
        )
        result = json.loads(response['body'].read())
        report_summary = result.get('results', [{}])[0].get('generated_text', "Aucun résumé disponible")
    except Exception as e:
        st.error(f"Erreur lors de la génération du résumé : {e}")
        report_summary = "Impossible de générer le résumé."
    
    return report_summary

# Fonction pour analyser l'évolution du sentiment dans le temps
def get_sentiment_trend(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&language=en&apiKey={YOUR_NEWS_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Erreur lors de la récupération des actualités.")
        return pd.DataFrame(), 0
    
    articles = response.json().get('articles', [])
    sentiments = []
    dates = []
    
    for article in articles:
        if 'description' in article and article['description']:
            polarity = TextBlob(article['description']).sentiment.polarity
            sentiments.append(polarity)
            dates.append(datetime.datetime.strptime(article['publishedAt'][:10], "%Y-%m-%d"))
    
    sentiment_df = pd.DataFrame({"Date": dates, "Sentiment": sentiments})
    sentiment_df = sentiment_df.set_index('Date').resample('M').mean()  # Moyenne mensuelle
    avg_sentiment = round(sentiment_df['Sentiment'].mean() * 100, 2) if not sentiment_df.empty else 0
    return sentiment_df, avg_sentiment

# Affichage du graphique de tendance du sentiment
def plot_sentiment_trend(sentiment_df, avg_sentiment):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sentiment_df.index, y=sentiment_df['Sentiment'], mode='lines+markers', name="Sentiment"))
    fig.update_layout(title="Évolution du Sentiment (moyenne mensuelle)", xaxis_title="Date", yaxis_title="Score de Sentiment")
    st.plotly_chart(fig)
    st.write(f"Sentiment moyen actuel : {avg_sentiment}%")

# Fonction Chatbot pour analyse avancée avec Titan de Bedrock
def chatbot_response(question):
    try:
        response = bedrock.invoke_model(
            modelId='amazon.titan-tg1-large',  # Remplacez par le modèle disponible
            body=json.dumps({"inputText": question}),
            contentType='application/json',
        )
        result = json.loads(response['body'].read())
        chatbot_reply = result.get('results', [{}])[0].get('generated_text', "Pas de réponse disponible")
    except Exception as e:
        st.error(f"Erreur lors de la génération de la réponse du chatbot : {e}")
        chatbot_reply = "Impossible de générer la réponse."
    
    return chatbot_reply

# Interface principale Streamlit
st.title("Tableau de Bord Financier Intelligent")

# Input pour choisir l'entreprise
symbol = st.sidebar.text_input("Entrez le symbole boursier :", value="AAPL").upper()

if symbol:
    # Affichage des KPI avec un graphique à barres annuelles
    kpi_data = get_kpi_data(symbol)
    st.subheader("📊 Données KPI Annuel")
    plot_kpi_barchart(kpi_data)
    
    # Affichage des scores ESG
    esg_scores = get_esg_scores(symbol)
    st.subheader("🌍 Score ESG")
    plot_esg_scores(esg_scores)
    
    # Résumé critique des rapports financiers via Bedrock
    st.subheader("📄 Résumé Critique des Rapports Financiers")
    report_summary = get_financial_report_summary(symbol)
    st.write(report_summary)
    
    # Graphique de l'évolution du sentiment des actualités
    st.subheader("📰 Sentiment des Actualités")
    sentiment_df, avg_sentiment = get_sentiment_trend(symbol)
    plot_sentiment_trend(sentiment_df, avg_sentiment)
    
    # Chatbot pour analyse avancée avec Titan de Bedrock
    st.subheader("💬 Chatbot d'Assistance")
    question = st.text_input("Posez une question à l'IA :")
    if question:
        response = chatbot_response(question)
        st.write(response)
