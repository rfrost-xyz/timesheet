SELECT
    c.clientName AS client,
    CONCAT(CONCAT(p.projectCode, COALESCE(': ' || p.projectSubCode, '')), ': ', p.projectName) AS project,
    task.taskName AS task,
    ROUND(SUM(julianday(t.endTime) - julianday(t.startTime)) * 24, 2) AS duration
FROM time t
LEFT JOIN task ON t.taskId = task.taskId
LEFT JOIN stage s ON t.stageId = s.stageId
LEFT JOIN project p ON s.projectId = p.projectId
LEFT JOIN client c ON p.clientId = c.clientID
WHERE DATE(t.startTime) = DATE('2024-04-17')
GROUP BY CONCAT(p.projectCode, COALESCE(': ' || p.projectSubCode, '')), c.clientName, task.taskName
ORDER BY project;
