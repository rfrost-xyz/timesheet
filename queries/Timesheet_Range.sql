SELECT
    c.clientName AS client,
    CONCAT(CONCAT(p.projectCode, COALESCE(': ' || p.projectSubCode, '')), ': ', p.projectName) AS project,
    ROUND(SUM(julianday(t.endTime) - julianday(t.startTime)) * 24, 2) AS duration
FROM time t
LEFT JOIN stage s ON t.stageId = s.stageId
LEFT JOIN project p ON s.projectId = p.projectId
LEFT JOIN client c ON p.clientId = c.clientID
WHERE DATE(t.startTime) BETWEEN '2023-01-01' AND '2025-01-01'
GROUP BY CONCAT(p.projectCode, COALESCE(': ' || p.projectSubCode, '')), c.clientName
ORDER BY project;
