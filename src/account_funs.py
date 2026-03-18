import rpydb
import os
import main


def account_selection(db, username, admin_bool) -> str:
    # Check if the current user is an admin
    is_admin = admin_bool

    if is_admin:
        all_users = db.list_all_users()
        if not all_users:
            print("No users found.")
            return

        print("\n--- [ADMIN] Select a User to Inspect ---")
        for i, name in enumerate(all_users, 1):
            print(f"{i}. {name}")

        u_choice = input("\nSelect user number (or 'q'): ").strip()
        if u_choice.lower() == "q" or not u_choice.isdigit():
            main.clear_screen()
            return

        u_idx = int(u_choice) - 1
        if 0 <= u_idx < len(all_users):
            target_user = all_users[u_idx]
        else:
            print("Invalid selection.")
            return
    else:
        return target_user


def confirmation_deletion(db, target_username):
    print(
        f"You are deleting {target_username}'s account.This will delete their notes too, Are you sure?"
    )
    confirm = input("Enter yes or no: ").strip().lower()

    if confirm == "yes":
        print("Are you REALLY sure?")
        double_confirm = input("Enter yes or no: ").strip().lower()

        if double_confirm == "yes":
            db.delete_account(target_username)
            print("Account deleted.")
        else:
            print("Deletion cancelled.")
    else:
        print("Deletion cancelled.")
