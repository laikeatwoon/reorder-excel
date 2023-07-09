# This app will read a csv file and display the data in a dataframe
# the csv file is read from streamlit upload file
# the csv file is then converted to a dataframe
# we will extract the product code, unit sold and balance stock from the dataframe
# we will store the new information into a new dataframe
# the dataframe is then displayed in a streamlit table
# the dataframe is saved in the session state


# import libraries
import streamlit as st
import pandas as pd


# This function will extract data from dataframe and return a dataframe
def extract_data(df):

        # Create a New Data with Columns with Information
    new_df = df.loc[:,['Unnamed: 1', 'Unnamed: 40', 'Unnamed: 61']]

    # Drop rows with empty data
    new_df = new_df.dropna()

    # rename columns
    new_df = new_df.rename(columns={'Unnamed: 1': 'Product Code'})
    new_df = new_df.rename(columns={'Unnamed: 40': 'Unit Sold'})
    new_df = new_df.rename(columns={'Unnamed: 61': 'Balance Stock'})
    
    # convert unit sold and balance stock to integer
    new_df['Unit Sold'] = new_df['Unit Sold'].astype(int).abs()
    new_df['Balance Stock'] = new_df['Balance Stock'].astype(int)

    # reindex new dataframe
    new_df = new_df.reset_index(drop=True)

    return new_df

# this function will extract the top 50 Unit Sold from dataframe and return a dataframe
def extract_top50(df):
    top50_df = df.sort_values(by=['Unit Sold'], ascending=False).head(50)
    top50_df = top50_df.reset_index(drop=True)
    return top50_df

# this function will extract the top 50 Unit Sold from dataframe and return a dataframe
def extract_top200(df):
    top200_df = df.sort_values(by=['Unit Sold'], ascending=False).head(200)
    top200_df = top200_df.reset_index(drop=True)
    return top200_df

# this function will extract Zero Unit Sold from dataframe and return a dataframe
def extract_deadstock(df):
    deadstock_df = df.query('`Unit Sold` == 0')
    deadstock_df = deadstock_df.reset_index(drop=True)
    return deadstock_df



# Define Main Function
def main():

    st.set_page_config(page_title="Stock App", layout="wide")

    st.title("Stock App")

    #create 2 columns
    col1, col2 = st.columns([2, 3])

    #create a blank dataframe in session state
    if 'df' not in st.session_state:
        # create a empty dataframe with 3 columns named Product Code, Unit Sold and Balance Stock
        st.session_state.df = pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])

    if 'df_display' not in st.session_state:
        # create a empty dataframe with 3 columns named Product Code, Unit Sold and Balance Stock
        st.session_state.df_display = pd.DataFrame(columns=['Product Code', 'Unit Sold', 'Balance Stock'])    
    
    #create a blank uploaded_file in session state
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None

    #create download file name in session state
    if 'download_csv' not in st.session_state:
        st.session_state.download_csv = "stock.csv"



    with col1:
        
        # create a button to manupulate the dataframe
        if st.button("All Products"):
            df = st.session_state.df
            st.session_state.df_display = df
            st.session_state.download_csv = "stock.csv"

        if st.button("Top50 Hot Selling Products"):
            df = st.session_state.df
            df = extract_top50(df)
            st.session_state.df_display = df
            st.session_state.download_csv = "top50.csv"

        if st.button("Top200 Hot Selling Products"):
            df = st.session_state.df
            df = extract_top200(df)
            st.session_state.df_display = df
            st.session_state.download_csv = "top200.csv"

        if st.button("Dead Stock Products"):
            df = st.session_state.df
            df = extract_deadstock(df)
            st.session_state.df_display = df
            st.session_state.download_csv = "deadstock.csv"

        # create a button to refresh the page
        # clear all the session state
        if st.button("Refresh"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.experimental_rerun()



    with col2:

        if st.session_state.uploaded_file is None:
            # create a upload file button
            uploaded_file = st.file_uploader("Choose a Excel file", type="xlsx")
            
            if uploaded_file:
                try:
                    # read the file
                    df = pd.read_excel(uploaded_file)
                    
                    # extract data from dataframe
                    df = extract_data(df)
                    
                    # save the dataframe in session state
                    st.session_state.df = df

                    # save uploaded file in session state
                    st.session_state.uploaded_file = uploaded_file

                    # save the display dataframe in session state
                    st.session_state.df_display = df
                    
                except Exception as e:
                    st.warning("The file is not in the correct format.")
                    st.write(e)


        # this is to display the number of rows in the dataframe
        st.title("Number of Items: " + str(st.session_state.df_display.shape[0]))

        # use streamlit to download the dataframe as csv file
        csv = st.session_state.df_display.to_csv(index=False)
        filename = st.session_state.download_csv
        st.download_button("Press to Download", csv, filename, "text/csv", key='download-csv')

        # display the dataframe in a table
        st.table(st.session_state.df_display)

       


       



if __name__ == "__main__":
    main()