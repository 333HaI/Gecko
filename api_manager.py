# File: api_manager.py
# This module is responsible for all interactions with the GeckoTerminal API
# and the PostgreSQL database.

import requests
import psycopg2
from datetime import datetime




DB_NAME="financial_analyzer_db"
DB_USER="postgres"
DB_PASSWORD="azizaziz2"
DB_HOST="localhost"
DB_PORT="5432"


# --- GeckoTerminal API Configuration ---
GECKO_API_BASE_URL = "https://api.geckoterminal.com/api/v2"
API_HEADERS = {'Accept': 'application/json'}

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error: Could not connect to database. {e}")
        return None

def get_newest_pools(network, page=1):
    """Fetches the most recently created pools from a given network."""
    print(f"Fetching newest pools on {network}...")
    url = f"{GECKO_API_BASE_URL}/networks/{network}/pools"
    params = {'page': page, 'include': 'base_token,quote_token'}
    try:
        response = requests.get(url, headers=API_HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching new pools: {e}")
        return None

def search_for_pools(network, token_query):
    """Searches for other pools containing a specific token."""
    url = f"{GECKO_API_BASE_URL}/search/pools"
    params = {'query': token_query, 'network': network, 'include': 'base_token,quote_token'}
    try:
        response = requests.get(url, headers=API_HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error searching for pools with query '{token_query}': {e}")
        return None

def save_opportunity(opportunity):
    """Saves a found arbitrage opportunity to the PostgreSQL database."""
    conn = get_db_connection()
    if not conn: return

    insert_query = """
        INSERT INTO arbitrage_opportunities (
            network, base_token_name, quote_token_name, base_token_address,
            quote_token_address, high_price_pool_address, low_price_pool_address,
            high_price, low_price, price_difference_percent
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    with conn.cursor() as cur:
        cur.execute(insert_query, (
            opportunity['network'],
            opportunity['base_token_name'],
            opportunity['quote_token_name'],
            opportunity['base_token_address'],
            opportunity['quote_token_address'],
            opportunity['high_price_pool_address'],
            opportunity['low_price_pool_address'],
            opportunity['high_price'],
            opportunity['low_price'],
            opportunity['price_difference_percent']
        ))
    conn.commit()
    conn.close()