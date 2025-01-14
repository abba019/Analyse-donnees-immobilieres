import streamlit as st
from sqlalchemy import create_engine
import pandas as pd
from babel.numbers import format_currency
import os

def amt(amount):
    return format_currency(amount, "CAD", "#,##0 ¤", "fr_CA", False)

POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
db_url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        
engine = create_engine(db_url)

# Function to load data
@st.cache_data
def load_data():
    query = "SELECT * FROM \"Logements\""
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

# Function to set up session state
def initialize_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "home"

# Function to display the home page
def display_home_page(data):
    # Page title
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>Annonces immobilières</h1>", unsafe_allow_html=True)

    # Filter section in horizontal layout
    st.subheader("Filtres de recherche")
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        prices = st.slider("Prix (CAD)", value=0, step=50000, key="price_slider")

    with col2:
        Parking = st.number_input("Espace stationnement", value=0, step=1, format="%d")

    with col3:
        bedrooms = st.number_input("Chambres", min_value=0, value=0)

    # Apply filters to data
    filtered_data = data[
        (data["price"] >= prices[0]) &
        (data["price"] <= prices[1]) &
        (data["parking_spaces"] >= Parking) &
        (data["bedrooms"] >= bedrooms)
    ]  # Limit to 10 listings for display

    # Display filtered data in rows of 4 columns using Streamlit's `columns`
    display_filtered_data(filtered_data)

# Affichage des statistiques générales améliorées
def display_statistics(data):
    st.subheader("📊 Statistiques Générales")

    # Statistiques calculées
    stats = {
        "🏠 Prix moyen (CAD)": f"{data['price'].mean():,.2f} CAD",
        "📈 Prix médian (CAD)": f"{data['price'].median():,.2f} CAD",
        "💰 Prix minimum (CAD)": f"{data['price'].min():,.2f} CAD",
        "💵 Prix maximum (CAD)": f"{data['price'].max():,.2f} CAD",
        "🔢 Nombre d'annonces": f"{len(data)}",
        "🛏 Chambres moyennes": f"{data['bedrooms'].mean():.2f}",
        "🚗 Places de parking moyennes": f"{data['parking_spaces'].mean():.2f}",
    }
# Function to display filtered data
def display_filtered_data(filtered_data):
    st.subheader("Annonces disponibles")
    # Iterate over the filtered data in chunks of 4 to create rows of 4 listings
    for i in range(0, len(filtered_data), 4):
        cols = st.columns(4)  # Create a new row with 4 columns
        for j, (col, (_, annonce)) in enumerate(zip(cols, filtered_data.iloc[i:i+4].iterrows())):
            with col:
                st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1); min-height: 200px;">
                        <a href="{annonce.get('url', '#')}">
                            <div style="font-size: 18px; color: #333; font-weight: bold; margin-bottom: 10px;">{annonce['address']}</div>
                        </a>
                        <div>{amt(annonce['price'])}</div>
                        <div>{int(annonce['bedrooms'])} chambres, {int(annonce['bathrooms'])} salles de bain</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Voir les détails", key=f"details_{i}_{j}"):
                    # Store the selected listing details in session_state
                    st.session_state.selected_annonce = annonce.to_dict()
                    st.session_state.page = "details"
                    st.switch_page("pages/details.py")

# Main app logic
def main():
    # Initialize session state
    initialize_session_state()
    # Load data
    data = load_data()


    # Display content based on the current page in session state
    if st.session_state.page == "home":
        display_home_page(data)
    elif st.session_state.page == "details":
        st.stop()

# Run the app
if __name__ == "__main__":
    main()
