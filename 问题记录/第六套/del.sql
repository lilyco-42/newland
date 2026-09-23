/* ============================================================
   del.sql
   删除 AD_AccountsRole 中不属于 AD_Accounts 的孤儿关系数据
   性能说明：
     - 采用 NOT EXISTS 关联子查询，SQL Server 优化器会把它
       改写成 LEFT ANTI SEMI JOIN（对 AD_Accounts.AccountId
       的主键聚集索引做 Index Seek），无需全表扫描关系表，
       也可避免 NOT IN 在遇到 NULL 时的语义陷阱。
     - 可在执行计划中观察到 Nested Loops (Left Anti Semi Join)
       或 Hash Match (Left Anti Semi Join)。
   ============================================================ */
USE nleedge;
GO

SET NOCOUNT ON;

BEGIN TRANSACTION;

DELETE ar
FROM dbo.AD_AccountsRole ar
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.AD_Accounts a
    WHERE a.AccountId = ar.AccountId
);

PRINT 'Deleted orphan rows: ' + CAST(@@ROWCOUNT AS VARCHAR(10));

COMMIT TRANSACTION;
GO

-- 删除后再次统计，便于核对
SELECT 'AD_Accounts'     AS TableName, COUNT(*) AS [RowCount] FROM dbo.AD_Accounts
UNION ALL
SELECT 'AD_Roles'       AS TableName, COUNT(*) AS [RowCount] FROM dbo.AD_Roles
UNION ALL
SELECT 'AD_AccountsRole' AS TableName, COUNT(*) AS [RowCount] FROM dbo.AD_AccountsRole;
GO
