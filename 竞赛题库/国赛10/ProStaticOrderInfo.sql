-- ============================================
-- 存储过程：ProStaticOrderInfo
-- 功能：实时统计每日商品销售数量以及销售金额（仅保留最新的统计记录），
--       将统计结果写入 T_OrderInfoStatic 表
-- 说明：T_SQL.sql 生成的订单表假设为 T_OrderInfo
--       （字段：OrderID/OrderDate/Quantity/Amount），
--       若实际表名/字段名不同，请按下划线位置改为实际名称。
-- ============================================
USE TestDataBase;
GO

IF OBJECT_ID('ProStaticOrderInfo', 'P') IS NOT NULL
    DROP PROCEDURE ProStaticOrderInfo;
GO

CREATE PROCEDURE ProStaticOrderInfo
AS
BEGIN
    SET NOCOUNT ON;

    -- 仅保留最新的统计记录：先清空统计表
    DELETE FROM T_OrderInfoStatic;

    -- 按销售日期分组统计：销售数量（件数）、销售金额（金额合计）
    INSERT INTO T_OrderInfoStatic(统计日期, 销售数量, 销售金额)
    SELECT CONVERT(date, OrderDate)            AS 统计日期,
           SUM(Quantity)                       AS 销售数量,
           SUM(Quantity * Amount)              AS 销售金额
    FROM T_OrderInfo
    GROUP BY CONVERT(date, OrderDate);
END
GO

-- 测试执行
-- EXEC ProStaticOrderInfo;
-- GO