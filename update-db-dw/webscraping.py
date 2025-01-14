import pandas as pd
import numpy as np
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from unidecode import unidecode
from urllib.parse import quote
import psycopg2
import os

## General functions

def define_summary_changes(listings: list, old_listings: pd.DataFrame) -> pd.DataFrame:
    current_info = pd.concat(listings)
    df = pd.merge(current_info, old_listings, 'outer', 'url', suffixes=('', '_old'))
    
    conditions = [
        df['price'].isna(),
        df['price_old'].isna()
    ]
    choices = ['sold', 'new']
    df['action'] = np.select(conditions, choices, 'price_change')
    
    df = df[df['price_old'] != df['price']][['url', 'price', 'action']]
    
    return df[df['url'].str.contains('duproprio')], df[~df['url'].str.contains('duproprio')]

def coordinates_osm(address):
    """
    Cette fonction prend une adresse, l'encode pour l'URL, envoie une requête à l'API OpenStreetMap
    et récupère les coordonnées géographiques (latitude, longitude), le code postal et le FSA.
    """
    encoded_address = quote(address)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded_address}&format=json&addressdetails=1&limit=1"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; OpenAI-Request;)'})

    if response.status_code == 200:
        data = response.json()
        if data:
            latitude = data[0]["lat"]
            longitude = data[0]["lon"]
            address_details = data[0].get("address", {})
            postal_code = address_details.get("postcode", None)
            fsa = None
            if postal_code and len(postal_code) > 3:
                fsa = postal_code[:3]
            return latitude, longitude, postal_code, fsa
        else:
            print(f"Aucun résultat trouvé pour l'adresse : {address}")
            return None, None, None, None
    else:
        print(f"Erreur lors de la requête pour l'adresse {address}: {response.status_code}")
        return None, None, None, None

def enhance(df):
    geocodes = df['address'].apply(lambda address: pd.Series(coordinates_osm(address)))
    if geocodes.shape[0] == 0:
        df[['latitude', 'longitude', 'postal_code', 'fsa']] = None, None, None, None
    else:
        df[['latitude', 'longitude', 'postal_code', 'fsa']] = geocodes
    return df

## DuProprio functions

def duproprio_summary_raw() -> list:
    raw_listings = []
    nb = float("inf")
    i = 1

    session = requests.Session()

    while len(raw_listings) < nb:
        url = f"https://duproprio.com/fr/rechercher/liste?search=true&cities%5B0%5D=1889&pageNumber={i}"
        soup = BeautifulSoup(session.get(url).text, "html5lib")
        raw_listings.extend(soup.find_all("div", {"class": "search-results-listings-list__container"}))
        nb = int(soup.find("span", {"class": "search-results-listings-header__properties-found__number"}).text.strip())
        i += 1

    return raw_listings

def duproprio_summary_info(raw_html: list) -> pd.DataFrame:
    res = []
    for listing in raw_html:
        try: url = listing.find("a", {"class": "search-results-listings-list__item-bottom-container"}).get("href")
        except: url = None

        try: price = int(re.sub("\\s|\\$", "", listing.find("div", {"class": "search-results-listings-list__item-description__price"}).text))
        except: price = None

        try: address = listing.find("div", {"class": "search-results-listings-list__item-description__address"}).text.strip()
        except: address = None

        res.append([url, price, address])
    return pd.DataFrame(res, columns=['url', 'price', 'address'])

def duproprio_individual_raw(urls: pd.Series) -> list:
    raw_listings = []
    session = requests.Session()
    for url in urls:
        soup = BeautifulSoup(session.get(url).text, "html5lib")
        raw_listings.append([url, soup.find("article", {"class": "listing-tab-content__content"})])
    return raw_listings

