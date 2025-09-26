# agents/bulk_creator.py

import csv
import time
import os
import json

# Use the standardized API clients
from api_clients import PrintifyApiClient, GeminiApiClient

def log_failed_job(log_file, data_row, error_message):
    """Appends failed job details to a CSV log file."""
    data_row['error'] = error_message
    file_exists = os.path.isfile(log_file)
    try:
        with open(log_file, mode='a', newline='', encoding='utf-8') as csvfile:
            # Use the keys from the data_row for dynamic fieldnames
            fieldnames = data_row.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data_row)
    except Exception as e:
        print(f"CRITICAL LOGGING ERROR: Could not write to log file {log_file}. Reason: {e}")

def create_products_from_csv(file_path, generate_seo=False):
    """
    Reads product data from a CSV, optionally generates SEO content, and creates products.
    
    Args:
        file_path (str): The path to the input CSV file.
        generate_seo (bool): If True, generates SEO titles and descriptions using Gemini.
    """
    print("🤖 Bulk Creator Agent: Initializing...")
    
    # --- Initialize API Clients ---
    printify_client = PrintifyApiClient()
    gemini_client = GeminiApiClient() if generate_seo else None

    if generate_seo:
        print("   - SEO generation is ENABLED.")

    log_file_name = "failed_creation_jobs.csv"
    success_count = 0
    failure_count = 0

    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            if not rows:
                print("CSV file is empty or invalid.")
                return
            print(f"Found {len(rows)} products to process.")

            for index, row in enumerate(rows):
                # Make a mutable copy of the row for logging purposes
                log_row = row.copy()
                
                base_title = log_row.get('base_title', 'No Title')
                description = log_row.get('description', 'No Description')
                
                print(f"\n--- Processing {index + 1}/{len(rows)}: '{base_title}' ---")

                try:
                    # --- 1. SEO Content Generation (Optional) ---
                    final_title = base_title # Default to base_title
                    if generate_seo and gemini_client:
                        theme = log_row.get('seo_theme', '')
                        if not theme:
                            raise ValueError("CSV must contain an 'seo_theme' column when SEO is enabled.")
                        
                        print(f"   - Generating SEO content with theme: '{theme}'...")
                        prompt = (
                            f"Generate an SEO-optimized product title and description for a product named '{base_title}' with the theme '{theme}'. "
                            "Return the result as a JSON object with two keys: 'title' and 'description'."
                        )
                        
                        response_text = gemini_client.generate_content(prompt)
                        if response_text:
                            seo_data = json.loads(response_text)
                            final_title = seo_data.get('title', base_title)
                            description = seo_data.get('description', description)
                            print(f"   - SEO Title: '{final_title}'")
                        else:
                            print("   - WARNING: SEO generation failed. Using default title and description.")
                    
                    # --- 2. Parse Variants and Prices ---
                    variants_str = log_row['variants_and_prices']
                    variants_payload = []
                    variant_ids_for_print_area = []
                    
                    for item in variants_str.split(','):
                        variant_id_str, price_str = item.split(':')
                        variants_payload.append({
                            "id": int(variant_id_str),
                            "price": int(price_str),
                            "is_enabled": True
                        })
                        variant_ids_for_print_area.append(int(variant_id_str))

                    # --- 3. Construct the Full API Payload ---
                    product_payload = {
                        "title": final_title,
                        "description": description,
                        "blueprint_id": int(log_row['blueprint_id']),
                        "print_provider_id": int(log_row['print_provider_id']),
                        "variants": variants_payload,
                        "print_areas": [{
                            "variant_ids": variant_ids_for_print_area,
                            "placeholders": [{
                                "position": "front",
                                "images": [{"id": log_row['image_id'], "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}]
                            }]
                        }]
                    }
                    
                    # --- 4. Send the Request to Printify ---
                    print("   - Sending data to Printify...")
                    response = printify_client.create_product(product_payload)
                    
                    if response and 'id' in response:
                        print(f"   ✅ Success! Product '{response['title']}' created with ID: {response['id']}")
                        success_count += 1
                    else:
                        raise Exception(f"API call failed or returned an invalid response. Response: {response}")

                except Exception as e:
                    error_message = str(e)
                    print(f"   ❌ FAILURE: {error_message}")
                    log_failed_job(log_file_name, log_row, error_message)
                    failure_count += 1
                
                time.sleep(1) # Rate limit between product creations

    except FileNotFoundError:
        print(f"🚨 Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An unexpected system-level error occurred: {e}")

    print("\n--- Bulk Creation Summary ---")
    print(f"Successful creations: {success_count}")
    print(f"Failed creations:     {failure_count}")
    if failure_count > 0:
        print(f"Details for failed jobs logged to '{log_file_name}'.")

