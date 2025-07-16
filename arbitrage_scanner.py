# File: arbitrage_scanner.py
# This is the main script. It scans for new pools and then searches for
# arbitrage opportunities among pools with the same token pair.

import sys
import time
from api_manager import get_newest_pools, search_for_pools, save_opportunity

# --- Scanner Configuration ---
# The minimum price difference to consider an opportunity
PRICE_DIFF_THRESHOLD = 0.5  # As a percentage

def find_arbitrage_opportunities(network):
    """The core logic for the arbitrage scanner."""
    new_pools_data = get_newest_pools(network)
    if not new_pools_data or not new_pools_data.get('data'):
        print("Could not fetch new pools. Exiting.")
        return

    # The API response includes related data (tokens) in a separate list
    included_data = new_pools_data.get('included', [])

    print(f"Scanning {len(new_pools_data['data'])} new pools for arbitrage opportunities...\n")

    for pool in new_pools_data['data']:
        pool_address = pool['attributes']['address']
        
        # --- Extract token info for the new pool ---
        try:
            base_token_ref = pool['relationships']['base_token']['data']
            quote_token_ref = pool['relationships']['quote_token']['data']

            # Find the full token data in the 'included' list
            base_token = next(item for item in included_data if item['id'] == base_token_ref['id'] and item['type'] == base_token_ref['type'])
            quote_token = next(item for item in included_data if item['id'] == quote_token_ref['id'] and item['type'] == quote_token_ref['type'])
            
            base_token_address = base_token['attributes']['address']
            quote_token_address = quote_token['attributes']['address']
            base_token_name = base_token['attributes']['symbol']
            quote_token_name = quote_token['attributes']['symbol']
            
            print(f"---> Analyzing new pool for {base_token_name}/{quote_token_name} ({pool_address[:10]}...)")

        except (KeyError, StopIteration):
            # Skip if the pool data is malformed
            continue

        # --- Search for other pools with the same base token ---
        time.sleep(1) # Add a delay to respect API rate limits
        search_results = search_for_pools(network, base_token_address)
        if not search_results or not search_results.get('data'):
            continue
        
        all_pools_for_pair = []
        
        # Filter search results to find pools with the exact same token pair
        for searched_pool in search_results['data']:
            try:
                sp_base_ref = searched_pool['relationships']['base_token']['data']
                sp_quote_ref = searched_pool['relationships']['quote_token']['data']
                
                # Check if the quote token also matches
                if sp_base_ref['id'] == base_token_ref['id'] and sp_quote_ref['id'] == quote_token_ref['id']:
                    price = float(searched_pool['attributes']['base_token_price_usd'])
                    address = searched_pool['attributes']['address']
                    all_pools_for_pair.append({'address': address, 'price': price})
            except KeyError:
                continue
        
        if len(all_pools_for_pair) < 2:
            # We need at least two pools to compare prices
            continue
            
        # --- Compare prices to find an opportunity ---
        highest_price_pool = max(all_pools_for_pair, key=lambda x: x['price'])
        lowest_price_pool = min(all_pools_for_pair, key=lambda x: x['price'])
        
        high_price = highest_price_pool['price']
        low_price = lowest_price_pool['price']

        if low_price > 0: # Avoid division by zero
            price_diff_percent = ((high_price - low_price) / low_price) * 100
            
            if price_diff_percent >= PRICE_DIFF_THRESHOLD:
                print("\n" + "="*25)
                print("!!! ARBITRAGE OPPORTUNITY FOUND !!!")
                print(f"  Pair: {base_token_name}/{quote_token_name}")
                print(f"  High Price: ${high_price:.6f} (Pool: ...{highest_price_pool['address'][-10:]})")
                print(f"  Low Price:  ${low_price:.6f} (Pool: ...{lowest_price_pool['address'][-10:]})")
                print(f"  Difference: {price_diff_percent:.2f}%")
                print("="*25 + "\n")

                # Log the opportunity to the database
                opportunity = {
                    'network': network,
                    'base_token_name': base_token_name,
                    'quote_token_name': quote_token_name,
                    'base_token_address': base_token_address,
                    'quote_token_address': quote_token_address,
                    'high_price_pool_address': highest_price_pool['address'],
                    'low_price_pool_address': lowest_price_pool['address'],
                    'high_price': high_price,
                    'low_price': low_price,
                    'price_difference_percent': price_diff_percent
                }
                save_opportunity(opportunity)


def main():
    """Main function to handle user input."""
    if len(sys.argv) > 1:
        network = sys.argv[1].lower()
    else:
        network = input("Enter the network to scan (e.g., eth, sol, base): ").lower()

    if not network:
        print("No network provided. Exiting.")
        return
        
    find_arbitrage_opportunities(network)


if __name__ == "__main__":
    main()