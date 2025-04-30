# utils.py
# Helper functions for time manipulation, validation, and logging setup

import datetime
from dateutil.relativedelta import relativedelta
import pathlib
import shutil
import logging # <<< Import logging module

# Import configuration constants
from config import (
    TIME_INCREMENT_MINUTES,
    DATABASE_PATH,
    BACKUP_PATH,
    LAST_BACKUP_TIMESTAMP_FILE,
    BACKUP_INTERVAL_DAYS,
    LOG_FILE_PATH # <<< Import log file path
)

# --- Logging Setup ---
def setup_logging():
    """Configures basic file logging."""
    # Basic configuration: append to file, include timestamp and level
    # Use basicConfig to set up the root logger
    logging.basicConfig(
        level=logging.DEBUG, # Log DEBUG level and above
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        filename=LOG_FILE_PATH,
        filemode='a' # Append mode ('w' to overwrite each time)
    )
    # Optional: Add a handler to also print logs to console during development
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO) # Or DEBUG
    # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # console_handler.setFormatter(formatter)
    # logging.getLogger('').addHandler(console_handler) # Add handler to root logger
    logging.info("--- Logging initialized ---") # Log initialization


# --- Time Handling ---
# (Keep existing time functions: snap_time_to_interval, parse_datetime_string, etc.)
def snap_time_to_interval(dt: datetime.datetime, interval_minutes: int = TIME_INCREMENT_MINUTES) -> datetime.datetime:
    """Rounds a datetime object down to the nearest specified minute interval."""
    if not isinstance(dt, datetime.datetime):
        return datetime.datetime.now() # Fallback
    if interval_minutes <= 0:
        return dt

    discard = datetime.timedelta(minutes=dt.minute % interval_minutes,
                                 seconds=dt.second,
                                 microseconds=dt.microsecond)
    return dt - discard

def parse_datetime_string(datetime_str: str, fmt: str = '%Y-%m-%d %H:%M') -> datetime.datetime | None:
    """Parses a datetime string into a datetime object."""
    try:
        if isinstance(datetime_str, str):
            return datetime.datetime.strptime(datetime_str, fmt)
        return None
    except (ValueError, TypeError):
        return None

def format_datetime_string(dt: datetime.datetime, fmt: str = '%Y-%m-%d %H:%M') -> str:
    """Formats a datetime object into a string."""
    if not isinstance(dt, datetime.datetime):
        return ""
    return dt.strftime(fmt)

def format_date_string(dt: datetime.date, fmt: str = '%Y-%m-%d') -> str:
    """Formats a date object into a string."""
    if not isinstance(dt, (datetime.date, datetime.datetime)):
        return ""
    return dt.strftime(fmt)

# --- Validation Helpers ---
def validate_datetime_format(value: str) -> bool:
    """Check if string matches YYYY-MM-DD HH:MM format."""
    return parse_datetime_string(value) is not None

def validate_iso_week(value: str) -> bool:
    """Check if string is an integer between 1 and 53."""
    try:
        week = int(value)
        return 1 <= week <= 53
    except ValueError:
        return False

# --- Backup Logic (Optional - Not used by simplified UI) ---
# (Include backup functions if needed)

