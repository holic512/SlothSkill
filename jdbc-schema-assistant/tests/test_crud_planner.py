import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "crud_planner.py"
SPEC = importlib.util.spec_from_file_location("crud_planner", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def build_table(name, primary_key, columns):
    return {
        "name": name,
        "primary_key": primary_key,
        "columns": columns,
    }


def build_column(name, data_type, nullable=False, default=None, auto_increment=False, java_type="String"):
    return {
        "name": name,
        "data_type": data_type,
        "nullable": nullable,
        "default": default,
        "auto_increment": auto_increment,
        "java_type": java_type,
    }


class CrudPlannerTests(unittest.TestCase):
    def test_build_table_plan_with_single_primary_key(self):
        table = build_table(
            "sys_user",
            ["id"],
            [
                build_column("id", "bigint", nullable=False, auto_increment=True, java_type="Long"),
                build_column("username", "varchar", nullable=False),
                build_column("status", "varchar", nullable=True),
                build_column("create_time", "datetime", nullable=False, java_type="LocalDateTime"),
            ],
        )
        plan = MODULE.build_table_plan(table)
        self.assertIn("SELECT", plan["query_templates"]["select_page"])
        self.assertIn("DELETE FROM `sys_user`", plan["query_templates"]["delete_by_primary_key"])
        self.assertIn("UPDATE `sys_user` SET `status` = 'DELETED'", plan["query_templates"]["logical_delete"])
        id_hint = next(item for item in plan["java_field_hints"] if item["field"] == "id")
        self.assertFalse(id_hint["allowed_on_update"])

    def test_build_table_plan_without_primary_key(self):
        table = build_table(
            "audit_log",
            [],
            [
                build_column("trace_id", "varchar"),
                build_column("content", "text"),
            ],
        )
        plan = MODULE.build_table_plan(table)
        self.assertIn("缺少主键", plan["summary"])
        self.assertIsNone(plan["query_templates"]["update_by_primary_key"])
        self.assertIsNone(plan["query_templates"]["delete_by_primary_key"])

    def test_build_table_plan_with_composite_primary_key(self):
        table = build_table(
            "user_role",
            ["user_id", "role_id"],
            [
                build_column("user_id", "bigint", java_type="Long"),
                build_column("role_id", "bigint", java_type="Long"),
                build_column("created_at", "datetime", java_type="LocalDateTime"),
            ],
        )
        plan = MODULE.build_table_plan(table)
        self.assertIn("Composite primary key", plan["risks"][0])
        self.assertIn("`user_id` = :userId AND `role_id` = :roleId", plan["query_templates"]["delete_by_primary_key"])

    def test_cli_plan_reads_and_writes_json(self):
        payload = {
            "connection": {"db_type": "mysql", "host": "localhost", "port": 3306, "database": "demo", "source": "cli"},
            "tables": [
                build_table(
                    "sys_user",
                    ["id"],
                    [
                        build_column("id", "bigint", nullable=False, auto_increment=True, java_type="Long"),
                        build_column("username", "varchar", nullable=False),
                    ],
                )
            ],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "schema.json"
            output_path = Path(tmp_dir) / "plan.json"
            input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = MODULE.main(["plan", "--input", str(input_path), "--output", str(output_path)])
            self.assertEqual(result, 0)
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["table_plans"][0]["table"], "sys_user")


if __name__ == "__main__":
    unittest.main()
