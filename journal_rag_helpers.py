import re
import json
import pandas as pd
from datetime import datetime, timedelta

def read_in_journal():
    """
    I read my journal from Google sheets to stay current, but just added dummy data to show the format
    """
    return pd.read_csv("dummy_journal_data.csv")

def get_ordinal_suffix(day):
    """Return the ordinal suffix for a given day."""
    if 4 <= day <= 20 or 24 <= day <= 30:
        return "th"
    else:
        return ["st", "nd", "rd"][day % 10 - 1]

def contains_date(text):
    """
    function to see if query should be a date query or non date
    """
    # Regular expression to match a four-digit year (e.g., 2020)
    year_pattern = r'\b(19|20)\d{2}\b'
    # Regular expression to match month names (full names)
    month_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b'

    # Check if the text contains a year or a month name
    if re.search(year_pattern, text) or re.search(month_pattern, text):
        return True
    else:
        return False

def estimate_tokens(text, method="max"):
    """
    Estimate OpenAI tokens based on the given method.

    :param text: Text to estimate tokens for.
    :param method: Method to use for estimation. Can be "average", "words", "chars", "max", "min". Defaults to "max".
    :return: Estimated token count or an error message for invalid method.
    """
    # Split text into words and count them, then get the total character count
    word_count = len(text.split(" "))
    char_count = len(text)

    # Calculate tokens count based on words and characters
    tokens_count_word_est = word_count / 0.75
    tokens_count_char_est = char_count / 4.0

    # Select method of estimation
    if method == "average":
        output = (tokens_count_word_est + tokens_count_char_est) / 2
    elif method == "words":
        output = tokens_count_word_est
    elif method == "chars":
        output = tokens_count_char_est
    elif method == "max":
        output = max(tokens_count_word_est, tokens_count_char_est)
    elif method == "min":
        output = min(tokens_count_word_est, tokens_count_char_est)
    else:
        # Return invalid method message
        return "Invalid method. Use 'average', 'words', 'chars', 'max', or 'min'."

    # Convert output to integer before returning
    return int(output)

def extract_date_range(openai_client, query):
    """
    call OpenAI to get the date range
    """
    extract_prompt = """
    From the following query, identify and extract the date range mentioned in the
    query and format it as a json. Ensure to cover various time frames such as specific
    days, months, years, or combinations thereof. Output the extracted date range in a
    json structured format that includes the start and end dates. Ex.

    {
    "start_date": {"year": 2022, "month": "July", "day": 1},
    "end_date": {"year": 2022, "month": "July", "day": 31}
    }
    """

    meta_query = extract_prompt + \
    "Query:" + query + \
    "Date Range as json:"

    final_answer = openai_client.chat.completions.create(
        messages=[{"role": "user", "content": meta_query}],
        model="gpt-3.5-turbo",
        )
    return final_answer.choices[0].message.content

def extract_keywords(openai_client, query):
    """
    Call OpenAI to get keywords that would be useful to filter by (feel free to make more strict or loose)
    """
    extract_prompt = """
    From the following query, identify the keywords that would be useful to filter the journal
    entries to, and only return those keywords as a python list of strings. Identify useful
    word derivatives and abbreviations.

    Question: When did I read the book Invisible Women?

    Keyword(s): ["Invisible Women"]

    Ex. When was my graduation from UVA?

    Keyword(s): ["graduation", "graduate", "grad", "UVA", "University of Virginia"]
    """

    meta_query = extract_prompt + \
    "Question:" + query + \
    "Answer:"

    final_answer = openai_client.chat.completions.create(
        messages=[{"role": "user", "content": meta_query}],
        model="gpt-3.5-turbo",
        )
    return final_answer.choices[0].message.content

