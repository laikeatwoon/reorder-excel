# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a **Streamlit inventory reorder application** that:
- Analyzes Excel inventory files to identify items needing reorder (when units sold ≥ balance stock)
- Integrates with Google Sheets API to track already ordered items
- Provides export functionality (CSV/Excel) for reorder lists
- Uses session state management for caching and performance optimization

## Core Architecture

### Main Files
- `reorder-app.py` - Original version of the Streamlit application
- `optimized_reorder_app.py` - Enhanced version with better error handling, logging, and modular structure
- `requirements.txt` - Python dependencies for the application

### Key Components
1. **Excel Data Processing** (`extract_inventory_data`)
   - Expects columns: `Unnamed: 1` (Product Code), `Unnamed: 40` (Unit Sold), `Unnamed: 61` (Balance Stock)
   - Handles data cleaning, type conversion, and validation

2. **Google Sheets Integration** (`fetch_google_sheet_data`)
   - Connects to 4 inventory sources: DF Items, Shandong Items, Taiwan Glass, Lug Cap
   - Requires Google Service Account credentials in Streamlit secrets
   - Uses caching with TTL for performance

3. **Reorder Logic** (`get_reorder_items`)
   - Identifies items where `Unit Sold >= Balance Stock`
   - Tracks order status by cross-referencing with Google Sheets data

4. **Session State Management**
   - Caches Excel data processing results
   - Maintains Google Sheets product codes for order status checking
   - Selective cache clearing (Google Sheets vs Excel data)

## Development Commands

### Running the Application
```bash
streamlit run reorder-app.py
```
or
```bash
streamlit run optimized_reorder_app.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Setting up Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Configuration Requirements

### Google Sheets API Setup
The application requires Streamlit secrets configuration:
```toml
# .streamlit/secrets.toml
SAMPLE_SPREADSHEET_ID = "your-google-sheets-id"

[keyfile]
# Google Service Account JSON credentials
type = "service_account"
project_id = "your-project"
# ... other service account fields
```

### Sheet Configuration
Sheet ranges are defined in `Config.SHEET_CONFIGS`:
- DF Items: `Loose Cargo!A1:C200`
- Shandong Items: `Shandong!A1:C200`
- Taiwan Glass: `Taiwan!A1:C200`
- Lug Cap: `Lug Cap!A1:C200`

## Code Patterns

### Error Handling
- Uses comprehensive try-catch blocks with user-friendly error messages
- Logging with Python's logging module (in optimized version)
- Graceful degradation when Google Sheets data is unavailable

### Data Processing Flow
1. Excel upload → validation → column mapping → data cleaning
2. Google Sheets fetch → caching → product code extraction
3. Reorder calculation → status checking → display/export

### Streamlit Best Practices
- Uses `@st.cache_data` for expensive operations
- Session state for maintaining data across interactions
- Modular rendering functions for UI components
- Progress indicators for long-running operations

## Known Dependencies
- streamlit>=1.28.0
- pandas>=2.0.0
- openpyxl>=3.1.0 (Excel file support)
- google-api-python-client>=2.100.0 (Google Sheets API)
- google-auth packages for authentication