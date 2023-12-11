import requests
from requests.exceptions import HTTPError, RequestException
import utils.utilfunctions as utilfunctions


BASE = 'http://127.0.0.1:5000'



def clone(username, token):
    '''
    Clones a GitHub repository and prints information about the latest commits.

    Parameters:
    - username (str): GitHub username.
    - token (str): GitHub personal access token.

    Returns:
    - None: Prints information about the latest commits and handles errors gracefully.

    Note:
    - This function prompts the user to input the repository name.
    - It sends a request to the server's `/clone` endpoint to clone the specified repository.
    - Displays a table of the latest commits if successful.
    - Handles various errors, including HTTP errors, request exceptions, and JSON parsing errors.
    - Adds the cloned repository name to the `repo_set` set.

    '''
    repo_name = input("Insert repo name: ")
    print("Cloning...")
    
    try:
        # Send a GET request to the server's /clone endpoint
        clone_response = requests.get(f'{BASE}/clone/{username}/{token}/{repo_name}/output')
        clone_response.raise_for_status()  # This will raise an HTTPError for bad responses
    except HTTPError as errh:
        print(f"HTTP Error: {errh}")
        return
    except RequestException as err:
        print(f"Request Exception: {err}")
        return
    
    try:
        # Parse JSON response from the server
        commits_data = clone_response.json()
        # Check for errors in the response
        if commits_data.startswith('Error'):
            print(commits_data)
            return
        # Check if no repo are found
        if commits_data == 'null':
            print("No repo found, check your credentials and try again")
            return
        # Print the table of the latest commits
        utilfunctions.print_table(utilfunctions.parse_json(commits_data))
        repo_set.add(repo_name)
        examples = min(5, len(clone_response.json()))
        print(f"Finished. Here are example {examples} commits.")
    except ValueError as ve:
        print(f"Error parsing JSON: {ve}")

def search():
    '''
    Searches for commits in a selected repository based on specified criteria.

    Returns:
    - None: Prints information about the search results and handles errors gracefully.

    Note:
    - Prompts the user to choose a repository from the available repositories.
    - Allows the user to specify search criteria such as SHA, author, date range, message content, and committer.
    - Optionally performs sentiment analysis on commit messages.
    - Handles various errors, including HTTP errors and JSON parsing errors.
    '''

    if len(repo_set) == 0:
        print("No repositories available, please clone a repository first")
        return
    
    search = ''
    print("Available repos: ", repo_set)
    repo_name = input("Choose a repo to search in: ")
    while (repo_name not in repo_set):
        repo_name = input("Invalid choise, please choose a from the above list or quit with qs: ")
        if repo_name == 'qs':
            return
        
    while search != 'qs':
        print("Skip all keys to get the whole history")
        sha = input("Insert sha: ")
        if sha == '':
            sha = 'None'

            author = input('Insert author name: ')
            author = 'None' if author == '' else author
            
            start_date = input('Insert start date (yyyy-mm-dd): ')
            if start_date == '':
                start_date = 'None'
            elif not utilfunctions.validate_date_format(start_date):
                print("Invalid date format")
                start_date = 'None'
            end_date = input('Insert end date (exclusive) (yyyy-mm-dd): ')
            if end_date == '':
                end_date = 'None'
            elif not utilfunctions.validate_date_format(end_date):
                print("Invalid date format")
                end_date = 'None'
            
            msg = input('Insert message content: ')
            msg = 'None' if msg == '' else msg

            commiters = input('Insert commiter name: ')
            commiters = 'None' if commiters == '' else commiters
        else:
            author = 'None'
            start_date = 'None'
            end_date = 'None'
            msg = 'None'
            commiters = 'None'

        sentiment = input('Do you want to run setiment analysis on commit messages? (Y if yes, else no): ')
        sentiment = 'True' if sentiment == 'Y' else 'None'

        try:
            # Send a GET request to the server's /search endpoint
            search_response = requests.get(f'{BASE}/search/{repo_name}/{sha}/{author}/{start_date}/{end_date}/{msg}/{commiters}/{sentiment}')
            search_response.raise_for_status()
        except HTTPError as errh:
            print(f"HTTP Error: {errh}", 'you might have to clone the repo again')
            return
        except RequestException as err:
            print(f"Request Exception: {err}")
            return

        try:
            # Parse JSON response from the server
            search_results = search_response.json()
            if search_results == 'null':
                print("No results found")
            else:
                data = utilfunctions.parse_json(search_results)
                if data is not None:
                    # Print a table of the search results
                    utilfunctions.print_table(data)
        except ValueError as ve:
            print(f"Error parsing JSON: {ve}")

        search = input("\nInsert 'qs' if you want to quit searching this repository (press Enter to continue): ")

def group(token, username):
    '''
    Groups repositories by developer clustering.

    Parameters:
    - token (str): GitHub personal access token.
    - username (str): GitHub username.

    Returns:
    - None: Prints information about the grouped repositories and handles errors gracefully.

    Example:
    ```
    group('your_token', 'your_username')
    ```

    Note:
    - Prompts the user to choose a repository from the available repositories.
    - Allows the user to specify the number of clusters (k) for grouping.
    - Sends a GET request to the server's /group endpoint to perform k-means clustering.
    - Prints a table of the grouped repositories if successful.
    - Handles various errors, including HTTP errors.

    '''
    if len(repo_set) == 0:
        print("No repositories available, please clone a repository first")
        return
    print("Available repos: ", repo_set)
    repo_name = input("Choose a repo to group: ")
    while (repo_name not in repo_set):
        repo_name = input("Invalid choise, please choose a from the above list or quit with qs: ")
        if repo_name == 'qs':
            return
    k = input("Insert number of clusters: ")
    while not k.isdigit():
        k = input("Invalid input, please insert a number: ")
    try:
        response = requests.get(f'{BASE}/group/{username}/{token}/{repo_name}/{k}')
        response.raise_for_status()
        utilfunctions.print_table(utilfunctions.parse_json(response.json()))    
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")

def info():
    print("In this program you can clone a repository, search in its commit history and group developers by their commits.")
    print("You'll be asked to provide a user name and a valid access token.")
    print("Then you'll be able to conduct searches in the repo commit history by either sha, author, date range or massage content.")
    print("You can also group developers by features ensambled from their commits history and their issue history")
    print("You can quit the program at any time by pressing q, and you can quit a search by pressing qs (quit search).")
    print("Enjoy!")

if __name__ == '__main__':
    files = ''
    proceed = ''
    repo_set = set()

    print("\nGuide of use: you'll be asked to provide user name, repo name and a valid access token.")
    print("Then you'll be able to conduct searches in the repo commit history by either sha, author, date range or massage content.")
    username = input("\ninsert user name: ")
    token = input("insert token: ")
    while proceed != 'q':
        proceed = input('Type c to clone, s to search, g to group developers, i for information or q to quit: ')
        if proceed == 'c':
            clone(username, token)
        elif proceed == 's':
            search()
        elif proceed == 'g':
            group(token, username)
        elif proceed == 'i':
            info()
        elif proceed == 'q':
            break
        else:
            print("Invalid input, try again")
    print("Bye bye")
