import os
import requests
import json
import time
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv, set_key, find_dotenv
from streamlit_local_storage import LocalStorage

# Initialize local storage
localStorage = LocalStorage()

# Load environment variables (keeping this for backward compatibility)
dotenv_path = find_dotenv(raise_error_if_not_found=False)
if dotenv_path:
    load_dotenv(dotenv_path)

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
1. Enter your Sirv API credentials in the sidebar ([get or create API credentials](https://my.sirv.com/#/account/settings/api))
2. Select a spin file from your account OR enter one or more spin URLs manually
3. Choose the platform you want to convert for and provide the required identifier
4. Click the conversion button to generate a downloadable zip file
5. Use the Bulk Conversion feature for processing multiple spins at once
""")

# Sidebar for authentication
st.sidebar.header("Authentication")
# Helper function to format Sirv Account URL
def format_account_url(url):
    url = url.strip()
    if not url:
        return ""
    if url.startswith("https://"):
        return url
    return "https://" + url
# Check if credentials are in localStorage, if not fall back to env vars
try:
    if 'client_id' not in st.session_state: # Initialize in session state if not present
        st.session_state.client_id = localStorage.getItem("sirv_client_id")
        if st.session_state.client_id is None:
            st.session_state.client_id = os.getenv("SIRV_CLIENT_ID", "")
    client_id = st.session_state.client_id # Use session state for client_id
except Exception as e:
    st.session_state.client_id = os.getenv("SIRV_CLIENT_ID", "") # Initialize even on error
    client_id = st.session_state.client_id

try:
    if 'client_secret' not in st.session_state: # Initialize in session state if not present
        st.session_state.client_secret = localStorage.getItem("sirv_client_secret")
        if st.session_state.client_secret is None:
            st.session_state.client_secret = os.getenv("SIRV_CLIENT_SECRET", "")
    client_secret = st.session_state.client_secret # Use session state for client_secret
except Exception as e:
    st.session_state.client_secret = os.getenv("SIRV_CLIENT_SECRET", "") # Initialize even on error
    client_secret = st.session_state.client_secret

# Remove account_url retrieval from storage and env, initialize it as empty
account_url = ""

# Function to save credentials to localStorage
def save_credentials_to_local_storage(client_id, client_secret):
    """Save credentials to browser localStorage."""
    try:
        localStorage.setItem("sirv_client_id", client_id, key="save_client_id")
        localStorage.setItem("sirv_client_secret", client_secret, key="save_client_secret")
        return True
    except Exception as e:
        st.sidebar.error(f"Error saving credentials: {str(e)}")
        return False

# If any of the credentials are not in localStorage, show input fields
if not st.session_state.client_id or not st.session_state.client_secret: # More explicit condition
    st.session_state.client_id = st.sidebar.text_input("Client ID", value=st.session_state.client_id,
                                     help="Your Sirv API client ID")
    st.session_state.client_secret = st.sidebar.text_input("Client Secret", value=st.session_state.client_secret,
                                         type="password", help="Your Sirv API client secret")

    # Add save button
    if st.session_state.client_id and st.session_state.client_secret:
        if st.sidebar.button("Apply and Save Credentials to Your Browser"):
            if save_credentials_to_local_storage(st.session_state.client_id, st.session_state.client_secret):
                st.sidebar.success("Credentials saved in your browser!")
            else:
                st.sidebar.error("Failed to save credentials.")
else:
    st.sidebar.success("✅ Credentials loaded from your browser")
    # Add button to clear credentials
    if st.sidebar.button("Clear Saved Credentials"):
        st.write("**[DEBUG START] Clear Credentials Button Clicked**")

        # Set client_id and client_secret in session_state to empty strings
        st.session_state.client_id = ""  # Update session state
        st.session_state.client_secret = "" # Update session state

        localStorage.deleteAll()
        st.sidebar.info("Credentials cleared. Please refresh your browser to complete the process.")
        time.sleep(1)  # Keep the delay - might still be helpful
        st.components.v1.html("""
            <script>
                window.location.reload(true);
            </script>
        """) # Force full page reload

# Initialize session state for token management
if 'token' not in st.session_state:
    st.session_state.token = ""
if 'token_timestamp' not in st.session_state:
    st.session_state.token_timestamp = 0
if 'conversion_results' not in st.session_state:
    # Try to load conversion history from localStorage
    try:
        saved_history = localStorage.getItem("conversion_history")
        if saved_history is not None and saved_history != "undefined":
            try:
                # Parse JSON string back into list of dictionaries
                st.session_state.conversion_results = json.loads(saved_history)
            except json.JSONDecodeError:
                st.session_state.conversion_results = []
        else:
            st.session_state.conversion_results = []
    except Exception as e:
        # If any error occurs loading from localStorage, start with an empty list
        st.session_state.conversion_results = []
if 'selected_spin' not in st.session_state:
    st.session_state.selected_spin = ""
if 'manual_spin_urls' not in st.session_state:
    st.session_state.manual_spin_urls = []
if 'selected_manual_spin' not in st.session_state:
    st.session_state.selected_manual_spin = ""
if 'spin_selection_method' not in st.session_state:
    st.session_state.spin_selection_method = "account"
if 'bulk_conversion_data' not in st.session_state:
    st.session_state.bulk_conversion_data = []
def fetch_account_url():
    """Fetch the cdnURL from the Sirv account details using the current token."""
    sirvurl = 'https://api.sirv.com/v2/account'
    headers = {
        'authorization': f'Bearer {st.session_state.token}',
        'content-type': 'application/json'
    }
    response = requests.get(sirvurl, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'cdnURL' in data:
            return format_account_url(data['cdnURL'])
        elif 'cdnTempURL' in data:
            return format_account_url(data['cdnTempURL'])
        else:
            return ""
    else:
        st.error(f"Error fetching account details: {response.status_code} - {response.text}")
        return ""
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
            global account_url
            if not account_url:
                account_url = fetch_account_url()
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

def get_spins(search_query='', max_results=1000):
    """Get list of spin files from Sirv account using search API."""
    if not get_token():
        return []

    spins = []

    # Construct the base search query to exclude trash
    base_query = '-dirname:\\/.Trash'

    # Add the user's search query if provided
    if search_query:
        search_query = f'{search_query} AND extension:.spin AND {base_query}'
    else:
        search_query = f'extension:.spin AND {base_query}'

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

def process_bulk_conversion_data(text_input):
    """Process bulk conversion data in format: spin_url,identifier."""
    bulk_data = []

    # Split by newlines and process each line
    lines = text_input.strip().split('\n')
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        # Check if line contains a comma for spin_url,identifier format
        parts = line.split(',', 1)  # Split only on the first comma
        if len(parts) != 2:
            st.warning(f"Line {line_num} skipped: Invalid format. Expected 'spin_url,identifier'")
            continue

        spin_url = parts[0].strip()
        identifier = parts[1].strip()

        if not spin_url or not identifier:
            st.warning(f"Line {line_num} skipped: Empty spin URL or identifier")
            continue

        # Process the spin URL to get the path
        # First, remove any @ prefix if present
        if spin_url.startswith('@'):
            spin_url = spin_url[1:]

        # If the URL includes the account URL, extract just the path
        if account_url and spin_url.startswith(account_url):
            path = spin_url.replace(account_url, "")
        # If it's already a path starting with /, use it as is
        elif spin_url.startswith('/'):
            path = spin_url
        # If it's a full URL, try to extract the path
        elif spin_url.startswith('http'):
            # Try to extract the path portion after the domain
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(spin_url)
                path = parsed_url.path
            except:
                # If parsing fails, just use the URL as is and let the API handle it
                path = spin_url
        # Otherwise, assume it's a path and add / if needed
        else:
            path = f"/{spin_url}" if not spin_url.startswith('/') else spin_url

        # Validate that it's a spin file
        if not path.endswith('.spin'):
            path = f"{path}.spin" if not path.endswith('/') else f"{path}spin.spin"

        bulk_data.append({
            'spin_path': path,
            'identifier': identifier,
            'original_url': spin_url
        })

    return bulk_data

def get_spin_path():
    """Get the selected spin path based on selection method."""
    if st.session_state.spin_selection_method == "account":
        return st.session_state.selected_spin
    else:
        # For manual URL entry, return the selected manual spin
        return st.session_state.selected_manual_spin

# Add this function after get_spin_path() function
def get_thumbnail_url(spin_path):
    """Generate a thumbnail URL for a spin."""
    # If it's already a full URL, just add ?thumb
    if spin_path.startswith('https'):
        return f"{spin_path}?thumb"

    # If it's a path and we have an account URL, combine them
    global account_url # Ensure we are using the global account_url
    if not account_url: # If account_url is empty, fetch it
        if not get_token(): # Ensure we have a token first and refresh if needed
            return None # If no token, cannot fetch account_url, return None
        account_url = fetch_account_url() # Fetch account_url

    if account_url and account_url != "": # Now check if account_url is available
        # Make sure there's no double slash between account_url and spin_path
        if account_url.endswith('/') and spin_path.startswith('/'):
            return f"{account_url}{spin_path[1:]}?thumb"
        elif not account_url.endswith('/') and not spin_path.startswith('/'):
            return f"{account_url}/{spin_path}?thumb"
        else:
            return f"{account_url}{spin_path}?thumb"

    # If no account_url is available, return None
    return None

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
def add_result(platform, identifier, url, spin_path=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not spin_path:
        spin_path = get_spin_path()
    result = {
        "timestamp": timestamp,
        "platform": platform,
        "identifier": identifier,
        "url": url,
        "spin_path": spin_path
    }
    # Add to the beginning of the list
    st.session_state.conversion_results.insert(0, result)

    # Save updated history to localStorage
    try:
        # Convert list to JSON string
        history_json = json.dumps(st.session_state.conversion_results)
        localStorage.setItem("conversion_history", history_json, key="save_history")
    except Exception as e:
        st.warning(f"Could not save conversion history: {str(e)}")

# Run bulk conversion for a specific platform
def run_bulk_conversion(platform, bulk_data):
    """Run bulk conversion for specified platform."""
    results = []
    successes = 0
    failures = 0

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, item in enumerate(bulk_data):
        spin_path = item['spin_path']
        identifier = item['identifier']

        # Update progress
        progress = (i / len(bulk_data))
        progress_bar.progress(progress)
        status_text.text(f"Processing {i+1} of {len(bulk_data)}: {spin_path}")

        result_url = None

        # Call the appropriate conversion function based on platform
        try:
            if platform == "MSC":
                result_url = convert_to_msc(spin_path, identifier)
            elif platform == "Amazon":
                result_url = convert_to_amazon(spin_path, identifier)
            elif platform == "Grainger":
                result_url = convert_to_grainger(spin_path, identifier)
            elif platform == "Walmart":
                result_url = convert_to_walmart(spin_path, identifier)
            elif platform == "Home Depot":
                # For Home Depot, the identifier should be a 9-digit OMSID
                if len(identifier) == 9:
                    result_url = convert_to_homedepot(spin_path, identifier)
                else:
                    st.warning(f"Skipping Home Depot conversion for {spin_path}: ID {identifier} must be 9 digits")
            elif platform == "Lowes":
                result_url = convert_to_lowes(spin_path, identifier)
        except Exception as e:
            st.error(f"Error converting {spin_path}: {str(e)}")
            failures += 1
            continue

        if result_url:
            successes += 1
            results.append({
                'spin_path': spin_path,
                'identifier': identifier,
                'url': result_url
            })
            # Add to conversion history
            add_result(platform, identifier, result_url, spin_path)
        else:
            failures += 1

    # Complete the progress bar
    progress_bar.progress(1.0)
    status_text.text("Processing complete!")

    return {
        'results': results,
        'successes': successes,
        'failures': failures
    }

# Main app interface
tab1, tab2, tab3 = st.tabs(["Conversion Tools", "Bulk Conversion", "Conversion History"])

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
        if client_id and client_secret:
            if get_token():
                spin_search_query = st.text_input("Search spins", placeholder="Enter spin name or keywords...", key="spin_search_query")
                with st.spinner("Loading spins from your account..."):
                    spins = get_spins(search_query=spin_search_query)
                if spins:
                    st.session_state.selected_spin = st.selectbox(
                        "Select a spin file to convert",
                        spins,
                        index=0 if st.session_state.selected_spin == "" else spins.index(st.session_state.selected_spin) if st.session_state.selected_spin in spins else 0
                    )
                    st.success(f"Selected spin: {st.session_state.selected_spin}")
                    # Display thumbnail for the selected spin
                    thumbnail_url = get_thumbnail_url(st.session_state.selected_spin)
                    if thumbnail_url:
                        st.image(thumbnail_url, caption="Spin Thumbnail", width=300)
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
            # Display thumbnail for the selected manual spin
            thumbnail_url = get_thumbnail_url(st.session_state.selected_manual_spin)
            if thumbnail_url:
                st.image(thumbnail_url, caption="Spin Thumbnail", width=300)

            # Add button to clear the list
            if st.button("Clear Spin List"):
                st.session_state.manual_spin_urls = []
                st.session_state.selected_manual_spin = ""

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

# Bulk Conversion tab
with tab2:
    st.header("Bulk Conversion")
    st.markdown("""
    Convert multiple spins at once. Enter your data in the format: `spin_url,identifier` (one per line).

    Examples:
    ```
    https://sirvreplit.sirv.com/Spins/Trainers/Trainers.spin,887276371399
    https://sirvreplit.sirv.com/Spins/Egg-Chair/Egg-Chair.spin,799123761
    ```

    You can also use the `@` prefix for the URL (it will be ignored):
    ```
    @https://sirvreplit.sirv.com/Spins/Trainers/Trainers.spin,887276371399
    ```
    """)

    # Platform selection for bulk conversion
    bulk_platform = st.selectbox(
        "Select conversion platform",
        options=["MSC", "Amazon", "Grainger", "Walmart", "Home Depot", "Lowes"],
        index=0
    )

    bulk_input = st.text_area(
        "Enter spin URLs and identifiers (one per line in format: spin_url,identifier)",
        height=200,
        help="Enter data in format: spin_url,identifier (one per line)"
    )

    if st.button("Process Bulk Conversion"):
        if bulk_input and bulk_platform:
            # Process the bulk input data
            bulk_data = process_bulk_conversion_data(bulk_input)

            if bulk_data:
                st.session_state.bulk_conversion_data = bulk_data
                st.success(f"Found {len(bulk_data)} items to process")

                # Run the bulk conversion
                with st.spinner(f"Processing {len(bulk_data)} conversions to {bulk_platform} format..."):
                    results = run_bulk_conversion(bulk_platform, bulk_data)

                # Show the results
                st.success(f"Bulk conversion completed: {results['successes']} successful, {results['failures']} failed")

                if results['results']:
                    st.subheader("Download Links")
                    for idx, result in enumerate(results['results']):
                        st.markdown(f"{idx+1}. **{result['identifier']}**: [{result['spin_path']}]({result['url']})")
            else:
                st.error("No valid data found. Please check your input format.")
        else:
            st.warning("Please enter data and select a platform.")

# Conversion History tab
with tab3:
    st.header("Conversion History")

    # Add information about localStorage persistence
    st.info("Conversion history is saved in your browser and will persist between sessions.")

    if not st.session_state.conversion_results:
        st.info("No conversions have been performed yet.")
    else:
        # Create a dataframe for the conversion history
        st.write(f"Total conversions: {len(st.session_state.conversion_results)}")

        # Display the conversion history as a table with thumbnails
        for result in st.session_state.conversion_results:
            col1, col2, col3, col4 = st.columns([1, 1, 1.5, 0.5])

            # Display thumbnail in the first column
            with col1:
                if 'spin_path' in result:
                    thumbnail_url = get_thumbnail_url(result['spin_path'])
                    if thumbnail_url:
                        st.image(thumbnail_url, width=100)

            with col2:
                st.write(f"**Platform:** {result['platform']}")
                st.write(f"**ID:** {result['identifier']}")
                if 'spin_path' in result:
                    st.write(f"**Spin:** {os.path.basename(result['spin_path'])}")

            with col3:
                st.write(f"**Time:** {result['timestamp']}")
                st.write(f"**Download:** [Link]({result['url']})")

            with col4:
                # Add a button to view the full spin
                if 'spin_path' in result:
                    spin_path = result['spin_path']
                    thumbnail_url = get_thumbnail_url(spin_path)
                    if thumbnail_url:
                        spin_url = thumbnail_url.replace('?thumb', '')
                        st.markdown(f"[View Spin]({spin_url})")

            st.divider()

        if st.button("Clear History"):
            st.session_state.conversion_results = []
            # Also clear the history in localStorage
            localStorage.setItem("conversion_history", "[]", key="clear_history")


