# Sirv Spin Conversion Tools

A Streamlit application for converting Sirv 360° spins to various marketplace formats including MSC, Amazon, Grainger, Walmart, Home Depot, and Lowe's.

## Features

- **Authentication**: Securely connect to your Sirv account
- **Multiple Conversion Options**: Convert spins to various marketplace formats
- **Conversion History**: Track all of your conversions in one place
- **User-friendly Interface**: Easy-to-use Streamlit interface

## Supported Platforms

- **MSC**: Convert spins to MSC 360° format
- **Amazon**: Convert spins to Amazon 360° format
- **Grainger**: Convert spins to Grainger 360° format
- **Walmart**: Convert spins to Walmart 360° format
- **Home Depot**: Convert spins to Home Depot 360° format
- **Lowe's**: Convert spins to Lowe's 360° format

## Setup

### Prerequisites

- Python 3.8+
- UV package manager
- A Sirv account with API access

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/sirv-streamlit.git
   cd sirv-streamlit
   ```

2. Create and activate a virtual environment:
   ```
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   uv pip install -r requirements.txt
   ```

4. Create a `.env` file with your Sirv credentials:
   ```
   cp .env.example .env
   ```

   Then edit the `.env` file and add your Sirv credentials:
   ```
   SIRV_CLIENT_ID=your_client_id
   SIRV_CLIENT_SECRET=your_client_secret
   SIRV_ACCOUNT_URL=your_sirv_account_url
   ```

### Usage

1. Run the Streamlit app:
   ```
   streamlit run app.py
   ```

2. Access the app in your web browser at `http://localhost:8501`

3. If you haven't set environment variables, enter your Sirv credentials in the sidebar.

4. Select a spin file from your Sirv account and choose the conversion format you need.

5. Enter the required identifier (ASIN, SKU, GTIN, etc.) for the target platform.

6. Click the Convert button and wait for the process to complete.

7. Once conversion is finished, a download link will be provided, and the conversion will be added to your history.

## License

MIT

## Acknowledgements

This app uses the Sirv API for all conversions. Please refer to the [Sirv API Documentation](https://sirv.com/help/articles/sirv-api/) for more information.