import json
import unittest

import main


class LeaveTests(unittest.TestCase):
    def test_decisions(self):
        cfg = json.load(open("config.json"))
        approved = dict(cfg["already_approved"])
        reqs = json.load(open("sample_requests.json"))
        got = [main.decide(r, cfg, approved)["decision"] for r in reqs]
        self.assertEqual(got, ["APPROVED", "DECLINE", "DECLINE", "ROUTE TO MANAGER", "CLARIFY"])

    def test_parse(self):
        s, e = main.parse_dates("20th to 24th Oct", 2026)
        self.assertEqual((s.day, e.day, e.month), (20, 24, 10))


if __name__ == "__main__":
    unittest.main()
