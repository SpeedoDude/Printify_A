# agents/bulk_updater.py

import csv
import time
import math
import os
from api_clients import PrintifyApiClient

def log_failed_job(log_file, data_row, error_message):
    """Appends failed job details to a CSV log file."""
    data_row['error'] = error_message
    file_exists = os.path.isfile(log_file)
    try:
        with open(log_file, mode='a', newline='', encoding='utf-8') as csvfile:
            fieldnames = data_row.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data_row)
    except Exception as e:
        print(f"CRITICAL LOGGING ERROR: Could not write to log file {log_file}. Reason: {e}")

def update_products_from_csv(file_path):
    """Reads a CSV file to update product properties in bulk using the API client."""
    print("🤖 Bulk Update Agent: Initializing...")
    client = PrintifyApiClient()
    log_file_name = "failed_jobs_updater.csv"
    success_count, failure_count = 0, 0

    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            print(f"Found {len(rows)} products to process.")

            for index, row in enumerate(rows):
                product_id = row.get('product_id')
                print(f"\n--- Processing {index + 1}/{len(rows)}: Product ID {product_id} ---")
                
                try:
                    if not product_id:
                        raise ValueError("product_id column is missing or empty.")

                    update_payload = {}
                    if 'title' in row:
                        update_payload['title'] = row['title']
                    if 'description' in row:
                        update_payload['description'] = row['description']

                    new_price_str = row.get('price')
                    new_margin_str = row.get('margin')
                    variants_to_update = []

                    if new_price_str or new_margin_str:
                        product_data = client.get_product(product_id)
                        if not product_data:
                            raise ConnectionError("Failed to fetch existing product data.")

                        if new_price_str:
                            new_price_int = int(new_price_str)
                            for variant in product_data['variants']:
                                variants_to_update.append({"id": variant['id'], "price": new_price_int})
                            print(f"   - Staging direct price update: ${new_price_int / 100:.2f}")

                        elif new_margin_str:
                            margin_decimal = float(new_margin_str) / 100.0
                            if not (0 < margin_decimal < 1):
                                raise ValueError(f"Invalid margin '{new_margin_str}%. Must be between 1 and 99.")
                            
                            for variant in product_data['variants']:
                                cost = variant['cost']
                                calculated_price = math.ceil(cost / (1 - margin_decimal))
                                variants_to_update.append({"id": variant['id'], "price": int(calculated_price)})
                            print(f"   - Staging margin-based price update ({new_margin_str}%)")
                        
                        update_payload['variants'] = variants_to_update

                    if update_payload:
                        response = client.update_product(product_id, update_payload)
                        if response:
                            print(f"   ✅ Success! Product {product_id} updated.")
                            success_count += 1
                        else:
                            raise ConnectionError("API call failed. Response was negative.")
                    else:
                        print("   - No changes specified. Skipping.")
                        success_count += 1

                except Exception as e:
                    print(f"   ❌ FAILURE: {e}")
                    log_failed_job(log_file_name, row, str(e))
                    failure_count += 1
                
                time.sleep(1)

    except FileNotFoundError:
        print(f"🚨 Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An unexpected system-level error occurred: {e}")

    print("\n--- Bulk Update Summary ---")
    print(f"Successful operations: {success_count}")
    print(f"Failed operations:     {failure_count}")

