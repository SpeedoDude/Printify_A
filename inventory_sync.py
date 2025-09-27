# agents/inventory_sync.py

import time
from api_clients import PrintifyApiClient

def attempt_provider_failover(client, product, all_store_variants):
    """
    Attempts to find a new print provider for the given product.
    Returns new provider ID and new variants list if successful, else None.
    """
    blueprint_id = product['blueprint_id']
    current_provider_id = product['print_provider_id']
    print(f"   - FAILOVER: Attempting to find alternative provider for blueprint {blueprint_id}...")

    blueprint_data = client.get_blueprint_details(blueprint_id)
    if not blueprint_data:
        print("   - FAILOVER ERROR: Could not fetch blueprint data.")
        return None, None

    potential_providers = blueprint_data['print_providers']
    for provider in potential_providers:
        new_provider_id = provider['id']
        if new_provider_id == current_provider_id:
            continue

        print(f"   - Evaluating alternative provider: {provider['title']} (ID: {new_provider_id})")
        
        new_catalog_variants_data = client.get_blueprint_variants(blueprint_id, new_provider_id)
        if not new_catalog_variants_data or 'variants' not in new_catalog_variants_data:
            print(f"     - Skipping: Provider has no variant data.")
            continue
        
        new_variants_map = {tuple(sorted(v['options'].items())): v for v in new_catalog_variants_data['variants']}

        new_variants_payload = []
        all_variants_mapped = True
        for store_variant in all_store_variants:
            target_options_tuple = tuple(sorted(store_variant['options'].items()))
            
            if target_options_tuple in new_variants_map:
                matched_variant = new_variants_map[target_options_tuple]
                new_variants_payload.append({
                    "id": matched_variant['id'],
                    "price": store_variant['price'],
                    "is_enabled": store_variant['is_enabled']
                })
            else:
                all_variants_mapped = False
                print(f"     - Skipping: Could not find match for variant options {target_options_tuple}")
                break
        
        if all_variants_mapped:
            print(f"   - FAILOVER SUCCESS: Found compatible provider: {provider['title']}")
            return new_provider_id, new_variants_payload

    print("   - FAILOVER FAILED: No suitable alternative providers found.")
    return None, None


def sync_product_inventory():
    """
    Compares store products against live catalog availability.
    Attempts provider failover before disabling variants.
    """
    print(f"[{time.ctime()}] Starting inventory synchronization task...")
    client = PrintifyApiClient()
    store_products_data = client.get_all_products()
    
    if not store_products_data or 'data' not in store_products_data:
        print("Could not retrieve store products.")
        return

    store_products = store_products_data['data']
    print(f"Found {len(store_products)} products to check.")

    for product in store_products:
        product_id = product['id']
        product_title = product['title']
        blueprint_id = product['blueprint_id']
        provider_id = product['print_provider_id']
        store_variants = product['variants']
        
        print(f"\nChecking stock for: '{product_title}' (ID: {product_id})")
        live_catalog_variants_data = client.get_blueprint_variants(blueprint_id, provider_id)
        
        if not live_catalog_variants_data or 'variants' not in live_catalog_variants_data:
            print(f"   - Warning: Could not fetch current catalog stock data for provider {provider_id}.")
            continue

        available_catalog_variant_ids = {v['id'] for v in live_catalog_variants_data['variants']}
        
        variants_for_update = []
        requires_update = False
        potential_failover_needed = False
        
        for variant in store_variants:
            new_enabled_status = variant['is_enabled']
            if variant['is_enabled'] and variant['id'] not in available_catalog_variant_ids:
                print(f"   - [Stock Issue] Variant '{variant['title']}' is out of stock.")
                potential_failover_needed = True
                new_enabled_status = False
                requires_update = True
            elif not variant['is_enabled'] and variant['id'] in available_catalog_variant_ids:
                print(f"   - [Stock Restored] Variant '{variant['title']}' is back in stock.")
                new_enabled_status = True
                requires_update = True

            variants_for_update.append({
                "id": variant['id'],
                "price": variant['price'],
                "is_enabled": new_enabled_status
            })

        if not requires_update:
            print("   - Stock levels are already in sync.")
            continue

        final_payload = {}
        if potential_failover_needed:
            new_provider_id, new_variants = attempt_provider_failover(client, product, store_variants)
            if new_provider_id and new_variants:
                final_payload = {"print_provider_id": new_provider_id, "variants": new_variants}
                print(f"   - Executing provider switch for product {product_id}...")
            else:
                final_payload = {"variants": variants_for_update}
                print(f"   - Proceeding to disable out-of-stock variants for product {product_id}.")
        else:
            final_payload = {"variants": variants_for_update}
            print(f"   - Applying stock re-enables for product {product_id}...")
        
        response = client.update_product(product_id, final_payload)
        if response:
            print(f"   - ✅ Success! Product stock levels updated for '{product_title}'.")
        else:
            print(f"   - ❌ Failure. Could not update product {product_id}.")
        
        time.sleep(1)
