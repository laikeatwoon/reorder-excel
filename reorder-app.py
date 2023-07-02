# %% [markdown]
# # Build a web application to extract data from an excel file

# %% [markdown]
# ### Import Libraries

# %%
#!pip install -r requirements.txt

import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account

from googleapiclient.discovery import build
from google.oauth2 import service_account

# %% [markdown]
# ### Define sub functions


# %%
#Check is the value an Integer or not
def isInt(value):
  try:
    int(value)
    return True
  except ValueError:
    return False
  
#Load Excel File  
def load_data(uploaded_file):
  data = pd.read_excel(uploaded_file)
  return data 

# %% [markdown]
# ### Extract Data from excel file

# %%
def extract_data(data):
    # Create a New Data with Columns with Information
    new_data = data.loc[:,['Unnamed: 1', 'Unnamed: 40', 'Unnamed: 61']]

    # Drop rows with empty data
    new_data = new_data.dropna()

    # rename columns
    new_data = new_data.rename(columns={'Unnamed: 1': 'Product Code'})
    new_data = new_data.rename(columns={'Unnamed: 40': 'Unit Sold'})
    new_data = new_data.rename(columns={'Unnamed: 61': 'Balance Stock'})

    new_data['Unit Sold'] = new_data['Unit Sold'].astype(int).abs()
    new_data['Balance Stock'] = new_data['Balance Stock'].astype(int)

    return new_data


# %% [markdown]
# ### Extract Reorder Data

# %%
def extract_reorder_data(new_data):
  reorder_data = new_data.query('`Unit Sold` >= `Balance Stock`')
  return reorder_data

# %% [markdown]
# ### Extract Data from google sheet

# %%
def extract_google_sheet(sheet_name_range):

  keyfile_dic = st.secrets["keyfile"]
  creds = None
  creds = service_account.Credentials.from_service_account_info(keyfile_dic)

  service = build('sheets', 'v4', credentials=creds)

  # Call the Sheets API
  sheet = service.spreadsheets()
  result = sheet.values().get(spreadsheetId=st.secrets["SAMPLE_SPREADSHEET_ID"],
                              range=sheet_name_range).execute()
  
  data = result.get('values', [])
  headers = data.pop(0)

  df = pd.DataFrame(data, columns=headers)
  df.dropna(how='all', inplace=True)

  return df

# %% [markdown]
# ### Extract Date from dataframes
def extract_date(new_data):
  # Get the last row of new_df
  last_row = new_data.iloc[-1]

  # Get the value of the last row
  last_row_value = last_row[0]

  # I want to find all the date inside the last row value
  # Split the last row value into a list
  last_row_value_list = last_row_value.split()

  # Create a new list to store the date
  date_list = []

  # Loop through the last_row_value_list
  for i in last_row_value_list:
      # Check if the value is a date
      if '/' in i:
          # If it is a date, append it to the date_list
          date_list.append(i)

  return date_list


# %% [markdown]
# ### Main Function

# %%
def main():
  
  st.set_page_config(layout="wide")

  st.title("Reorder App")

  #write a markdown to include css style
  st.markdown(
    """
    <style>
        .streamlit-expander {
            background-color: #f5f5f5;
        }
      </style>  
    """,
    unsafe_allow_html=True,    
  )

  #create 2 columns
  col1, col2 = st.columns([2, 3])

  with col1:

    with st.expander("DF Items"):
      
      try:
        google_data = extract_google_sheet("Loose Cargo!A1:C70")
        st.dataframe(google_data, use_container_width=True)
      except Exception as e:
        st.warning("Not able to load Google Sheet.")  
    
    with st.expander("Shandong Items"):
      try:
        google_data = extract_google_sheet("Shandong!A1:C70")
        st.dataframe(google_data, use_container_width=True)
      except Exception as e:
        st.warning("Not able to load Google Sheet.") 

    with st.expander("Taiwan Glass"):
      try:
        google_data = extract_google_sheet("Taiwan!A1:C70")
        st.dataframe(google_data, use_container_width=True)
      except Exception as e:
        st.warning("Not able to load Google Sheet.") 

    with st.expander("Lug Cap"):
      try:
        google_data = extract_google_sheet("Lug Cap!A1:C70")
        st.dataframe(google_data, use_container_width=True)
      except Exception as e:
        st.warning("Not able to load Google Sheet.") 
       
  with col2:
    st.header("Please Order Stocks Display in the Table")
    uploaded_file = st.file_uploader("Choose a Excel file", type="xlsx")
    
    if uploaded_file:
      try:
        #load data
        data = load_data(uploaded_file)
        new_data = extract_data(data)
        
        date_list = extract_date(data)

        #print the length of date_list
        st.write("Date List Length: ", len(date_list))

        #check if date_list has 2 values
        if len(date_list) == 2:
          st.write("From ", date_list[0], " To ", date_list[1])


        reorder_data = extract_reorder_data(new_data)
        st.table(reorder_data)
      except Exception as e:
        st.warning("The file is not in the correct format.")

if __name__ == "__main__":
    main()




