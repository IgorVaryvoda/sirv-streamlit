import os
import requests
import json
import time
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App title and description
st.set_page_config(
    page_title="Sirv Spin Conversion Tools",
    page_icon="🔄",
    layout="wide"
)

st.title("Sirv Spin Conversion Tools")
st.markdown("""
This app allows you to convert Sirv 360° spins to various formats required by
different platforms like MSC, Amazon, Grainger, Walmart, Home Depot, and Lowe's.

**How it works:**
1. Enter your Sirv API credentials in the sidebar
2. Select a spin file from your account OR enter one or more spin URLs manually
3. Choose the platform you want to convert for and provide the required identifier
4. Click the conversion button to generate a downloadable zip file
""")

# Sidebar for authentication
st.sidebar.header("Authentication")

# Check if credentials are in env vars, otherwise use input fields
client_id = os.getenv("SIRV_CLIENT_ID", "")
client_secret = os.getenv("SIRV_CLIENT_SECRET", "")
account_url = os.getenv("SIRV_ACCOUNT_URL", "")

# If any of the credentials are not in env vars, show input fields
if not (client_id and client_secret and account_url):
    account_url = st.sidebar.text_input("Sirv Account URL", value=account_url,
                                       help="Your Sirv account URL, e.g., https://demo.sirv.com")
    client_id = st.sidebar.text_input("Client ID", value=client_id,
                                     help="Your Sirv API client ID")
    client_secret = st.sidebar.text_input("Client Secret", value=client_secret,
                                         type="password", help="Your Sirv API client secret")

# Initialize session state for token management
if 'token' not in st.session_state:
    st.session_state.token = ""
if 'token_timestamp' not in st.session_state:
    st.session_state.token_timestamp = 0
if 'conversion_results' not in st.session_state:
    st.session_state.conversion_results = []
if 'selected_spin' not in st.session_state:
    st.session_state.selected_spin = ""
if 'manual_spin_urls' not in st.session_state:
    st.session_state.manual_spin_urls = []
if 'selected_manual_spin' not in st.session_state:
    st.session_state.selected_manual_spin = ""
if 'spin_selection_method' not in st.session_state:
    st.session_state.spin_selection_method = "account"

# Token management functions
TOKEN_EXPIRY = 4.5 * 60  # 4.5 minutes in seconds (token expires after 5 minutes)

def get_token():
    """Get a fresh token if current one is expired or doesn't exist."""
    current_time = time.time()

    # If token is expired or doesn't exist, get a new one
    if (not st.session_state.token or
        current_time - st.session_state.token_timestamp > TOKEN_EXPIRY):
        sirvurl = 'https://api.sirv.com/v2/token'
        payload = {
            'clientId': client_id,
            'clientSecret': client_secret
        }
        headers = {'content-type': 'application/json'}
        response = requests.request(
            'POST', sirvurl, data=json.dumps(payload), headers=headers
        )

        if response.status_code == 200:
            st.session_state.token = response.json()['token']
            st.session_state.token_timestamp = current_time
            return True
        else:
            st.error(f"Error getting token: {response.status_code} - {response.text}")
            return False
    return True

def check_folder(folder_path):
    """Check if a folder exists, create it if not."""
    if not get_token():
        return False

    sirvurl = f'https://api.sirv.com/v2/files/readdir?dirname={folder_path}'
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('GET', sirvurl, headers=headers)

    if response.status_code == 200:
        return True
    else:
        return create_folder(folder_path)

def create_folder(folder_path):
    """Create a folder in Sirv account."""
    if not get_token():
        return False

    sirvurl = f'https://api.sirv.com/v2/files/mkdir?dirname={folder_path}'
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', sirvurl, headers=headers)

    if response.status_code == 200:
        st.success(f"Created folder: {folder_path}")
        return True
    else:
        st.error(f"Error creating folder: {response.status_code} - {response.text}")
        return False

