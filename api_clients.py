# api_clients.py

import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PrintifyApiClient:
    """A client to handle all communications with the Printify API."""
    def __init__(self):
        self.api_key = os.getenv("PRINTIFY_API_TOKEN")
        self.shop_id = os.getenv("PRINTIFY_SHOP_ID")
        self.base_url = "https://api.printify.com/v1"
        if not all([self.api_key, self.shop_id]):
            raise ValueError("Error: PRINTIFY_API_TOKEN and PRINTIFY_SHOP_ID must be set in .env file.")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method, endpoint, payload=None):
        """Generic request handler."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error for {method} {endpoint}: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {method} {endpoint}: {e}")
        return None

    def get_product(self, product_id):
        """Fetches a single product by its ID."""
        return self._request("GET", f"/shops/{self.shop_id}/products/{product_id}.json")

    def get_all_products(self):
        """Fetches all products from the shop."""
        return self._request("GET", f"/shops/{self.shop_id}/products.json")
    
    def update_product(self, product_id, payload):
        """Updates a product with a given payload."""
        return self._request("PUT", f"/shops/{self.shop_id}/products/{product_id}.json", payload=payload)

    def create_product(self, payload):
        """Creates a new product."""
        return self._request("POST", f"/shops/{self.shop_id}/products.json", payload=payload)

    def get_orders(self, status="any"):
        """Fetches orders from the shop, filtering by status."""
        return self._request("GET", f"/shops/{self.shop_id}/orders.json?status={status}")

    def send_to_production(self, order_id):
        """Sends an external order to production."""
        endpoint = f"/shops/{self.shop_id}/orders/{order_id}/send_to_production.json"
        return self._request("POST", endpoint, payload={})


class GeminiApiClient:
    """A client to handle communications with the Google Gemini API."""
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Error: GEMINI_API_KEY must be set in .env file.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_content(self, prompt):
        """Generates content based on a given prompt."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Gemini content generation failed: {e}")
            return None

