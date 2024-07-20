# Timesheet

This is a Python-based timesheet management application that helps you track time entries for different projects, stages and tasks. The script interacts with an SQLite database to store and retrieve time tracking data.

## Features
- Add time entries for specific projects, stages, and tasks.
- View timesheets for today, yesterday, or any specified date.
- Interact with the script via a terminal menu for ease of use.

## Prerequisites
- Python 3.x
- SQLite3

## Installation

1. Clone the repository:

```sh
git clone git@github.com:rfrost-xyz/timesheet.git
cd timesheet-management
```

2. Install the required libraries using `venv` or similiar.

```sh
pip install tabulate simple-term-menu
```

3. Ensure you have an SQLite database and the file is resolved in the connection schema.

## Usage
Run the script using the following command:

```sh
./main.py
```

You can also directly view the timesheet for a specific date using the command line argument:

```sh
main.py --timesheet YYYY-MM-DD
```

## Database Schema
Make sure your SQLite database has the following tables:

### client Table
```sql
Copy code
CREATE TABLE client (
    clientID INTEGER PRIMARY KEY,
    clientName TEXT NOT NULL
);
```

### project Table
```sql
CREATE TABLE project (
    projectId INTEGER PRIMARY KEY,
    projectCode TEXT NOT NULL,
    projectSubCode TEXT,
    projectName TEXT NOT NULL,
    clientId INTEGER,
    FOREIGN KEY (clientId) REFERENCES client (clientID)
);
```

### stage Table
```sql
CREATE TABLE stage (
    stageId INTEGER PRIMARY KEY,
    stageName TEXT NOT NULL,
    projectId INTEGER,
    FOREIGN KEY (projectId) REFERENCES project (projectId)
);
```

### task Table
```sql
CREATE TABLE task (
    taskId INTEGER PRIMARY KEY,
    taskName TEXT NOT NULL,
    projectId INTEGER,
    stageId INTEGER,
    FOREIGN KEY (projectId) REFERENCES project (projectId),
    FOREIGN KEY (stageId) REFERENCES stage (stageId)
);
```

### time Table
```sql
CREATE TABLE time (
    timeId INTEGER PRIMARY KEY,
    userId INTEGER,
    stageId INTEGER,
    taskId INTEGER,
    startTime TEXT NOT NULL,
    endTime TEXT NOT NULL,
    FOREIGN KEY (stageId) REFERENCES stage (stageId),
    FOREIGN KEY (taskId) REFERENCES task (taskId)
);
```
