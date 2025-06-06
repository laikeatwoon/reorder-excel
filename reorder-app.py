import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
import re
from typing import Optional, List, Dict, Any

# Configuration constants
SHEET_CONFIGS = {
    'DF Items': 'Loose Cargo!A1:C200',
    'Shandong Items': 'Shandong!A1:C200', 
    'Taiwan Glass': 'Taiwan!A1:C200',
    'Lug Cap': 'Lug Cap!A1:C200'
}

COLUMN_MAPPING = {
    'Unnamed: 1': 'Product Code',
    'Unnamed: 40': 'Unit Sold', 
    'Unnamed: 61': 'Balance Stock'
}

@st.cache_data
def load_excel_data(uploaded_file) -> Optional[pd.DataFrame]:
    """Load Excel file with error handling and caching."""
    try:
        return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return None

def extract_inventory_data(data: pd.DataFrame) -> pd.DataFrame:
    """Extract and clean inventory data from Excel."""
    if data is None or data.empty:
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    # Select required columns
    required_cols = ['Unnamed: 1', 'Unnamed: 40', 'Unnamed: 61']
    missing_cols = [col for col in required_cols if col not in data.columns]
    
    if missing_cols:
        st.warning(f"Missing columns in Excel file: {missing_cols}")
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    new_data = data[required_cols].copy()
    
    # Drop rows with all NaN values
    new_data = new_data.dropna(how='all')
    
    if new_data.empty:
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    # Rename columns
    new_data = new_data.rename(columns=COLUMN_MAPPING)
    
    # Clean and convert data types
    try:
        new_data['Unit Sold'] = pd.to_numeric(new_data['Unit Sold'], errors='coerce').fillna(0).astype(int).abs()
        new_data['Balance Stock'] = pd.to_numeric(new_data['Balance Stock'], errors='coerce').fillna(0).astype(int)
        
        # Remove rows where Product Code is NaN
        new_data = new_data.dropna(subset=['Product Code'])
        
    except Exception as e:
        st.warning(f"Error processing data types: {str(e)}")
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    return new_data

