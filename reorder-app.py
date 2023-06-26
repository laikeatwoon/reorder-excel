import streamlit as st
import pandas as pd

def load_data(uploaded_file):
  data = pd.read_csv(uploaded_file)
  return data
  
def main():
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file:
  data = load_data(uploaded_file)
  st.write(data)



if __name__ == "__main__":
    main()

