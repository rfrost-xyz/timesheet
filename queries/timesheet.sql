-- Pivot log hours by Project/Stage for a specific ISO week
-- Replace :year and :week with the target year and week number

-- Common Table Expression to hold input parameters
WITH InputParams AS (
    SELECT 2024 AS target_year, 10 AS target_week -- e.g., '2023', 20
),
-- CTE to calculate the start date (Monday) of the target ISO week
TargetWeekRange AS (
    SELECT
        target_year,
        target_week,
        -- Calculate the date of the Monday of the target week W
        date(
            date(date(target_year || '-01-04'), '-' || CAST(((CAST(strftime('%w', date(target_year || '-01-04')) AS INTEGER) + 6) % 7) AS TEXT) || ' days'),
            '+' || CAST(((target_week - 1) * 7) AS TEXT) || ' days'
        ) AS start_of_target_week
    FROM InputParams
),
-- CTE to filter logs for the target week and calculate duration in hours
LogDurations AS (
    SELECT
        p.name AS project_name, -- Original name from project table
        s.name AS stage_name,   -- Original name from stage table
        l.start,
        l.end,
        -- Calculate duration in hours (using julianday for precision)
        (julianday(l.end) - julianday(l.start)) * 24.0 AS duration_hours,
        -- Extract the date part of the start time
        date(l.start) AS log_date
    FROM
        log l
    LEFT JOIN
        stage s ON l.stage_id = s.id
    LEFT JOIN
        project p ON s.project_id = p.id
    CROSS JOIN -- Make target week start date available for filtering
        TargetWeekRange twr
    WHERE
        -- Filter logs to include only those starting within the target week
        l.start >= twr.start_of_target_week
        AND l.start < date(twr.start_of_target_week, '+7 days') -- Up to (but not including) the next Monday
),
-- CTE for calculating hours per project/stage/day
PivotedData AS (
    SELECT
        ld.project_name,
        ld.stage_name,
        ROUND(SUM(CASE WHEN ld.log_date = twr.start_of_target_week THEN ld.duration_hours ELSE 0 END), 2) AS "Mon",
        ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+1 day') THEN ld.duration_hours ELSE 0 END), 2) AS "Tue",
        ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+2 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Wed",
        ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+3 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Thu",
        ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+4 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Fri",
        ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+5 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Sat",
        ROUND(SUM(CASE WHEN ld.log_date = date(twr.start_of_target_week, '+6 days') THEN ld.duration_hours ELSE 0 END), 2) AS "Sun",
        ROUND(SUM(ld.duration_hours), 2) AS "Total"
    FROM
        LogDurations ld
    CROSS JOIN -- Make target week start date available for calculations
        TargetWeekRange twr
    GROUP BY
        ld.project_name,
        ld.stage_name
)
-- Final SELECT from the pivoted data, applying new column aliases
SELECT
    project_name AS project,
    stage_name AS name,
    "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total"
FROM PivotedData
ORDER BY
    project,
    name;