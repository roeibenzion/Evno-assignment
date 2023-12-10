from transformers import pipeline
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans  


#Sentiment analysis
def init_pipeline(task = 'sentiment-analysis', model = None):
    '''
    Initializes a HuggingFace Transformers pipeline for a specific NLP task.

    Parameters:
    - task (str): The NLP task to perform (default: 'sentiment-analysis').
    - model (str): Optional parameter specifying the pre-trained model to use.

    Returns:
    - transformers.Pipeline: A Hugging Face Transformers pipeline.
    '''
    if model:
        return pipeline(task=task, model=model)
    return pipeline(task=task)

def sentiment_analysis(commit_msgs):
    '''
    Performs sentiment analysis on commit messages using a pre-trained model.

    Parameters:
    - commit_msgs (list): List of commit messages to analyze.

    Returns:
    - list: List of dictionaries containing sentiment analysis results for each commit message.
    '''
    model = init_pipeline('sentiment-analysis', model='ProsusAI/finbert')
    return model(commit_msgs)

#end of sentiment analysis

#Developer clustering
def get_num_days_between_dates(date1, date2):
    '''
    Calculates the number of days between two dates.

    Parameters:
    - date1 (datetime.datetime): The first date.
    - date2 (datetime.datetime): The second date.

    Returns:
    - int: The number of days between the two dates.
    '''
    # Calculate the number of days between the two dates
    num_days = (date1 - date2).days

    return num_days

def get_repo_time(df):
    '''
    Calculates the number of days between the latest and oldest dates in a DataFrame.

    Parameters:
    - df (pd.DataFrame): DataFrame containing commit history with a 'date' column.

    Returns:
    - int: The number of days between the latest and oldest dates.
    '''
    # Ensure the 'date' column is in datetime format
    df_copy = df.copy()
    df_copy['date'] = pd.to_datetime(df_copy['date'])


    # Find the latest and oldest dates in the 'date' column
    latest_date = df_copy['date'].max()
    oldest_date = df_copy['date'].min()

    # Calculate the number of days between the latest and oldest dates
    num_days = get_num_days_between_dates(latest_date, oldest_date)

    return num_days

def extract_features_commits_df(df):
    '''
    Extracts features from commit history in a DataFrame.

    Parameters:
    - df (pd.DataFrame): DataFrame containing commit history with relevant columns.

    Returns:
    - pd.DataFrame: DataFrame with features extracted for each author.

    Note:
    - Extracts features such as the number of commits, commit frequency, number of files changed, 
      number of lines added, number of lines deleted, and number of lines changed for each author.
    - Calculates commit frequency as the number of commits divided by the repository duration.
    - Returns a DataFrame with aggregated features for each author.
    '''
    authors = {}
    for _, row in df.iterrows():
        curr_commit = {}
        curr_commit['date'] = row['date']
        curr_commit['files'] = len(row['files'])
        curr_commit['#added'] = row['#added']
        curr_commit['#deleted'] = row['#deleted']
        curr_commit['#lines changed'] = row['#lines changed']
        name = row['author']
        if name in authors.keys():
            authors[name]['name'] = name
            authors[name]['num_commits'] += 1
            authors[name]['num_files_changed'] += curr_commit['files']
            authors[name]['num_lines_added'] += curr_commit['#added']
            authors[name]['num_lines_deleted'] += curr_commit['#deleted']
            authors[name]['num_lines_changed'] += curr_commit['#lines changed']
        else:
            authors[name] = {'name': name,
                             'num_commits':1, 
                             'commit_frequency':0, 
                             'num_files_changed':curr_commit['files'], 
                             'num_lines_added':curr_commit['#added'], 
                             'num_lines_deleted':curr_commit['#deleted'], 
                             'num_lines_changed':curr_commit['#lines changed'], 
                             }
    for name in authors.keys():
        authors[name]['commit_frequency'] = authors[name]['num_commits'] / get_repo_time(df)
    df_parse = pd.DataFrame(authors).T
    return df_parse

def extract_features_issues_response(response_json):
    authors = {}
    for issue in response_json:
      name = issue['user']['login']
      if name in authors.keys():
        authors[name]['num_issues'] += 1
        authors[name]['num_opened'] += 1 if issue['state'] == 'opened' else 0
        authors[name]['num_closed'] += 1 if issue['state'] == 'opened' else 0
        for label in issue['labels']:
          authors[name][label] += 1
      else:
        authors[name] = {'name': name,
                         'num_issues':1,
                         'num_opened' : 1 if issue['state'] == 'opened' else 0,
                         'num_closed' : 1 if issue['state'] == 'closed' else 0,
                         'bug': 0,
                         'documentation': 0,
                         'duplicate': 0,
                         'enhancement': 0,
                         'future': 0
        } 
      df = pd.DataFrame(authors).T
      return df

def cluster_developers(df, num_clusters=3):
    '''
    Extracts features from GitHub issues API response.

    Parameters:
    - response_json (list): List of dictionaries representing issues from the GitHub API.

    Returns:
    - pd.DataFrame: DataFrame with features extracted for each author from issues.

    Note:
    - Extracts features such as the number of issues, number of opened issues, number of closed issues,
      and counts of different label types (e.g., bug, documentation, enhancement) for each author.
    - Returns a DataFrame with aggregated features for each author from GitHub issues.

    '''
    #take care of nan values
    df = df.fillna(0)
    X = df.drop(columns=['name']).to_numpy()
    # Apply k-means clustering
    kmeans = KMeans(n_clusters=num_clusters, random_state=0).fit(X)
    df['cluster'] = kmeans.labels_

    # Create a new DataFrame with 'name:cluster' format
    result_df = df[['name', 'cluster']]

    return result_df

def kmeans(commits_df, num_clusters=2, response_json_issues = None):
    '''
    Performs K-means clustering on developers based on their commit history.

    Parameters:
    - commits_df (pd.DataFrame): DataFrame containing commit history with relevant columns.
    - num_clusters (int): Number of clusters for K-means. Defaults to 2.
    - response_json_issues (list): List of dictionaries representing issues from the GitHub API.

    Returns:
    - pd.DataFrame: DataFrame with developer names and their corresponding cluster assignments.

    Note:
    - Extracts features from commit history using `extract_features_commits_df` function.
    - Optionally incorporates features from issues using `extract_features_issues_response`.
    - Performs K-means clustering on the combined feature set.
    - Returns a DataFrame with developer names and their corresponding cluster assignments.
    '''
    try: 
        num_clusters = int(num_clusters)
    except ValueError:
        print("Error: Invalid number of clusters")
        return None
    df_commits = extract_features_commits_df(commits_df)
    if response_json_issues:
        df_issues = extract_features_issues_response(response_json_issues)
        df_commits = pd.merge(df_commits, df_issues, how='outer', on='name')
        
    if len(df_commits) < num_clusters:
        print("Error: Number of clusters is greater than the number of developers")
        return None
    #make the name column the index
    return cluster_developers(df_commits, num_clusters)
#end of developer clustering