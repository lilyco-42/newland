SELECT
  table_name AS 表名,
  table_rows AS 记录数
FROM
  information_schema.TABLES
WHERE
  table_schema = 'nleedge';