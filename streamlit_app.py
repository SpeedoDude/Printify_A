# streamlit_app.py

import streamlit as st
import pandas as pd
import os
import io
import sys

# --- Agent Imports ---
# This assumes your agent scripts are in a subfolder named 'agents'.
# Create this folder and place your agent .py files inside it.
try:
    from agents.bulk_creator import create_products_from_csv
    from agents.bulk_updater import update_products_from_csv
    from agents.catalog_explorer import export_all_blueprints_to_csv, export_blueprint_details_to_csv
    from agents.order_fulfiller import run_order_fulfiller
    from agents.order_reporter import run_order_reporter
    from agents.inventory_sync import sync_product_inventory
except ImportError:
    st.error("Could not import agent scripts. Please ensure your agent files (e.g., 'bulk_creator.py') are inside a subfolder named 'agents'.")
    st.stop()

# --- Helper Functions ---

def save_uploaded_file(uploaded_file, file_path):
    """Saves an uploaded file to a specified path."""
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return False

def run_agent_and_display_output(agent_function, *args, **kwargs):
    """Runs an agent function and displays its print output in real-time."""
    log_container = st.empty()
    log_output = ""
    
    original_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()

    try:
        agent_function(*args, **kwargs)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
    finally:
        log_output = captured_output.getvalue()
        sys.stdout = original_stdout
        
        log_container.code(log_output, language='log')

# ============================
# Main App Layout
# ============================

st.set_page_config(layout="wide", page_title="Printify Agent Dashboard")
st.title("🤖 Printify Agent Control Panel")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Choose an Agent", [
        "Home", 
        "Bulk Creator",
        "Bulk Updater", 
        "Catalog Explorer",
        "Order Fulfiller",
        "Sales Reporter",
        "Inventory Sync"
    ])

# ============================
# Page Implementations
# ============================

if page == "Home":
    st.header("Welcome to Your Automated Store Manager")
    st.markdown("""
    Select an agent from the sidebar to perform tasks. Each agent will display a real-time log of its operations below.
    
    * **Bulk Creator:** Create products from a CSV file.
    * **Bulk Updater:** Update products from a CSV file.
    * **Catalog Explorer:** Download Printify product data.
    * **Order Fulfiller:** Fulfill 'on-hold' orders.
    * **Sales Reporter:** Generate a sales report.
    * **Inventory Sync:** Check stock and find alternative providers.
    """)
    st.info("Ensure your `.env` file with API keys is in the root directory before running agents.")

elif page == "Bulk Creator":
    st.header("📝 Bulk Product Creator")
    uploaded_file = st.file_uploader("Upload creation CSV", type=["csv"], key="creator_upload")
    
    if uploaded_file:
        st.markdown("**CSV Preview:**")
        st.dataframe(pd.read_csv(uploaded_file).head())
        
        generate_seo = st.checkbox("Generate SEO-optimized titles and descriptions? (Requires Gemini API)")
        
        if st.button("Run Bulk Creation"):
            file_path = "products_to_create.csv"
            if save_uploaded_file(uploaded_file, file_path):
                run_agent_and_display_output(create_products_from_csv, file_path, generate_seo=generate_seo)
                st.success("Bulk creation process finished!")
    
    if os.path.exists("failed_creation_jobs.csv"):
        st.warning("Detected failed jobs. Details below:")
        st.dataframe(pd.read_csv("failed_creation_jobs.csv"))

elif page == "Bulk Updater":
    st.header("🔄 Bulk Product Updater")
    uploaded_file = st.file_uploader("Upload update CSV", type=["csv"], key="updater_upload")
    
    if uploaded_file:
        st.markdown("**CSV Preview:**")
        st.dataframe(pd.read_csv(uploaded_file).head())
        
        if st.button("Run Bulk Update"):
            file_path = "products_to_update.csv"
            if save_uploaded_file(uploaded_file, file_path):
                run_agent_and_display_output(update_products_from_csv, file_path)
                st.success("Bulk update process finished!")

    if os.path.exists("failed_jobs_updater.csv"):
        st.warning("Detected failed jobs. Details below:")
        st.dataframe(pd.read_csv("failed_jobs_updater.csv"))

elif page == "Catalog Explorer":
    st.header("🔍 Catalog Explorer")
    if st.button("Export All Blueprints to CSV"):
        run_agent_and_display_output(export_all_blueprints_to_csv)
        st.success("Blueprint export finished!")
        if os.path.exists("printify_blueprints.csv"):
            with open("printify_blueprints.csv", "rb") as f:
                st.download_button("Download Blueprints CSV", f, file_name="printify_blueprints.csv")

    st.markdown("---")
    blueprint_id = st.text_input("Enter a specific Blueprint ID to get its details:")
    if st.button("Export Specific Blueprint Details"):
        if blueprint_id.isdigit():
            run_agent_and_display_output(export_blueprint_details_to_csv, int(blueprint_id))
            st.success("Blueprint detail export finished!")
        else:
            st.error("Please enter a valid numeric ID.")

elif page == "Order Fulfiller":
    st.header("📦 Order Fulfillment Agent")
    st.markdown("Finds 'on-hold' orders and sends them to production.")
    if st.button("Scan and Fulfill Pending Orders"):
        run_agent_and_display_output(run_order_fulfiller)
        st.success("Order fulfillment scan finished!")

elif page == "Sales Reporter":
    st.header("📈 Sales Reporter Agent")
    st.markdown("Generates a sales report from fulfilled orders.")
    if st.button("Generate Sales Report"):
        run_agent_and_display_output(run_order_reporter)
        st.success("Sales report generation finished!")

elif page == "Inventory Sync":
    st.header("⚕️ Inventory Sync Agent")
    st.markdown("Checks for out-of-stock variants and attempts to find alternative providers.")
    if st.button("Run Inventory Sync"):
        run_agent_and_display_output(sync_product_inventory)
        st.success("Inventory sync finished!")
