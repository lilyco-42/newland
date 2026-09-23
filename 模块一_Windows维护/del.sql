/* =====================================================================
 * del.sql
 * 功能：删除 AD_AccountsRole 中与 AD_Accounts 用户表无关联的关系数据
 * 数据库：SQL Server (nleedge)
 *
 * 性能优化说明：
 *   1. 为关联字段 AccountId、RoleId 建立索引，
 *      关联查询可走索引查找(Nested Loop)，避免全表扫描；
 *   2. 使用 LEFT JOIN 反连接(反半连接)定位“不存在匹配账号”的行，
 *      支持哈希/合并连接，性能优于 NOT IN（NOT IN 遇到 NULL 还会出错）；
 *   3. 对驱动表引用聚集索引 PK_AD_Accounts 进一步提高关联速度。
 * ===================================================================== */

USE nleedge;
GO

-- 1. 为关联字段建立索引，保证关联查询性能
IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = N'IX_AR_AccountId' AND object_id = OBJECT_ID(N'dbo.AD_AccountsRole'))
    CREATE INDEX IX_AR_AccountId ON dbo.AD_AccountsRole(AccountId);

IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = N'IX_AR_RoleId' AND object_id = OBJECT_ID(N'dbo.AD_AccountsRole'))
    CREATE INDEX IX_AR_RoleId ON dbo.AD_AccountsRole(RoleId);
GO

-- 2. 删除与 AD_Accounts 无关联的数据
DELETE r
FROM dbo.AD_AccountsRole r
LEFT JOIN dbo.AD_Accounts a WITH (INDEX = PK_AD_Accounts)
    ON r.AccountId = a.AccountId
WHERE a.AccountId IS NULL;
GO

-- 3. 显示删除的影响行数
SELECT @@ROWCOUNT AS [删除记录数];
GO