def query_to_filtered_df(openai_client, journal_query, df):
    if contains_date(journal_query):
        keywords = False
        date_range = json.loads(extract_date_range(openai_client, journal_query))
        print(date_range)
    else:
        date_range = False
        try:
            raw_keywords = extract_keywords(openai_client, journal_query)
            print(raw_keywords)
            keywords = json.loads(raw_keywords)
        except json.JSONDecodeError:
            print("Error decoding JSON for keywords.")
            return pd.DataFrame(), False
        except Exception as e:
            print(f"Unexpected error extracting keywords: {e}")
            return pd.DataFrame(), False
    if date_range:
        year, months_str = convert_json_to_year_and_months_str(date_range)
        print("Year:", year)
        print("Months:", months_str)
        # Create a boolean mask for rows with the specified year and any of the specified months
        mask = (df['Year'] == year) & (df['Month'].isin(months_str))

        # Apply the mask to filter the DataFrame
        filtered_df = df[mask]
    else:
        # Initially, try filtering with a minimum of 2 matches
        initial_filtered_df = filter_by_multiple_keywords(df, 'Entry', keywords, min_matches=2)

        # If the result has fewer than 3 rows, reduce the min_matches criteria to 1
        if len(initial_filtered_df) < 3:
            filtered_df = filter_by_multiple_keywords(df, 'Entry', keywords, min_matches=1)
        else:
            filtered_df = initial_filtered_df
    return filtered_df, date_range

def filter_by_multiple_keywords(df, column_name, keywords, min_matches=2):
    """
    Filter a DataFrame to include rows where a specified column contains 2 or more of the given keywords.

    :param df: The pandas DataFrame to filter.
    :param column_name: The name of the column to search for keywords.
    :param keywords: A list of strings, each a keyword to search for in the column.
    :param min_matches: The minimum number of keywords that must be found in a row for it to be included.
    :return: A filtered DataFrame containing only rows that match the criteria.
    """
    if not isinstance(keywords, list) or min_matches < 1:
        raise ValueError("Keywords must be a list and min_matches must be at least 1.")

    # Initialize a Series of zeros with the same index as the DataFrame, to count keyword matches per row
    matches_per_row = pd.Series(0, index=df.index)

    # Iterate over keywords and update counts
    for keyword in keywords:
        # Use str.contains to check for the keyword in the specified column, case-insensitive
        keyword_matches = df[column_name].str.contains(keyword, case=False, na=False)
        # Add the boolean Series to the count (True becomes 1, False becomes 0)
        matches_per_row += keyword_matches.astype(int)

    # Filter df to include only rows with min_matches or more keyword matches
    filtered_df = df[matches_per_row >= min_matches]

    return filtered_df

def convert_json_to_year_and_months_str(date_range_json):
    # Define a list of month names for checking the order
    months_ordered = [
        "January", "February", "March",
        "April", "May", "June",
        "July", "August", "September",
        "October", "November", "December"
    ]

    # Extract start and end year, month, and day
    start_year = date_range_json['start_date']['year']
    start_month_str = date_range_json['start_date']['month']
    start_day = date_range_json['start_date']['day']

    end_year = date_range_json['end_date']['year']
    end_month_str = date_range_json['end_date']['month']
    end_day = date_range_json['end_date']['day']

    # Check if the range spans more than one year (this function assumes it does not)
    if start_year != end_year:
        raise ValueError("The date range spans more than one year, which is not supported by this function.")

    # Find the indices of the start and end month in the ordered month list
    start_month_index = months_ordered.index(start_month_str)
    end_month_index = months_ordered.index(end_month_str)

    # Generate the list of month names between start and end, inclusively
    months = months_ordered[start_month_index:end_month_index + 1]

    return start_year, months

def create_batches_from_df(df, max_tokens=3500, method="max"):
    """
    Create batches of DataFrame rows where the sum of estimated tokens per batch does not exceed max_tokens to OpenAI

    :param df: pandas DataFrame with Year, Month, and entry columns.
    :param max_tokens: Maximum sum of estimated tokens per batch.
    :param method: Method to use for token estimation. Can be "average", "words", "chars", "max", "min".
    :return: List of batches, where each batch is a list of DataFrame rows (as dicts).
    """

    batches = []
    current_batch = []
    current_batch_token_sum = 0

    for _, row in df.iterrows():
        entry_text = row['Entry']
        estimated_tokens = estimate_tokens(entry_text, method=method)

        if current_batch_token_sum + estimated_tokens > max_tokens:
            # Current batch is full, start a new one
            batches.append(current_batch)
            current_batch = [row.to_dict()]
            current_batch_token_sum = estimated_tokens
        else:
            # Add entry to current batch
            current_batch.append(row.to_dict())
            current_batch_token_sum += estimated_tokens

    # Don't forget to add the last batch if it's not empty
    if current_batch:
        batches.append(current_batch)

    return batches

