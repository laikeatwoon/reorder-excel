import streamlit as st
import pandas as pd
import openpyxl


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

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

  
def main():
  uploaded_file = st.file_uploader("Choose a Excel file", type="xlsx")
  if uploaded_file:
    data = load_data(uploaded_file)
    new_data = extract_data(data)
    st.write(new_data)



if __name__ == "__main__":
    main()