def get_spins(max_results=1000):
    """Get list of spin files from Sirv account using search API."""
    if not get_token():
        return []

    spins = []

    # Construct the search query to find all .spin files, excluding trash
    search_query = 'extension:.spin AND -dirname:\\/.Trash'

    payload = {
        'query': search_query,
        'sort': {'filename.raw': 'asc'},
        'from': 0,
        'size': 100  # Fetch in batches of 100
    }

    # If we potentially need more than 1000 results, use scroll API
    if max_results > 1000:
        payload['scroll'] = True

    sirvurl = 'https://api.sirv.com/v2/files/search'
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }

    response = requests.request(
        'POST', sirvurl, headers=headers, data=json.dumps(payload)
    )

    if response.status_code == 200:
        results = response.json()

        # Process initial results
        if 'hits' in results and results['hits']:
            for hit in results['hits']:
                if '_source' in hit and 'filename' in hit['_source']:
                    filename = hit['_source']['filename']
                    if filename.endswith('.spin'):
                        spins.append(filename)

        total_found = results.get('total', 0)

        # If we need more results and scroll is supported
        if len(spins) < total_found and len(spins) < max_results and 'scrollId' in results:
            scroll_id = results['scrollId']

            # Continue scrolling until we have all results or hit max_results
            while len(spins) < total_found and len(spins) < max_results:
                if not get_token():  # Refresh token if needed
                    break

                scroll_url = 'https://api.sirv.com/v2/files/search/scroll'
                scroll_payload = {'scrollId': scroll_id}

                scroll_response = requests.request(
                    'POST', scroll_url, headers=headers, data=json.dumps(scroll_payload)
                )

                if scroll_response.status_code != 200:
                    break

                scroll_results = scroll_response.json()

                if 'hits' not in scroll_results or not scroll_results['hits']:
                    break

                for hit in scroll_results['hits']:
                    if '_source' in hit and 'filename' in hit['_source']:
                        filename = hit['_source']['filename']
                        if filename.endswith('.spin'):
                            spins.append(filename)

                # Update scroll_id for next iteration if available
                if 'scrollId' in scroll_results:
                    scroll_id = scroll_results['scrollId']
                else:
                    break

        return spins
    else:
        st.error(f"Error fetching spins: {response.status_code} - {response.text}")
        return []

def process_manual_spin_urls(text_input):
    """Process manual spin URLs/paths from text input."""
    urls = []

    # Split by newlines and process each line
    lines = text_input.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If the URL includes the account URL, extract just the path
        if account_url and line.startswith(account_url):
            path = line.replace(account_url, "")
        # If it's already a path starting with /, use it as is
        elif line.startswith('/'):
            path = line
        # If it's a full URL but not from the account domain, skip it
        elif line.startswith('http'):
            st.warning(f"Skipping URL not from your Sirv account domain: {line}")
            continue
        # Otherwise, assume it's a path and add / if needed
        else:
            path = f"/{line}" if not line.startswith('/') else line

        # Validate that it's a spin file
        if not path.endswith('.spin'):
            path = f"{path}.spin" if not path.endswith('/') else f"{path}spin.spin"

        urls.append(path)

    return urls

def get_spin_path():
    """Get the selected spin path based on selection method."""
    if st.session_state.spin_selection_method == "account":
        return st.session_state.selected_spin
    else:
        # For manual URL entry, return the selected manual spin
        return st.session_state.selected_manual_spin

# API conversion functions
def convert_to_msc(spin_path, msc_id):
    """Convert spin to MSC format."""
    if not get_token():
        return None

    output_folder = '/Zips-MSC/'
    if not check_folder(output_folder):
        return None

    sirvurl = 'https://api.sirv.com/v2/files/spin2msc360'
    payload = {'filename': spin_path, 'mscid': msc_id}
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', sirvurl, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        # Get the filename from the response
        zip_path = response.json()['filename']

        # Move the file to the output folder
        if move_zip_file(zip_path, f"{output_folder}{msc_id}.zip"):
            return f"{account_url}{output_folder}{msc_id}.zip"
    else:
        st.error(f"Error generating MSC zip: {response.status_code} - {response.text}")
    return None

def convert_to_amazon(spin_path, asin):
    """Convert spin to Amazon format."""
    if not get_token():
        return None

    output_folder = '/Zips-Amazon/'
    if not check_folder(output_folder):
        return None

    sirvurl = 'https://api.sirv.com/v2/files/spin2amazon360'
    payload = {'filename': spin_path, 'asin': asin}
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', sirvurl, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        # Get the filename from the response
        zip_path = response.json()['filename']

        # Move the file to the output folder
        if move_zip_file(zip_path, f"{output_folder}{asin}.zip"):
            return f"{account_url}{output_folder}{asin}.zip"
    else:
        st.error(f"Error generating Amazon zip: {response.status_code} - {response.text}")
    return None

