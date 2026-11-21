"""Test Phase 4 (Test Contract v1.3): manifest, soak_cmd, bench_cmd (renderer software cho nhanh)."""

import json
import os
import shlex
import subprocess
import unittest

from helpers import ROOT, Workdir


def contract():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


def run_cmd(key, *args):
    p = subprocess.run([*shlex.split(contract()[key]), *args], cwd=ROOT, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stderr


class ManifestV13(unittest.TestCase):
    def test_v13_commands(self):
        c = contract()
        self.assertEqual(c["contract_version"], "1.3")
        for k in ("headless_cmd", "run_cmd", "build_cmd", "bench_cmd", "soak_cmd"):
            self.assertTrue(c[k].strip(), k)
        self.assertIn("freshness", c["tuning"])


class Soak(unittest.TestCase):
    def test_soak_schema_and_repeatable(self):
        with Workdir() as w:
            outs = []
            for i in (1, 2):
                code, err = run_cmd("soak_cmd", "--seed", "7", "--days", "6", "--out", w.path(f"s{i}.json"))
                self.assertEqual(code, 0, err)
                with open(w.path(f"s{i}.json"), encoding="utf-8") as f:
                    outs.append(json.load(f))
            r = outs[0]
            self.assertEqual(set(r), {"days", "days_completed", "crashes", "results", "duration_s"})
            self.assertEqual((r["days"], r["days_completed"], r["crashes"]), (6, 6, 0))
            self.assertEqual([x["day"] for x in r["results"]], list(range(1, 7)))
            for x in r["results"]:
                self.assertEqual(set(x), {"day", "earned", "reputation", "score"})
            strip = lambda o: {k: v for k, v in o.items() if k != "duration_s"}  # noqa: E731
            self.assertEqual(strip(outs[0]), strip(outs[1]), "lặp lại cùng seed -> cùng trường gameplay")


class Bench(unittest.TestCase):
    def test_bench_writes_five_fields(self):
        with Workdir() as w:
            code, err = run_cmd("bench_cmd", "--seed", "42", "--duration", "1", "--warmup", "0.2",
                                "--renderer", "software", "--out", w.path("bench.json"))
            self.assertEqual(code, 0, err)
            with open(w.path("bench.json"), encoding="utf-8") as f:
                b = json.load(f)
            self.assertEqual(set(b), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
            self.assertGreater(b["frames"], 0)
            self.assertAlmostEqual(b["avg_fps"], b["frames"] / b["measured_s"], delta=0.05)
            self.assertLessEqual(b["p1_low_fps"], b["avg_fps"] + 0.01)


if __name__ == "__main__":
    unittest.main()
