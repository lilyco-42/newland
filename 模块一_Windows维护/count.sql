/* =====================================================================
 * count.sql
 * 功能：统计 AD_Accounts、AD_Roles、AD_AccountsRole 三张表的记录数
 * 数据库：SQL Server (nleedge)
 * ===================================================================== */

USE nleedge;
GO

SELECT N'AD_Accounts'     AS [表名], COUNT(*) AS [记录数] FROM dbo.AD_Accounts
UNION ALL
SELECT N'AD_Roles',       COUNT(*) FROM dbo.AD_Roles
UNION ALL
SELECT N'AD_AccountsRole', COUNT(*) FROM dbo.AD_AccountsRole;
GO