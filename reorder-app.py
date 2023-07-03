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
    print(e)
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
# ### A function compare a list of product code with a dataframe of product code
# ### and return a dataframe with a new column name Ordered
# ### The value of the new column is Yes or No
# ### Yes means the product code is in the list
# ### No means the product code is not in the list
def compare_product_code(product_code_list, df):
  # Create a new column name Ordered
  df['Ordered'] = ''

  # Loop through the product_code_list
  for i in product_code_list:
      # Check if the product code is in the dataframe
      if i in df['Product Code'].values:
          # If the product code is in the dataframe, change the value of the Ordered column to Yes
          df.loc[df['Product Code'] == i, 'Ordered'] = 'Yes'
          
      else:
          # If the product code is not in the dataframe, change the value of the Ordered column to No
          df.loc[df['Product Code'] == i, 'Ordered'] = 'No'

  return df

# %% [markdown]
# ### Main Function

# %%
def main():
  
  # This code displays the title of the app
  st.title("Reorder App")

  st.set_page_config(layout="wide")

  #create 2 columns
  col1, col2 = st.columns([2, 3])
  
  #create a empty google_data_product_code list
  google_data_product_list = []


  with col1:

    with st.expander("DF Items"):
      
      try:

        #extract data from google sheet
        google_data = extract_google_sheet("Loose Cargo!A1:C70")
        st.dataframe(google_data, use_container_width=True)

      # extract product code from google_data and add into google_data_product_list
        for i in google_data['Product Code']:
          google_data_product_list.append(i)
        

      except Exception as e:
        st.warning("Not able to load Google Sheet.")  
    
    with st.expander("Shandong Items"):
      try:

        #extract data from google sheet
        google_data = extract_google_sheet("Shandong!A1:C70")
        st.dataframe(google_data, use_container_width=True)

        # extract product code from google_data and add into google_data_product_list
        for i in google_data['Product Code']:
          google_data_product_list.append(i)


      except Exception as e:
        st.warning("Not able to load Google Sheet.") 

    with st.expander("Taiwan Glass"):
      try:
        
        #extract data from google sheet
        google_data = extract_google_sheet("Taiwan!A1:C70")
        st.dataframe(google_data, use_container_width=True)

        #extract product code from google_data and add into google_data_product_list
        for i in google_data['Product Code']:
          google_data_product_list.append(i)


      except Exception as e:
        st.warning("Not able to load Google Sheet.") 

    with st.expander("Lug Cap"):
      try:
        
        #extract data from google sheet
        google_data = extract_google_sheet("Lug Cap!A1:C70")
        st.dataframe(google_data, use_container_width=True)

        #extract product code from google_data and add into google_data_product_list
        for i in google_data['Product Code']:
          google_data_product_list.append(i)
        
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
        
        #extract date
        date_list = extract_date(data)

        #check if date_list has 2 values
        if len(date_list) == 2:
          st.write("From ", date_list[0], " To ", date_list[1])

        #display reorder data
        reorder_data = extract_reorder_data(new_data)

        #compare data
        reorder_data = compare_product_code(google_data_product_list, reorder_data)

        st.table(reorder_data)

      except Exception as e:
        st.warning("The file is not in the correct format.")

if __name__ == "__main__":
    main()




