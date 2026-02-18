"""Main function, will be the flow of the program for draft"""

# Main program draft

# Will first gave rust setupdb or check if there is one
# fn debsetup
## first will check if there are prexisting accounts in the rust sql server
## if not it will greet and ask them to create a master account and a normal account (not allowed to change password)
# if there are accounts, terminal greeting and username/password insert and check, will have stated certain amount of tries and very short lock out

# if not admim
## terminal will clear and then display the notes of the signed in user
## Rust backend will send the python front end all the files owned by user with time stamp of last used
## The user can selectet which notepad to create or open and edit, or delete, hoping to be like vim (might need subprocess) ((If deleted, python front end will send back "DELETE" which rust server will then run a delet query))
## Selected file is sent back to rust backend and rust sends back the file to python which then calls vim to open and edit
## Once user quits or saves, python sends file back to rust db and it stores it. Will update last access log
## Will go back to menu

## Just double checking for me current user can only see their own files Will also check for no dupe usernames

# If admin
## Terminal will clear and display notes of signed in user and other users
## Rust backend will send the python front end all the files owned by user and other accounts with time stamp of last used (combine 1 and 2)
## Selected file is sent back to rust backend, rust sends back selected file to python which calls vim
## Admin and read and write
## Once user quits or saves, python sends file back to db and it stores it, will update access log
## back to item selection menu

import rpydb


def main():
    "this will create the rust sqlite db"
    # call rust db creation function
    db = rpydb.Database("banjo.db")  # opens DB and keeps it alive while `db` exists
    # db.initialize()  # create tables if needed
    # titles = db.get_user_notes(1)  # call method implemented in Rust
    table = db.list_tables()
    print(table)
    db.close()
    # print("Titles:", titles)


if __name__ == "__main__":
    main()
# Passowrd and account management

## def account check
## Will query the rust backend db to see if there are any accounts
#
## if not it will prompt them to make and account,
### return false
## if there are it will ask them to enter a password
### Return True

## Def account create
## Will be asked to submit a user and a password. Once submitted it will make a salt and combine it with each then hashed and store it, hash password only
## will make add the owener name to the column id
## will check if any accounts with the same user exist, if they do it will ask them to try again
##

## Def acccount login
## Will be asked to submit user and password, once submitted it will then go find the user name and compare the hash
## if it matches
###return true
## if it doesn't have them try again, max of 3 tries