def duproprio_individual_info(raw_listing_html: list, listings: pd.DataFrame) -> pd.DataFrame:
    res = []
    for listing in raw_listing_html:
        main_specs = listing[1].find_all("div", {"class": "listing-main-characteristics__label"})
        main_specs = dict(re.sub("\\s+", " ", re.sub("\\n", "", x.text).strip()).split(" ", 1)[::-1] for x in main_specs)

        try: bedrooms = [int(main_specs[key]) for key in ["chambre", "chambres"] if key in main_specs][0]
        except: bedrooms = None

        try: bathrooms = [int(main_specs[key]) for key in ["salle de bain", "salles de bain"] if key in main_specs][0]
        except: bathrooms = None

        try: powder_rooms = [int(main_specs[key]) for key in ["salle d’eau", "salles d’eau"] if key in main_specs][0]
        except: powder_rooms = None

        try: stories = [int(main_specs[key]) for key in ["étage", "étages"] if key in main_specs][0]
        except: stories = None

        try:
            living_area = listing[1].find("div", {"class": "listing-main-characteristics__item listing-main-characteristics__item--living-space-area"})
            living_area = living_area.find("span", {"class": "listing-main-characteristics__number listing-main-characteristics__number--dimensions"}).text.strip()
            living_area = re.sub(r"[^0-9.]", "", living_area)
        except: living_area = None

        try:
            land_area = listing[1].find("div", {"class": "listing-main-characteristics__item listing-main-characteristics__item--lot-dimensions"})
            land_area = land_area.find("span", {"class": "listing-main-characteristics__number listing-main-characteristics__number--dimensions"}).text.strip()
            land_area = re.sub(r"[^0-9.]", "", land_area)
        except: land_area = None

        other_specs = listing[1].find_all("div", {"class": "listing-box__dotted-row"})
        other_specs = dict(re.sub("\\n\\s*\\n*", "|", x.text.strip()).split("|") for x in other_specs)

        try: construction_year = int(other_specs["Année de construction"])
        except: construction_year = None

        try: property_style = other_specs["Style"]
        except: property_style = None

        try: floors = other_specs["Situé à quel étage?"]
        except: floors = None

        try: municipal_valuation = sum([int(other_specs[key]) for key in ["Évaluation municipale", "Évaluation municipale du terrain", "Évaluation municipale du bâtiment"] if key in other_specs])
        except: municipal_valuation = None

        try: parking_spaces = sum([int(other_specs[key]) for key in ["Nombre de stationnements", "Nombre de stationnements intérieur", "Nombre de stationnements extérieur"] if key in other_specs])
        except: parking_spaces = None

        res.append([listing[0], bedrooms, bathrooms, powder_rooms, stories, living_area, land_area,
                    construction_year, property_style, floors, municipal_valuation, parking_spaces])

    res = pd.DataFrame(res, columns=['url', 'bedrooms', 'bathrooms', 'powder_rooms', 'stories', 'living_area', 'land_area',
                                     'construction_year', 'property_style', 'floors', 'municipal_valuation', 'parking_spaces'])
    return pd.merge(listings, res, on='url')

## RoyalLepage functions

def royallepage_summary_raw() -> list:
    raw_listings = []
    nb = float("inf")
    i = 1

    session = requests.Session()

    while len(raw_listings) < nb:
        url = f"https://www.royallepage.ca/fr/searchgeo/homes/qc/rosemontla-petite-patrie/{i}/%7Bi%7D/?search_str=Rosemont%E2%80%93La+Petite-Patrie%2C+Montr%C3%A9al%2C+QC%2C+CAN&csrfmiddlewaretoken=4McZvjFoVDaH7IUZtZBZkqipdIQpaTksLFTO3N9wXP9aq9p9XKVyz3dnN0cxZpem&property_type=&house_type=&features=&listing_type=&lat=45.561401723&lng=-73.590413287&upper_lat=&upper_lng=&lower_lat=&lower_lng=&bypass=&radius=5&zoom=&display_type=gallery-view&travel_time=&travel_time_min=30&travel_time_mode=drive&travel_time_congestion=&da_id=&segment_id=&tier2=False&tier2_proximity=0&address=Rosemont%E2%80%93La+Petite-Patrie&method=homes&address_type=city&city_name=Rosemont%E2%80%93La+Petite-Patrie&prov_code=QC&school_id=&boundary=&min_price=0&max_price=5000000%2B&min_leaseprice=0&max_leaseprice=5000%2B&beds=0&baths=0&transactionType=SALE&archive_timespan=3&keyword=&sortby="
        soup = BeautifulSoup(session.get(url).text, "html5lib")
        raw_listings.extend(soup.find_all("div", {"class": "card card--listing-card js-listing js-property-details"}))
        nb = int(re.sub("\\s", "", unidecode(soup.find("span", {"id": "search-results-result-count"}).text.strip())))
        i += 1

    return raw_listings

def royallepage_summary_info(raw_html: list) -> pd.DataFrame:
    res = []
    for listing in raw_html:
        try: url = listing.find("a").get("href")
        except: url = None

        try: mls = re.search(r"mls(\\d+)", url).group(1)
        except: mls = None

        try: price = int(re.sub("\\s|\\$", "", listing.find("span", {"class": "title--h3 price"}).span.text))
        except: price = None

        try: address = listing.find("img").get("alt")
        except: address = None

        res.append([url, mls, price, address])
    return pd.DataFrame(res, columns=['url', 'mls', 'price', 'address'])