def get_reorder_items(inventory_data: pd.DataFrame) -> pd.DataFrame:
    """Extract items that need reordering."""
    if inventory_data.empty:
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    reorder_data = inventory_data[inventory_data['Unit Sold'] >= inventory_data['Balance Stock']].copy()
    return reorder_data.reset_index(drop=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_google_sheet_data(sheet_range: str) -> Optional[pd.DataFrame]:
    """Fetch data from Google Sheets with caching and error handling."""
    try:
        # Get credentials from secrets
        keyfile_dict = st.secrets.get("keyfile")
        spreadsheet_id = st.secrets.get("SAMPLE_SPREADSHEET_ID")
        
        if not keyfile_dict or not spreadsheet_id:
            st.error("Missing Google Sheets credentials in secrets")
            return None
        
        # Create credentials and service
        credentials = service_account.Credentials.from_service_account_info(keyfile_dict)
        service = build('sheets', 'v4', credentials=credentials)
        
        # Fetch data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_range
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return pd.DataFrame()
        
        # Create DataFrame
        headers = values[0]
        data_rows = values[1:] if len(values) > 1 else []
        
        # Ensure all rows have the same length as headers
        normalized_rows = []
        for row in data_rows:
            # Pad row with empty strings if it's shorter than headers
            padded_row = row + [''] * (len(headers) - len(row))
            normalized_rows.append(padded_row[:len(headers)])  # Trim if longer
        
        df = pd.DataFrame(normalized_rows, columns=headers)
        
        # Clean the dataframe
        df = df.dropna(how='all')  # Remove completely empty rows
        df = df.reset_index(drop=True)
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching Google Sheet data: {str(e)}")
        return None

def extract_date_range(data: pd.DataFrame) -> List[str]:
    """Extract date range from the last row of data."""
    if data is None or data.empty:
        return []
    
    try:
        # Get the last row and convert to string
        last_row_text = str(data.iloc[-1, 0]) if not data.empty else ""
        
        # Find dates using regex (matches DD/MM/YYYY, MM/DD/YYYY, etc.)
        date_pattern = r'\d{1,2}/\d{1,2}/\d{2,4}'
        dates = re.findall(date_pattern, last_row_text)
        
        return dates[:2]  # Return max 2 dates
        
    except Exception as e:
        st.warning(f"Error extracting dates: {str(e)}")
        return []

def add_order_status(product_list: List[str], df: pd.DataFrame) -> pd.DataFrame:
    """Add order status column to dataframe."""
    if df.empty:
        return df
    
    df_copy = df.copy()
    df_copy['Ordered'] = df_copy['Product Code'].isin(product_list).map({True: 'Yes', False: 'No'})
    return df_copy

def initialize_session_state():
    """Initialize session state variables."""
    if 'google_product_codes' not in st.session_state:
        st.session_state.google_product_codes = set()

def load_sheet_data(sheet_name: str, sheet_range: str, session_key: str):
    """Load and cache Google Sheet data."""
    if session_key not in st.session_state:
        with st.spinner(f"Loading {sheet_name}..."):
            sheet_data = fetch_google_sheet_data(sheet_range)
            if sheet_data is not None:
                st.session_state[session_key] = sheet_data
                # Add product codes to the set
                if 'Product Code' in sheet_data.columns:
                    product_codes = sheet_data['Product Code'].dropna().tolist()
                    st.session_state.google_product_codes.update(product_codes)
            else:
                st.session_state[session_key] = pd.DataFrame()
    
    return st.session_state[session_key]

def clear_session_state():
    """Clear relevant session state variables."""
    keys_to_clear = [
        'google_data_df', 'google_data_sd', 'google_data_tw', 'google_data_lc',
        'google_product_codes', 'date_range', 'reorder_data'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def main():
    """Main application function."""
    st.set_page_config(
        page_title="Reorder App",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📦 Inventory Reorder Application")
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar for Google Sheets data
    with st.sidebar:
        st.header("📊 Inventory Sources")
        
        # Load all sheet data
        for sheet_name, sheet_range in SHEET_CONFIGS.items():
            session_key = f"google_data_{sheet_name.lower().replace(' ', '_')}"
            
            with st.expander(sheet_name):
                try:
                    sheet_data = load_sheet_data(sheet_name, sheet_range, session_key)
                    
                    if not sheet_data.empty:
                        st.dataframe(sheet_data, use_container_width=True)
                        st.caption(f"Loaded {len(sheet_data)} items")
                    else:
                        st.warning(f"No data available for {sheet_name}")
                        
                except Exception as e:
                    st.error(f"Error loading {sheet_name}: {str(e)}")
        
        # Refresh button
        if st.button("🔄 Refresh Data", type="secondary"):
            clear_session_state()
            st.rerun()
        
        # Display total product codes loaded
        if st.session_state.google_product_codes:
            st.success(f"Total products loaded: {len(st.session_state.google_product_codes)}")
    
    # Main content area
    st.header("📈 Reorder Analysis")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Excel Inventory File",
        type=['xlsx', 'xls'],
        help="Upload your inventory Excel file to analyze reorder requirements"
    )
    
    if uploaded_file is not None:
        with st.spinner("Processing inventory file..."):
            try:
                # Load and process data
                raw_data = load_excel_data(uploaded_file)
                if raw_data is not None:
                    inventory_data = extract_inventory_data(raw_data)
                    
                    # Extract date range
                    date_range = extract_date_range(raw_data)
                    st.session_state.date_range = date_range
                    
                    # Get reorder items
                    reorder_data = get_reorder_items(inventory_data)
                    st.session_state.reorder_data = reorder_data
                    
                    # Success message
                    st.success(f"✅ Processed {len(inventory_data)} inventory items")
                    
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
    
    # Display results
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display date range
        if 'date_range' in st.session_state and st.session_state.date_range:
            date_range = st.session_state.date_range
            if len(date_range) >= 2:
                st.info(f"📅 Period: {date_range[0]} to {date_range[1]}")
            elif len(date_range) == 1:
                st.info(f"📅 Date: {date_range[0]}")
    
    with col2:
        # Display summary stats
        if 'reorder_data' in st.session_state and not st.session_state.reorder_data.empty:
            reorder_count = len(st.session_state.reorder_data)
            st.metric("Items Requiring Reorder", reorder_count)
    
    # Display reorder table
    if 'reorder_data' in st.session_state and not st.session_state.reorder_data.empty:
        st.subheader("🛒 Items Requiring Reorder")
        
        # Add order status
        reorder_with_status = add_order_status(
            list(st.session_state.google_product_codes),
            st.session_state.reorder_data
        )
        
        # Display the table with better formatting
        st.dataframe(
            reorder_with_status,
            use_container_width=True,
            column_config={
                "Product Code": st.column_config.TextColumn("Product Code", width="medium"),
                "Unit Sold": st.column_config.NumberColumn("Units Sold", format="%d"),
                "Balance Stock": st.column_config.NumberColumn("Balance Stock", format="%d"),
                "Ordered": st.column_config.TextColumn("Order Status", width="small")
            }
        )
        
        # Summary by order status
        if 'Ordered' in reorder_with_status.columns:
            status_counts = reorder_with_status['Ordered'].value_counts()
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Yes' in status_counts:
                    st.success(f"✅ Already Ordered: {status_counts['Yes']}")
            
            with col2:
                if 'No' in status_counts:
                    st.warning(f"⏳ Needs Ordering: {status_counts['No']}")
    
    elif 'reorder_data' in st.session_state:
        st.info("📋 No items currently require reordering")
    
    else:
        st.info("📁 Please upload an Excel file to begin analysis")

if __name__ == "__main__":
    main()