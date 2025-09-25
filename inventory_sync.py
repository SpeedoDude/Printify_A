# inventory_sync.py (Upgraded with Provider Failover Logic)

import time
from printify_client import get_request, put_request, SHOP_ID

def attempt_provider_failover(product, all_store_variants):
    """
    Attempts to find a new print provider for the given product.
    Returns new provider ID and new variants list if successful, else None.
    """
    blueprint_id = product['blueprint_id']
    current_provider_id = product['print_provider_id']
    print(f"   - FAILOVER: Attempting to find alternative provider for blueprint {blueprint_id}...")

    # 1. Get list of all potential providers for this blueprint
    blueprint_data = get_request(f"/catalog/blueprints/{blueprint_id}.json")
    if not blueprint_data:
        print("   - FAILOVER ERROR: Could not fetch blueprint data.")
        return None, None

    potential_providers = blueprint_data['print_providers']
    for provider in potential_providers:
        new_provider_id = provider['id']
        if new_provider_id == current_provider_id:
            continue # Skip current provider

        print(f"   - Evaluating alternative provider: {provider['title']} (ID: {new_provider_id})")
        
        # 2. Get all variants from the alternative provider
        new_catalog_variants_data = get_request(f"/catalog/blueprints/{blueprint_id}/print_providers/{new_provider_id}/variants.json")
        if not new_catalog_variants_data or 'variants' not in new_catalog_variants_data:
            print(f"     - Skipping: Provider has no variant data.")
            continue
        
        # Create a quick lookup for new variants based on their options (size, color, etc.)
        new_variants_map = {tuple(sorted(v['options'].items())): v for v in new_catalog_variants_data['variants']}

        # 3. Try to map all existing store variants to the new provider's variants
        new_variants_payload = []
        all_variants_mapped = True
        for store_variant in all_store_variants:
            target_options_tuple = tuple(sorted(store_variant['options'].items()))
            
            if target_options_tuple in new_variants_map:
                matched_variant = new_variants_map[target_options_tuple]
                new_variants_payload.append({
                    "id": matched_variant['id'],
                    "price": store_variant['price'], # Keep existing price from store setting
                    "is_enabled": store_variant['is_enabled'] # Keep existing enabled status
                })
            else:
                # If even one variant doesn't have a match, we can't switch providers cleanly.
                all_variants_mapped = False
                print(f"     - Skipping: Could not find match for variant options {target_options_tuple}")
                break
        
        # 4. If all variants mapped successfully, return new provider info
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
    store_products_data = get_request(f"/shops/{SHOP_ID}/products.json")
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
        live_catalog_variants_data = get_request(f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json")
        
        if not live_catalog_variants_data or 'variants' not in live_catalog_variants_data:
            print(f"   - Warning: Could not fetch current catalog stock data for provider {provider_id}.")
            continue

        available_catalog_variant_ids = {v['id'] for v in live_catalog_variants_data['variants']}

        # --- Rebuild variants payload and detect issues ---
        variants_for_update = []
        requires_update = False
        potential_failover_needed = False
        
        for variant in store_variants:
            variant_id = variant['id']
            is_enabled = variant['is_enabled']
            is_available = variant_id in available_catalog_variant_ids
            
            new_enabled_status = is_enabled # Start with current status

            if is_enabled and not is_available:
                print(f"   - [Stock Issue] Variant '{variant['title']}' is out of stock.")
                potential_failover_needed = True
                new_enabled_status = False # Prepare to disable if failover fails
                requires_update = True # Mark that an update is needed regardless

            elif not is_enabled and is_available:
                print(f"   - [Stock Restored] Variant '{variant['title']}' is back in stock.")
                new_enabled_status = True
                requires_update = True

            variants_for_update.append({
                "id": variant['id'],
                "price": variant['price'],
                "options": variant['options'], # Keep options for re-mapping logic
                "is_enabled": new_enabled_status
            })

        # --- Execution Logic ---
        if potential_failover_needed:
            new_provider_id, new_variants = attempt_provider_failover(product, store_variants)
            if new_provider_id and new_variants:
                # If failover successful, prepare payload for provider switch
                final_payload = {"print_provider_id": new_provider_id, "variants": new_variants}
                print(f"   - Executing provider switch for product {product_id}...")
            else:
                # If failover failed, proceed with disabling OOS variants
                final_payload = {"variants": [{"id": v['id'], "price": v['price'], "is_enabled": v['is_enabled']} for v in variants_for_update]}
                print(f"   - Proceeding to disable out-of-stock variants for product {product_id}.")
        
        elif requires_update:
            # For simple restocks (no failover needed)
            final_payload = {"variants": [{"id": v['id'], "price": v['price'], "is_enabled": v['is_enabled']} for v in variants_for_update]}
            print(f"   - Applying stock re-enables for product {product_id}...")
        
        else:
            print("   - Stock levels are already in sync.")
            continue # Skip to next product

        # Push updates to Printify
        update_endpoint = f"/shops/{SHOP_ID}/products/{product_id}.json"
        response = put_request(update_endpoint, final_payload)
        if response:
            print(f"   - ✅ Success! Product stock levels updated for '{product_title}'.")
        else:
            print(f"   - ❌ Failure. Could not update product {product_id}.")
        
        time.sleep(1) # Rate limit between checking each product

# --- Main execution block ---
if __name__ == "__main__":
    print("🤖 Self-Healing Inventory Agent started.")
    print("This agent will check stock levels and attempt provider failover.")
    sync_product_inventory() # Run once for testing, loop for production
