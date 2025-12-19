"""
Claude Code Analytics Dashboard

A Streamlit application for analyzing Claude Code conversation transcripts.
"""

import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Claude Code Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define pages
about_page = st.Page(
    "pages/about.py",
    title="About",
    icon="ℹ️",
)

browser_page = st.Page(
    "pages/browser.py",
    title="Browse Sessions",
    icon="📚",
    default=True,
)

analysis_page = st.Page(
    "pages/analysis.py",
    title="Run Analysis",
    icon="🔬",
)

analytics_page = st.Page(
    "pages/analytics.py",
    title="Analytics Dashboard",
    icon="📊",
)

conversation_page = st.Page(
    "pages/conversation.py",
    title="View Conversation",
    icon="💬",
)

import_data_page = st.Page(
    "pages/import_data.py",
    title="Import Data",
    icon="📥",
)

# Build navigation
pg = st.navigation(
    {
        "Browse": [browser_page, conversation_page],
        "Analysis": [analysis_page, analytics_page],
        "Data": [import_data_page],
        "Info": [about_page],
    }
)

# Run the selected page
pg.run()
