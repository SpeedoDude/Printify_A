# agents/catalog_explorer.py

import csv
import time
from api_clients import PrintifyApiClient

def export_all_blueprints_to_csv():
    """Fetches all available blueprints and saves them to a CSV file."""
    print("\nFetching all blueprints from the Printify catalog...")
    client = PrintifyApiClient()
    # Assumes your PrintifyApiClient has a method like `get_blueprints()`
    blueprints = client.get_blueprints() 
    
    if not blueprints:
        print("❌ Could not retrieve catalog blueprints.")
        return

    file_name = "printify_blueprints.csv"
    with open(file_name, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['id', 'title'])
        writer.writeheader()
        for blueprint in blueprints:
            writer.writerow({'id': blueprint['id'], 'title': blueprint['title']})
            
    print(f"✅ Success! Exported {len(blueprints)} blueprints to '{file_name}'.")

def export_blueprint_details_to_csv(blueprint_id):
    """Fetches all details for a specific blueprint and saves them to a CSV file."""
    print(f"\nFetching details for Blueprint ID: {blueprint_id}...")
    client = PrintifyApiClient()
    
    # Assumes your client has methods like these
    details = client.get_blueprint_details(blueprint_id)
    if not details:
        print(f"❌ Could not find details for Blueprint ID: {blueprint_id}.")
        return

    blueprint_title = details['title']
    file_name = f"blueprint_{blueprint_id}_{blueprint_title.replace(' ', '_')}.csv"
    print(f"   - Exporting data to '{file_name}'...")

    with open(file_name, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['blueprint_id', 'blueprint_title', 'provider_id', 'provider_title', 'variant_id', 'variant_title', 'size', 'color']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
      
        total_variants = 0
        for provider in details['print_providers']:
            provider_id = provider['id']
            provider_title = provider['title']
            print(f"   - Fetching variants from provider: '{provider_title}'")
            
            variant_data = client.get_blueprint_variants(blueprint_id, provider_id)
            if variant_data and 'variants' in variant_data:
                for variant in variant_data['variants']:
                    writer.writerow({
                        'blueprint_id': blueprint_id,
                        'blueprint_title': blueprint_title,
                        'provider_id': provider_id,
                        'provider_title': provider_title,
                        'variant_id': variant['id'],
                        'variant_title': variant['title'],
                        'size': variant['options'].get('size', 'N/A'),
                        'color': variant['options'].get('color', 'N/A')
                    })
                    total_variants += 1
            time.sleep(0.5)

    print(f"✅ Success! Exported {total_variants} total variants to '{file_name}'.")
