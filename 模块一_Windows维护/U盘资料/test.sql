/* =====================================================================
   数据库：nleedge
   功能：还原 AD_Accounts(用户表)、AD_Roles(角色表)、AD_AccountsRole(用户角色关系表)
   说明：AD_AccountsRole 中故意保留部分与 AD_Accounts 无关联的孤儿数据，
         供删除关联数据任务使用。
   ===================================================================== */

IF DB_ID(N'nleedge') IS NULL
    CREATE DATABASE nleedge;
GO

USE nleedge;
GO

IF OBJECT_ID(N'dbo.AD_AccountsRole', N'U') IS NOT NULL DROP TABLE dbo.AD_AccountsRole;
IF OBJECT_ID(N'dbo.AD_Roles', N'U') IS NOT NULL DROP TABLE dbo.AD_Roles;
IF OBJECT_ID(N'dbo.AD_Accounts', N'U') IS NOT NULL DROP TABLE dbo.AD_Accounts;
GO

/* ------------------- 用户表 ------------------- */
CREATE TABLE dbo.AD_Accounts
(
    AccountId   INT          NOT NULL CONSTRAINT PK_AD_Accounts PRIMARY KEY,
    AccountName NVARCHAR(50) NOT NULL,
    Password    NVARCHAR(64) NOT NULL,
    FullName    NVARCHAR(50) NULL,
    Phone       NVARCHAR(20) NULL
);
GO

/* ------------------- 角色表 ------------------- */
CREATE TABLE dbo.AD_Roles
(
    RoleId      INT          NOT NULL CONSTRAINT PK_AD_Roles PRIMARY KEY,
    RoleName    NVARCHAR(50) NOT NULL,
    Description NVARCHAR(100) NULL
);
GO

/* ------------------- 用户角色关系表 ------------------- */
CREATE TABLE dbo.AD_AccountsRole
(
    Id        INT NOT NULL CONSTRAINT PK_AD_AccountsRole PRIMARY KEY IDENTITY(1,1),
    AccountId INT NOT NULL,
    RoleId    INT NOT NULL
);
GO

/* ------------------- 数据 ------------------- */
INSERT INTO dbo.AD_Accounts(AccountId, AccountName, Password, FullName, Phone) VALUES
(1,  N'admin',    N'123456', N'系统管理员', N'13800000001'),
(2,  N'zhangsan', N'123456', N'张三',       N'13800000002'),
(3,  N'lisi',     N'123456', N'李四',       N'13800000003'),
(4,  N'wangwu',   N'123456', N'王五',       N'13800000004'),
(5,  N'zhaoliu',  N'123456', N'赵六',       N'13800000005'),
(6,  N'sunqi',    N'123456', N'孙七',       N'13800000006'),
(7,  N'zhouba',   N'123456', N'周八',       N'13800000007'),
(8,  N'wujiu',    N'123456', N'吴九',       N'13800000008'),
(9,  N'zhengshi', N'123456', N'郑十',       N'13800000009'),
(10, N'cheng11',  N'123456', N'陈十一',     N'13800000010');
GO

INSERT INTO dbo.AD_Roles(RoleId, RoleName, Description) VALUES
(1, N'超级管理员', N'拥有系统全部权限'),
(2, N'管理员',     N'负责系统日常运维'),
(3, N'操作员',     N'负责数据采集与监控'),
(4, N'质检员',     N'负责数据质量检查'),
(5, N'访客',       N'仅可查看公开数据');
GO

INSERT INTO dbo.AD_AccountsRole(AccountId, RoleId) VALUES
(1, 1), (2, 3), (2, 4), (3, 3),
(4, 5), (5, 2), (6, 3), (7, 4),
(8, 5), (9, 3), (10, 2),
/* -------- 以下为与 AD_Accounts 无关联的孤儿数据 -------- */
(11, 3), (12, 1), (13, 5);
GO