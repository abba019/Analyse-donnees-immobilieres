import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import folium_static
from sqlalchemy import create_engine

# Configuration de la base de données
db_url = "postgresql://postgres:postgres.123@postgres:5432/db_immo"
engine = create_engine(db_url)

# Fonction d'initialisation de session_state
def initialize_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "home"  # Page d'accueil par défaut
    if "selected_annonce" not in st.session_state:
        st.session_state.selected_annonce = {}

# Charger les données
@st.cache_data
def load_all_data():
    logements = pd.read_sql('SELECT * FROM "Logements"', engine)
    bornes = pd.read_sql('SELECT * FROM "bornes-recharge-publiques-a-jour"', engine)
    stationnements = pd.read_sql('SELECT * FROM "stationnements-h-2023-2024"', engine)
    return logements, bornes, stationnements

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

    # Mise en forme avec deux colonnes
    col1, col2 = st.columns([1, 1])  # Diviser en 2 colonnes égales

    with col1:
        st.markdown(f"""
            <div style="text-align:center; font-size: 18px;">
                <strong>🏠 Prix moyen (CAD)</strong><br> {stats['🏠 Prix moyen (CAD)']}<br><br>
                <strong>📈 Prix médian (CAD)</strong><br> {stats['📈 Prix médian (CAD)']}<br><br>
                <strong>💰 Prix minimum (CAD)</strong><br> {stats['💰 Prix minimum (CAD)']}<br><br>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div style="text-align:center; font-size: 18px;">
                <strong>💵 Prix maximum (CAD)</strong><br> {stats['💵 Prix maximum (CAD)']}<br><br>
                <strong>🔢 Nombre d'annonces</strong><br> {stats['🔢 Nombre d\'annonces']}<br><br>
                <strong>🛏 Chambres moyennes</strong><br> {stats['🛏 Chambres moyennes']}<br><br>
            </div>
        """, unsafe_allow_html=True)

    # Affichage des "Places de parking moyennes"
    st.markdown(f"""
        <div style="text-align:center; font-size: 18px;">
            <strong>🚗 Places de parking moyennes</strong><br> {stats['🚗 Places de parking moyennes']}
        </div>
    """, unsafe_allow_html=True)

# Fonction pour afficher les annonces filtrées
def display_filtered_data(filtered_data):
    st.subheader("📋 Annonces disponibles")
    filtered_data = filtered_data.head(10)  # Limiter à 10 annonces
    col1, col2 = st.columns(2)  # Créer 2 colonnes pour afficher les annonces
    
    for i, (_, annonce) in enumerate(filtered_data.iterrows()):
        col = col1 if i % 2 == 0 else col2
        with col:
            st.markdown(f"""
                <div style="background-color: #f7f7f7; border: 1px solid #ddd; border-radius: 10px; padding: 20px; box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1); min-height: 200px;">
                    <div style="font-size: 18px; color: #333; font-weight: bold; margin-bottom: 10px;">Annonce {i + 1}</div>
                    <div><strong>Prix:</strong> {annonce['price']} CAD</div>
                    <div><strong>Adresse:</strong> {annonce['address']}</div>
                    <div><strong>Chambres:</strong> {annonce['bedrooms']} | <strong>Salles de bain:</strong> {annonce['bathrooms']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Bouton pour voir plus de détails avec un style vert
            if st.button(f"Voir détails - Annonce {i + 1}", key=f"details_{i}", use_container_width=True):
                st.session_state.selected_annonce = annonce.to_dict()
                st.session_state.page = "details"
                st.switch_page("pages/details.py")

# Fonction principale du tableau de bord
def main():
    # Initialiser le session_state
    initialize_session_state()

    # Charger les données
    data, bornes_data, stationnement_data = load_all_data()

    # Titre de la page
    st.title("🏡 Plateforme de Recherche Immobilière")

    # Affichage des statistiques
    display_statistics(data)

    # Filtres dans la barre latérale
    with st.sidebar:
        st.write("Filtres")
        min_price = st.number_input("Min Prix", min_value=0, value=0)
        max_price = st.number_input("Max Prix", min_value=0, value=2000000)
        parking = st.number_input("Parking", min_value=0, value=0)
        bedrooms = st.number_input("Chambres", min_value=0, value=0)

    # Filtrage des données
    filtered_data = data[(data["price"] >= min_price) & 
                         (data["price"] <= max_price) & 
                         (data["parking_spaces"] >= parking) & 
                         (data["bedrooms"] >= bedrooms)]
    
    # Affichage des annonces filtrées
    display_filtered_data(filtered_data)

# Exécution de l'application
if __name__ == "__main__":
    main()