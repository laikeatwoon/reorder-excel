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
  
#Load Excel File and print the error message from the read_excel function  
def load_data(uploaded_file):
  try:
    data = pd.read_excel(uploaded_file)
    return data
  except Exception as e:
    st.write(e)
    return None



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

  # The keyfile is a dictionary, so we can access the individual keys
  # by using the keyfile_dic variable we just created.
  keyfile_dic = st.secrets["keyfile"]

  # Initialize the credentials variable.
  creds = None
  
  # Create credentials using the keyfile dictionary.
  creds = service_account.Credentials.from_service_account_info(keyfile_dic)

# Build the service variable using the credentials we just created.
  service = build('sheets', 'v4', credentials=creds)

  # Call the Sheets API
  sheet = service.spreadsheets()
  result = sheet.values().get(spreadsheetId=st.secrets["SAMPLE_SPREADSHEET_ID"],
                              range=sheet_name_range).execute()
  
  # Get the data from the Google Sheet
  data = result.get('values', [])
  headers = data.pop(0)

  # If there are no values in the Google Sheet, create an empty list
  data.append([''] * len(headers))

  # Convert the data into a Pandas dataframe
  df = pd.DataFrame(data, columns=headers)

  # Drop the last row if it is empty
  df.drop(df.tail(1).index, inplace=True)

  # Drop rows that are entirely empty
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
# ### A function compare a list of product code with a dataframe of product code
# ### and return a dataframe with a new column name Ordered
# ### The value of the new column is Yes or No
# ### Yes means the product code is in the list
# ### No means the product code is not in the list
def add_ordered_column(product_code_list, df):
  # Create a copy of the slice of the dataframe and then add the new column name Ordered without SettingWithCopyWarning
  new_df = df.copy()
  new_df.loc[:, 'Ordered'] = ''

  # Loop through the product_code_list
  for i in product_code_list:
      # Check if the product code is in the dataframe
      if i in new_df['Product Code'].values:
          # If the product code is in the dataframe, change the value of the Ordered column to Yes
          new_df.loc[df['Product Code'] == i, 'Ordered'] = 'Yes'
          
      else:
          # If the product code is not in the dataframe, change the value of the Ordered column to No
          new_df.loc[df['Product Code'] == i, 'Ordered'] = 'No'

  return new_df

# %% [markdown]
# ### Main Function

# %%
def main():

  st.set_page_config(layout="wide")
  
  # This code displays the title of the app
  st.title("Reorder App")

  #create 2 columns
  col1, col2 = st.columns([2, 3])
  
  #create a empty google_data_product_code list in a session state
  if 'google_data_product_list' not in st.session_state:
    st.session_state.google_data_product_list = []
 
  with col1:
    
    with st.expander("DF Items"):

      try:
        if 'google_data_df' not in st.session_state:
          #extract data from google sheet
          google_data = extract_google_sheet("Loose Cargo!A1:C70")
          st.session_state.google_data_df = google_data
          #extract product code from google_data and add into google_data_product_list
          for i in google_data['Product Code']:
            st.session_state.google_data_product_list.append(i)
        else: 
          google_data = st.session_state.google_data_df
        
        st.dataframe(google_data, use_container_width=True)
      
      except Exception as e:
        st.warning("Not able to load Google Sheet.")  
    
    with st.expander("Shandong Items"):
      try:

        if 'google_data_sd' not in st.session_state:
          #extract data from google sheet
          google_data = extract_google_sheet("Shandong!A1:C70")
          st.session_state.google_data_sd = google_data
          #extract product code from google_data and add into google_data_product_list
          for i in google_data['Product Code']:
            st.session_state.google_data_product_list.append(i)
        else:
          google_data = st.session_state.google_data_sd

        st.dataframe(google_data, use_container_width=True)

      except Exception as e:
        st.warning("Not able to load Google Sheet.") 

    with st.expander("Taiwan Glass"):
      try:
        
        if 'google_data_tw' not in st.session_state:
          #extract data from google sheet
          google_data = extract_google_sheet("Taiwan!A1:C70")
          st.session_state.google_data_tw = google_data
          #extract product code from google_data and add into google_data_product_list
          for i in google_data['Product Code']:
            st.session_state.google_data_product_list.append(i)
        else:
          google_data = st.session_state.google_data_tw
          
        st.dataframe(google_data, use_container_width=True)

      except Exception as e:
        st.warning("Not able to load Google Sheet.") 

    with st.expander("Lug Cap"):
      try:

        if 'google_data_lc' not in st.session_state:
          #extract data from google sheet
          google_data = extract_google_sheet("Lug Cap!A1:C70")
          st.session_state.google_data_lc = google_data
          #extract product code from google_data and add into google_data_product_list
          for i in google_data['Product Code']:
            st.session_state.google_data_product_list.append(i)
        else:
          google_data = st.session_state.google_data_lc

        st.dataframe(google_data, use_container_width=True)
        
      except Exception as e:
        st.warning("Not able to load Google Sheet.") 

    ## A button to remove certain variable in the session state and refresh the page
    if st.button("Refresh"):
      if 'google_data_df' in st.session_state:
        del st.session_state.google_data_df
      if 'google_data_sd' in st.session_state:
        del st.session_state.google_data_sd
      if 'google_data_tw' in st.session_state:
        del st.session_state.google_data_tw
      if 'google_data_lc' in st.session_state:
        del st.session_state.google_data_lc
      if 'google_data_product_list' in st.session_state:
        del st.session_state.google_data_product_list
      st.experimental_rerun()
    
       
  with col2:
    st.header("Please Order Stocks Display in the Table")
    uploaded_file = st.file_uploader("Choose a Excel file", type="xlsx")  
    
    if uploaded_file:
      try:
        #load data
        data = load_data(uploaded_file)
        new_data = extract_data(data)
        
        #extract date
        st.session_state.date_list = extract_date(data)

        #extract reorder data
        st.session_state.reorder_data = extract_reorder_data(new_data)
        
      except Exception as e:
        st.warning("The file is not in the correct format.")


    #display date list if it is in the session state
    if 'date_list' in st.session_state:
        if len(st.session_state.date_list) == 2:
          st.write("From ", st.session_state.date_list[0], " To ", st.session_state.date_list[1])

    #display reorder data if it is in the session state
    if 'reorder_data' in st.session_state:
        #add ordered column
        st.session_state.reorder_data = add_ordered_column(
          st.session_state.google_data_product_list, st.session_state.reorder_data)
        
        st.table(st.session_state.reorder_data)

  

if __name__ == "__main__":
    main()




