# db.py
# Database interaction logic (Simplified relevant functions + Restored get_log_entries_for_day)

import sqlite3
import datetime
from typing import List, Tuple, Dict, Any, Optional

# Import configuration constants
from config import DATABASE_PATH

# --- Connection ---
def create_connection(db_file: str = str(DATABASE_PATH)) -> Optional[sqlite3.Connection]:
    """Creates a database connection."""
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON;')
        return conn
    except sqlite3.Error as e:
        print(f'SQLite Error connecting to database {db_file}: {e}')
        return None

# --- Generic Helper ---
def _execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False, commit: bool = False) -> Any:
    """Executes a query with error handling."""
    conn = create_connection()
    if not conn:
        return None if fetch_one else ([] if fetch_all else False)
    result = None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch_one:
            row = cursor.fetchone()
            result = dict(row) if row else None # Return dict or None
        elif fetch_all:
            rows = cursor.fetchall()
            result = [dict(row) for row in rows] # Return list of dicts
        elif commit:
            conn.commit()
            result = True
        else:
            result = True
    except sqlite3.Error as e:
        print(f'SQLite Error executing query:\nQuery: {query}\nParams: {params}\nError: {e}')
        if commit:
            try: conn.rollback()
            except sqlite3.Error as rb_err: print(f'SQLite Error during rollback: {rb_err}')
        result = None if fetch_one else ([] if fetch_all else False)
    finally:
        if conn: conn.close()
    return result

# --- Functions needed for Simplified UI ---

def get_all_stages_with_project() -> List[Dict]:
    """ Gets all stages with project names, ordered for selection. """
    query = """
        SELECT s.id, s.name, s.project_id, p.name as project_name
        FROM stage s
        JOIN project p ON s.project_id = p.id
        ORDER BY p.name, s.name
    """
    return _execute_query(query, fetch_all=True)

def get_stages(project_id: Optional[int] = None) -> List[Dict]:
    """Retrieves stages as dictionaries, optionally filtered by project."""
    base_query = """
        SELECT s.id, s.name, s.project_id, p.name as project_name
        FROM stage s
        JOIN project p ON s.project_id = p.id
    """
    params = ()
    if project_id is not None:
        base_query += ' WHERE s.project_id = ?'
        params = (project_id,)
    base_query += ' ORDER BY p.name, s.name'
    return _execute_query(base_query, params, fetch_all=True)

def get_projects() -> List[Dict]:
    """Retrieves all projects with client names as dictionaries."""
    query = """
        SELECT p.id, p.name, p.code, p.sub_code, c.name as client_name, p.client_id
        FROM project p
        LEFT JOIN client c ON p.client_id = c.id
        ORDER BY p.name
    """
    return _execute_query(query, fetch_all=True)


def get_focuses() -> List[Dict]:
    """Retrieves all focuses."""
    query = 'SELECT id, name FROM focus ORDER BY name'
    return _execute_query(query, fetch_all=True)

def add_log_entry(stage_id: int, focus_id: Optional[int], start_time: str, end_time: str) -> bool:
    """Adds a new log entry."""
    query = 'INSERT INTO log (stage_id, focus_id, start, end) VALUES (?, ?, ?, ?)'
    return _execute_query(query, (stage_id, focus_id, start_time, end_time), commit=True)

def get_log_entries_for_day(log_date: str) -> List[Dict]:
    """Retrieves log entries for a specific date as dictionaries."""
    # <<< Added p.id AS project_id >>>
    query = """
        SELECT
            l.id, l.start, l.end,
            s.name AS stage_name,
            p.name AS project_name,
            p.id AS project_id,
            f.name AS focus_name,
            l.stage_id, l.focus_id
        FROM log l
        JOIN stage s ON l.stage_id = s.id
        JOIN project p ON s.project_id = p.id
        LEFT JOIN focus f ON l.focus_id = f.id
        WHERE date(l.start) = date(?)
        ORDER BY l.start
    """
    return _execute_query(query, (log_date,), fetch_all=True)

def update_log_entry(log_id: int, stage_id: int, focus_id: Optional[int], start_time: str, end_time: str) -> bool:
    """Updates an existing log entry."""
    # This function is needed for editing
    query = 'UPDATE log SET stage_id = ?, focus_id = ?, start = ?, end = ? WHERE id = ?'
    return _execute_query(query, (stage_id, focus_id, start_time, end_time, log_id), commit=True)

def delete_log_entry(log_id: int) -> bool:
    """Deletes a log entry."""
    # This function is needed for deleting
    query = 'DELETE FROM log WHERE id = ?'
    return _execute_query(query, (log_id,), commit=True)


def get_latest_log_entry() -> Optional[Dict]:
    """Retrieves the most recent log entry."""
    query = """
        SELECT l.id, l.start, l.end, s.id as stage_id, f.id as focus_id,
               s.name as stage_name, p.name as project_name, f.name as focus_name
        FROM log l
        JOIN stage s on l.stage_id = s.id
        JOIN project p on s.project_id = p.id
        LEFT JOIN focus f on l.focus_id = f.id
        ORDER BY l.end DESC LIMIT 1
    """
    return _execute_query(query, fetch_one=True)

def get_timesheet_report(year: int, week: int) -> List[Dict]:
    """Executes the pivot query for the specified ISO year and week."""
    # Report function remains unchanged
    query = """
        WITH InputParams AS (SELECT ? AS target_year, ? AS target_week),
        TargetWeekRange AS (
            SELECT target_year, target_week,
                   date(date(date(target_year || '-01-04'), '-' || CAST(((CAST(strftime('%w', date(target_year || '-01-04')) AS INTEGER) + 6) % 7) AS TEXT) || ' days'),
                        '+' || CAST(((target_week - 1) * 7) AS TEXT) || ' days') AS start_of_target_week
            FROM InputParams
        ),
        LogDurations AS (
            SELECT p.name AS project_name, s.name AS stage_name, l.start, l.end,
                   (julianday(l.end) - julianday(l.start)) * 24.0 AS duration_hours,
                   date(l.start) AS log_date
            FROM log l
            LEFT JOIN stage s ON l.stage_id = s.id
            LEFT JOIN project p ON s.project_id = p.id
            CROSS JOIN TargetWeekRange twr
            WHERE l.start >= twr.start_of_target_week AND l.start < date(twr.start_of_target_week, '+7 days')
        ),
        PivotedData AS (
            SELECT ld.project_name, ld.stage_name,
                   ROUND(SUM(CASE WHEN ld.log_date = twr.start_of_target_week THEN ld.duration_hours ELSE 0 END), 2) AS "Mon",
                   ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+1 day') THEN ld.duration_hours ELSE 0 END), 2) AS "Tue",
                   ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+2 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Wed",
                   ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+3 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Thu",
                   ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+4 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Fri",
                   ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+5 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Sat",
                   ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+6 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Sun",
                   ROUND(SUM(ld.duration_hours), 2) AS "Total_Week_Hours"
            FROM LogDurations ld
            CROSS JOIN TargetWeekRange twr
            GROUP BY ld.project_name, ld.stage_name
        )
        SELECT project_name AS project, stage_name AS name,
               "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total_Week_Hours"
        FROM PivotedData ORDER BY project, name;
        """
    return _execute_query(query, (str(year), str(week)), fetch_all=True)