def batch_prompt_date(openai_client, journal_query, batches):
    """
    Iteratively call OpenAI with batches of journal entries, finally get a summary at the end
    """
    summaries = []
    number_of_calls = 1 # starts at 1 bc we already did one to filter the query df
    for batch in batches:

        # get batch header string
        first_day = batch[0]
        last_day = batch[-1]

        # Construct the date range string
        # Check if the range is within the same month and year
        if first_day['Year'] == last_day['Year'] and first_day['Month'] == last_day['Month']:
            date_range_str = f"{first_day['Month']} {first_day['Day']}{get_ordinal_suffix(first_day['Day'])} - {last_day['Day']}{get_ordinal_suffix(last_day['Day'])}, {first_day['Year']}:"
        else:
            # Handle the case where the range spans different months or years
            date_range_str = f"{first_day['Month']} {first_day['Day']}{get_ordinal_suffix(first_day['Day'])}, {first_day['Year']} - {last_day['Month']} {last_day['Day']}{get_ordinal_suffix(last_day['Day'])}, {last_day['Year']}:"

        # prompt each batch
        entry_str = ''
        for day in batch:
            entry_str += day['Entry'] + "\n\n"

        question_plus_entries = "Use the following context to answer this question:" + "\n\n" + \
        "Question:" + journal_query + "\n\n" + \
        "Be very specific and thorough with this context, use direct quotes where possible." + \
        "The answer might not be here, it that's the case, write 'not here'." + \
        "Context from " + date_range_str + ":" + \
        entry_str + \
        "Answer:"

        completion = openai_client.chat.completions.create(
            messages=[{"role": "user", "content": question_plus_entries}],
            model="gpt-3.5-turbo",
        )
        number_of_calls += 1

        summaries.append(date_range_str + "\n" + completion.choices[0].message.content)

    final_prompt = "Please answer this question using the context below:" + "\n\n" + \
    "Question:" + journal_query + "\n\n" + \
    "Please identify patterns and include details from the context, use direct quotes where possible" + \
    "Context:" + "\n\n" + " ".join(summaries) + \
    "\n\n" + "Answer:"

    print("Final Prompt Tokens: " + str(estimate_tokens(final_prompt)))

    final_answer = openai_client.chat.completions.create(
        messages=[{"role": "user", "content": final_prompt}],
        model="gpt-3.5-turbo",
        )
    return final_answer.choices[0].message.content, summaries, number_of_calls

def batch_prompt_date_non_date(openai_client, journal_query, batches):
    """
    Iteratively call OpenAI with batches of journal entries, finally get a summary at the end
    """
    summaries = []
    number_of_calls = 1 # starts at 1 bc we already did one to filter the query df
    for batch in batches:

        # prompt each batch
        entry_str = ''
        for day in batch:
            entry_str += day['Month'] + " " + str(day['Day']) + ", " + str(day["Year"]) + ": " + day['Entry'] + "\n\n"

        question_plus_entries = "Use the following context to answer this question:" + "\n\n" + \
        "Question:" + journal_query + "\n\n" + \
        "The context is journal entries talking about me in the first person." + \
        "Context:" + \
        entry_str + \
        "Answer:"

        completion = openai_client.chat.completions.create(
            messages=[{"role": "user", "content": question_plus_entries}],
            model="gpt-3.5-turbo",
        )
        number_of_calls += 1

        summaries.append(completion.choices[0].message.content)

    final_prompt = "Please answer this question using the context below:" + "\n\n" + \
    "Question:" + journal_query + "\n\n" + \
    "The answer might just be in one line of the context, or all the lines could be useful. Be specific" + \
    "Context:" + "\n\n" + " ".join(summaries) + \
    "\n\n" + "Answer:"

    final_answer = openai_client.chat.completions.create(
        messages=[{"role": "user", "content": final_prompt}],
        model="gpt-3.5-turbo",
        )
    return final_answer.choices[0].message.content, number_of_calls
