# Output Contract

## db_inspector.py

顶层字段：

- `connection`: 连接来源和 JDBC 解析结果
- `database_summary`: 表数量和表名概览
- `tables`: 每张表的完整结构
- `warnings`: 非阻塞告警
- `generated_at`: ISO 8601 时间

### connection

```json
{
  "db_type": "mysql",
  "host": "localhost",
  "port": 3306,
  "database": "a-20",
  "params": {
    "serverTimezone": "Asia/Shanghai"
  },
  "source": "src/main/resources/application.yml"
}
```

### tables[]

```json
{
  "name": "sys_user",
  "comment": "用户表",
  "engine": "InnoDB",
  "charset": "utf8mb4",
  "estimated_rows": 1200,
  "estimated_rows_is_approximate": true,
  "primary_key": ["id"],
  "columns": [],
  "indexes": [],
  "foreign_keys": [],
  "sample_rows": []
}
```

`columns[]` 至少包含：

- `name`
- `ordinal_position`
- `data_type`
- `column_type`
- `length`
- `numeric_precision`
- `numeric_scale`
- `nullable`
- `default`
- `comment`
- `auto_increment`
- `unsigned`
- `java_type`
- `sample_excluded`

`indexes[]` 至少包含：

- `name`
- `unique`
- `columns`
- `index_type`

`foreign_keys[]` 至少包含：

- `name`
- `columns`
- `referenced_table`
- `referenced_columns`
- `update_rule`
- `delete_rule`

## crud_planner.py

顶层字段：

- `connection`
- `table_plans`
- `summary`
- `generated_at`

### table_plans[]

```json
{
  "table": "sys_user",
  "summary": "适合标准单表 CRUD，推荐按 create_time 倒序分页。",
  "risks": [],
  "primary_key": ["id"],
  "java_field_hints": [],
  "filters": [],
  "sort_candidates": ["create_time", "id"],
  "query_templates": {}
}
```

`query_templates` 约定这些键：

- `select_page`
- `select_by_primary_key`
- `insert`
- `update_by_primary_key`
- `delete_by_primary_key`
- `logical_delete`

不适用时可以返回 `null`。
