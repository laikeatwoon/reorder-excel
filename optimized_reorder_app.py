import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
import re
import logging
import io
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration constants
class Config:
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
    
    # Excel processing settings
    MAX_ROWS = 30000
    DATE_PATTERNS = [r'\d{1,2}/\d{1,2}/\d{2,4}', r'\d{4}-\d{2}-\d{2}']
    
    # Reorder calculation settings
    REORDER_THRESHOLD_RATIO = 1.0  # When sold >= stock * ratio
    MIN_REORDER_QUANTITY = 1
    
    # UI Settings
    PAGE_TITLE = "Inventory Reorder App"
    PAGE_ICON = "📦"
    FOOTER_TEXT = "🔧 Enhanced inventory management system with improved performance and usability"
    
    # Export settings
    EXPORT_INCLUDE_TIMESTAMP = True

@st.cache_data
def load_excel_data(uploaded_file) -> Optional[pd.DataFrame]:
    """Load Excel file with enhanced error handling and validation."""
    try:
        logger.info(f"Loading Excel file: {uploaded_file.name}")
        
        # Read Excel file with error handling for different formats
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        if df.empty:
            st.warning("⚠️ Excel file is empty")
            return None
            
        if len(df) > Config.MAX_ROWS:
            st.warning(f"⚠️ File has {len(df)} rows. Processing first {Config.MAX_ROWS} rows.")
            df = df.head(Config.MAX_ROWS)
            
        logger.info(f"Successfully loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
        return df
        
    except Exception as e:
        error_msg = f"Error loading Excel file: {str(e)}"
        logger.error(error_msg)
        st.error(f"❌ {error_msg}")
        
        # Provide helpful suggestions
        if "No such file" in str(e):
            st.info("💡 Make sure the file is properly uploaded")
        elif "Excel" in str(e) or "openpyxl" in str(e):
            st.info("💡 Ensure the file is a valid Excel file (.xlsx or .xls)")
            
        return None

def validate_excel_structure(data: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate if Excel file has the expected structure."""
    required_cols = list(Config.COLUMN_MAPPING.keys())
    missing_cols = [col for col in required_cols if col not in data.columns]
    
    if missing_cols:
        return False, missing_cols
    return True, []

def extract_inventory_data(data: pd.DataFrame) -> pd.DataFrame:
    """Extract and clean inventory data from Excel with enhanced validation."""
    if data is None or data.empty:
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    # Validate Excel structure
    is_valid, missing_cols = validate_excel_structure(data)
    if not is_valid:
        st.error(f"❌ Missing required columns: {missing_cols}")
        st.info("💡 Expected columns: " + ", ".join(Config.COLUMN_MAPPING.keys()))
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    required_cols = list(Config.COLUMN_MAPPING.keys())
    new_data = data[required_cols].copy()
    
    # Drop rows with all NaN values
    initial_rows = len(new_data)
    new_data = new_data.dropna(how='all')
    
    if new_data.empty:
        st.warning("⚠️ No valid data rows found after cleaning")
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    # Log data cleaning stats
    if initial_rows != len(new_data):
        logger.info(f"Removed {initial_rows - len(new_data)} empty rows")
    
    # Rename columns
    new_data = new_data.rename(columns=Config.COLUMN_MAPPING)
    
    # Enhanced data cleaning and validation
    try:
        # Clean and convert Unit Sold
        new_data['Unit Sold'] = pd.to_numeric(
            new_data['Unit Sold'], errors='coerce'
        ).fillna(0).astype(int).abs()
        
        # Clean and convert Balance Stock
        new_data['Balance Stock'] = pd.to_numeric(
            new_data['Balance Stock'], errors='coerce'
        ).fillna(0).astype(int)
        
        # Remove rows where Product Code is NaN or empty
        initial_count = len(new_data)
        new_data = new_data.dropna(subset=['Product Code'])
        new_data = new_data[new_data['Product Code'].astype(str).str.strip() != '']
        
        if initial_count != len(new_data):
            logger.info(f"Removed {initial_count - len(new_data)} rows with invalid Product Codes")
        
        # Data quality checks
        negative_stock = (new_data['Balance Stock'] < 0).sum()
        if negative_stock > 0:
            st.warning(f"⚠️ Found {negative_stock} items with negative stock")
            
        zero_sold = (new_data['Unit Sold'] == 0).sum()
        if zero_sold > 0:
            logger.info(f"Found {zero_sold} items with zero units sold")
        
    except Exception as e:
        error_msg = f"Error processing data types: {str(e)}"
        logger.error(error_msg)
        st.error(f"❌ {error_msg}")
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    logger.info(f"Successfully processed {len(new_data)} inventory items")
    return new_data

def get_reorder_items(inventory_data: pd.DataFrame) -> pd.DataFrame:
    """Extract items that need reordering."""
    if inventory_data.empty:
        return pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
    
    reorder_data = inventory_data[inventory_data['Unit Sold'] >= inventory_data['Balance Stock']].copy()
    return reorder_data.reset_index(drop=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_google_sheet_data(sheet_range: str, _force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """Fetch data from Google Sheets with enhanced caching and error handling.
    
    Args:
        sheet_range: The range to fetch from the sheet
        _force_refresh: Force refresh parameter (underscore prefix to exclude from cache key)
    """
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
    """Extract date range from the last row of data with enhanced pattern matching."""
    if data is None or data.empty:
        return []
    
    try:
        # Get the last row and convert to string
        last_row_text = str(data.iloc[-1, 0]) if not data.empty else ""
        
        # Try multiple date patterns
        dates = []
        for pattern in Config.DATE_PATTERNS:
            matches = re.findall(pattern, last_row_text)
            dates.extend(matches)
            
        # Remove duplicates while preserving order
        unique_dates = []
        for date in dates:
            if date not in unique_dates:
                unique_dates.append(date)
        
        logger.info(f"Extracted dates: {unique_dates[:2]}")
        return unique_dates[:2]  # Return max 2 dates
        
    except Exception as e:
        error_msg = f"Error extracting dates: {str(e)}"
        logger.warning(error_msg)
        st.warning(f"⚠️ {error_msg}")
        return []

def create_export_data(df: pd.DataFrame, include_timestamp: bool = True) -> pd.DataFrame:
    """Prepare data for export with optional timestamp."""
    export_df = df.copy()
    
    if include_timestamp:
        export_df['Export_Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    return export_df

def generate_csv_download(df: pd.DataFrame, filename: str) -> str:
    """Generate CSV data for download."""
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()

def generate_excel_download(df: pd.DataFrame) -> bytes:
    """Generate Excel data for download."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reorder_List')
    return output.getvalue()

def add_order_status(product_list: List[str], df: pd.DataFrame) -> pd.DataFrame:
    """Add order status column to dataframe."""
    if df.empty:
        return df
    
    df_copy = df.copy()
    df_copy['Ordered'] = df_copy['Product Code'].isin(product_list).map({
        True: '✓ Ordered', False: '❌ Pending'
    })
    
    return df_copy

def initialize_session_state():
    """Initialize session state variables."""
    if 'google_product_codes' not in st.session_state:
        st.session_state.google_product_codes = set()

def load_sheet_data(sheet_name: str, sheet_range: str, session_key: str, force_refresh: bool = False):
    """Load and cache Google Sheet data."""
    if session_key not in st.session_state or force_refresh:
        with st.spinner(f"Loading {sheet_name}..."):
            sheet_data = fetch_google_sheet_data(sheet_range, _force_refresh=force_refresh)
            if sheet_data is not None:
                st.session_state[session_key] = sheet_data
                # Add product codes to the set (clear and rebuild if refreshing)
                if 'Product Code' in sheet_data.columns:
                    product_codes = sheet_data['Product Code'].dropna().tolist()
                    if force_refresh:
                        # If refreshing, we'll rebuild the entire product codes set later
                        pass
                    else:
                        st.session_state.google_product_codes.update(product_codes)
            else:
                st.session_state[session_key] = pd.DataFrame()
    
    return st.session_state[session_key]

def clear_google_sheets_data():
    """Clear only Google Sheets related session state variables, preserving Excel data."""
    google_sheets_keys = [
        'google_data_df_items', 'google_data_shandong_items', 'google_data_taiwan_glass', 'google_data_lug_cap',
        'google_product_codes'
    ]
    
    for key in google_sheets_keys:
        if key in st.session_state:
            del st.session_state[key]

def clear_all_session_state():
    """Clear all session state variables including Excel data."""
    keys_to_clear = [
        'google_data_df_items', 'google_data_shandong_items', 'google_data_taiwan_glass', 'google_data_lug_cap',
        'google_product_codes', 'date_range', 'reorder_data', 'excel_data', 'inventory_data'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def render_sidebar():
    """Render the sidebar with Google Sheets data and controls."""
    with st.sidebar:
        st.header("📊 Inventory Sources")
        
        # Load all sheet data
        for sheet_name, sheet_range in Config.SHEET_CONFIGS.items():
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
                    error_msg = f"Error loading {sheet_name}: {str(e)}"
                    logger.error(error_msg)
                    st.error(error_msg)
        
        # Refresh controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", type="secondary"):
                handle_data_refresh()
        
        with col2:
            if st.button("🗑️ Clear Cache", type="secondary", help="Force clear all caches"):
                handle_force_cache_clear()
        
        # Display total product codes loaded and cache status
        if st.session_state.google_product_codes:
            st.success(f"Total products loaded: {len(st.session_state.google_product_codes)}")
            st.caption("💡 Use 'Refresh Data' to get latest Google Sheets changes")
        else:
            st.info("🔄 Click 'Refresh Data' to load Google Sheets data")

def handle_data_refresh():
    """Handle the refresh of Google Sheets data with proper cache clearing."""
    try:
        # Clear Streamlit's cache for Google Sheets data
        fetch_google_sheet_data.clear()
        logger.info("Cleared Streamlit cache for Google Sheets data")
        
        # Clear session state Google Sheets data
        clear_google_sheets_data()
        
        # Force refresh all Google Sheets
        for sheet_name, sheet_range in Config.SHEET_CONFIGS.items():
            session_key = f"google_data_{sheet_name.lower().replace(' ', '_')}"
            load_sheet_data(sheet_name, sheet_range, session_key, force_refresh=True)
        
        # Rebuild the product codes set after refreshing all sheets
        st.session_state.google_product_codes = set()
        for sheet_name in Config.SHEET_CONFIGS.keys():
            session_key = f"google_data_{sheet_name.lower().replace(' ', '_')}"
            if session_key in st.session_state:
                sheet_data = st.session_state[session_key]
                if 'Product Code' in sheet_data.columns:
                    product_codes = sheet_data['Product Code'].dropna().tolist()
                    st.session_state.google_product_codes.update(product_codes)
        
        # Update reorder data with new order status if Excel data exists
        if 'reorder_data' in st.session_state and not st.session_state.reorder_data.empty:
            st.session_state.reorder_data_with_status = add_order_status(
                list(st.session_state.google_product_codes),
                st.session_state.reorder_data
            )
        
        st.success("✅ Google Sheets data refreshed! Cache cleared.")
        logger.info("Successfully refreshed Google Sheets data")
        st.rerun()
        
    except Exception as e:
        error_msg = f"Error refreshing Google Sheets data: {str(e)}"
        logger.error(error_msg)
        st.error(f"❌ {error_msg}")

def handle_force_cache_clear():
    """Force clear all caches and data."""
    try:
        # Clear all Streamlit caches
        st.cache_data.clear()
        logger.info("Cleared all Streamlit caches")
        
        # Clear all session state
        clear_all_session_state()
        logger.info("Cleared all session state")
        
        st.success("🗑️ All caches and data cleared! Please re-upload your files.")
        st.info("💡 This forces a complete refresh - you'll need to re-upload your Excel file.")
        st.rerun()
        
    except Exception as e:
        error_msg = f"Error clearing caches: {str(e)}"
        logger.error(error_msg)
        st.error(f"❌ {error_msg}")

def handle_file_upload():
    """Handle Excel file upload and processing."""
    uploaded_file = st.file_uploader(
        "Upload Excel Inventory File",
        type=['xlsx', 'xls'],
        help="Upload your inventory Excel file to analyze reorder requirements"
    )
    
    if uploaded_file is not None:
        # Store uploaded file info to detect changes
        file_info = {
            'name': uploaded_file.name,
            'size': uploaded_file.size,
            'type': uploaded_file.type
        }
        
        # Check if this is a new file or if we should reprocess
        should_process = (
            'excel_file_info' not in st.session_state or 
            st.session_state.excel_file_info != file_info or
            'inventory_data' not in st.session_state
        )
        
        if should_process:
            process_uploaded_file(uploaded_file, file_info)
        else:
            # File already processed, just show success message
            if 'inventory_data' in st.session_state:
                st.info(f"✅ Using previously processed file: {uploaded_file.name}")
                st.caption(f"📊 {len(st.session_state.inventory_data)} inventory items loaded")
    
    return uploaded_file is not None

def process_uploaded_file(uploaded_file, file_info):
    """Process the uploaded Excel file."""
    with st.spinner("Processing inventory file..."):
        try:
            # Load and process data
            raw_data = load_excel_data(uploaded_file)
            if raw_data is not None:
                # Store the processed data in session state
                st.session_state.excel_file_info = file_info
                st.session_state.raw_excel_data = raw_data
                
                inventory_data = extract_inventory_data(raw_data)
                st.session_state.inventory_data = inventory_data
                
                # Extract date range
                date_range = extract_date_range(raw_data)
                st.session_state.date_range = date_range
                
                # Get reorder items
                reorder_data = get_reorder_items(inventory_data)
                st.session_state.reorder_data = reorder_data
                
                # Success message
                st.success(f"✅ Processed {len(inventory_data)} inventory items")
                logger.info(f"Successfully processed {uploaded_file.name} with {len(inventory_data)} items")
                
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")

def render_analysis_results():
    """Render the main analysis results and tables."""
    # Always update the reorder data with current order status when Google Sheets data changes
    if ('reorder_data' in st.session_state and 
        not st.session_state.reorder_data.empty and 
        st.session_state.google_product_codes):
        
        # Update reorder data with current order status
        st.session_state.reorder_data_with_status = add_order_status(
            list(st.session_state.google_product_codes),
            st.session_state.reorder_data
        )
    
    # Display results summary
    render_results_summary()
    
    # Display reorder table with export options
    render_reorder_table()

def render_results_summary():
    """Render the results summary section."""
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

def render_reorder_table():
    """Render the reorder table with export functionality."""
    if 'reorder_data' in st.session_state and not st.session_state.reorder_data.empty:
        st.subheader("🛒 Items Requiring Reorder")
        
        # Use the updated reorder data with current order status
        display_data = st.session_state.get('reorder_data_with_status', st.session_state.reorder_data)
        
        # If we don't have the updated version, create it
        if 'reorder_data_with_status' not in st.session_state:
            display_data = add_order_status(
                list(st.session_state.google_product_codes),
                st.session_state.reorder_data
            )
        
        # Display the table with better formatting
        column_config = {
            "Product Code": st.column_config.TextColumn("Product Code", width="medium"),
            "Unit Sold": st.column_config.NumberColumn("Units Sold", format="%d"),
            "Balance Stock": st.column_config.NumberColumn("Balance Stock", format="%d"),
            "Ordered": st.column_config.TextColumn("Order Status", width="small")
        }
        
        # Add reorder quantity column if it exists
        if 'Reorder Qty' in display_data.columns:
            column_config["Reorder Qty"] = st.column_config.NumberColumn("Suggested Reorder Qty", format="%d")
        
        st.dataframe(
            display_data,
            use_container_width=True,
            column_config=column_config
        )
        
        # Export options
        render_export_options(display_data)
        
        # Summary by order status
        render_order_status_summary(display_data)
        
    elif 'reorder_data' in st.session_state:
        st.info("📋 No items currently require reordering")
    
    else:
        st.info("📁 Please upload an Excel file to begin analysis")

def render_export_options(data: pd.DataFrame):
    """Render export options for the reorder data."""
    if data.empty:
        return
    
    st.subheader("📥 Export Options")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV Export
        export_data = create_export_data(data, Config.EXPORT_INCLUDE_TIMESTAMP)
        csv_data = generate_csv_download(export_data, "reorder_list")
        st.download_button(
            label="📄 Download CSV",
            data=csv_data,
            file_name=f"reorder_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Excel Export
        excel_data = generate_excel_download(export_data)
        st.download_button(
            label="📈 Download Excel",
            data=excel_data,
            file_name=f"reorder_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col3:
        # Summary stats
        st.metric("Total Items", len(data))

def render_order_status_summary(data: pd.DataFrame):
    """Render summary statistics by order status."""
    if 'Ordered' in data.columns:
        status_counts = data['Ordered'].value_counts()
        col1, col2 = st.columns(2)
        
        with col1:
            ordered_count = status_counts.get('✓ Ordered', 0)
            if ordered_count > 0:
                st.success(f"✅ Already Ordered: {ordered_count}")
        
        with col2:
            pending_count = status_counts.get('❌ Pending', 0)
            if pending_count > 0:
                st.warning(f"⏳ Needs Ordering: {pending_count}")

def main():
    """Main application function - now modular and clean."""
    st.set_page_config(
        page_title=Config.PAGE_TITLE,
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon=Config.PAGE_ICON
    )
    
    st.title("📦 Inventory Reorder Application")
    st.markdown("*Analyze inventory data and identify items requiring reorder*")
    
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar with Google Sheets data
    render_sidebar()
    
    # Main content area
    st.header("📈 Reorder Analysis")
    
    # Handle file upload and processing
    file_uploaded = handle_file_upload()
    
    # Render analysis results if data is available
    if file_uploaded or ('inventory_data' in st.session_state and 
                        not st.session_state.get('inventory_data', pd.DataFrame()).empty):
        render_analysis_results()
    
    # Footer
    st.markdown("---")
    st.caption(Config.FOOTER_TEXT)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"❌ Application Error: {str(e)}")
        st.info("💡 Please refresh the page and try again")