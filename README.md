# Sirv Spin Conversion Tools

A Streamlit application for converting Sirv 360° spins to various marketplace formats including MSC, Amazon, Grainger, Walmart, Home Depot, and Lowe's.

## Features

- **Authentication**: Securely connect to your Sirv account
- **Multiple Conversion Options**: Convert spins to various marketplace formats
- **Flexible Spin Selection**: Either select from your Sirv account or manually enter spin URLs
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
   git clone https://github.com/IgorVaryvoda/sirv-streamlit.git
   cd sirv-streamlit
   ```

2. Create and activate a virtual environment:
   ```
   uv venv
   source .venv/bin/activate.fish  # For fish shell
   # Or for other shells:
   # source .venv/bin/activate  # For bash/zsh
   # .venv\Scripts\activate  # For Windows
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

1. Make sure you're in the project directory and your virtual environment is activated:
   ```
   source .venv/bin/activate.fish  # For fish shell
   ```

2. Run the Streamlit app:
   ```
   streamlit run app.py
   ```

3. Access the app in your web browser at `http://localhost:8501`

4. If you haven't set environment variables, enter your Sirv credentials in the sidebar.

5. Select a spin in one of two ways:
   - **From your account**: Select a spin file from the dropdown of all spin files in your Sirv account
   - **Manual entry**: Enter a spin URL or path directly (e.g., `/folder/product.spin` or the full URL)

6. Choose the conversion format you need and enter the required identifier (ASIN, SKU, GTIN, etc.) for the target platform.

7. Click the Convert button and wait for the process to complete.

8. Once conversion is finished, a download link will be provided, and the conversion will be added to your history.

## Troubleshooting

If you see an error like `fish: Unknown command: streamlit`, this means the Streamlit package is not in your PATH. Make sure you've:

1. Activated the virtual environment:
   ```
   source .venv/bin/activate.fish
   ```

2. Installed the requirements:
   ```
   uv pip install -r requirements.txt
   ```

3. If needed, you can also run the app with the full path:
   ```
   python -m streamlit run app.py
   ```

## License

MIT

## Acknowledgements

This app uses the Sirv API for all conversions. Please refer to the [Sirv API Documentation](https://sirv.com/help/articles/sirv-api/) for more information.