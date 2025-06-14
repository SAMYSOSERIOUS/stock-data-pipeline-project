import streamlit as st

def apply_theme():
    # Import Cascadia Code font
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Cascadia+Code:wght@400;700&display=swap" rel="stylesheet">
    <style>
        /* Base theme */
        .stApp {
            background-color: #0E1117;
            color: #E0E0E0;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        
        /* Headers and Sections using Cascadia Code */
        .header-style, h1, h2, h3, 
        div[data-testid="stMarkdownContainer"] h1,
        div[data-testid="stMarkdownContainer"] h2,
        div[data-testid="stMarkdownContainer"] h3,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
        div[data-testid="stSidebar"] .stMarkdown h1,
        div[data-testid="stSidebar"] .stMarkdown h2 {
            font-family: 'Cascadia Code', monospace;
            font-weight: 700;
            color: #00ADB5;
        }
        
        /* Metric titles in Cascadia Code */
        div[data-testid="stMetricLabel"] {
            font-family: 'Cascadia Code', monospace;
            font-weight: 700;
            color: #00ADB5;
        }
        
        .stock-card, div[data-testid="stMetricValue"] {            background-color: #1A1B26;
            padding: 1rem;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            margin-bottom: 1rem;
            border: 1px solid #2F3136;
        }
        div[data-testid="stMetricValue"] {
            background-color: #1A1B26;
            padding: 1rem;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 0.5rem 0;
        }
        div[data-testid="stMetricDelta"] {
            background-color: transparent;
        }
        .header-style {
            color: #1d4f90;
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .subheader-style {
            color: #2c3e50;
            font-size: 1.4rem;
            font-weight: 500;
            margin: 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #eaeaea;
        }
        .stSelectbox > div {
            background-color: white;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }        div[data-testid="stSidebar"] {
            background-color: #1A1B26;
            border-right: 1px solid #2F3136;
            padding: 2rem 1rem;
        }
        div[data-testid="stSidebar"] > div:first-child {
            padding: 1rem;
        }
        div[data-testid="stSidebar"] .stMetric {
            background-color: #151821;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        .element-container .stDataFrame, .element-container .stTable {
            background-color: white;
            padding: 1rem;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }        div[data-testid="stMetricValue"] > div {
            font-family: 'Cascadia Code', monospace;
            font-size: 1.6rem;
            font-weight: 700;
            color: #E0E0E0;
        }
        div[data-testid="stMetricDelta"] > div {
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 1rem;
            color: #A0A0A0;
        }
        div[data-testid="stMetricDelta"][data-direction="up"] > div {
            color: #00FF9F;
        }
        div[data-testid="stMetricDelta"][data-direction="down"] > div {
            color: #FF5B5B;
        }
        .stAlert {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
        }
        .stImage > img {
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
