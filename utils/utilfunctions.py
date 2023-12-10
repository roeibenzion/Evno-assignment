import pandas as pd
from dateutil import parser
import json
from tabulate import tabulate
import re
from datetime import datetime
import io

'''
This module contains utility functions used by the server and client.
'''

def validate_date_format(date):
    '''
    Validates the format of a date string in the 'yyyy-mm-dd' format.

    Parameters:
    - date (str): Date string to be validated.

    Returns:
    - bool: True if the date string has a valid format, False otherwise.

    Note:
    - Checks if the date string matches the specified pattern 'yyyy-mm-dd'.
    - Uses a regular expression to perform the initial format check.
    - Tries to parse the date using the `datetime.strptime` method to ensure it is a valid date.
    - Returns True if the date string is in a valid format, False otherwise.

    '''
    # Check if the date matches the specified pattern
    pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if not pattern.match(date):
        return False

    # Try to parse the date using datetime
    try:
        datetime.strptime(date, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def format_date(input_date):
    '''
    Formats a date string into "dd-mm-yyyy" format.

    Parameters:
    - input_date (str): Date string to be formatted.

    Returns:
    - str or None: Formatted date string in "dd-mm-yyyy" format if successful, None otherwise.

    Note:
    - Checks if the input date is already in "dd-mm-yyyy" format. If yes, returns the input as is.
    - Attempts to parse the input date using dateutil's `parser.parse` method.
    - If parsing is successful, formats the date to "dd-mm-yyyy" using `strftime`.
    - Returns the formatted date if successful, otherwise returns None.

    '''
    try:
        # Check if the date is in "dd-mm-yyyy" format
        if len(input_date.split('-')) == 3:
            return input_date

        # Try to parse the input date in ISO 8601 format
        parsed_date = parser.parse(input_date)

        # If successful, format the date to "dd-mm-yyyy"
        formatted_date = parsed_date.strftime('%d-%m-%Y')

        return formatted_date

    except ValueError as e:
        # If parsing fails, print the error for debugging
        #print("Error: Invalid date format. Details:", e)
        return None
    

def filter_dataframe_by_date(start_date, end_date):
    '''
    Returns a filter query to filter a DataFrame by a date range.

    Parameters:
    - start_date (str): Start date of the desired date range (format: "yyyy-mm-dd").
    - end_date (str): End date of the desired date range (format: "yyyy-mm-dd").

    Returns:
    - str or None: Filter query string if successful, None if an error occurs.

    Note:
    - Parses start and end dates using the `format_date` function.
    - Converts the parsed dates to datetime objects.
    - Creates a filter query string based on the date range.
    - Returns the filter query if successful, otherwise returns None.
    '''
    # Parse start and end dates using the format_date function
    start_date = format_date(start_date)
    end_date = format_date(end_date)
    
    try:
        # Convert the start and end dates to datetime objects
        start_date = pd.to_datetime(start_date) if start_date else None
        end_date = pd.to_datetime(end_date) if end_date else None
        date_query = ""
        # Filter the df based on the date range
        if start_date and end_date:
            date_query = f"date >= '{start_date}' & date <= '{end_date}'"
        elif start_date:
           date_query = f"date >= '{start_date}'"
        elif end_date:
            date_query = f"date <= '{end_date}'"
        else:
            # If both dates are None, then empy query
            return ""

        return date_query
    except ValueError:
        # Handle invalid date formats
        print("Error: Invalid date format in DataFrame")
        return None

def extract_key(json_data):
    '''
    Parameters:
    - json_data (str): Json string representing a sentiment analysis result.
    Returns:
    - str or None: Label if successful, None otherwise.
    '''
    try:
        return json_data[0]['label']
    except (json.JSONDecodeError, KeyError):
        return None
    
def parse_json(json_string):
    '''
    Parses a JSON string and returns a DataFrame.

    Parameters:
    - json_string (str): JSON string to be parsed.

    Returns:
    - pd.DataFrame or None: DataFrame containing parsed data if successful, None otherwise.

    Note:
    - Converts the JSON string to a DataFrame using `pd.read_json`.
    - Formats the 'date' column using the `format_date` function if present.
    - Extracts sentiment labels from the 'sentiment' column, if present.
    - Drops the 'sentiment' column after extracting labels.
    - Sets the display option for column width in the DataFrame.
    - Returns the parsed DataFrame if successful, otherwise returns None.
    '''
    if json_string != 'null':
        data = pd.DataFrame(pd.read_json(io.StringIO((json_string))))
        if 'date' in data.columns:
            data['date'] = data['date'].apply(lambda x: format_date(str(x)))
        if 'sentiment' in data.columns:
            #extract only label
            data['label'] = data['sentiment'].apply(extract_key)
            data = data.drop(columns=['sentiment'])
        pd.set_option('display.max_colwidth', 20)
        return data
    return None

def parse_commits(response_json):
    '''
    Parses commit data from a GitHub API response and returns a fitting pandas DataFrame.

    Parameters:
    - response_json (dict): JSON data representing a commit from a GitHub API response.

    Returns:
    - pd.DataFrame: DataFrame containing parsed commit information.

    Note:
    - Extracts relevant information from the commit JSON data.
    - Creates a DataFrame containing columns for SHA, author, committer, date, message, files, and basic statistics.
    - The date is formatted using the `format_date` function.
    - Returns the parsed DataFrame.

    '''
    commit = response_json
    curr_commit = {}
    curr_commit['sha'] = commit['sha']
    curr_commit['author'] = commit['commit']['author']['name']
    curr_commit['committer'] = commit['commit']['committer']['name']
    curr_commit['date'] = format_date(commit['commit']['author']['date'])
    curr_commit['msg'] = commit['commit']['message']
    curr_commit['files'] = [file['filename'] for file in commit['files']]
    curr_commit['#changed'] = len(commit['files'])
    curr_commit['#added'] = commit['stats']['additions']
    curr_commit['#deleted'] = commit['stats']['deletions']
    curr_commit['#lines changed'] = commit['stats']['total']
    commit_data = [curr_commit]

    df_parse = pd.DataFrame(commit_data)
    print("Finished parsing commit history")
    return df_parse
    
def search_commit(df, sha=None, author=None, date=None, msg=None, commiter=None):
    '''
    Searches commit(s) in a DataFrame based on given criteria.

    Parameters:
    - df (pd.DataFrame): DataFrame containing commit history.
    - sha (str): SHA of the commit to search for.
    - author (str): Author name of the commit(s) to search for.
    - date (tuple): Tuple representing the date range (start_date, end_date) to filter commits.
    - msg (str): Substring of the commit message to search for.
    - commiter (str): Committer name of the commit(s) to search for.

    Returns:
    - list of dict: List of dictionaries representing the matching commit(s) if successful.
    '''
    if not (sha or author or date or msg or commiter):
        return df.to_dict(orient='records')

    conditions = []

    if sha:
        conditions.append(f"sha == '{sha}'")
    
    if author:
        conditions.append(f"author == '{author}'")
    
    if date:
        (start_date, end_date) = date
        conditions.append(filter_dataframe_by_date(start_date, end_date))
    
    if msg:
        conditions.append(f"msg.str.contains('{msg}')")
    
    if commiter:
        conditions.append(f"committer == '{commiter}'")

    query_str = " and ".join(conditions)
    
    return df.query(query_str).to_dict(orient='records')

def print_table(data):
    '''
    Function to print a table from a DataFrame using the tabulate library.
    Parameters:
    - data (pd.DataFrame): DataFrame to be printed.
    '''
    if data is None:
        print("No results found")
        return
    print(tabulate(data, headers='keys', tablefmt='fancy_grid', maxcolwidths=10))

def check_response(response, repo_name):
    '''
    Checks if a response from a GitHub API request is valid.

    Parameters:
    - response (requests.Response): The response object from the GitHub API request.
    - repo_name (str): The name of the repository associated with the API request.

    Returns:
    - str or None: Error message if the response is invalid, None if the response is valid.
    '''
    if response.status_code == 401 and 'message' in response.json() and response.json()['message'] == 'Bad credentials':
        return f"Error : Invalid token provided for '{repo_name}'"
    elif response.status_code != 200:
        return (f"Error: '{response.status_code}'")
    elif isinstance(response.json(), dict) and 'message' in response.json():
        return f"Error: '{response.json()['message']}'"
    else:
        return None
    