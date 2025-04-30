# main.py
# Main entry point for the simplified Textual timesheet application

import sys
import logging # <<< Import logging
from typing import Type

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Placeholder
from textual.reactive import var
from textual.screen import Screen

# Import configuration, utilities, db, and the main screen from ui.py
import config
import utils # <<< Import utils to call setup_logging
import db
from ui import MainAppScreen


class TimesheetApp(App[None]):
    """Simplified Textual timesheet application."""

    TITLE = "Timesheet Terminal (Keyboard)"
    SUB_TITLE = "Daily Log Entry"
    CSS_PATH = "main.css"
    BINDINGS = [
        ("q", "quit", "Quit App"),
    ]

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        logging.info("Timesheet App Mounted.")
        self.push_screen(MainAppScreen())

    # action_quit is handled by the default App implementation


def check_database():
    """Checks if the database file exists and attempts schema creation if not."""
    if not config.DATABASE_PATH.exists():
         logging.warning(f'Database file not found at {config.DATABASE_PATH}')
         try:
             schema_path = config.BASE_DIR / 'schema.sql'
             if schema_path.exists():
                 conn = db.create_connection()
                 if conn:
                     logging.info(f'Attempting to create schema from {schema_path}...')
                     with open(schema_path, 'r') as f: schema_sql = f.read()
                     conn.executescript(schema_sql)
                     conn.close()
                     logging.info('Database schema created successfully.')
                     return True
                 else:
                     logging.error('Failed to connect to database to create schema.')
                     return False
             else:
                 logging.error(f'Schema file ({schema_path}) not found. Cannot create database.')
                 logging.error('Please create the database and schema manually.')
                 return False
         except Exception as e:
              logging.exception(f'Failed to create schema: {e}') # Log full traceback
              return False
    logging.info("Database check passed.")
    return True


if __name__ == "__main__":
    # <<< Setup Logging >>>
    utils.setup_logging()
    logging.info("--- Application Start ---")

    # Optional: Backup check (commented out)
    # try:
    #     logging.info("Performing startup checks...")
    #     # utils.check_and_perform_backup()
    # except Exception as e:
    #     logging.exception('Error during startup backup check')

    # Ensure database exists before starting the app
    if not check_database():
        logging.critical("Database check failed. Exiting.")
        sys.exit(1)

    # Run the Textual app
    app = TimesheetApp()
    app.run()
    logging.info("--- Application Finish ---")

