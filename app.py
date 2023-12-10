from flask import Flask, jsonify
from flask_restful import Api, Resource
import subprocess
import requests
import json
import pandas as pd
import utils.utilfunctions as utilfunctions
import utils.statsitcs as statistics

#All dataframes
df_dict = {}
#keys that require a GET call per commit
KEYS_FOR_COMMIT = ['filename', 'addition', 'deletion', 'changes']

app = Flask(__name__)
api = Api(app)
@app.route('/')
def home():
    return "Place holder."

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"An error occurred: {error}")
    return "Internal Server Error", 500

# Global error handler for 400 Bad Request
@app.errorhandler(400)
def handle_bad_request(error):
    app.logger.error(f"Bad Request: {error}")
    return jsonify({"error": "Bad Request"}), 400

# Global error handler for 401 Unauthorized
@app.errorhandler(401)
def handle_unauthorized(error):
    app.logger.error(f"Unauthorized: {error}")
    return jsonify({"error": "Unauthorized"}), 401

# Global error handler for 403 Forbidden
@app.errorhandler(403)
def handle_forbidden(error):
    app.logger.error(f"Forbidden: {error}")
    return jsonify({"error": "Forbidden"}), 403

# Global error handler for 404 Not Found
@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f"An error occurred: {error}")
    return "Not found", 404

class Clone(Resource):
    '''
    GET request to clone a repository.
    '''
    def get_sha_list_from_json(self, json_string):
        '''
        Parses a JSON string from the GitHub API response and returns a list of commit SHAs.

        Parameters:
        - json_string (str): JSON string from the GitHub API response obtained through commit GET.

        Returns:
        - list: A list of commit SHAs.

        Example:
        ```
        json_string = '[{"sha": "abc123"...}, {"sha": "def456"...}]'
        sha_list = get_sha_list_from_json(json_string)
        print(sha_list)  # Output: ['abc123', 'def456']
        ```
        '''
        sha_list = []
        for commit in json_string:
            sha_list.append(commit['sha'])
        return sha_list
    
    def get_request(self, username, repo_name, token):
        '''
        Retrieves commit information from a GitHub repository using the GitHub REST API.

        Parameters:
        - username (str): GitHub username.
        - repo_name (str): Name of the repository.
        - token (str): GitHub personal access token.

        Returns:
        - pd.DataFrame: A pandas DataFrame containing commit information.

        Raises:
        - subprocess.CalledProcessError: If an error occurs during the process.
        - Exception: If the response from the GitHub API is not as expected.
        - ValueError: If the provided token is invalid or missing.
        - requests.exceptions.RequestException: If a network-related error occurs during the HTTP request.
        '''
        headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        try:
            print('hello')
            response = requests.get(f'https://api.github.com/repos/{username}/{repo_name}/commits', headers=headers)
            check = utilfunctions.check_response(response, repo_name)
            # If an error message is returned, return it
            if isinstance(check, str):
               return check
            commits = response.json()
            # Check if there are more pages
            while "next" in response.links.keys():
                url = response.links["next"]["url"]
                response = requests.get(url, headers=headers)
                commits.extend(response.json())
            # Extract all SHA keys from the JSON response
            sha_list = self.get_sha_list_from_json(commits)
            df_list = []  
            # Iterate through each commit and retrieve detailed information
            for sha in sha_list:
                response = requests.get(f'https://api.github.com/repos/{username}/{repo_name}/commits/{sha}', headers=headers)
                check = utilfunctions.check_response(response, repo_name)
                if isinstance(check, str):
                    return check
                else:
                    # Parse commit information and append to the list of DataFrames
                    df_list.append(utilfunctions.parse_commits(response.json()))

            # Concatenate all DataFrames in the list
            df = pd.concat(df_list, ignore_index=True)
            return df
        
        except subprocess.CalledProcessError as e:
            print(f"Error getting the logs of the repository '{repo_name}': {e}")

    def get(self, username, token, repo_name, dest_path):
        '''
        GET function for the clone API request.

        Parameters:
        - username (str): GitHub username.
        - token (str): GitHub personal access token.
        - repo_name (str): Name of the repository to clone.
        - dest_path (str): Destination path for the cloned repository.

        Returns:
        - str: JSON representation of the DataFrame head.

        Raises:
        - subprocess.CalledProcessError: If an error occurs during the cloning process or when obtaining logs.
        '''
        global df_dict


        repo_url = f'https://github.com/{username}/{repo_name}.git'
        # Defining the clone command
        clone_cmd = ['git', 'clone', repo_url, dest_path]
        try:
            # Cloning the repository
            subprocess.run(clone_cmd, check=True)
            print(f"Repository '{repo_name}' cloned successfully.")
            try:
                df = self.get_request(username, repo_name, token)
                if not isinstance(df, pd.DataFrame):
                    return json.dumps(df)
                df_dict[repo_name] = df
                return df.head().to_json()
            except subprocess.CalledProcessError as e:
                print(f"Error getting the logs of the repository '{repo_name}': {e}")

        except subprocess.CalledProcessError as e:
            # Check if the error is due to the repository already existing
            if e.returncode == 128:
                print(f"Repository '{repo_name}' already exists. Proceeding.")
                try:
                    df = self.get_request(username, repo_name, token)
                    if not isinstance(df, pd.DataFrame):
                        return 'null'
                    df_dict[repo_name] = df
                    return df.head().to_json()
                except subprocess.CalledProcessError as e:
                    print(f"Error getting the logs of the repository '{repo_name}': {e}")
            else:
                print(f"Error cloning repository '{repo_name}': {e}")


