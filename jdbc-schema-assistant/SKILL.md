---
name: jdbc-schema-assistant
description: 读取 Spring 配置或显式 JDBC MySQL 连接信息，探查数据库表结构、索引、约束与样例数据，并生成结构化 JSON 和 CRUD/条件查询辅助规划，适用于 Spring/MyBatis/JPA 开发中的库表理解、SQL 调整与排障。
---

# JDBC Schema Assistant

这个 skill 用于把“从 Spring 配置找数据源、连 MySQL、人工整理表结构、再手写 CRUD 草稿”的重复工作收敛成稳定脚本。

默认目标是探查和规划，不直接改库。第一版只支持 MySQL 单数据源。

## 适用场景

- 用户给出 Spring 项目目录，希望自动读取 `application.yml`、`application.yaml` 或 `application.properties`
- 需要快速获取数据库、表、字段、索引、外键、样例数据
- 需要为增删改查、分页列表、条件筛选、排序字段提供 SQL 模板或开发建议
- 需要把结果输出成稳定 JSON，供后续脚本、AI 或人工继续消费

## 默认流程

1. 优先运行 `db_inspector.py` 获取 schema JSON
2. 再用 `crud_planner.py` 基于 schema JSON 生成 CRUD 规划
3. 默认只读，不执行任何写库 SQL

## 主要命令

从 Spring 配置读取：

```bash
python3 jdbc-schema-assistant/scripts/db_inspector.py inspect-config --project-dir /path/to/project
```

显式传 JDBC 信息：

```bash
python3 jdbc-schema-assistant/scripts/db_inspector.py inspect-url \
  --url "jdbc:mysql://localhost:3306/a-20?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai" \
  --username root \
  --password 123456
```

生成 CRUD 规划：

```bash
python3 jdbc-schema-assistant/scripts/crud_planner.py plan --input /path/to/schema.json
```

## 输出约定

- `db_inspector.py` 输出 schema JSON
- `crud_planner.py` 输出 CRUD 规划 JSON，并附带简洁摘要
- 详细字段见 [references/output-contract.md](references/output-contract.md)

## 安全边界

- 默认只读
- 不执行 `INSERT`、`UPDATE`、`DELETE`、`DDL`
- 样例数据强制 `LIMIT`
- 默认对敏感字段掩码
- 连接失败、权限不足、配置缺失时返回明确错误

## 依赖

脚本依赖：

- `PyMySQL`
- `PyYAML`

如果环境未安装，先执行：

```bash
python3 -m pip install -r jdbc-schema-assistant/requirements.txt
```
