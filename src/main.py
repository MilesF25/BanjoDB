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
import os
import time
import notes_funcs


# personal reminder, use the db. for database function calls
def main():
    print(
        "Welcome, checking if the database exists (as of now its hardcoded to look for banjo db)"
    )
    exists = file_checks()
    if not exists:
        # (RUST) Need to check if a db exists, if there are accounts and if there is a master account
        "this will create the rust sqlite db"
        # call rust db creation function
        db = rpydb.Database("banjo.db")  # opens DB and keeps it alive while `db` exists
        print("Create a admin account")
        make_admin_account(db)
        print("Create a user account")
        make_user_account(db)
        clear_screen()
        print("Login")
        result, user = account_login(db)
        if not result:
            print("failed login")
        else:
            main_menu(db, user)

        # print(table)
        db.close()
    else:
        db = rpydb.Database("banjo.db")
        accountE = account_exist(db)
        # Handle the result of account_exist(db):
        # accountE is a tuple (any_acc, master_acc)
        # - (False, False): No accounts exist. Prompt to create the first account.
        # - (True, False): Accounts exist, but no admin/master account. (TODO: Decide what to do in this case)
        # - (True, True): Accounts exist and a master/admin account exists. (TODO: Implement login/account creation logic)
        # print("accountE:", accountE)
        # any_acc, master_acc = accountE
        # print("any_acc:", any_acc, "master_acc:", master_acc)
        # print(accountE)'
        ## TODO: these two parts need to have the user login after
        if accountE == (False, False):
            print("No accounts detected, moving to account creation")
            # account_create()
            make_admin_account(db)
        elif accountE == (True, False):
            print("An accout existst but there is no admin, password recovery maybe")
            # print("Login with Admin account")
            # result, user = account_login(db)
            # if not result:
            #     print(
            #         "Not an Admin, please find the admin creds and enter them to gain access"
            #     )
            # else:
            #     time.sleep(1)
            #     clear_screen()
            #     main_menu(db, user)

            pass
        elif accountE == (True, True):
            # retuns a bool if loging works
            result, user = account_login(db)

            if not result:
                print("failed login")
            else:
                time.sleep(1)
                clear_screen()
                main_menu(db, user)

        db.close()


# Function for main menu
def main_menu(database_connection, username):
    """Display the main menu for a logged-in user and handle actions.

    This function performs actions directly (calls other functions)
    rather than returning a numeric code. It loops until the user
    chooses to logout/exit.
    """
    while True:
        print("What would you like to do?")
        print("1. Make new account (Admin)")
        print("2. Make a new admin account (Admin only)")
        print("3. Delete account (Admin only)")
        print("4. View notes")
        print("5. Logout/Exit")
        choice = input("Enter a number: ").strip()

        if choice == "1":
            if admin_check(database_connection, username):
                make_user_account(database_connection)
            else:
                print("Permission denied: admin only.")
                print(f"{username} is")
        elif choice == "2":
            if admin_check(database_connection, username):
                make_admin_account(database_connection)
            else:
                print("Permission denied: admin only.")
        elif choice == "3":
            clear_screen()
            if admin_check(database_connection, username):
                # Placeholder: deletion flow not implemented in Python layer
                try:
                    database_connection.delete_account_prompt()
                except AttributeError:
                    print("Delete account not implemented.")
            else:
                print("Permission denied: admin only.")
        elif choice == "4":
            clear_screen()
            print("Note Options.")
            notes_user_version(database_connection, username)
            # TODO: Need to create the notes so they can be viewd. Only make things that can be viewed in vim
            # call view notes function (2 versions, 1 admin, 1 user)
            # takes username and db connection
            # should let them
        elif choice == "5":
            print("Logging out.")
            database_connection.close()
            break
        else:
            print("Invalid choice, please try again.")


