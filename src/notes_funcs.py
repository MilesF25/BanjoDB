import rpydb
import os


def note_retrieval(db, username):
    # Call Rust to get the list
    files = db.list_my_files(username)

    if not files:
        print("--- No notes, make some so you can view them ---")
        return

    print(f"\n--- {username}'s Vault ---")

    # Python displays the list to the user
    for i, (title, ext) in enumerate(files):
        print(f"{i + 1}. {title}{ext}")

    # Now the user can pick one
    choice = input("\nSelect a number to open a file (or 'q' to quit): ")
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            selected_title = files[idx][0]  # Get the 'title' string

            # NOW you use the other function we wrote to get the bytes
        # fetch_and_open_file(db, username, selected_title)
