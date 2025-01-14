from datetime import datetime
import psycopg2
import os

POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_DW = os.getenv('POSTGRES_DW')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

def connect_to_db():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

def connect_to_dw(before_creation=False):
    if before_creation:
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
    else:
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )

def create_dw_database():
    """Create the Data Warehouse database if it doesn't exist."""
    conn = connect_to_dw(True)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (POSTGRES_DW,))
    if not cur.fetchone():
        cur.execute(f"CREATE DATABASE {POSTGRES_DW};")
        print(f"Database {POSTGRES_DW} created successfully.")
    else:
        print(f"Database {POSTGRES_DW} already exists.")

    cur.close()
    conn.close()

def create_dw_tables():
    """Create the dimension and fact tables in the Data Warehouse."""
    conn = connect_to_dw()
    cur = conn.cursor()

    # Create dimension tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dw_dim_logements (
            dw_id SERIAL PRIMARY KEY, -- Auto-incrementing primary key
            url VARCHAR(255), 
            price NUMERIC, 
            address VARCHAR(255), 
            bedrooms INT, 
            bathrooms INT, 
            powder_rooms INT, 
            stories INT, 
            construction_year INT, 
            property_style VARCHAR(255),
            floors INT, 
            municipal_valuation NUMERIC, 
            parking_spaces INT, 
            living_area VARCHAR(255), 
            land_area VARCHAR(255),
            latitude DOUBLE PRECISION, 
            longitude DOUBLE PRECISION, 
            postal_code VARCHAR(255), 
            fsa VARCHAR(255), 
            update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            state VARCHAR(255) DEFAULT 'new');""")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dw_dim_lignes_metro (
            dw_ligne_id SERIAL PRIMARY KEY, -- Auto-incrementing primary key
            route_id VARCHAR(255),
            route_name VARCHAR(255),
            headsign VARCHAR(255),
            shape_id VARCHAR(255),
            service_id VARCHAR(255),
            latitude VARCHAR(255),
            longitude VARCHAR(255),
            "Postal Code" VARCHAR(255),
            fsa VARCHAR(255),
            update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dw_dim_arrets_metro (
            dw_arrets_id SERIAL PRIMARY KEY, -- Auto-incrementing primary key
            stop_id VARCHAR(255),
            stop_code VARCHAR(255),
            stop_name VARCHAR(255),
            stop_url VARCHAR(255),
            wheelchair VARCHAR(255),
            route_id VARCHAR(255),
            loc_type VARCHAR(255),
            service_id VARCHAR(255),
            latitude VARCHAR(255),
            longitude VARCHAR(255),
            "Postal Code" VARCHAR(255),
            fsa VARCHAR(255),
            update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP );""")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dw_dim_bornes_recharge (
            nom_borne_recharge TEXT PRIMARY KEY, 
            nom_parc TEXT, 
            adresse TEXT, 
            ville TEXT, 
            niveau_recharge TEXT, 
            mode_tarification TEXT,
            type_emplacement TEXT, 
            longitude DOUBLE PRECISION, 
            latitude DOUBLE PRECISION, 
            "Postal Code" TEXT, 
            fsa TEXT);""")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dw_dim_stationnements_deneigement (
            id_sta SERIAL PRIMARY KEY, 
            arrondissement TEXT, 
            nbr_pla INT, 
            juridiction TEXT, 
            emplacement TEXT, 
            heures TEXT,
            hours TEXT, 
            note_fr TEXT, 
            latitude DOUBLE PRECISION, 
            longitude DOUBLE PRECISION, 
            "Postal Code" TEXT, 
            fsa TEXT, 
            update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""")

    # Create fact table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dw_fact_logements (
            fact_id SERIAL PRIMARY KEY, 
            logement_id INT REFERENCES dw_dim_logements(dw_id), 
            metro_ligne_id INT REFERENCES dw_dim_lignes_metro(dw_ligne_id), 
            metro_arret_id INT REFERENCES dw_dim_arrets_metro(dw_arrets_id), 
            borne_id TEXT REFERENCES dw_dim_bornes_recharge(nom_borne_recharge), 
            stationnement_id INT REFERENCES dw_dim_stationnements_deneigement(id_sta), 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Les tables de fait et dimensions crée avec succès.")

def fetch_table_data(table_name):
    """Fetch all rows from a table in db_immo."""
    conn = connect_to_db()
    cur = conn.cursor()

    cur.execute(f"SELECT * FROM \"{table_name}\";")
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows

def insert_data_into_dw(table_name, dw_table_name, rows):
    """Insert rows into a Data Warehouse dimension table."""
    conn = connect_to_dw()
    cur = conn.cursor()

    for row in rows:
        placeholders = ', '.join(['%s'] * len(row))
        if dw_table_name in ["dw_dim_bornes_recharge", "dw_dim_stationnements_deneigement"]:
            cur.execute(f"INSERT INTO {dw_table_name} VALUES ({placeholders})", row)
        else:
            cur.execute(f"INSERT INTO {dw_table_name} VALUES (DEFAULT, {placeholders})", row)

    conn.commit()
    cur.close()
    conn.close()

def load_fact_logements():
    """Load data into the fact table dw_fact_logements."""
    conn = connect_to_dw()
    cur = conn.cursor()

    # Prepare fact table data by joining dimension tables
    cur.execute("""
        INSERT INTO dw_fact_logements (logement_id, metro_ligne_id, metro_arret_id, borne_id, stationnement_id)
        SELECT 
            l.dw_id AS logement_id,
            lm.dw_ligne_id AS metro_ligne_id,
            am.dw_arrets_id AS metro_arret_id,
            br.nom_borne_recharge AS borne_id,
            sd.id_sta AS stationnement_id
        FROM 
            dw_dim_logements l
        LEFT JOIN dw_dim_lignes_metro lm 
            ON l.postal_code = lm."Postal Code"  -- Relate based on postal code
        LEFT JOIN dw_dim_arrets_metro am 
            ON l.latitude = am.latitude::DOUBLE PRECISION AND l.longitude = am.longitude::DOUBLE PRECISION -- Explicit type cast
        LEFT JOIN dw_dim_bornes_recharge br 
            ON l.postal_code = br."Postal Code"  -- Relate based on postal code
        LEFT JOIN dw_dim_stationnements_deneigement sd 
            ON l.postal_code = sd."Postal Code";  -- Relate based on postal code
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("Les données ont été chargées dans la table de faits 'dw_fact_logements'.")

def load_data():
    """Load data into the Data Warehouse."""
    
    logements = fetch_table_data("Logements")
    insert_data_into_dw("Logements", "dw_dim_logements", logements)
    
    lignes_metro = fetch_table_data("ligne_metro")
    insert_data_into_dw("ligne_metro", "dw_dim_lignes_metro", lignes_metro)
    
    arrets_metro = fetch_table_data("arrets_metro")
    insert_data_into_dw("arrets_metro", "dw_dim_arrets_metro", arrets_metro)
    
    bornes_recharge = fetch_table_data("bornes-recharge-publiques-a-jour")
    insert_data_into_dw("bornes-recharge-publiques-a-jour", "dw_dim_bornes_recharge", bornes_recharge)
    
    stationnements = fetch_table_data("stationnements-h-2023-2024")
    insert_data_into_dw("stationnements-h-2023-2024", "dw_dim_stationnements_deneigement", stationnements)
    
    load_fact_logements()
    print("Les données ont été bien enregistrées dans les tables de faits et dimensions.")

if __name__ == "__main__":
    create_dw_database()
    create_dw_tables()
    load_data()