class Search(Resource):
    '''
    Resource that searches through an existing commit on the server.
    '''
    def get(self, repo_name, sha=None, author=None, start_date=None, end_date = None, msg=None, commiter = None,  analyze = False):
        '''
        Handles a GET request to search through commit data for a specified repository.

        Parameters:
        - repo_name (str): Name of the repository to search.
        - sha (str, optional): SHA of the commit to filter by.
        - author (str, optional): Author's name to filter by.
        - start_date (str, optional): Start date for filtering commits (ISO 8601 format).
        - end_date (str, optional): End date for filtering commits (ISO 8601 format).
        - msg (str, optional): Commit message to filter by.
        - committer (str, optional): Committer's name to filter by.
        - analyze (bool, optional): If True, performs sentiment analysis on commit messages.

        Returns:
        - str: JSON representation of the search results.

        Note:
        - If the specified repository does not exist in the server's commit data, 'null' is returned.
        - Sentiment analysis is applied to commit messages if the `analyze` parameter is set to True.
        '''
        global df_dict

        if not repo_name in df_dict.keys():
            print("No such repository")
            return 'null'
        df = df_dict[repo_name]

        # Convert 'None' strings to actual None values
        sha = None if sha == 'None' else sha
        author = None if author == 'None' else author
        date_range = None if start_date == 'None' and end_date == 'None' else (start_date, end_date)
        msg = None if msg == 'None' else msg
        commiter = None if commiter == 'None' else commiter

        # Perform commit search using utility function
        response = utilfunctions.search_commit(df, sha, author, date_range, msg, commiter)
        # Optionally, perform sentiment analysis on commit messages
        if analyze == 'True':
            for commit in response:
                commit['sentiment'] = statistics.sentiment_analysis(commit['msg'])
        # If no matching commits are found, return 'null'
        if len(response) == 0:
            return 'null'
        
        # Return JSON representation of the search results
        return json.dumps(response)


class Group(Resource):
    '''
    Resource that groups developers based on their commit history and issues history.
    '''
    def get_issues(self, username, repo_name, token):
        '''
        Calls the GitHub API to retrieve issues for a specified repository and parses the response into a pandas DataFrame.

        Parameters:
        - username (str): GitHub username.
        - repo_name (str): Name of the repository.
        - token (str): GitHub personal access token.

        Returns:
        - pd.DataFrame or str: A pandas DataFrame containing issues data if successful, otherwise an error message.
        '''
        headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        try:
            response = requests.get(f'https://api.github.com/repos/{username}/{repo_name}/issues', headers=headers)
            check = utilfunctions.check_response(response, repo_name)
            issues = response.json()
            # Check if there are more pages
            while "next" in response.links.keys():
                url = response.links["next"]["url"]
                response = requests.get(url, headers=headers)
                check = utilfunctions.check_response(response, repo_name)
                issues.extend(response.json())
            # If an error message is returned, return it
            if isinstance(check, str):
                return check
            return issues
        except subprocess.CalledProcessError as e:
            print(f"Error getting the logs of the repository '{repo_name}': {e}")

    def get(self, username, token, repo_name, k):
        '''
        Groups developers based on their commit history and issues history using k-means clustering.

        Parameters:
        - username (str): GitHub username.
        - token (str): GitHub personal access token.
        - repo_name (str): Name of the repository.
        - k (int): Number of clusters for k-means clustering.

        Returns:
        - str: JSON representation of the grouped developers.

        Note:
        - If the specified repository does not exist in the server's commit data, 'null' is returned.
        - If there is an issue retrieving the GitHub issues, 'null' is returned.
        - The k-means clustering is performed on the combined features of commit history and issues history.
        '''
        global df_dict

        if not repo_name in df_dict.keys():
            return 'null'
        # Retrieve the commit data DataFrame for the specified repository
        df = df_dict[repo_name]
        # Retrieve issues data from the GitHub API
        response = self.get_issues(username, repo_name, token)
        # If there is an issue retrieving the GitHub issues, go with commit history only
        if isinstance(response, str):
            ret = statistics.kmeans(df, k)
            if ret is None:
                return 'null'
            return ret.to_json()
        
        # Perform k-means clustering using issues data as well
        ret = statistics.kmeans(df, k, response)
        if ret is None:
            return 'null'
        return ret.to_json()
    
api.add_resource(Clone, '/clone/<username>/<token>/<repo_name>/<dest_path>/')
api.add_resource(Search, '/search/<repo_name>/<sha>/<author>/<start_date>/<end_date>/<msg>/<commiter>/<analyze>')
api.add_resource(Group, '/group/<username>/<token>/<repo_name>/<k>')
if __name__ == "__main__":
    app.run(debug=True)
