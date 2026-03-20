#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlparse

try:
    import pymysql
except ImportError:  # pragma: no cover
    pymysql = None

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


SUPPORTED_URL_PREFIX = "jdbc:mysql://"
CONFIG_CANDIDATES = (
    "application.yml",
    "application.yaml",
    "application.properties",
)
SENSITIVE_FIELD_NAMES = {
    "password",
    "pwd",
    "secret",
    "token",
    "phone",
    "mobile",
    "id_card",
}
LARGE_SAMPLE_TYPES = {
    "blob",
    "tinyblob",
    "mediumblob",
    "longblob",
    "binary",
    "varbinary",
    "text",
    "tinytext",
    "mediumtext",
    "longtext",
    "json",
}
JAVA_TYPE_MAPPING = {
    "bigint": "Long",
    "int": "Integer",
    "integer": "Integer",
    "smallint": "Short",
    "tinyint": "Integer",
    "decimal": "BigDecimal",
    "numeric": "BigDecimal",
    "float": "Float",
    "double": "Double",
    "bit": "Boolean",
    "bool": "Boolean",
    "boolean": "Boolean",
    "char": "String",
    "varchar": "String",
    "text": "String",
    "tinytext": "String",
    "mediumtext": "String",
    "longtext": "String",
    "json": "String",
    "date": "LocalDate",
    "datetime": "LocalDateTime",
    "timestamp": "LocalDateTime",
    "time": "LocalTime",
}


class InspectorError(RuntimeError):
    pass


@dataclass
class ResolvedConnection:
    url: str
    username: str
    password: str
    source: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect MySQL schema from Spring config or JDBC URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_config = subparsers.add_parser("inspect-config", help="Read Spring datasource config from a project")
    inspect_config.add_argument("--project-dir", required=True, help="Spring project root directory")
    inspect_config.add_argument("--url", help="Override JDBC URL")
    inspect_config.add_argument("--username", help="Override username")
    inspect_config.add_argument("--password", help="Override password")
    inspect_config.add_argument("--sample-limit", type=int, default=3, help="Rows to fetch per table")
    inspect_config.add_argument("--output", help="Optional output JSON file")

    inspect_url = subparsers.add_parser("inspect-url", help="Inspect using explicit JDBC URL")
    inspect_url.add_argument("--url", required=True, help="JDBC MySQL URL")
    inspect_url.add_argument("--username", required=True, help="Database username")
    inspect_url.add_argument("--password", required=True, help="Database password")
    inspect_url.add_argument("--sample-limit", type=int, default=3, help="Rows to fetch per table")
    inspect_url.add_argument("--output", help="Optional output JSON file")

    return parser.parse_args(argv)


def require_dependency(dep: Any, package_name: str) -> None:
    if dep is None:
        raise InspectorError(f"Missing dependency: {package_name}. Install with `python3 -m pip install -r jdbc-schema-assistant/requirements.txt`.")


def parse_jdbc_mysql_url(jdbc_url: str) -> Dict[str, Any]:
    if not jdbc_url:
        raise InspectorError("Missing JDBC URL.")
    if not jdbc_url.startswith(SUPPORTED_URL_PREFIX):
        raise InspectorError("Unsupported JDBC URL. Only jdbc:mysql://... is supported in this version.")

    parsed = urlparse(jdbc_url[len("jdbc:") :])
    if parsed.scheme != "mysql":
        raise InspectorError("Unsupported JDBC URL. Only MySQL is supported in this version.")
    if not parsed.hostname:
        raise InspectorError("Invalid JDBC URL: host is missing.")
    database = parsed.path.lstrip("/")
    if not database:
        raise InspectorError("Invalid JDBC URL: database name is missing.")

    return {
        "db_type": "mysql",
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "database": database,
        "params": dict(parse_qsl(parsed.query, keep_blank_values=True)),
    }


def flatten_mapping(mapping: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for key, value in mapping.items():
        new_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten_mapping(value, new_key))
        else:
            flat[new_key] = value
    return flat


def parse_yaml_config(path: Path) -> Dict[str, Any]:
    require_dependency(yaml, "PyYAML")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise InspectorError(f"Unexpected YAML structure in {path}.")
    return flatten_mapping(loaded)


