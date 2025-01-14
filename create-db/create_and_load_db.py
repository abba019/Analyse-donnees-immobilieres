import os
import pandas as pd
import psycopg2
from psycopg2 import extensions
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DATA_DIR = '/create-db/dbfiles/'

def create_database_and_tables():
    # Étape 1 : Création de la base de données
    conn = None
    try:
        # Connexion sans spécifier de base de données
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Suppression et création de la base de données
        cur.execute(f'DROP DATABASE IF EXISTS {POSTGRES_DB};')
        cur.execute(f'CREATE DATABASE {POSTGRES_DB};')
        print(f"La base de données '{POSTGRES_DB}' a été créée avec succès.")
        cur.close()
    except Exception as e:
        print("Erreur lors de la création de la base de données :", e)
    finally:
        if conn:
            conn.close()

    # Étape 2 : Création des tables
    try:
        # Connexion à la nouvelle base de données
        engine = create_engine(f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        metadata = MetaData()

        # Définir les tables
        logements = Table('Logements', metadata,
                          Column('url', String, primary_key=True),
                          Column('price', Float),
                          Column('address', String),
                          Column('bedrooms', Integer),
                          Column('bathrooms', Integer),
                          Column('powder_rooms', Integer),
                          Column('stories', Integer),
                          Column('construction_year', Integer),
                          Column('property_style', String),
                          Column('floors', Integer),
                          Column('municipal_valuation', Float),
                          Column('parking_spaces', Integer),
                          Column('living_area', Float), 
                          Column('land_area', Float),
                          Column('latitude', DOUBLE_PRECISION),
                          Column('longitude', DOUBLE_PRECISION),
                          Column('postal_code', String),
                          Column('fsa', String))

        lignes_metro = Table('ligne_metro', metadata,
                             Column('route_id', String),
                             Column('route_name', String),
                             Column('headsign', String),
                             Column('shape_id', String),
                             Column('service_id', String),
                             Column('Latitude', DOUBLE_PRECISION),
                             Column('Longitude', DOUBLE_PRECISION),
                             Column('Postal Code', String),
                             Column('FSA', String))

        arrets_metro = Table('arrets_metro', metadata,
                             Column('stop_id', String),
                             Column('stop_code', Integer),
                             Column('stop_name', String),
                             Column('stop_url', String),
                             Column('wheelchair', Integer),
                             Column('route_id', String),
                             Column('loc_type', Integer),
                             Column('service_id', String),
                             Column('Latitude', DOUBLE_PRECISION),
                             Column('Longitude', DOUBLE_PRECISION),
                             Column('Postal Code', String),
                             Column('FSA', String))

        borne_recharge = Table('bornes-recharge-publiques-a-jour', metadata,
                               Column('NOM_BORNE_RECHARGE', String, primary_key=True),
                               Column('NOM_PARC', String),
                               Column('ADRESSE', String),
                               Column('VILLE', String),
                               Column('NIVEAU_RECHARGE', String),
                               Column('MODE_TARIFICATION', String),
                               Column('TYPE_EMPLACEMENT', String),
                               Column('Longitude', DOUBLE_PRECISION),
                               Column('Latitude', DOUBLE_PRECISION),
                               Column('Postal Code', String),
                               Column('FSA', String))

        stationnement_deneigement = Table('stationnements-h-2023-2024', metadata,
                                          Column('ID_STA', Integer, primary_key=True),
                                          Column('ARRONDISSEMENT', String),
                                          Column('NBR_PLA', Integer),
                                          Column('JURIDICTION', String),
                                          Column('EMPLACEMENT', String),
                                          Column('HEURES', String),
                                          Column('HOURS', String),
                                          Column('NOTE_FR', String),
                                          Column('Latitude', DOUBLE_PRECISION),
                                          Column('Longitude', DOUBLE_PRECISION),
                                          Column('Postal Code', String),
                                          Column('FSA', String))

        # Créer les tables dans la base
        metadata.create_all(engine)
        print(f"Les tables ont été créées avec succès dans la base '{POSTGRES_DB}'.")

        return engine, metadata
    except Exception as e:
        print("Erreur lors de la création des tables :", e)
        return None, None
    finally:
        if engine:
            engine.dispose()
        print("Connexion à la base de données fermée.")

# Fonction pour charger les données dans les tables
def load_data(engine, metadata, data_dir):
    try:
        for filename in os.listdir(data_dir):
            file_wo_ext = os.path.splitext(filename)[0]
            file_path = os.path.join(data_dir, filename)

            # Charger les données du fichier CSV ou XLSX
            if filename.endswith(".csv") and os.path.isfile(file_path):
                df = pd.read_csv(file_path)
            elif filename.endswith(".xlsx") and os.path.isfile(file_path):
                df = pd.read_excel(file_path)
            else:
                continue  # Skip files that ne sont pas au format attendu

            # Suppression des colonnes sans nom
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

            # Vérifier si la table correspondante existe
            if file_wo_ext in metadata.tables:
                df.to_sql(file_wo_ext, engine, if_exists='append', index=False)
                print(f"Les données ont été importées dans la table '{file_wo_ext}'.")
            else:
                print(f"Aucune table correspondante trouvée pour '{file_wo_ext}'.")

    except Exception as e:
        print("Erreur lors de l'importation des données :", e)
    
    finally:
        # Ensure the connection is closed
        if engine:
            engine.dispose()
        print("Connexion à la base de données fermée.")


# Appel des fonctions principales
if __name__ == "__main__":
    engine, metadata = create_database_and_tables()
    if engine and metadata:
        load_data(engine, metadata, DATA_DIR)
        engine.dispose()
