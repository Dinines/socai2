"""Check pagination and tenant guards at the boundary used by the workbench page."""
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

import processing_workbench_source as source


class WorkbenchSourceTest(unittest.TestCase):
    def test_page_continuation_uses_last_displayed_case_even_for_equal_times(self):
        tenant = uuid4()
        stamp = "2026-11-06T09:00:00.123456+00:00"
        rows = [{"case_id": str(UUID(int=i)), "title": str(i), "updated_at": stamp} for i in range(6, 0, -1)]
        with patch.object(source, "query", side_effect=[rows, rows[-1:]]) as query:
            first = source.list_cases("dsn", tenant)
            self.assertEqual(first["cases"], rows[:5])
            second = source.list_cases("dsn", tenant, first["next_cursor"])
            self.assertEqual(second, {"cases": rows[-1:], "next_cursor": None})
            seek_at, seek_id = query.call_args.args[-1]
            self.assertEqual((seek_at.isoformat(), seek_id), (stamp, UUID(int=2)))

    def test_invalid_cursor_revision_or_tenant_never_reaches_ssh(self):
        with patch.object(source.subprocess, "run") as run:
            for cursor in ("2026-11-06|1", "bad' OR true;--", "a" * 200):
                with self.subTest(cursor=cursor), self.assertRaisesRegex(ValueError, "invalid cursor"):
                    source.list_cases("21", source.HANDOFF_TENANT, cursor)
            with self.assertRaisesRegex(ValueError, "invalid revision"):
                source.read_case_if_changed("21", source.HANDOFF_TENANT, uuid4(), "bogus")
            with self.assertRaisesRegex(ValueError, "invalid handoff tenant"):
                source.list_cases("21", uuid4())
            run.assert_not_called()

    def test_ssh_failures_exclude_private_db_and_connection_messages(self):
        with patch.object(source.subprocess, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = b"private connection data"
            with self.assertRaisesRegex(RuntimeError, "^workbench source unavailable$"):
                source.list_cases("21", source.HANDOFF_TENANT)
            run.return_value.returncode = 0
            run.return_value.stdout = b"SCOPE_DENIED\n"
            with self.assertRaisesRegex(ValueError, "read-only tenant RLS"):
                source.list_cases("21", source.HANDOFF_TENANT)
