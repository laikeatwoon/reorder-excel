# %% [markdown]
# # Build a web application to extract data from an excel file

# %% [markdown]
# ### Import Libraries

# %%
import streamlit as st
import pandas as pd

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


# %%
def extract_data_V2(data):
  
  new_data = pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
  i = 0
  for index, row in data.iterrows():
    product_code = data.at[index, 'Unnamed: 1']
    unit_sold = data.at[index, 'Unnamed: 40']
    balance_stock = data.at[index, 'Unnamed: 61']

    if isinstance(product_code, str) and isInt(unit_sold):
        new_data.loc[i] = [product_code, abs(unit_sold), balance_stock]
        i = i + 1

  #Convert the data from Float to Int      
  new_data[['Unit Sold', 'Balance Stock']] = new_data[['Unit Sold', 'Balance Stock']].astype(int)
  
  return new_data

def extract_reorder_data(new_data):
  reorder_data = new_data.query('`Unit Sold` >= `Balance Stock`')
  return reorder_data

# %% [markdown]
# ### Main Function

# %%
def main():
  st.header("Please Order Stocks Display in the Table")
  uploaded_file = st.file_uploader("Choose a Excel file", type="xlsx")
  
  if uploaded_file:
    try:
      data = load_data(uploaded_file)
      new_data = extract_data(data)
      reorder_data = extract_reorder_data(new_data)
      st.table(reorder_data)
    except Exception as e:
        st.warning("The file is not in the correct format.")

if __name__ == "__main__":
    main()