def convert_to_grainger(spin_path, sku):
    """Convert spin to Grainger format."""
    if not get_token():
        return None

    output_folder = '/Zips-Grainger/'
    if not check_folder(output_folder):
        return None

    sirvurl = 'https://api.sirv.com/v2/files/spin2grainger360'
    payload = {'filename': spin_path, 'sku': sku}
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', sirvurl, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        # Get the filename from the response
        zip_path = response.json()['filename']

        # Move the file to the output folder
        if move_zip_file(zip_path, f"{output_folder}{sku}.zip"):
            return f"{account_url}{output_folder}{sku}.zip"
    else:
        st.error(f"Error generating Grainger zip: {response.status_code} - {response.text}")
    return None

def convert_to_walmart(spin_path, gtin):
    """Convert spin to Walmart format."""
    if not get_token():
        return None

    output_folder = '/Zips-Walmart/'
    if not check_folder(output_folder):
        return None

    sirvurl = 'https://api.sirv.com/v2/files/spin2walmart360'
    payload = {'filename': spin_path, 'gtin': gtin}
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', sirvurl, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        # Get the filename from the response
        zip_path = response.json()['filename']

        # Move the file to the output folder
        if move_zip_file(zip_path, f"{output_folder}{gtin}.zip"):
            return f"{account_url}{output_folder}{gtin}.zip"
    else:
        st.error(f"Error generating Walmart zip: {response.status_code} - {response.text}")
    return None

def convert_to_homedepot(spin_path, omsid, spin_number=None):
    """Convert spin to Home Depot format."""
    if not get_token():
        return None

    output_folder = '/Zips-HomeDepot/'
    if not check_folder(output_folder):
        return None

    sirvurl = 'https://api.sirv.com/v2/files/spin2homedepot360'
    payload = {'filename': spin_path, 'omsid': omsid}

    if spin_number:
        payload['spinNumber'] = int(spin_number)

    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', sirvurl, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        # Get the filename from the response
        zip_path = response.json()['filename']

        # Move the file to the output folder
        if move_zip_file(zip_path, f"{output_folder}{omsid}.zip"):
            return f"{account_url}{output_folder}{omsid}.zip"
    else:
        st.error(f"Error generating Home Depot zip: {response.status_code} - {response.text}")
    return None

def convert_to_lowes(spin_path, barcode):
    """Convert spin to Lowe's format."""
    if not get_token():
        return None

    output_folder = '/Zips-Lowes/'
    if not check_folder(output_folder):
        return None

    sirvurl = 'https://api.sirv.com/v2/files/spin2lowes360'
    payload = {'filename': spin_path, 'barcode': barcode}
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', sirvurl, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        # Get the filename from the response
        zip_path = response.json()['filename']

        # Move the file to the output folder
        if move_zip_file(zip_path, f"{output_folder}{barcode}.zip"):
            return f"{account_url}{output_folder}{barcode}.zip"
    else:
        st.error(f"Error generating Lowe's zip: {response.status_code} - {response.text}")
    return None

def move_zip_file(from_path, to_path):
    """Move/rename a file in Sirv account."""
    if not get_token():
        return False

    # Remove the account URL if it's in the from_path
    if account_url and from_path.startswith(account_url):
        from_path = from_path.replace(account_url, "")

    rename_url = f'https://api.sirv.com/v2/files/rename?from={from_path}&to={to_path}'
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {st.session_state.token}'
    }
    response = requests.request('POST', rename_url, headers=headers)

    if response.status_code == 200:
        return True
    else:
        st.error(f"Error moving file: {response.status_code} - {response.text}")
        return False

# Add a result to the conversion history
def add_result(platform, identifier, url):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    spin_path = get_spin_path()
    result = {
        "timestamp": timestamp,
        "platform": platform,
        "identifier": identifier,
        "url": url,
        "spin_path": spin_path
    }
    st.session_state.conversion_results.insert(0, result)  # Add to the beginning

