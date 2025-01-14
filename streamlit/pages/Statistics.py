import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium.plugins import MarkerCluster
from geopy.distance import geodesic
from streamlit_folium import folium_static
from sqlalchemy import create_engine

# Configuration de la base de données
db_url = "postgresql://postgres:postgres.123@postgres:5432/db_immo"
engine = create_engine(db_url)

# Charger les données
@st.cache_data
def load_data():
    logements = pd.read_sql('SELECT * FROM "Logements"', engine)
    bornes_recharge = pd.read_sql('SELECT * FROM "bornes-recharge-publiques-a-jour"', engine)
    stationnements = pd.read_sql('SELECT * FROM "stationnements-h-2023-2024"', engine)
    return logements, bornes_recharge, stationnements

# Fonction pour afficher les visualisations des données
def display_visualizations(data):
    st.subheader("📊 Visualisations des Données")
    
    # Prix moyen au m²
    st.subheader("💵 Prix Moyen au m²")
    data['Prix_m2'] = data['price'] / data['living_area']
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(data['Prix_m2'], bins=30, kde=True, color='green', ax=ax)
    ax.set_title("Distribution des Prix Moyens au m²")
    st.pyplot(fig)
    st.write("Ce graphique montre la répartition des prix moyens au m². Il utilise le prix total en dollars canadiens et la surface habitable (en m²). Cela permet d'identifier les logements les plus coûteux au m².")

    # Appréciation des valeurs immobilières par quartier
    st.subheader("📈 Appréciation des Valeurs Immobilières par Quartier")
    price_by_quarter = data.groupby('postal_code')['price'].mean().reset_index()
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(x="postal_code", y="price", data=price_by_quarter, palette="viridis", ax=ax)
    ax.set_title("Appréciation des Valeurs Immobilières par Quartier")
    ax.set_xlabel("Code Postal")
    ax.set_ylabel("Prix Moyen (CAD)")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
    st.pyplot(fig)
    st.write("Ce graphique représente l'appréciation des valeurs immobilières par quartier. Il montre le prix moyen des logements en fonction du code postal, ce qui permet d'identifier les quartiers les plus coûteux ou abordables.")

    # Répartition des annonces par zone géographique (FSA)
    st.subheader("🗺 Répartition des Annonces par Zone Géographique")
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.countplot(x="fsa", data=data, palette="Set2", ax=ax)
    ax.set_title("Répartition des Annonces par FSA")
    ax.set_xlabel("FSA (Forward Sortation Area)")
    ax.set_ylabel("Nombre de Logements")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
    st.pyplot(fig)
    st.write("Ce diagramme montre la répartition des annonces immobilières selon la zone géographique (FSA). Il permet d'identifier les zones avec la plus grande concentration d'annonces.")

    # Indices de l'accessibilité à la nature et aux espaces verts
    st.subheader("🌳 Accessibilité aux Espaces Verts")
    data['Accessibilité_Nature'] = data['living_area'] / data['land_area'] * 100  # Exemple fictif
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(data['Accessibilité_Nature'], bins=30, kde=True, color='lightblue', ax=ax)
    ax.set_title("Indice d'Accessibilité à la Nature et aux Espaces Verts")
    st.pyplot(fig)
    st.write("Ce graphique montre un indice d'accessibilité à la nature, calculé en fonction de la proportion de surface habitable par rapport à la surface du terrain. Une plus grande proportion suggère une meilleure utilisation de l'espace terrain pour des logements spacieux.")

    # Indice de la demande immobilière par zone géographique
    st.subheader("📍 Demande Immobilière par Zone Géographique")
    demand_by_zone = data['postal_code'].value_counts().reset_index()
    demand_by_zone.columns = ['postal_code', 'Nombre de Logements']
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x="postal_code", y="Nombre de Logements", data=demand_by_zone, palette="rocket", ax=ax)
    ax.set_title("Demande Immobilière par Zone Géographique")
    ax.set_xlabel("Code Postal")
    ax.set_ylabel("Nombre de Logements")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
    st.pyplot(fig)
    st.write("Ce graphique montre la demande immobilière par zone géographique. Il représente le nombre de logements par code postal, permettant de visualiser les zones avec une forte demande de logements.")

# Fonction principale pour la page de visualisation
def main():
    # Charger les données
    data, bornes_recharge, stationnements = load_data()

    # Afficher les visualisations
    display_visualizations(data)

    # Afficher la carte avec services à proximité
    display_map_with_services(data, bornes_recharge, stationnements)

# Fonction pour calculer la distance entre deux points
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).km

# Fonction pour trouver les services à proximité
def find_nearby_services(logement_lat, logement_lon, distance_km, bornes_recharge, stationnements):
    nearby_services = []

    # Chercher les bornes de recharge à proximité
    for _, row in bornes_recharge.iterrows():
        service_distance = calculate_distance(logement_lat, logement_lon, row["Latitude"], row["Longitude"])
        if service_distance <= distance_km:
            nearby_services.append({"type": "Borne de recharge", "lat": row["Latitude"], "lon": row["Longitude"], "distance": service_distance})

    # Chercher les stationnements à proximité
    for _, row in stationnements.iterrows():
        service_distance = calculate_distance(logement_lat, logement_lon, row["Latitude"], row["Longitude"])
        if service_distance <= distance_km:
            nearby_services.append({"type": "Stationnement", "lat": row["Latitude"], "lon": row["Longitude"], "distance": service_distance})

    return nearby_services

# Fonction pour afficher la carte avec les services
def display_map_with_services(data, bornes_recharge, stationnements):
    st.subheader("🗺 Carte des Annonces Immobilières et Services à Proximité")
    logement_options = data[['address', 'latitude', 'longitude']].dropna().reset_index(drop=True)

    # Liste déroulante pour choisir un logement
    selected_logement = st.selectbox("Choisissez un logement:", logement_options['address'])
    
    # Récupérer les coordonnées du logement sélectionné
    logement_coord = logement_options[logement_options['address'] == selected_logement].iloc[0]
    logement_lat = logement_coord['latitude']
    logement_lon = logement_coord['longitude']

    # Sélectionner la distance à parcourir pour trouver des services
    distance_km = st.slider("Choisir la distance (en km) pour trouver des services:", min_value=1, max_value=50, value=5)

    # Carte de l'annonce sélectionnée
    m = folium.Map(location=[logement_lat, logement_lon], zoom_start=14)
    folium.Marker([logement_lat, logement_lon], popup=f"Logement : {selected_logement}", icon=folium.Icon(color="blue")).add_to(m)

    # Trouver les services à proximité
    nearby_services = find_nearby_services(logement_lat, logement_lon, distance_km, bornes_recharge, stationnements)

    # Ajouter les services sur la carte avec des couleurs différentes
    for service in nearby_services:
        if service["type"] == "Borne de recharge":
            color = "green"
        elif service["type"] == "Stationnement":
            color = "red"

        # Ajouter un marqueur pour chaque service
        folium.Marker(
            [service["lat"], service["lon"]],
            popup=f"{service['type']} - Distance: {service['distance']:.2f} km",
            icon=folium.Icon(color=color)
        ).add_to(m)

    # Afficher la carte
    folium_static(m)

# Exécution de l'application
if __name__ == "__main__":
    main()