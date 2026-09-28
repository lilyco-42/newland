/* ============================================================
   count.sql
   统计 AD_Accounts / AD_Roles / AD_AccountsRole 三张表的记录数
   ============================================================ */
USE nleedge;
GO

SET NOCOUNT ON;

SELECT 'AD_Accounts'     AS TableName, COUNT(*) AS [RowCount] FROM dbo.AD_Accounts
UNION ALL
SELECT 'AD_Roles'       AS TableName, COUNT(*) AS [RowCount] FROM dbo.AD_Roles
UNION ALL
SELECT 'AD_AccountsRole' AS TableName, COUNT(*) AS [RowCount] FROM dbo.AD_AccountsRole;
GO