# Main app interface
tab1, tab2 = st.tabs(["Conversion Tools", "Conversion History"])

with tab1:
    # Spin selection section
    st.header("Step 1: Select a Spin")
    spin_selection_method = st.radio(
        "Choose how to select your spins",
        options=["Select from account", "Enter spin URLs manually"],
        horizontal=True,
        key="spin_selection_radio",
        on_change=lambda: setattr(st.session_state, 'spin_selection_method',
                                 "account" if st.session_state.spin_selection_radio == "Select from account" else "manual")
    )

    # Test connection and fetch spins if credentials are provided
    if spin_selection_method == "Select from account":
        st.session_state.spin_selection_method = "account"
        if client_id and client_secret and account_url:
            if get_token():
                with st.spinner("Loading spins from your account..."):
                    spins = get_spins()
                if spins:
                    st.session_state.selected_spin = st.selectbox(
                        "Select a spin file to convert",
                        spins,
                        index=0 if st.session_state.selected_spin == "" else spins.index(st.session_state.selected_spin) if st.session_state.selected_spin in spins else 0
                    )
                    st.success(f"Selected spin: {st.session_state.selected_spin}")
                else:
                    st.warning("No spin files found in your Sirv account.")
            else:
                st.error("Failed to authenticate with Sirv API. Please check your credentials.")
        else:
            st.info("Please enter your Sirv API credentials in the sidebar to get started.")
    else:
        st.session_state.spin_selection_method = "manual"
        manual_input = st.text_area(
            "Enter spin URLs or paths (one per line)",
            height=150,
            help="Enter one or more spin URLs or paths, one per line. E.g., /folder/product.spin"
        )

        if st.button("Add Spins"):
            if manual_input:
                st.session_state.manual_spin_urls = process_manual_spin_urls(manual_input)
                if st.session_state.manual_spin_urls:
                    st.success(f"Added {len(st.session_state.manual_spin_urls)} spin paths")
                else:
                    st.error("No valid spin paths found in your input")
            else:
                st.warning("Please enter at least one spin URL or path")

        # Display and select from the manual spins list if available
        if st.session_state.manual_spin_urls:
            st.subheader("Your Added Spins")

            st.session_state.selected_manual_spin = st.selectbox(
                "Select a spin to convert",
                st.session_state.manual_spin_urls,
                index=0 if st.session_state.selected_manual_spin == "" or st.session_state.selected_manual_spin not in st.session_state.manual_spin_urls else st.session_state.manual_spin_urls.index(st.session_state.selected_manual_spin)
            )

            st.success(f"Selected spin: {st.session_state.selected_manual_spin}")

            # Add button to clear the list
            if st.button("Clear Spin List"):
                st.session_state.manual_spin_urls = []
                st.session_state.selected_manual_spin = ""
                st.experimental_rerun()

    # Only show conversion tools if a spin is selected or entered
    spin_selected = (st.session_state.spin_selection_method == "account" and st.session_state.selected_spin) or \
                   (st.session_state.spin_selection_method == "manual" and st.session_state.selected_manual_spin)

    if spin_selected:
        st.header("Step 2: Choose Conversion Format")
        st.markdown("---")

        # MSC Conversion
        with st.expander("MSC Conversion", expanded=True):
            st.markdown("Convert a spin to MSC 360° format.")
            msc_id = st.text_input("MSC ID", key="msc_id")

            if st.button("Convert to MSC Format"):
                if msc_id:
                    with st.spinner("Converting to MSC format..."):
                        result_url = convert_to_msc(get_spin_path(), msc_id)
                        if result_url:
                            st.success(f"Successfully converted to MSC format!")
                            st.markdown(f"[Download MSC Zip]({result_url})")
                            add_result("MSC", msc_id, result_url)
                else:
                    st.warning("Please enter an MSC ID.")

        # Amazon Conversion
        with st.expander("Amazon Conversion"):
            st.markdown("Convert a spin to Amazon 360° format.")
            asin = st.text_input("Amazon ASIN", key="asin",
                               help="Amazon Standard Identification Number")

            if st.button("Convert to Amazon Format"):
                if asin:
                    with st.spinner("Converting to Amazon format..."):
                        result_url = convert_to_amazon(get_spin_path(), asin)
                        if result_url:
                            st.success(f"Successfully converted to Amazon format!")
                            st.markdown(f"[Download Amazon Zip]({result_url})")
                            add_result("Amazon", asin, result_url)
                else:
                    st.warning("Please enter an Amazon ASIN.")

        # Grainger Conversion
        with st.expander("Grainger Conversion"):
            st.markdown("Convert a spin to Grainger 360° format.")
            sku = st.text_input("Grainger SKU", key="sku")

            if st.button("Convert to Grainger Format"):
                if sku:
                    with st.spinner("Converting to Grainger format..."):
                        result_url = convert_to_grainger(get_spin_path(), sku)
                        if result_url:
                            st.success(f"Successfully converted to Grainger format!")
                            st.markdown(f"[Download Grainger Zip]({result_url})")
                            add_result("Grainger", sku, result_url)
                else:
                    st.warning("Please enter a Grainger SKU.")

        # Walmart Conversion
        with st.expander("Walmart Conversion"):
            st.markdown("Convert a spin to Walmart 360° format.")
            gtin = st.text_input("Walmart GTIN", key="gtin")

            if st.button("Convert to Walmart Format"):
                if gtin:
                    with st.spinner("Converting to Walmart format..."):
                        result_url = convert_to_walmart(get_spin_path(), gtin)
                        if result_url:
                            st.success(f"Successfully converted to Walmart format!")
                            st.markdown(f"[Download Walmart Zip]({result_url})")
                            add_result("Walmart", gtin, result_url)
                else:
                    st.warning("Please enter a Walmart GTIN.")

        # Home Depot Conversion
        with st.expander("Home Depot Conversion"):
            st.markdown("Convert a spin to Home Depot 360° format.")
            omsid = st.text_input("Home Depot OMSID", key="omsid",
                                help="Home Depot OMSID (9 digits)")
            spin_number = st.number_input("Spin Number (Optional)",
                                        key="spin_number",
                                        min_value=1, step=1,
                                        help="Only needed if product has multiple spins")

            if st.button("Convert to Home Depot Format"):
                if omsid:
                    if len(omsid) == 9:
                        with st.spinner("Converting to Home Depot format..."):
                            result_url = convert_to_homedepot(
                                get_spin_path(),
                                omsid,
                                spin_number
                            )
                            if result_url:
                                st.success(f"Successfully converted to Home Depot format!")
                                st.markdown(f"[Download Home Depot Zip]({result_url})")
                                add_result("Home Depot", omsid, result_url)
                    else:
                        st.warning("Home Depot OMSID must be 9 digits.")
                else:
                    st.warning("Please enter a Home Depot OMSID.")

        # Lowe's Conversion
        with st.expander("Lowe's Conversion"):
            st.markdown("Convert a spin to Lowe's 360° format.")
            barcode = st.text_input("Lowe's Barcode", key="barcode")

            if st.button("Convert to Lowe's Format"):
                if barcode:
                    with st.spinner("Converting to Lowe's format..."):
                        result_url = convert_to_lowes(get_spin_path(), barcode)
                        if result_url:
                            st.success(f"Successfully converted to Lowe's format!")
                            st.markdown(f"[Download Lowe's Zip]({result_url})")
                            add_result("Lowe's", barcode, result_url)
                else:
                    st.warning("Please enter a Lowe's Barcode.")

# Conversion History tab
with tab2:
    st.header("Conversion History")

    if not st.session_state.conversion_results:
        st.info("No conversions have been performed yet.")
    else:
        # Create a dataframe for the conversion history
        st.write(f"Total conversions: {len(st.session_state.conversion_results)}")

        # Display the conversion history as a table
        for result in st.session_state.conversion_results:
            col1, col2, col3 = st.columns([1.5, 1, 2])
            with col1:
                st.write(f"**Platform:** {result['platform']}")
                st.write(f"**ID:** {result['identifier']}")
                if 'spin_path' in result:
                    st.write(f"**Spin:** {result['spin_path']}")
            with col2:
                st.write(f"**Time:** {result['timestamp']}")
            with col3:
                st.write(f"**Download:** [Link]({result['url']})")
            st.divider()

        if st.button("Clear History"):
            st.session_state.conversion_results = []
            st.experimental_rerun()