def royallepage_individual_raw(urls: pd.Series) -> list:
    raw_listings = []
    session = requests.Session()
    for url in urls:
        soup = BeautifulSoup(session.get(url).text, "html5lib")
        raw_listings.append([url, soup.find("div", {"class": "property-wrapper feed-3 rlp"})])
    return raw_listings

def royallepage_individual_info(raw_listing_html: list, listings: pd.DataFrame) -> pd.DataFrame:
    res = []
    for listing in raw_listing_html:
        try:
            main_specs = listing[1].find("div", {"class": "expandable-box__hidden js-expandable-box-target"})
            main_specs = [re.sub("\\s?:?\\n\\s*", "|", unidecode(x.text).strip()).split("|") for x in main_specs.find_all("li")]
            main_specs = dict(filter(lambda x: len(x) == 2, main_specs))
        except: continue

        try: bedrooms = int(main_specs['Chambres'])
        except: bedrooms = None

        try: bathrooms = int(main_specs['Salle(s) de bains'])
        except: bathrooms = None

        try: powder_rooms = int(main_specs["Salle(s) d'eau"])
        except: powder_rooms = None

        try: stories = [int(main_specs[key]) for key in ["étage", "étages"] if key in main_specs][0]
        except: stories = None

        try:
            living_area = main_specs['Superficie habitable (approx)']
            living_area = re.sub(r"[^0-9.]", "", living_area)
        except: living_area = None

        try:
            land_area = listing[1].find("div", {"class": "listing-main-characteristics__item listing-main-characteristics__item--lot-dimensions"})
            land_area = land_area.find("span", {"class": "listing-main-characteristics__number listing-main-characteristics__number--dimensions"}).text.strip()
            land_area = re.sub(r"[^0-9.]", "", land_area)
        except: land_area = None

        try: construction_year = int(main_specs['Bati en'])
        except: construction_year = None

        try: property_style = other_specs["Style"]
        except: property_style = None

        try: floors = other_specs["Situé à quel étage?"]
        except: floors = None

        #TODO déterminer si c'est la bonne valeur
        try: municipal_valuation = int(re.sub("\\s|\\$", "", main_specs['Evaluation totale']))
        except: municipal_valuation = None

        try: parking_spaces = int(main_specs["Nbre d'espaces de stationnement"])
        except: parking_spaces = None

        try: municipal_tax = int(re.sub("\\s|\\$", "", main_specs['Taxes municipales']))
        except: municipal_tax = None

        try: school_tax = int(re.sub("\\s|\\$", "", main_specs['Taxe scolaire']))
        except: school_tax = None

        res.append([listing[0], bedrooms, bathrooms, powder_rooms, stories, living_area, land_area,
                    construction_year, property_style, floors, municipal_valuation, parking_spaces])

    res = pd.DataFrame(res, columns=['url', 'bedrooms', 'bathrooms', 'powder_rooms', 'stories', 'living_area', 'land_area',
                                     'construction_year', 'property_style', 'floors', 'municipal_valuation', 'parking_spaces'])
    return pd.merge(listings, res, on='url').drop_duplicates()

## Database functions

