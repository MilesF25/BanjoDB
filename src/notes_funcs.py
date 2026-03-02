import rpydb
import os
import subprocess
import tempfile
import platform

import main


def note_retrieval(db, username, admin_bool):
    # Check if the current user is an admin
    is_admin = admin_bool

    if is_admin:
        # --- ADMIN VERSION: Select a user first ---
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
        # --- USER VERSION: Target is just themselves ---
        target_user = username

    # --- SHARED FLOW: List files for the target_user ---
    files = db.list_my_files(target_user)

    if not files:
        print(f"\n--- No notes found for {target_user} ---")
        return

    print(f"\n--- Viewing Vault: {target_user} ---")
    for i, (title, ext) in enumerate(files, 1):
        print(f"{i}. {title}{ext}")

    f_choice = input("\nSelect file number to open (or 'q'): ").strip()
    if f_choice.lower() == "q" or not f_choice.isdigit():
        return

    f_idx = int(f_choice) - 1
    if 0 <= f_idx < len(files):
        selected_title = files[f_idx][0]

        # Fetch the content
        result = db.get_file_content(target_user, selected_title)
        if result:
            file_bytes, extension = result

            # Decide mode: Admin gets 'view' (read-only), User gets 'vim' (editor)
            mode = "view" if is_admin else "edit"
            view_file_logic(selected_title, extension, file_bytes, mode)
        else:
            print("Error: Could not retrieve file data.")
    else:
        print("Invalid file selection.")


# Updated helper to handle both modes and OS platforms
def view_file_logic(title, extension, data, mode):
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tf:
        tf.write(data)
        temp_path = tf.name

    try:
        # not sure if this will wokr on other systems
        # vim/view (e.g. stock Windows).
        if extension in [".txt", ".md", ".py", ".rs", ".sh"]:
            if mode == "view":
                print(f"Opening {title} in Read-Only mode (edits won't be saved)...")
                # always attempt to launch vim in readonly mode; if it's not
                # available fall back gracefully.
                try:
                    subprocess.run(["vim", "-R", temp_path])
                except FileNotFoundError:
                    # user doesn't have vim; fall back to platform-specific view
                    if platform.system() == "Windows":
                        try:
                            with open(temp_path, "r", errors="ignore") as f:
                                print(f.read())
                        except Exception:
                            pass
                        input("Press Enter to continue...")
                    else:
                        # old version used  'view', keep that as a last resort
                        subprocess.run(["view", temp_path])
            else:
                print(f"Opening {title} in Editor...")
                if platform.system() == "Windows":
                    subprocess.run(["notepad", temp_path])
                else:
                    subprocess.run(["vim", temp_path])
        else:
            print(f"Opening {title} in system viewer...")
            if platform.system() == "Windows":
                os.startfile(temp_path)
            else:
                # Use 'open' for Mac, 'xdg-open' for Linux
                cmd = "open" if platform.system() == "Darwin" else "xdg-open"
                subprocess.run([cmd, temp_path])
            input("Press Enter to close and secure the file...")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# for making the note
def note_creation(db, username):
    title = input("Enter a title for your new note: ").strip()
    if not title:
        return

    # Extension menu
    extensions = {"1": ".txt", "2": ".md", "3": ".py", "4": ".json"}
    print(f"\nSelect file type: {extensions} ")
    choice = input("Choice: ") or "1"
    selected_ext = extensions.get(choice, ".txt")

    # 1. Create the 'Actual File' on disk temporarily
    with tempfile.NamedTemporaryFile(suffix=selected_ext, delete=False) as tf:
        temp_path = tf.name

    try:
        # 2. Hand the file over to an editor. fall back to notepad on Windows
        editor_cmd = ["gvim", temp_path]
        if platform.system() == "Windows":
            editor_cmd = ["notepad", temp_path]
        subprocess.run(editor_cmd, check=True)

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
