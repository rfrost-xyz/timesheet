# Configuration settings for the timesheet application

import pathlib

# --- Database Configuration ---
BASE_DIR = pathlib.Path(__file__).parent.resolve()
DATABASE_PATH = BASE_DIR / 'data.db'

# --- Logging Configuration ---
LOG_FILE_PATH = BASE_DIR / 'error.log'

# --- Time Configuration ---
TIME_INCREMENT_MINUTES = 15

# --- Backup Configuration (Optional - Not used by simplified UI) ---
BACKUP_PATH = BASE_DIR / 'backups'
BACKUP_INTERVAL_DAYS = 1
LAST_BACKUP_TIMESTAMP_FILE = BASE_DIR / BACKUP_PATH / '.last_backup'