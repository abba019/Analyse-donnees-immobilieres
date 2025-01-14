import streamlit as st
from sqlalchemy import create_engine
import pandas as pd
import pydeck as pdk
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import os
# from streamlit.home import initialize_session_state
from babel.numbers import format_currency

def amt(amount):
    return format_currency(amount, "CAD", "#,##0 ¤", "fr_CA", False)

POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DB_URL)

# Function to display property details
def display_annonce_details(annonce):
    # Generate Visualization (Example: Comparison of living area and land area)
    def generate_price_comparison(fsa, current_price):
        # Query to get the average price of properties in the same FSA
        query = f"""
        SELECT AVG("price") as avg_price
        FROM "Logements"
        WHERE "fsa" = '{fsa}'
        """
        try:
            with engine.connect() as conn:
                avg_price_data = pd.read_sql(query, conn)
                avg_price = avg_price_data["avg_price"].iloc[0] if not avg_price_data.empty else 0
        except Exception as e:
            st.error(f"Erreur lors de la récupération du prix moyen pour l'FSA: {e}")
            avg_price = 0

        # Visualization Data
        plt.rcParams['axes.unicode_minus'] = False
        labels = ["Prix", "Moyenne Prix"]
        values = [current_price, avg_price]

        # Generate the Bar Chart
        fig, ax = plt.subplots(figsize=(3, 2))
        sns.barplot(x=labels, y=values, palette="coolwarm", ax=ax)
        ax.set_title(f"Prix Zone FSA ({fsa})")
        ax.set_ylabel("Prix (CAD)")
        ax.set_xlabel("")
        plt.tight_layout()

        # Save the plot to a BytesIO object
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        plt.close(fig)
        return buffer
    
    # Generate the price comparison visualization
    price_viz_buffer = generate_price_comparison(annonce.get("fsa"), annonce.get("price", 0))
    price_encoded_image = base64.b64encode(price_viz_buffer.read()).decode("utf-8")

    # Display the property details
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>🏠 Détails de l'Annonce</h2>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; gap: 5px;">
            <!-- Upper Section -->
            <div style="display: flex; gap: 20px; align-items: flex-start;">
                <!-- Details Box -->
                <div style="
                    flex: 1.5;background-color: #f9f9f9;border: 1px solid #ddd;border-radius: 10px; 
                    padding: 15px; 
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                    <p style="margin: 5px 0;"><strong>Prix (CAD) :</strong> {amt(annonce.get('price', 'N/A'))}</p>
                    <p style="margin: 5px 0;"><strong>Adresse :</strong> {annonce.get('address', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Chambres :</strong> {int(annonce.get('bedrooms', 'N/A'))} | 
                    <strong>Salles de bain :</strong> {int(annonce.get('bathrooms', 'N/A'))}</p>
                    <p style="margin: 5px 0;"><strong>Salles d'eau :</strong> {annonce.get('powder_rooms', 'N/A')} | 
                    <strong>Niveau dans le bâtiment :</strong> {annonce.get('stories', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Année de construction :</strong> {annonce.get('construction_year', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Style de propriété :</strong> {annonce.get('property_style', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Nombre d'étages :</strong> {annonce.get('floors', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Évaluation municipale (CAD) :</strong> {amt(annonce.get('municipal_valuation', 'N/A'))}</p>
                    <p style="margin: 5px 0;"><strong>Espaces de stationnement :</strong> {annonce.get('parking_spaces', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Superficie habitable (m²) :</strong> {annonce.get('living_area', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Superficie du terrain (m²) :</strong> {annonce.get('land_area', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Code postal :</strong> {annonce.get('postal_code', 'N/A')}</p>
                    <p style="margin: 5px 0;"><a href="{annonce.get('url', '#')}" style="color: #4CAF50; text-decoration: none; font-weight: bold;">Voir l'annonce complète</a></p>
                </div>
                <div>
                    <div style="
                        flex: 0.25;background-color: #ffffff;border: 1px solid #ddd;border-radius: 10px;padding: 5px; 
                        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);text-align: center;">
                        <img src="data:image/png;base64,{price_encoded_image}" alt="Visualisation" style="max-width: 100%; height: auto; border-radius: 8px;">
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True,
    )

# Function to display the map
def display_map(fsa, annonce):
    property_location = pd.DataFrame([{
        "latitude": annonce["latitude"],
        "longitude": annonce["longitude"],
        "type": "Logement",
        "color": [0, 0, 0]  # Black for the property itself
    }])

    queries = {
        "Stationnements": f'SELECT "Latitude", "Longitude" FROM "stationnements-h-2023-2024" WHERE "FSA" = \'{fsa}\'',
        "Bornes de recharge": f'SELECT "Latitude", "Longitude" FROM "bornes-recharge-publiques-a-jour" WHERE "FSA" = \'{fsa}\'',
        "Arrêts de métro": f'SELECT "Latitude", "Longitude" FROM "arrets_metro" WHERE "FSA" = \'{fsa}\'',
        "Lignes de métro": f'SELECT "Latitude", "Longitude" FROM "ligne_metro" WHERE "FSA" = \'{fsa}\''
    }

    color_map = {
        "Stationnements": [255, 0, 0],  # Red
        "Bornes de recharge": [0, 255, 0],  # Green
        "Arrêts de métro": [0, 0, 255],  # Blue
        "Lignes de métro": [255, 255, 0]  # Yellow
    }
    
    counts = {key: 0 for key in queries.keys()}  # Initialize counts

    map_data = property_location.copy()
    for location_type, query in queries.items():
        try:
            with engine.connect() as conn:
                result = pd.read_sql(query, conn)
                if not result.empty:
                    result = result.rename(columns={"Latitude": "latitude", "Longitude": "longitude"})
                    result["type"] = location_type
                    result["color"] = [color_map[location_type]] * len(result)
                    map_data = pd.concat([map_data, result], ignore_index=True)
                    counts[location_type] = len(result)  # Update counts based on the number of rows
        except Exception as e:
            st.error(f"Erreur lors de la récupération des données pour {location_type}: {e}")

    st.subheader("Carte de Localisation")
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position='[longitude, latitude]',
        get_color="color",
        get_radius=50,
        pickable=True
    )

    view_state = pdk.ViewState(
        latitude=property_location["latitude"].iloc[0],
        longitude=property_location["longitude"].iloc[0],
        zoom=14,
        pitch=0
    )

    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v11",
            layers=[scatter_layer],
            initial_view_state=view_state
        )
    )

     # Display legends and counts
    st.markdown("<h6 style='color: #4CAF50;'>Légende et Nombre de Points Trouvés</h6>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; gap: 15px;">
            <span>🟥 <strong>Stationnements</strong>: {counts['Stationnements']}</span>
            <span>🟩 <strong>Bornes de recharge</strong>: {counts['Bornes de recharge']}</span>
            <span>🟦 <strong>Arrêts de métro</strong>: {counts['Arrêts de métro']}</span>
            <span>🟨 <strong>Lignes de métro</strong>: {counts['Lignes de métro']}</span>
            <span>⚫ <strong>Logement</strong>: 1</span>
        </div>
        """,
        unsafe_allow_html=True
    )

def display_supplementary_info(fsa):
    st.markdown("<h4 style='color: #4CAF50;'>📌 Informations complémentaires</h4>", unsafe_allow_html=True)

    related_queries = {
        "Stationnements": f'''
            SELECT "ARRONDISSEMENT", "NBR_PLA", "JURIDICTION", "EMPLACEMENT", "HEURES", "NOTE_FR", "Postal Code"
            FROM "stationnements-h-2023-2024" WHERE "FSA" = '{fsa}' LIMIT 2
        ''',
        "Bornes de Recharge": f'''
            SELECT "NOM_BORNE_RECHARGE", "ADRESSE", "VILLE", "NIVEAU_RECHARGE", "MODE_TARIFICATION", "TYPE_EMPLACEMENT", "Postal Code"
            FROM "bornes-recharge-publiques-a-jour" WHERE "FSA" = '{fsa}' LIMIT 2
        ''',
        "Arrêts de Métro": f'''
            SELECT "stop_name", "Postal Code" FROM "arrets_metro" WHERE "FSA" = '{fsa}' LIMIT 2
        ''',
        "Lignes de Métro": f'''
            SELECT "route_name", "headsign", "Postal Code" FROM "ligne_metro" WHERE "FSA" = '{fsa}' LIMIT 2
        '''
    }

    for title, query in related_queries.items():
        try:
            with engine.connect() as conn:
                data = pd.read_sql(query, conn)
                if not data.empty:
                    st.markdown(f"<h4 style='color: #333;'>{title}</h4>", unsafe_allow_html=True)
                    
                    # Group results based on the relevant key
                    if title == "Stationnements":
                        grouped = data.groupby("ARRONDISSEMENT")
                        for arrondissement, group in grouped:
                            n_places = " et ".join(group["NBR_PLA"].astype(str))
                            emplacements = " et ".join(group["EMPLACEMENT"])
                            heures = " et ".join(group["HEURES"])
                            notes = " et ".join(group["NOTE_FR"])
                            st.markdown(
                                f"""
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; background-color: #f9f9f9;">
                                    🅿️ Dans l'arrondissement {arrondissement}, il y a {n_places} places de stationnement situées à {emplacements}.  
                                    Les heures d'accès sont de {heures}. Note: {notes}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    
                    elif title == "Bornes de Recharge":
                        grouped = data.groupby("NOM_BORNE_RECHARGE")
                        for nom_borne, group in grouped:
                            adresses = " et ".join(group["ADRESSE"])
                            villes = " et ".join(group["VILLE"])
                            niveaux = " et ".join(group["NIVEAU_RECHARGE"].astype(str))
                            tarifications = " et ".join(group["MODE_TARIFICATION"])
                            st.markdown(
                                f"""
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; background-color: #f9f9f9;">
                                    🔋 Une borne de recharge appelée {nom_borne} est située à {adresses} ({villes}).  
                                    C'est une borne de niveau {niveaux}, avec un mode de tarification {tarifications}.
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    
                    elif title == "Arrêts de Métro":
                        grouped = data.groupby("stop_name")
                        for stop_name, group in grouped:
                            postcodes = " et ".join(group["Postal Code"])
                            st.markdown(
                                f"""
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; background-color: #f9f9f9;">
                                    🚉 L'arrêt de métro {stop_name} se trouve à proximité de cette propriété (Codes Postaux: {postcodes}).
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    
                    elif title == "Lignes de Métro":
                        grouped = data.groupby("route_name")
                        for route_name, group in grouped:
                            directions = " et ".join(group["headsign"])
                            postcodes = " et ".join(group["Postal Code"])
                            st.markdown(
                                f"""
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; background-color: #f9f9f9;">
                                    🚇 La ligne de métro {route_name} passe dans cette zone et dessert les directions {directions} (Codes Postaux: {postcodes}).
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

        except Exception as e:
            st.error(f"Erreur lors de la récupération des données pour {title}: {e}")

# Main logic
if "selected_annonce" in st.session_state:
    annonce = st.session_state["selected_annonce"]
    fsa = annonce["fsa"]

    display_annonce_details(annonce)
    display_map(fsa, annonce)
    display_supplementary_info(fsa)

    # Button to return to home page
    if st.button("Retour aux annonces"):
       st.session_state.page = "home"
       st.session_state.pop("selected_annonce", None)
       st.switch_page("home.py")
else:
    if st.session_state.page == "home":
       st.session_state.page = "home"
       st.session_state.pop("selected_annonce", None)
    st.warning("Aucune annonce sélectionnée.")
    st.stop()