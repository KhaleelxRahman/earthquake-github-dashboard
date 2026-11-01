import pathlib
import re
import subprocess
import sys

def check_html_file(file_path: pathlib.Path) -> bool:
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    content = file_path.read_text(encoding="utf-8")
    pattern = re.compile(r'<script(?![^>]*type=["\']application/json["\'])[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
    scripts = pattern.findall(content)
    print(f"[{file_path.name}] Found {len(scripts)} executable script block(s).")

    all_passed = True
    for idx, script_body in enumerate(scripts, 1):
        code = script_body.strip()
        if not code:
            continue
        proc = subprocess.run(
            ["node", "--check"],
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode != 0:
            print(f"[{file_path.name}] Script block #{idx} SYNTAX ERROR:")
            print(proc.stderr.strip())
            all_passed = False
        else:
            print(f"[{file_path.name}] Script block #{idx} syntax OK.")

    return all_passed

if __name__ == "__main__":
    t_ok = check_html_file(pathlib.Path("templates/dashboard.html"))
    i_ok = check_html_file(pathlib.Path("index.html"))
    if not (t_ok and i_ok):
        sys.exit(1)
    print("All scripts passed syntax validation.")
