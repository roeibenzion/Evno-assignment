# Evno-assignment
This is the git repo for the Evno home assignment.
## Instructions
1. Clone this repo and cd to the cloned folder.
2. Install dependencies using:
```
pip install -r requirements
```
3. Run the server:
```
pyhton app.py
```
5. open another terminal window and run the client:
```
python test.py
```
Note: make sure the client's terminal is on full screen for the output to be well structured.

## Details
This application lets the client to clone repositories given user name and valid access token, the user can also search the cloned repository and run
a clustering algorithm on the contributors commit and issue history.
After running the test.py client file you will be asked to provide the fitting user name and access token for you github account.
Now, you can choose 'c' to clone (can clone as many repositories as you want), 's' to search by selected keys in the commit history and 'g' to group developers contributed to that repo. 
