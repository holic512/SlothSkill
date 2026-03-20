import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "db_inspector.py"
SPEC = importlib.util.spec_from_file_location("db_inspector", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeCursor:
    def __init__(self):
        self._result = []

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        if "FROM information_schema.tables" in normalized:
            self._result = [
                {
                    "table_name": "sys_user",
                    "table_comment": "用户表",
                    "engine": "InnoDB",
                    "table_collation": "utf8mb4_general_ci",
                    "table_rows": 12,
                }
            ]
        elif "FROM information_schema.columns" in normalized:
            self._result = [
                {
                    "table_name": "sys_user",
                    "column_name": "id",
                    "ordinal_position": 1,
                    "data_type": "bigint",
                    "column_type": "bigint(20)",
                    "character_maximum_length": None,
                    "numeric_precision": 20,
                    "numeric_scale": 0,
                    "is_nullable": "NO",
                    "column_default": None,
                    "column_comment": "主键",
                    "extra": "auto_increment",
                },
                {
                    "table_name": "sys_user",
                    "column_name": "username",
                    "ordinal_position": 2,
                    "data_type": "varchar",
                    "column_type": "varchar(64)",
                    "character_maximum_length": 64,
                    "numeric_precision": None,
                    "numeric_scale": None,
                    "is_nullable": "NO",
                    "column_default": None,
                    "column_comment": "用户名",
                    "extra": "",
                },
                {
                    "table_name": "sys_user",
                    "column_name": "password",
                    "ordinal_position": 3,
                    "data_type": "varchar",
                    "column_type": "varchar(128)",
                    "character_maximum_length": 128,
                    "numeric_precision": None,
                    "numeric_scale": None,
                    "is_nullable": "YES",
                    "column_default": None,
                    "column_comment": "密码",
                    "extra": "",
                },
                {
                    "table_name": "sys_user",
                    "column_name": "bio",
                    "ordinal_position": 4,
                    "data_type": "text",
                    "column_type": "text",
                    "character_maximum_length": 65535,
                    "numeric_precision": None,
                    "numeric_scale": None,
                    "is_nullable": "YES",
                    "column_default": None,
                    "column_comment": "简介",
                    "extra": "",
                },
            ]
        elif "FROM information_schema.statistics" in normalized:
            self._result = [
                {
                    "table_name": "sys_user",
                    "index_name": "PRIMARY",
                    "non_unique": 0,
                    "column_name": "id",
                    "seq_in_index": 1,
                    "index_type": "BTREE",
                },
                {
                    "table_name": "sys_user",
                    "index_name": "idx_username",
                    "non_unique": 0,
                    "column_name": "username",
                    "seq_in_index": 1,
                    "index_type": "BTREE",
                },
            ]
        elif "FROM information_schema.key_column_usage" in normalized:
            self._result = []
        elif normalized.startswith("SELECT `id`, `username`, `password` FROM `sys_user` LIMIT 3"):
            self._result = [
                {
                    "id": 1,
                    "username": "demo",
                    "password": "secret-value",
                }
            ]
        else:
            raise AssertionError(f"Unexpected query: {normalized} / params={params}")

    def fetchall(self):
        return self._result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def cursor(self):
        return FakeCursor()

    def close(self):
        return None


class DbInspectorTests(unittest.TestCase):
    def test_parse_jdbc_mysql_url(self):
        parsed = MODULE.parse_jdbc_mysql_url(
            "jdbc:mysql://localhost:3306/a-20?useUnicode=true&characterEncoding=UTF-8"
        )
        self.assertEqual(parsed["host"], "localhost")
        self.assertEqual(parsed["port"], 3306)
        self.assertEqual(parsed["database"], "a-20")
        self.assertEqual(parsed["params"]["useUnicode"], "true")

    def test_parse_jdbc_mysql_url_rejects_non_mysql(self):
        with self.assertRaises(MODULE.InspectorError):
            MODULE.parse_jdbc_mysql_url("jdbc:postgresql://localhost:5432/demo")

    def test_parse_properties_config(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "application.properties"
            path.write_text(
                "\n".join(
                    [
                        "spring.datasource.url=jdbc:mysql://localhost:3306/demo",
                        "spring.datasource.username=root",
                        "spring.datasource.password=123456",
                    ]
                ),
                encoding="utf-8",
            )
            parsed = MODULE.parse_properties_config(path)
            self.assertEqual(parsed["spring.datasource.username"], "root")

    @unittest.skipIf(MODULE.yaml is None, "PyYAML is not installed")
    def test_resolve_connection_from_yaml(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            path = root / "application.yml"
            path.write_text(
                """
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/demo
    username: root
    password: 123456
""".strip(),
                encoding="utf-8",
            )
            resolved = MODULE.resolve_connection_from_config(root, {})
            self.assertEqual(resolved.username, "root")
            self.assertEqual(resolved.source, "application.yml")

    @unittest.skipIf(MODULE.yaml is None, "PyYAML is not installed")
    def test_resolve_connection_from_application_yaml(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            path = root / "src" / "main" / "resources"
            path.mkdir(parents=True)
            config = path / "application.yaml"
            config.write_text(
                """
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/demo
    username: root
    password: 123456
""".strip(),
                encoding="utf-8",
            )
            resolved = MODULE.resolve_connection_from_config(root, {})
            self.assertEqual(resolved.source, "src/main/resources/application.yaml")

    def test_resolve_connection_missing_fields_raises(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            path = root / "application.properties"
            path.write_text("spring.datasource.url=jdbc:mysql://localhost:3306/demo", encoding="utf-8")
            with self.assertRaises(MODULE.InspectorError):
                MODULE.resolve_connection_from_config(root, {})

    def test_inspect_database_builds_expected_payload(self):
        payload = MODULE.inspect_database(
            FakeConnection(),
            {
                "host": "localhost",
                "port": 3306,
                "database": "demo",
                "params": {"serverTimezone": "Asia/Shanghai"},
            },
            "application.yml",
            sample_limit=3,
        )
        self.assertEqual(payload["database_summary"]["table_count"], 1)
        table = payload["tables"][0]
        self.assertEqual(table["primary_key"], ["id"])
        self.assertEqual(table["indexes"][0]["name"], "idx_username")
        self.assertEqual(table["sample_rows"][0]["password"], "***MASKED***")
        bio_column = next(item for item in table["columns"] if item["name"] == "bio")
        self.assertTrue(bio_column["sample_excluded"])

    def test_main_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "schema.json"
            fake_payload = {
                "connection": {"db_type": "mysql", "host": "localhost", "port": 3306, "database": "demo", "params": {}, "source": "cli"},
                "database_summary": {"table_count": 0, "tables": []},
                "tables": [],
                "warnings": [],
                "generated_at": "2026-03-20T00:00:00+00:00",
            }
            with mock.patch.object(MODULE, "connect_mysql", return_value=FakeConnection()):
                with mock.patch.object(MODULE, "inspect_database", return_value=fake_payload):
                    result = MODULE.main(
                        [
                            "inspect-url",
                            "--url",
                            "jdbc:mysql://localhost:3306/demo",
                            "--username",
                            "root",
                            "--password",
                            "123456",
                            "--output",
                            str(output_path),
                        ]
                    )
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["connection"]["database"], "demo")


if __name__ == "__main__":
    unittest.main()
