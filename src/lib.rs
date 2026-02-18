use pyo3::prelude::*;
use rusqlite::{Connection, Result};
use std::path::Path;
use std::sync::Mutex;

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

    //change later temp notes from ai to help//
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
