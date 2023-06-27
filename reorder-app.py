import streamlit as st
import pandas as pd
#import openpyxl


def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

def load_data(uploaded_file):
  data = pd.read_excel(uploaded_file)
  return data

def extract_data(data):
  new_data = pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
  i = 0
  for index, row in data.iterrows():
    product_code = data.at[index, "Unnamed: 1"]
    unit_sold = data.at[index, "Unnamed: 40"]
    balance_stock = data.at[index, "Unnamed: 61"]

    if isinstance(product_code, str) and isfloat(unit_sold):
        new_data.loc[i] = [product_code, abs(unit_sold), balance_stock]
        i = i + 1

  return new_data

def extract_reorder_data(new_data):
  reorder_data = pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])
  j = 0
  for index, row in new_data.iterrows():
    product_code = new_data.at[index, "Product Code"]
    unit_sold = new_data.at[index, "Unit Sold"]
    balance_stock = new_data.at[index, "Balance Stock"]

    if unit_sold >= balance_stock:
        reorder_data.loc[j] = [product_code, unit_sold, balance_stock]
        j = j + 1
  return reorder_data

  
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