def connect_to_postgres():
    conn_db = psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT')
    )
    
    conn_dw = psycopg2.connect(
        dbname=os.getenv('POSTGRES_DW'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT')
    )
    
    return [conn_db, conn_dw]

def db_current_info(conn):
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM "Logements"')
    rows = cursor.fetchall()
    colnames = [desc[0].lower() for desc in cursor.description]
    cursor.close()
    return pd.DataFrame(rows, columns=colnames)

def db_dw_add_new_info(conns, df):
    df.replace('', None, inplace=True)
    df.replace(np.nan, None, inplace=True)
    
    with conns[0].cursor() as cursor:
        for index, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO "Logements" (url, price, address, bedrooms, bathrooms, powder_rooms, stories, living_area, land_area,
                                         construction_year, property_style, floors, municipal_valuation, parking_spaces, latitude, longitude, postal_code, fsa)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                """,
                (row.get('url'), row.get('price'), row.get('address'), row.get('bedrooms'), row.get('bathrooms'), row.get('powder_rooms'), row.get('stories'), row.get('living_area'), row.get('land_area'),
                 row.get('construction_year'), row.get('property_style'), row.get('floors'), row.get('municipal_valuation'), row.get('parking_spaces'), row.get('latitude'), row.get('longitude'), row.get('postal_code'), row.get('fsa'))
            )
    conns[0].commit()
    
    with conns[1].cursor() as cursor:
        for index, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO "dw_dim_logements" (url, price, address, bedrooms, bathrooms, powder_rooms, stories, living_area, land_area,
                                                construction_year, property_style, floors, municipal_valuation, parking_spaces, latitude, longitude, postal_code, fsa)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (row.get('url'), row.get('price'), row.get('address'), row.get('bedrooms'), row.get('bathrooms'), row.get('powder_rooms'), row.get('stories'), row.get('living_area'), row.get('land_area'),
                 row.get('construction_year'), row.get('property_style'), row.get('floors'), row.get('municipal_valuation'), row.get('parking_spaces'), row.get('latitude'), row.get('longitude'), row.get('postal_code'), row.get('fsa'))
            )
    conns[1].commit()
    
def db_update_price(conns, df):
    with conns[0].cursor() as cursor:
        for index, row in df.iterrows():
            cursor.execute("""UPDATE "Logements" SET price = %s WHERE url = %s""", (row.get('price'), row.get('url')))
    conns[0].commit()
    
    with conns[1].cursor() as cursor:
        for index, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO "dw_dim_logements" (url, price, address, bedrooms, bathrooms, powder_rooms, stories, living_area, land_area,
                                                construction_year, property_style, floors, municipal_valuation, parking_spaces, latitude, longitude, postal_code, fsa,
                                                state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (row.get('url'), row.get('price'), row.get('address'), row.get('bedrooms'), row.get('bathrooms'), row.get('powder_rooms'), row.get('stories'), row.get('living_area'), row.get('land_area'),
                 row.get('construction_year'), row.get('property_style'), row.get('floors'), row.get('municipal_valuation'), row.get('parking_spaces'), row.get('latitude'), row.get('longitude'), row.get('postal_code'), row.get('fsa'),
                 'price_change')
            )
    conns[1].commit()
    
def db_remove_sold_info(conns, df):
    with conns[0].cursor() as cursor:
        for index, row in df.iterrows():
            cursor.execute("""DELETE FROM "Logements" WHERE url = %s""", (row.get('url'),))
    conns[0].commit()
    
    with conns[1].cursor() as cursor:
        for index, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO "dw_dim_logements" (url, price, address, bedrooms, bathrooms, powder_rooms, stories, living_area, land_area,
                                                construction_year, property_style, floors, municipal_valuation, parking_spaces, latitude, longitude, postal_code, fsa,
                                                state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (row.get('url'), row.get('price'), row.get('address'), row.get('bedrooms'), row.get('bathrooms'), row.get('powder_rooms'), row.get('stories'), row.get('living_area'), row.get('land_area'),
                 row.get('construction_year'), row.get('property_style'), row.get('floors'), row.get('municipal_valuation'), row.get('parking_spaces'), row.get('latitude'), row.get('longitude'), row.get('postal_code'), row.get('fsa'),
                 'sold')
            )
    conns[1].commit()
    
## Database update
if __name__ == "__main__":
    conns = connect_to_postgres()
    current_info = db_current_info(conns[0])
    
    duproprio_summary_raw = duproprio_summary_raw()
    duproprio_summary_info = duproprio_summary_info(duproprio_summary_raw)

    royallepage_summary_raw = royallepage_summary_raw()
    royallepage_summary_info = royallepage_summary_info(royallepage_summary_raw)

    duproprio_summary_changes, royallepage_summary_changes = define_summary_changes([duproprio_summary_info, royallepage_summary_info], current_info)
    
    # DuProprio
    
    duproprio_individual_raw = duproprio_individual_raw(duproprio_summary_changes[duproprio_summary_changes['action'] == 'new']['url'])
    duproprio_individual_info = duproprio_individual_info(duproprio_individual_raw, duproprio_summary_info)
    duproprio_enhance_info = enhance(duproprio_individual_info)
    db_dw_add_new_info(conns, duproprio_enhance_info)
    
    db_update_price(conns, duproprio_summary_changes[duproprio_summary_changes['action'] == 'price_change'])
    
    db_remove_sold_info(conns, duproprio_summary_changes[duproprio_summary_changes['action'] == 'sold'])
    
    print("DuProprio listings updated")

    # RoyalLepage
    
    royallepage_individual_raw = royallepage_individual_raw(royallepage_summary_changes[royallepage_summary_changes['action'] == 'new']['url'])
    royallepage_individual_info = royallepage_individual_info(royallepage_individual_raw, royallepage_summary_info)
    royallepage_enhance_info = enhance(royallepage_individual_info)
    db_dw_add_new_info(conns, royallepage_enhance_info)
    
    db_update_price(conns, royallepage_summary_changes[royallepage_summary_changes['action'] == 'price_change'])

    db_remove_sold_info(conns, royallepage_summary_changes[royallepage_summary_changes['action'] == 'sold'])
    
    print("RoyalLepage listings updated")
    
    conns[0].close()
    conns[1].close()
