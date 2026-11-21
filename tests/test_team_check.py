"""Test cho tools/check_team.py (kiểm danh sách thành viên)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import check_team  # noqa: E402

GOOD = """# TEAM
| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| An | @an-nguyen | sim/gather | Integrator | quan |
| Bình | binh-tran | sim/quan | PO | gather |
| Chi | chi-le | client/ui | QA | quan |
| Dũng | dung-pham | qa | Scrum | ui |
"""


class TeamCheck(unittest.TestCase):
    def test_good(self):
        m = check_team.parse_team(GOOD)
        self.assertEqual([x["handle"] for x in m], ["an-nguyen", "binh-tran", "chi-le", "dung-pham"])
        self.assertEqual(check_team.validate(m, 4, actor="an-nguyen", event="pull_request"), [])

    def test_team_md_of_group(self):
        """Starter: TEAM.md mẫu phải bị từ chối. Nhóm đã điền TEAM.md (4 người) nên đổi thành: TEAM.md của
        nhóm phải hợp lệ; nếu còn chỗ <handle-...> chưa điền thì vẫn phải bị từ chối."""
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TEAM.md"), encoding="utf-8") as f:
            text = f.read()
        m = check_team.parse_team(text)
        errs = check_team.validate(m, 4)
        if "<handle" in text or "<điền" in text:
            self.assertTrue(errs)
        else:
            self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
