"""Chạy toàn bộ test + kiểm tất định + ghi bằng chứng vào docs/proof/phase-<n>/.
    python3 .agents/skills/proof-run/run.py <n>
Ghi: test-output.txt (kết quả unittest thật), determinism.txt (hai lần chạy cùng seed có giống từng byte không).
"""
import hashlib
import os
import subprocess
import sys
import tempfile


def sh(cmd, env=None):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(n):
    out = os.path.join("docs", "proof", f"phase-{n}")
    os.makedirs(out, exist_ok=True)
    env = dict(os.environ, PYTHONPATH="tests:.")
    code, text = sh("python3 -m unittest discover -s tests -v", env)
    with open(os.path.join(out, "test-output.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    lines = []
    ok_det = True
    with tempfile.TemporaryDirectory() as d:
        for mode in ("gather", "quan"):
            hs = []
            for i in (1, 2):
                p = os.path.join(d, f"{mode}{i}.jsonl")
                sh(f"python3 -m chonoi.headless --mode {mode} --seed 7 --ticks 1500 --out {p}")
                hs.append(digest(p))
            same = hs[0] == hs[1]
            ok_det &= same
            lines.append(f"{mode}: seed 7, 1500 tick, 2 lần chạy -> {'GIỐNG từng byte' if same else 'KHÁC'} ({hs[0][:12]})")
    with open(os.path.join(out, "determinism.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(text.strip().splitlines()[-3:])
    print("\n".join(lines))
    return 0 if code == 0 and ok_det else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "1"))
