#!/usr/bin/python3

import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate
from simple_term_menu import TerminalMenu
import argparse

# Define the get_current_date function
def get_current_date():
    return datetime.today().date()

# Define the get_previous_date function
def get_yesterday_date():
    # Calculate the date of yesterday
    yesterday_date = datetime.now().date() - timedelta(days=1)
    return yesterday_date

# Function to retrieve projects from the database
def get_projects(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT projectId, projectCode, projectSubCode, projectName, clientName FROM project INNER JOIN client ON project.clientID = client.clientID")
        projects = cursor.fetchall()
        return projects
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

# Function to retrieve stages for a given project from the database
def stages(connection, project_id):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT stageId, stageName FROM stage WHERE projectId = ?", (project_id,))
        stages = cursor.fetchall()
        return stages
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

# Function to retrieve tasks for a given project and stage from the database
def tasks(connection, project_id, stage_id):
    try:
        cursor = connection.cursor()

        if project_id in [1, 2]:
            query = "SELECT taskId, taskName FROM task WHERE projectId = ? AND stageId = ?"
            params = (project_id, stage_id)
        else:
            query = "SELECT taskId, taskName FROM task WHERE projectId IS NULL AND stageId IS NULL"
            params = ()

        cursor.execute(query, params)
        tasks = cursor.fetchall()
        return tasks
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

# Function to add a time entry to the database
def add_time_entry(connection, user_id, stage_id, task_id, start_time, end_time):
    try:
        cursor = connection.cursor()
        
        # Format start_time and end_time to 'YYYY-MM-DDTHH:MM' format
        formatted_start_time = start_time.strftime("%Y-%m-%dT%H:%M")
        formatted_end_time = end_time.strftime("%Y-%m-%dT%H:%M")
        
        # Insert the time entry into the 'time' table
        cursor.execute("INSERT INTO time (userId, stageId, taskId, startTime, endTime) VALUES (?, ?, ?, ?, ?)",
                       (user_id, stage_id, task_id, formatted_start_time, formatted_end_time))
        
        # Commit the transaction
        connection.commit()
        
        print("Time entry added successfully!")

        # Display all time entries for the specified date
        display_time_entries_for_specific_date(connection, start_time.date())

    except sqlite3.Error as e:
        connection.rollback()  # Rollback the transaction in case of error
        print(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()

# Function to handle time entry option
def handle_time_entry(connection):
    projects_data = get_projects(connection)
    project_options = [f"{project[1]}{'_' + project[2] if project[2] else ''}: {project[4]} {project[3]}" for project in projects_data]
    terminal_menu = TerminalMenu(project_options)
    menu_entry_index = terminal_menu.show()
    selected_project = projects_data[menu_entry_index]
    print(f"You have selected {selected_project[1]}-{selected_project[2]}: {selected_project[4]} {selected_project[3]} with ID {selected_project[0]}!")

    # Get stage selection
    project_stages = stages(connection, selected_project[0])
    stage_options = [stage[1] for stage in project_stages]

    if stage_options:
        stage_menu = TerminalMenu(stage_options)
        stage_menu_index = stage_menu.show()
        selected_stage = project_stages[stage_menu_index]
        print(f"You have selected stage '{selected_stage[1]}' with ID '{selected_stage[0]}'")
    else:
        print("No stages found for the selected project.")
        return

    # Get task selection based on task group
    project_tasks = tasks(connection, selected_project[0], selected_stage[0])
    
    if project_tasks:
        task_options = [task[1] for task in project_tasks]
        task_menu = TerminalMenu(task_options)
        task_menu_index = task_menu.show()
        selected_task = project_tasks[task_menu_index]
        print(f"You have selected task '{selected_task[1]}' with ID '{selected_task[0]}'")
    else:
        print("No tasks found for the selected project.")
        return

    # Prompt for date, start time, and end time
    date_input = input("Enter date in ISO 8601 format (YYYY-MM-DD): ")
    start_time = input("Enter start time (HH:MM): ")
    end_time = input("Enter end time (HH:MM): ")

    # Format date, start time, and end time
    start_datetime = datetime.strptime(f"{date_input} {start_time}", "%Y-%m-%d %H:%M")
    end_datetime = datetime.strptime(f"{date_input} {end_time}", "%Y-%m-%d %H:%M")

    # Add the time entry to the database
    add_time_entry(connection, 1, selected_stage[0], selected_task[0], start_datetime, end_datetime)

# Function to handle today's timesheet option and return data as a formatted table
def handle_today_timesheet(connection):
    try:
        cursor = connection.cursor()

        # Get the current date using the get_current_date function
        current_date = get_current_date()

        # Define the SQL statement to select all columns from the 'project' table
        sql_statement = f"SELECT c.clientName AS client, (p.projectCode || COALESCE(': ' || p.projectSubCode, '') || ': ' || p.projectName) AS project, s.stageName AS stage, ROUND(SUM(julianday(t.endTime) - julianday(t.startTime)) * 24, 2) AS duration FROM time t LEFT JOIN stage s ON t.stageId = s.stageId LEFT JOIN project p ON s.projectId = p.projectId LEFT JOIN client c ON p.clientId = c.clientID WHERE DATE(t.startTime) = DATE('{current_date}') GROUP BY (p.projectCode || COALESCE(': ' || p.projectSubCode, '')), c.clientName, s.stageName ORDER BY project;"

        # Execute the SQL statement
        cursor.execute(sql_statement)

        # Fetch all rows from the result set
        rows = cursor.fetchall()

        # Get column names
        headers = [desc[0] for desc in cursor.description]

        # Format data into a table
        table = tabulate(rows, headers=headers, tablefmt="rounded_outline")

        # Display time entries for today
        display_time_entries_for_specific_date(connection, current_date)

        # Print timesheet for today
        print("\nTimesheet for " + str(current_date))
        print(table)

        # Close the cursor
        cursor.close()

    except sqlite3.Error as e:
        print(f"Database error: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Function to handle yesterday's timesheet option
def handle_yesterday_timesheet(connection):
    try:
        cursor = connection.cursor()

        # Get the current date using the get_current_date function
        yesterday_date = get_yesterday_date()

        # Define the SQL statement to select all columns from the 'project' table
        sql_statement = f"SELECT c.clientName AS client, (p.projectCode || COALESCE(': ' || p.projectSubCode, '') || ': ' || p.projectName) AS project, s.stageName AS stage, ROUND(SUM(julianday(t.endTime) - julianday(t.startTime)) * 24, 2) AS duration FROM time t LEFT JOIN stage s ON t.stageId = s.stageId LEFT JOIN project p ON s.projectId = p.projectId LEFT JOIN client c ON p.clientId = c.clientID WHERE DATE(t.startTime) = DATE('{yesterday_date}') GROUP BY (p.projectCode || COALESCE(': ' || p.projectSubCode, '')), c.clientName, s.stageName ORDER BY project;"

        # Execute the SQL statement
        cursor.execute(sql_statement)

        # Fetch all rows from the result set
        rows = cursor.fetchall()

        # Get column names
        headers = [desc[0] for desc in cursor.description]

        # Format data into a table
        table = tabulate(rows, headers=headers, tablefmt="rounded_outline")

        # Display time entries for yesterday
        display_time_entries_for_specific_date(connection, yesterday_date)

        # Print timesheet for yesterday
        print("\nTimesheet for " + str(yesterday_date))
        print(table)

        # Close the cursor
        cursor.close()

    except sqlite3.error as e:
        print(f"database error: {e}")

    except exception as e:
        print(f"an error occurred: {e}")

# Function to handle timesheet for specific date option
def handle_specific_date_timesheet(connection, specified_date):
    try:
        cursor = connection.cursor()

        # Define the SQL statement to select timesheet data for the specified date
        sql_statement = f"SELECT c.clientName AS client, (p.projectCode || COALESCE(': ' || p.projectSubCode, '') || ': ' || p.projectName) AS project, s.stageName AS stage, ROUND(SUM(julianday(t.endTime) - julianday(t.startTime)) * 24, 2) AS duration FROM time t LEFT JOIN stage s ON t.stageId = s.stageId LEFT JOIN project p ON s.projectId = p.projectId LEFT JOIN client c ON p.clientId = c.clientID WHERE DATE(t.startTime) = DATE(?) GROUP BY (p.projectCode || COALESCE(': ' || p.projectSubCode, '')), c.clientName, s.stageName ORDER BY project;"

        # Execute the SQL statement with the specified date parameter
        cursor.execute(sql_statement, (specified_date,))

        # Fetch all rows from the result set
        rows = cursor.fetchall()

        # Get column names
        headers = [desc[0] for desc in cursor.description]

        # Format data into a table
        table = tabulate(rows, headers=headers, tablefmt="rounded_outline")

        # Display time entries for specified date
        display_time_entries_for_specific_date(connection, specified_date)

        # Print timesheet for specified date
        print("\nTimesheet for " + str(specified_date))
        print(table)

        # Close the cursor
        cursor.close()

    except sqlite3.Error as e:
        print(f"Database error: {e}")

    except ValueError as e:
        print("Invalid date format. Please enter the date in the correct format (YYYY-MM-DD).")

    except Exception as e:
        print(f"An error occurred: {e}")

# Function to display time entries for a specific date
def display_time_entries_for_specific_date(connection, date):
    try:
        cursor = connection.cursor()

        # Define the SQL statement to select time entries for the specified date
        sql_statement = "SELECT t.timeId, c.clientName, p.projectName, s.stageName, ts.taskName, t.startTime, t.endTime FROM time t LEFT JOIN stage s ON t.stageId = s.stageId LEFT JOIN project p ON s.projectId = p.projectId LEFT JOIN client c ON p.clientId = c.clientId LEFT JOIN task ts ON t.taskId = ts.taskId WHERE DATE(t.startTime) = DATE(?)"

        # Execute the SQL statement with the specified date parameter
        cursor.execute(sql_statement, (date,))

        # Fetch all rows from the result set
        rows = cursor.fetchall()

        # Convert string representations of time to datetime objects
        rows = [(time_id, client, project, stage, task, datetime.strptime(start, '%Y-%m-%dT%H:%M'), datetime.strptime(end, '%Y-%m-%dT%H:%M')) for time_id, client, project, stage, task, start, end in rows]

        # Format the time entries
        formatted_rows = [(time_id, client, project, stage, task, start.strftime('%H:%M'), end.strftime('%H:%M')) for time_id, client, project, stage, task, start, end in rows]

        # Print the time entries for the specified date
        if formatted_rows:
            headers = ["timeID", "client", "project", "stage", "task", "start", "end"]
            table = tabulate(formatted_rows, headers=headers, tablefmt="rounded_outline")
            print(f"\nAll time entries for {date}:")
            print(table)
        else:
            print("\nNo time entries found for the specified date.")

        # Close the cursor
        cursor.close()

    except sqlite3.Error as e:
        print(f"Database error: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Timesheet management script.")
    parser.add_argument("-t", "--timesheet", help="Show timesheet for a specific date (format: YYYY-MM-DD).")
    args = parser.parse_args()

    try:
        connection = sqlite3.connect("/mnt/g/My Drive/DB/Timesheet/Timesheet.db")
        if args.timesheet:
            specified_date = datetime.strptime(args.timesheet, "%Y-%m-%d").date()
            handle_specific_date_timesheet(connection, specified_date)
        else:
            initial_options = ["Time Entry", "Today's Timesheet", "Yesterday's Timesheet", "Timesheet for Specific Date"]
            initial_functions = [
                lambda conn=connection: handle_time_entry(conn), 
                lambda conn=connection: handle_today_timesheet(conn), 
                lambda conn=connection: handle_yesterday_timesheet(conn),
                lambda conn=connection: handle_specific_date_timesheet(conn, None)]
            initial_menu = TerminalMenu(initial_options)
            initial_menu_index = initial_menu.show()
            initial_functions[initial_menu_index]()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        print("") # blank last line
        if connection:
            connection.close()

if __name__ == "__main__":
    main()
