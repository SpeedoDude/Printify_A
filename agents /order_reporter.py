# agents/order_reporter.py

from api_clients import PrintifyApiClient
from collections import defaultdict

def run_order_reporter():
    """Fetches all completed orders and generates a sales report."""
    print("🤖 Order Reporter Agent: Initializing...")
    client = PrintifyApiClient()

    print("   - Fetching all fulfilled orders...")
    orders_data = client.get_orders(status="fulfilled")

    if not orders_data or not orders_data.get('data'):
        print("No fulfilled orders found to report on.")
        return

    orders = orders_data['data']
    total_revenue = sum(o.get('total_price', 0) for o in orders)
    total_cost = sum(o.get('total_cost', 0) for o in orders)
    product_sales = defaultdict(int)

    for order in orders:
        for item in order.get('line_items', []):
            title = item.get('metadata', {}).get('title', 'Unknown')
            product_sales[title] += item.get('quantity', 0)

    print("\n--- 📈 Printify Sales Report ---")
    print(f"Total Orders Analyzed: {len(orders)}")
    print(f"Total Revenue: ${(total_revenue / 100):.2f}")
    print(f"Total Cost:    ${(total_cost / 100):.2f}")
    print(f"Gross Profit:  ${((total_revenue - total_cost) / 100):.2f}")
    print("\n--- 👕 Top Selling Products (Top 10) ---")
    
    sorted_products = sorted(product_sales.items(), key=lambda item: item[1], reverse=True)
    for product, count in sorted_products[:10]:
        print(f"  - {product}: {count} units sold")
    print("---------------------------------")