def parse_properties_config(path: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        match = re.match(r"([^:=\s]+)\s*[:=]\s*(.*)", line)
        if not match:
            continue
        key, value = match.groups()
        result[key.strip()] = value.strip()
    return result


def load_config_file(path: Path) -> Dict[str, Any]:
    if path.name.endswith((".yml", ".yaml")):
        return parse_yaml_config(path)
    if path.name.endswith(".properties"):
        return parse_properties_config(path)
    raise InspectorError(f"Unsupported config file: {path}")


def rank_config_candidate(project_dir: Path, path: Path) -> Tuple[int, int, str]:
    rel = str(path.relative_to(project_dir))
    preferred = {
        "application.yml": 0,
        "application.yaml": 1,
        "application.properties": 2,
        "src/main/resources/application.yml": 3,
        "src/main/resources/application.yaml": 4,
        "src/main/resources/application.properties": 5,
        "config/application.yml": 6,
        "config/application.yaml": 7,
        "config/application.properties": 8,
    }
    return (preferred.get(rel, 99), len(path.parts), rel)


def find_spring_config(project_dir: Path) -> Path:
    candidates: List[Path] = []
    for name in CONFIG_CANDIDATES:
        direct = project_dir / name
        if direct.exists():
            candidates.append(direct)
        nested = project_dir / "src" / "main" / "resources" / name
        if nested.exists():
            candidates.append(nested)
        config_dir = project_dir / "config" / name
        if config_dir.exists():
            candidates.append(config_dir)
    if not candidates:
        candidates.extend(project_dir.rglob("application.y*ml"))
        candidates.extend(project_dir.rglob("application.properties"))
    if not candidates:
        raise InspectorError(f"No Spring datasource config found under {project_dir}.")
    return sorted({path.resolve() for path in candidates}, key=lambda item: rank_config_candidate(project_dir.resolve(), item))[0]


def resolve_connection_from_config(project_dir: Path, overrides: Dict[str, Optional[str]]) -> ResolvedConnection:
    config_path = find_spring_config(project_dir)
    flat = load_config_file(config_path)
    url = overrides.get("url") or flat.get("spring.datasource.url")
    username = overrides.get("username") or flat.get("spring.datasource.username")
    password = overrides.get("password") or flat.get("spring.datasource.password")
    missing = [name for name, value in (("url", url), ("username", username), ("password", password)) if not value]
    if missing:
        raise InspectorError(f"Datasource config is incomplete in {config_path}: missing {', '.join(missing)}.")
    project_dir_resolved = project_dir.resolve()
    try:
        source = str(config_path.relative_to(project_dir_resolved))
    except ValueError:
        source = config_path.name
    return ResolvedConnection(
        url=str(url),
        username=str(username),
        password=str(password),
        source=source,
    )


def connect_mysql(connection: ResolvedConnection, parsed_url: Dict[str, Any]):
    require_dependency(pymysql, "PyMySQL")
    try:
        return pymysql.connect(
            host=parsed_url["host"],
            port=parsed_url["port"],
            user=connection.username,
            password=connection.password,
            database=parsed_url["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            read_timeout=10,
            write_timeout=10,
        )
    except Exception as exc:  # pragma: no cover
        message = str(exc).lower()
        if "access denied" in message:
            raise InspectorError("Database authentication failed. Check username and password.") from exc
        if "unknown database" in message:
            raise InspectorError("Database does not exist or is not accessible.") from exc
        if "denied" in message and "command" not in message:
            raise InspectorError("Database permission denied.") from exc
        raise InspectorError(f"Failed to connect to database: {exc}") from exc


def fetch_all(cursor: Any, query: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
    cursor.execute(query, params or ())
    return list(cursor.fetchall())


def mask_value(column_name: str, value: Any) -> Any:
    lowered = column_name.lower()
    if lowered in SENSITIVE_FIELD_NAMES and value not in (None, ""):
        return "***MASKED***"
    return value


def truncate_value(value: Any, max_length: int = 120) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return "<binary>"
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "...<truncated>"
    return value


def infer_java_type(data_type: str, column_type: str) -> str:
    lowered = data_type.lower()
    if lowered == "tinyint" and column_type.startswith("tinyint(1)"):
        return "Boolean"
    return JAVA_TYPE_MAPPING.get(lowered, "String")


def build_column_metadata(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    columns: List[Dict[str, Any]] = []
    for row in rows:
        data_type = row["data_type"]
        column_type = row["column_type"]
        columns.append(
            {
                "name": row["column_name"],
                "ordinal_position": row["ordinal_position"],
                "data_type": data_type,
                "column_type": column_type,
                "length": row["character_maximum_length"],
                "numeric_precision": row["numeric_precision"],
                "numeric_scale": row["numeric_scale"],
                "nullable": row["is_nullable"] == "YES",
                "default": row["column_default"],
                "comment": row["column_comment"] or "",
                "auto_increment": "auto_increment" in (row["extra"] or "").lower(),
                "unsigned": "unsigned" in (column_type or "").lower(),
                "java_type": infer_java_type(data_type, column_type or ""),
                "sample_excluded": data_type.lower() in LARGE_SAMPLE_TYPES,
            }
        )
    return columns


def group_indexes(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    primary_key: List[str] = []
    for row in rows:
        name = row["index_name"]
        if name not in grouped:
            grouped[name] = {
                "name": name,
                "unique": row["non_unique"] == 0,
                "columns": [],
                "index_type": row["index_type"],
            }
        grouped[name]["columns"].append(row["column_name"])
        if name == "PRIMARY":
            primary_key.append(row["column_name"])
    indexes = [value for key, value in grouped.items() if key != "PRIMARY"]
    return indexes, primary_key


def group_foreign_keys(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        name = row["constraint_name"]
        if name not in grouped:
            grouped[name] = {
                "name": name,
                "columns": [],
                "referenced_table": row["referenced_table_name"],
                "referenced_columns": [],
                "update_rule": row["update_rule"],
                "delete_rule": row["delete_rule"],
            }
        grouped[name]["columns"].append(row["column_name"])
        grouped[name]["referenced_columns"].append(row["referenced_column_name"])
    return list(grouped.values())


def build_sample_query(table_name: str, sample_columns: Iterable[Dict[str, Any]], limit: int) -> str:
    names = ", ".join(f"`{column['name']}`" for column in sample_columns) or "*"
    return f"SELECT {names} FROM `{table_name}` LIMIT {int(limit)}"


def fetch_table_sample_rows(cursor: Any, table_name: str, columns: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    sample_columns = [column for column in columns if not column["sample_excluded"]]
    if not sample_columns:
        return []
    query = build_sample_query(table_name, sample_columns, limit)
    cursor.execute(query)
    rows = list(cursor.fetchall())
    sanitized: List[Dict[str, Any]] = []
    for row in rows:
        item: Dict[str, Any] = {}
        for key, value in row.items():
            item[key] = truncate_value(mask_value(key, value))
        sanitized.append(item)
    return sanitized


def inspect_database(connection: Any, parsed_url: Dict[str, Any], source: str, sample_limit: int) -> Dict[str, Any]:
    schema_name = parsed_url["database"]
    with connection.cursor() as cursor:
        table_rows = fetch_all(
            cursor,
            """
            SELECT
                table_name AS table_name,
                table_comment AS table_comment,
                engine AS engine,
                table_collation AS table_collation,
                table_rows AS table_rows
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (schema_name,),
        )
        columns_rows = fetch_all(
            cursor,
            """
            SELECT
                table_name AS table_name,
                column_name AS column_name,
                ordinal_position AS ordinal_position,
                data_type AS data_type,
                column_type AS column_type,
                character_maximum_length AS character_maximum_length,
                numeric_precision AS numeric_precision,
                numeric_scale AS numeric_scale,
                is_nullable AS is_nullable,
                column_default AS column_default,
                column_comment AS column_comment,
                extra AS extra
            FROM information_schema.columns
            WHERE table_schema = %s
            ORDER BY table_name, ordinal_position
            """,
            (schema_name,),
        )
        index_rows = fetch_all(
            cursor,
            """
            SELECT
                table_name AS table_name,
                index_name AS index_name,
                non_unique AS non_unique,
                column_name AS column_name,
                seq_in_index AS seq_in_index,
                index_type AS index_type
            FROM information_schema.statistics
            WHERE table_schema = %s
            ORDER BY table_name, index_name, seq_in_index
            """,
            (schema_name,),
        )
        foreign_key_rows = fetch_all(
            cursor,
            """
            SELECT
                kcu.table_name AS table_name,
                kcu.constraint_name AS constraint_name,
                kcu.column_name AS column_name,
                kcu.referenced_table_name AS referenced_table_name,
                kcu.referenced_column_name AS referenced_column_name,
                rc.update_rule AS update_rule,
                rc.delete_rule AS delete_rule
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.referential_constraints rc
              ON rc.constraint_schema = kcu.constraint_schema
             AND rc.constraint_name = kcu.constraint_name
            WHERE kcu.table_schema = %s
              AND kcu.referenced_table_name IS NOT NULL
            ORDER BY kcu.table_name, kcu.constraint_name, kcu.ordinal_position
            """,
            (schema_name,),
        )

        columns_by_table: Dict[str, List[Dict[str, Any]]] = {}
        for row in columns_rows:
            columns_by_table.setdefault(row["table_name"], []).append(row)

        indexes_by_table: Dict[str, List[Dict[str, Any]]] = {}
        for row in index_rows:
            indexes_by_table.setdefault(row["table_name"], []).append(row)

        foreign_keys_by_table: Dict[str, List[Dict[str, Any]]] = {}
        for row in foreign_key_rows:
            foreign_keys_by_table.setdefault(row["table_name"], []).append(row)

        tables: List[Dict[str, Any]] = []
        warnings: List[str] = []
        for table in table_rows:
            table_name = table["table_name"]
            columns = build_column_metadata(columns_by_table.get(table_name, []))
            indexes, primary_key = group_indexes(indexes_by_table.get(table_name, []))
            foreign_keys = group_foreign_keys(foreign_keys_by_table.get(table_name, []))
            sample_rows = fetch_table_sample_rows(cursor, table_name, columns, sample_limit)
            if not primary_key:
                warnings.append(f"Table `{table_name}` has no primary key.")
            tables.append(
                {
                    "name": table_name,
                    "comment": table["table_comment"] or "",
                    "engine": table["engine"] or "",
                    "charset": (table["table_collation"] or "").split("_")[0] if table["table_collation"] else "",
                    "estimated_rows": int(table["table_rows"] or 0),
                    "estimated_rows_is_approximate": True,
                    "primary_key": primary_key,
                    "columns": columns,
                    "indexes": indexes,
                    "foreign_keys": foreign_keys,
                    "sample_rows": sample_rows,
                }
            )

    return {
        "connection": {
            "db_type": "mysql",
            "host": parsed_url["host"],
            "port": parsed_url["port"],
            "database": parsed_url["database"],
            "params": parsed_url["params"],
            "source": source,
        },
        "database_summary": {
            "table_count": len(tables),
            "tables": [table["name"] for table in tables],
        },
        "tables": tables,
        "warnings": warnings,
        "generated_at": utc_now(),
    }


def write_output(payload: Dict[str, Any], output: Optional[str]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = parse_args(argv)
        if args.command == "inspect-config":
            project_dir = Path(args.project_dir).resolve()
            resolved = resolve_connection_from_config(
                project_dir,
                {
                    "url": args.url,
                    "username": args.username,
                    "password": args.password,
                },
            )
        else:
            missing = [name for name in ("url", "username", "password") if not getattr(args, name)]
            if missing:
                raise InspectorError(f"Missing required arguments: {', '.join(missing)}.")
            resolved = ResolvedConnection(args.url, args.username, args.password, "cli")

        parsed_url = parse_jdbc_mysql_url(resolved.url)
        connection = connect_mysql(resolved, parsed_url)
        try:
            payload = inspect_database(connection, parsed_url, resolved.source, args.sample_limit)
        finally:
            connection.close()
        write_output(payload, args.output)
        return 0
    except InspectorError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
