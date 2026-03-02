import rpydb
import os
import subprocess
import tempfile

import main


def note_retrieval(db, username):
    # 1. Get the list from Rust
    files = db.list_my_files(username)

    if not files:
        print("\n--- No notes found. Create one first! ---")
        return

    # 2. Display the menu
    print(f"\n--- {username}'s Vault ---")
    for i, (title, ext) in enumerate(files):
        print(f"{i + 1}. {title}{ext}")

    # 3. Get User Selection
    choice = input("\nSelect a number to open (or 'q' to quit): ").strip()
    if choice.lower() == "q":
        return

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            selected_title = files[idx][0]

            # --- START OF FETCH AND OPEN LOGIC ---

            # 4. Fetch the 'Actual File' bytes and extension from Rust
            result = db.get_file_content(username, selected_title)

            if result is None:
                print("Error: Could not retrieve file data.")
                return

            file_bytes, extension = result

            # 5. Create a temporary "Real File" so Vim/OS can read it
            # delete=False is important so we can close the handle but keep the file for Vim
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tf:
                tf.write(file_bytes)
                temp_path = tf.name

            try:
                # 6. Decide how to open based on extension
                if extension in [".txt", ".md", ".py", ".rs", ".sh"]:
                    print(f"Opening {selected_title} in Vim...")
                    subprocess.run(["vim", temp_path])
                else:
                    print(f"Opening {selected_title} in system viewer...")
                    # This works for PDFs, Images, etc.
                    import platform

                    if platform.system() == "Windows":
                        os.startfile(temp_path)
                    else:
                        subprocess.run(["open", temp_path])

                    input("Press Enter once you are finished viewing the file...")

            finally:
                # 7. SECURE CLEANUP: Wipe the file from the disk
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    print(f"Temporary file {selected_title} has been wiped.")

            # --- END OF FETCH AND OPEN LOGIC ---
        else:
            print("Invalid selection.")
    else:
        print("Please enter a valid number.")


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
