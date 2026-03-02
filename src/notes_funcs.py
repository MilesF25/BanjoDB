import rpydb
import os
import subprocess
import tempfile

import main


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


def note_creation(db, username):
    title = input("Enter a title for your new note: ").strip()
    if not title:
        return

    # Extension menu (for Vim's benefit)
    extensions = {"1": ".txt", "2": ".md", "3": ".py", "4": ".json"}
    print(f"\nSelect file type: {extensions} ")
    choice = input("Choice [1]: ") or "1"
    selected_ext = extensions.get(choice, ".txt")

    # 1. Create the 'Actual File' on disk temporarily
    with tempfile.NamedTemporaryFile(suffix=selected_ext, delete=False) as tf:
        temp_path = tf.name

    try:
        # 2. Hand the file over to Vim
        subprocess.run(["gvim", temp_path], check=True)

        # 3. CRITICAL: Read the 'Actual File' as raw bytes
        # Opening in "rb" mode ensures we get the exact file data
        with open(temp_path, "rb") as f:
            file_blob = f.read()

        if not file_blob:
            print("File is empty, nothing to save.")
        else:
            # 4. Pass the entire file blob to Rust
            db.save_new_note(username, title, selected_ext, file_blob)
            print("✅ File has been saved")

    except Exception as e:
        print(f"{e}")

    finally:
        # main.clear_screen()
        # 5. Destroy the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
