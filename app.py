import os
import time
import re
from datetime import datetime, timedelta
import streamlit as st
import openai
import json
import pandas as pd

from journal_rag_helpers import read_in_journal, contains_date, extract_date_range, \
extract_keywords, filter_by_multiple_keywords, query_to_filtered_df, create_batches_from_df, \
batch_prompt_date, batch_prompt_date_non_date

# Set page layout to 'wide' so it looks better
st.set_page_config(layout="wide")

# Initialize OpenAI client
openai_client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

journal_df = read_in_journal()

##------------------------------ Start Streamlit App Layout ---------------------------------------------------------------------------

# app title
st.title("AI Journal Assistant")

##------------------------------ Two Columns (main part of app) -----------------------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    # Set default values
    if 'journal_query' not in st.session_state:
        st.session_state['journal_query'] = ""

    # Create text area for job description
    journal_query = st.text_area("Enter a Journal Query:", value=st.session_state['journal_query'], height=100)

    # Check if the values have changed
    if (journal_query != st.session_state['journal_query']):
        st.session_state['button_clicked'] = False  # Reset the button_clicked state
        st.session_state['journal_query'] = journal_query  # Update the session state
        # Reset other relevant variables
        st.session_state['response'] = None
        st.session_state['summaries'] = None
        st.session_state['number_of_calls'] = None
        st.session_state['start_time'] = None
        st.session_state['stop_time'] = None
        st.session_state['duration'] = None

## ----------------- QUERY BUTTON

# Use the classify button to set 'button_clicked' state
if st.button("Query") or st.session_state.get('button_clicked', False):
    st.session_state['button_clicked'] = True  # Mark the button as clicked
    st.session_state['response'] = None
    st.session_state['summaries'] = None
    st.session_state['number_of_calls'] = None
    st.session_state['start_time'] = None
    st.session_state['stop_time'] = None
    st.session_state['duration'] = None

    with st.spinner('Querying journal...'):
        if not st.session_state['start_time']:
            st.session_state['start_time'] = time.time()
            filtered_df, date_range = query_to_filtered_df(openai_client, journal_query, journal_df)
            if filtered_df.shape[0] == 0:
                number_of_calls = 1
                response = "No entries identified from query. Please adjust query and try again."
            elif filtered_df.empty:
                response = "Rephrase your query and try again. No keywords were identified."
                number_of_calls = 1
            else:
                batches = create_batches_from_df(filtered_df)
                if date_range:
                    response, summaries, number_of_calls = batch_prompt_date(openai_client, journal_query, batches)
                    st.session_state['summaries'] = summaries
                else:
                    summaries = False
                    response, number_of_calls = batch_prompt_date_non_date(openai_client, journal_query, batches)
                    st.session_state['summaries'] = None

        st.session_state['response'] = response
        st.session_state['number_of_calls'] = number_of_calls
        if not st.session_state['stop_time']:
            st.session_state['stop_time'] = time.time()

    st.session_state['duration'] = st.session_state['stop_time'] - st.session_state['start_time']

    # Reset the button_clicked state after query execution
    st.session_state['button_clicked'] = False

    ## ---------------- RIGHT COLUMN (RESULTS)
    col2.subheader("Answer:")
    answer_html = f"""
    <div style='text-align: center; padding: 10px; font-size: 16px; border-radius: 10px; color: #ffffff; background-color: #0078aa; margin-bottom: 20px;'>
        {st.session_state['response']}
    </div>
    """
    col2.markdown(answer_html, unsafe_allow_html=True)
    col2.info(f"Processed in {st.session_state['duration']:.3f} seconds.")
    col2.info(f"Called GPT {st.session_state['number_of_calls']} times for this query.")

    if st.session_state['summaries']:
        st.markdown("### Section Breakdown")
        summaries_with_breaks = "<br><br><br><br>".join(f"{summary}" for summary in st.session_state['summaries'])
        st.markdown(summaries_with_breaks, unsafe_allow_html=True)

    if not filtered_df.empty:
        st.markdown("### Filtered Dataframe")
        filtered_df['Year'] = filtered_df['Year'].astype(str)
        # Display the number of records in 'filtered_df'
        num_records = len(filtered_df)
        st.markdown(f"#### Number of Records: {num_records}")

        # Display the first few rows of 'filtered_df'
        st.markdown("#### DataFrame Preview:")
        st.dataframe(filtered_df.head())  # Display the first 5 rows
