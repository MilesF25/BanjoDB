use pyo3::prelude::*;
// use rand::rngs::OsRng;
use rusqlite::{Connection, params};
use std::sync::Mutex;

// Password hashing imports
// use argon2::{
//     Argon2, PasswordHash, PasswordVerifier,
//     password_hash::{PasswordHasher, SaltString},
// ;

use argon2::{
    Argon2, PasswordHash, PasswordVerifier,
    password_hash::{PasswordHasher, SaltString, rand_core::OsRng},
};

/// A Python module implemented in Rust.

// Define the `Database` struct before implementing its methods so the
// `impl Database` block can find the type in scope.
#[pyclass]
pub struct Database {
    // Store the rusqlite connection inside a Mutex so methods can lock it
    // from `&self` and safely perform DB operations.
    // Use Option<Connection> so we can implement an explicit `close()` that
    // drops the connection by setting the Option to None.
    conn: Mutex<Option<Connection>>,
}

// Module initialization: expose `Database` to Python as `rpydb.Database`

#[pymethods]
impl Database {
    #[new]
    fn new(path: String) -> PyResult<Self> {
        let conn = Connection::open(path)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        // Enable Foreign Keys
        conn.execute("PRAGMA foreign_keys = ON;", ())
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        // Initialize Tables
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                failed_attempts INTEGER DEFAULT 0,
                lock_until INTEGER
            )",
            (),
        )
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                file_extension TEXT NOT NULL,
                content BLOB NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_accessed INTEGER,
                UNIQUE(owner_id, title),
                FOREIGN KEY(owner_id) REFERENCES users(id)
            )",
            (),
        )
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        Ok(Database {
            conn: Mutex::new(Some(conn)),
        })
    }

    //Notes functions//
    //function for saving a created note into the db//
    fn save_new_note(
        &self,
        username: String,
        title: String,
        extension: String,
        content: Vec<u8>,
    ) -> PyResult<String> {
        let guard = self.conn.lock().unwrap();
        let conn = guard
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        // The 'content' here is the raw binary image of the file
        conn.execute(
            "INSERT INTO notes (owner_id, title, file_extension, content, created_at, updated_at) 
             VALUES ((SELECT id FROM users WHERE username = ?1), ?2, ?3, ?4, unixepoch(), unixepoch())",
            params![username, title, extension, content],
        ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        Ok(format!("File '{}' successfully vaulted.", title))
    }

    // Returns a list of all file titles and their extensions for a specific user NOT ADMIN VERSION
    fn list_my_files(&self, username: String) -> PyResult<Vec<(String, String)>> {
        let guard = self.conn.lock().unwrap();
        let conn = guard
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        // Query only the metadata (title and extension), not the heavy BLOB data
        let mut stmt = conn
            .prepare(
                "SELECT n.title, n.file_extension 
             FROM notes n 
             JOIN users u ON n.owner_id = u.id 
             WHERE u.username = ?1",
            )
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let note_iter = stmt
            .query_map([username], |row| {
                Ok((
                    row.get::<_, String>(0)?, // Title
                    row.get::<_, String>(1)?, // Extension
                ))
            })
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let mut results = Vec::new();
        for note in note_iter {
            results
                .push(note.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?);
        }

        // If there are no files, results will be an empty Vec [].
        // PyO3 turns this into an empty list [] in Python.
        Ok(results)
    }

    // login functions//
    //checks if the user is a admin
    fn is_admin(&self, username: String) -> PyResult<bool> {
        let guard = self.conn.lock().unwrap();
        let conn = guard
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        // Prepare the query to look up the role for the given username
        let mut stmt = conn
            .prepare("SELECT role FROM users WHERE username = ?1")
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        // Query for the role string
        let role: String = match stmt.query_row([username], |row| row.get(0)) {
            Ok(r) => r,
            Err(rusqlite::Error::QueryReturnedNoRows) => return Ok(false), // User doesn't exist, so not an admin
            Err(e) => return Err(pyo3::exceptions::PyRuntimeError::new_err(e.to_string())),
        };

        // Return true if the role is exactly "Admin"
        Ok(role == "Admin")
    }
    //verify account

    fn verify_login(&self, username: String, password_attempt: String) -> PyResult<(bool, String)> {
        let guard = self.conn.lock().unwrap();
        let conn = guard
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        // 1. Fetch the stored hash from the DB
        let mut stmt = conn
            .prepare("SELECT password_hash FROM users WHERE username = ?1")
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        // Handle User existence
        let stored_hash: String = match stmt.query_row([username], |row| row.get(0)) {
            Ok(hash) => hash,
            Err(rusqlite::Error::QueryReturnedNoRows) => {
                // Tell the user the account doesn't exist
                return Ok((false, "User account not found.".to_string()));
            }
            Err(e) => return Err(pyo3::exceptions::PyRuntimeError::new_err(e.to_string())),
        };

        // 2. Compare the attempt with the stored hash
        let parsed_hash = match PasswordHash::new(&stored_hash) {
            Ok(h) => h,
            Err(_) => {
                return Ok((
                    false,
                    "Internal error: Corrupted password hash.".to_string(),
                ));
            }
        };

        let is_valid = Argon2::default()
            .verify_password(password_attempt.as_bytes(), &parsed_hash)
            .is_ok();

        if is_valid {
            Ok((true, "Login successful!".to_string()))
        } else {
            // Tell the user the password was wrong
            Ok((false, "Invalid password. Please try again.".to_string()))
        }
    }

    //makes the admin account. really is only called once//
    fn create_admin_account(&self, username: String, password: String) -> PyResult<String> {
        let mut guard = self.conn.lock().unwrap();
        let conn = guard
            .as_mut()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        // 1. Hash the password
        // Argon2 handles the salt automatically using OsRng (secure random)
        let salt = SaltString::generate(&mut OsRng);
        let argon2 = Argon2::default();
        let password_hash = argon2
            .hash_password(password.as_bytes(), &salt)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?
            .to_string();

        // 2. Insert into Database
        let res = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?1, ?2, ?3)",
            params![username, password_hash, "Admin"],
        );

        // 3. Handle Errors (like if the username already exists)
        match res {
            Ok(_) => Ok(format!("Admin account '{}' created successfully", username)),
            Err(e) => {
                if e.to_string().contains("UNIQUE constraint failed") {
                    Err(pyo3::exceptions::PyValueError::new_err(
                        "Username already exists",
                    ))
                } else {
                    Err(pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
                }
            }
        }
    }
    fn create_user_account(&self, username: String, password: String) -> PyResult<String> {
        let mut guard = self.conn.lock().unwrap();
        let conn = guard
            .as_mut()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        // 1. Hash the password
        // Argon2 handles the salt automatically using OsRng (secure random)
        let salt = SaltString::generate(&mut OsRng);
        let argon2 = Argon2::default();
        let password_hash = argon2
            .hash_password(password.as_bytes(), &salt)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?
            .to_string();

        // 2. Insert into Database
        let res = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?1, ?2, ?3)",
            params![username, password_hash, "User"],
        );

        // 3. Handle Errors (like if the username already exists)
        match res {
            Ok(_) => Ok(format!("User account '{}' created successfully", username)),
            Err(e) => {
                if e.to_string().contains("UNIQUE constraint failed") {
                    Err(pyo3::exceptions::PyValueError::new_err(
                        "Username already exists",
                    ))
                } else {
                    Err(pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
                }
            }
        }
    }

    //change later temp notes from ai to help//
    // fn create_admin_account(&self, username: String, password: String) -> PyResult<String> {
    //     let mut guard = self.conn.lock().unwrap();
    //     let conn = guard
    //         .as_mut()
    //         .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

    //     // Now OsRng will be recognized!
    //     let salt = SaltString::generate(&mut OsRng);
    //     let argon2 = Argon2::default();

    //     let password_hash = argon2
    //         .hash_password(password.as_bytes(), &salt)
    //         .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?
    //         .to_string();
    //     // 2. Insert into Database
    //     let res = conn.execute(
    //         "INSERT INTO users (username, password_hash, role) VALUES (?1, ?2, ?3)",
    //         params![username, password_hash, "admin"],
    //     );

    //     // 3. Handle Errors (like if the username already exists)
    //     match res {
    //         Ok(_) => Ok(format!("Admin account '{}' created successfully", username)),
    //         Err(e) => {
    //             if e.to_string().contains("UNIQUE constraint failed") {
    //                 Err(pyo3::exceptions::PyValueError::new_err(
    //                     "Username already exists",
    //                 ))
    //             } else {
    //                 Err(pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    //             }
    //         }
    //     }
    // }

    fn account_exisiting_check(&self) -> PyResult<(bool, bool)> {
        let guard = self.conn.lock().unwrap();

        // Check if connection is still open
        let conn = guard
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        // We query the total count and the count of admins in one go.
        // SUM(CASE...) is a common SQL trick to count specific types of rows.
        let mut stmt = conn
            .prepare("SELECT COUNT(*), SUM(CASE WHEN role = 'Admin' THEN 1 ELSE 0 END) FROM users")
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        // query_row returns a single row of results
        let result: (i32, i32) = stmt
            .query_row([], |row| {
                Ok((
                    row.get(0)?,                                // Total users
                    row.get::<_, Option<i32>>(1)?.unwrap_or(0), // Admin users (handles NULL if table is empty)
                ))
            })
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let any_exists = result.0 > 0;
        let admin_exists = result.1 > 0;

        // Rust returns a tuple, Python receives (True/False, True/False)
        Ok((any_exists, admin_exists))
    }

    fn list_tables(&self) -> PyResult<Vec<String>> {
        let guard = self.conn.lock().unwrap();

        // Check if connection is still open
        let conn = guard
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        let mut stmt = conn
            .prepare(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
            )
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let table_iter = stmt
            .query_map([], |row| row.get(0))
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let mut tables = Vec::new();
        for name in table_iter {
            tables
                .push(name.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?);
        }
        Ok(tables)
    }

    /// Manually closes the connection
    fn close(&self) -> PyResult<()> {
        let mut guard = self.conn.lock().unwrap();

        // By setting the Option to None, the Connection is dropped and closed
        *guard = None;

        println!("Rust: Database connection closed.");
        Ok(())
    }
    // Changed to get_user_notes to match your table schema
    fn get_user_notes(&self, owner_id: i32) -> PyResult<Vec<String>> {
        let guard = self.conn.lock().unwrap();

        // If the connection has been closed (None), return an error to Python.
        let conn = guard
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Connection is closed"))?;

        let mut stmt = conn
            .prepare("SELECT title FROM notes WHERE owner_id = ?1")
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let note_iter = stmt
            .query_map([owner_id], |row| row.get(0))
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let mut titles = Vec::new();
        for title in note_iter {
            // Convert rusqlite error to PyErr if a row fails
            titles
                .push(title.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?);
        }
        Ok(titles)
    }
}

#[pymodule]
fn rpydb(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Database>()?;
    Ok(())
}