def notes_user_version(database_connection, username):
    print("What would you like to do?")
    print(
        "1. View You're Notes"
    )  # should bring a list of their notes for them to select, once python gets the notes back if empty will say no notes and let them reutrn to menu

    print("2. Edit Notes")  # again a list but this time it will open vim for editing
    print(
        "3. Delete Notes"
    )  # List of their notes but the ones they select will be deleted, will double confirm
    print("4. Make New Note")
    choice = input("Enter a number: ").strip()

    # Calls functions from the note funcs file
    if choice == "1":
        notes_funcs.note_retrieval(database_connection, username)
    if choice == "4":
        notes_funcs.note_creation(database_connection, username)


# first function
def file_checks() -> bool:
    # THE CODE IS HARDCODED FOR BANJO DB

    databasename = "banjo.db"
    # Check if BanjoDB directory exists in current directory
    if os.path.isfile(databasename):
        print("The database file has been found. Starting program.")
    else:
        print(
            f"The database file '{databasename}' was not found. Making a new Database"
        )
    # Return True if the file exists, False otherwise
    return os.path.isfile(databasename)


# Passowrd and account management

## def account check
## Will query the rust backend db to see if there are any accounts
#
## if not it will prompt them to make and account,
### return false
## if there are it will ask them to enter a password
### Return True


def account_exist(database_connection) -> (bool, bool):
    # Will call rust function to see if any accounts exists in the user database
    # Will return a tuple (True, True), if accounts are found, if a master account (has admin role) is there.
    # Will return a tuple (True, False), if only a master account is foun
    # Will return a tuple (False, True), if an account is found but no master account
    # Will return a tuple (False, False), if nothing is found

    # Call the Rust function
    any_acc, master_acc = database_connection.account_exisiting_check()

    if not any_acc:
        print("System is empty. Please create the first account.")
    elif any_acc and not master_acc:
        print("""Accounts exist, but no Admin found! Safety risk.
              (Please check the the role is Admin and not admin. It is hard coded for Admin)""")
    elif any_acc and master_acc:
        print("System ready. Admin account verified.")
    else:
        print("Unexpected result from account_exisiting_check.")

    return (any_acc, master_acc)


## Def account create
## Admin useres are given the role adminc
## Will be asked to submit a user and a password. Once submitted it will make a salt and combine it with each then hashed and store it, hash password only
## will make add the owener name to the column id
## will check if any accounts with the same user exist, if they do it will ask them to try again


# Returns true if admin, false if not
def admin_check(database_connection, username) -> bool:
    print("Verifying Credentials")
    admin = database_connection.is_admin(username)
    if admin:
        return True
    else:
        return False


def make_admin_account(database_connection):
    print("creating the admin account")
    username = input("Enter a username: ")
    password = input("Enter a password: ")
    try:
        database_connection.create_admin_account(username, password)
        print("Admin account has been made")
    except ValueError:
        print("Account already exists")


def make_user_account(database_connection):
    print("creating the user account")
    username = input("Enter a username: ")
    password = input("Enter a password: ")
    try:
        database_connection.create_user_account(username, password)
        print("User Account has been made")
    except ValueError:
        # lazy but this is small project
        print("That account already exists or another issue")


# Function for clearing the screen


def clear_screen():
    # Check the operating system name
    if os.name == "nt":
        # Command for Windows
        _ = os.system("cls")
    else:
        # Command for Linux/macOS (posix)
        _ = os.system("clear")


def account_login(database_connection) -> (bool, str):
    print("Enter your user and pass to login")
    username = input("Enter a username: ")
    password = input("Enter a password: ")
    success, message = database_connection.verify_login(username, password)

    if success:
        print(f"SUCCESS: {message}")
        return True, username
    else:
        print(f"FAILURE: {message}")
        return False, username


## Def acccount login
## Will be asked to submit user and password, once submitted it will then go find the user name and compare the hash
## if it matches
###return true
## if it doesn't have them try again, max of 3 tries


if __name__ == "__main__":
    main()
