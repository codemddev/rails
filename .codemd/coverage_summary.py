import json, os, re, sys
import xml.etree.ElementTree as ET

kind, report, target, start, end, index = sys.argv[1], sys.argv[2], sys.argv[3].replace("\\", "/"), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
# Optional: only these lines (a change's added lines) instead of start..end.
wanted = {int(n) for n in sys.argv[7].split(",") if n} if len(sys.argv) > 7 else set()


def hit(first, last):
    return any(first <= n <= last for n in wanted) if wanted else first <= end and last >= start


def same_file(path):
    path = str(path).replace("\\", "/")
    return path.endswith(target) or target.endswith(path.lstrip("./"))


executed = tracked = 0
missed = set()


def miss(first, last=None):
    # Lines of the change that coverage tracked but the run never executed.
    last = first if last is None else last
    for n in range(first, min(last, first + 2000) + 1):
        if (n in wanted) if wanted else (start <= n <= end):
            missed.add(n)


try:
    if kind == "lcov":
        current = False
        for line in open(report, encoding="utf-8"):
            line = line.strip()
            if line.startswith("SF:"):
                current = same_file(line[3:])
            elif line == "end_of_record":
                current = False
            elif current and line.startswith("DA:"):
                number, _, hits = line[3:].partition(",")
                if hit(int(number), int(number)):
                    tracked += 1
                    executed += 1 if int(hits.split(",")[0] or 0) else 0
                    if not int(hits.split(",")[0] or 0):
                        miss(int(number))
    elif kind == "clover":
        # PHPUnit/Pest --coverage-clover: <file name="..."><line num="12" type="stmt" count="1"/>
        for node in ET.parse(report).getroot().iter("file"):
            if same_file(node.get("name") or node.get("path") or ""):
                for row in node.iter("line"):
                    if row.get("type") == "stmt" and hit(int(row.get("num")), int(row.get("num"))):
                        tracked += 1
                        executed += 1 if int(row.get("count") or 0) else 0
                        if not int(row.get("count") or 0):
                            miss(int(row.get("num")))
    elif kind == "go":
        for line in open(report, encoding="utf-8"):
            match = re.match(r"(.+):(\d+)\.\d+,(\d+)\.\d+ (\d+) (\d+)", line.strip())
            if match and same_file(match.group(1)) and hit(int(match.group(2)), int(match.group(3))):
                tracked += int(match.group(4))
                executed += int(match.group(4)) if int(match.group(5)) else 0
                if not int(match.group(5)):
                    miss(int(match.group(2)), int(match.group(3)))
    else:
        data = json.load(open(report, encoding="utf-8"))
        if kind == "coverage.py":
            for path, entry in (data.get("files") or {}).items():
                if same_file(path):
                    ran, missed_here = set(entry.get("executed_lines") or []), set(entry.get("missing_lines") or [])
                    executed += sum(1 for n in ran if hit(n, n))
                    tracked += sum(1 for n in ran | missed_here if hit(n, n))
                    for n in missed_here:
                        if hit(n, n):
                            miss(n)
        elif kind == "simplecov":
            # .resultset.json: {command: {"coverage": {file: {"lines": [hits or null, ...]} (or the list itself)}}}
            for run in data.values():
                for path, entry in ((run or {}).get("coverage") or {}).items():
                    if same_file(path):
                        for i, count in enumerate((entry.get("lines") if isinstance(entry, dict) else entry) or []):
                            if count is not None and hit(i + 1, i + 1):
                                tracked += 1
                                executed += 1 if count else 0
                                if not count:
                                    miss(i + 1)
        else:
            for path, entry in data.items():
                if same_file(entry.get("path") or path):
                    for key, loc in (entry.get("statementMap") or {}).items():
                        if hit(loc["start"]["line"], loc["end"]["line"]):
                            tracked += 1
                            executed += 1 if (entry.get("s") or {}).get(key) else 0
                            if not (entry.get("s") or {}).get(key):
                                miss(loc["start"]["line"], loc["end"]["line"])
except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
    pass
print("CODEMD_COVERAGE", index, executed, tracked)
if missed and ".f" not in index:
    print("CODEMD_MISSED", index, ",".join(str(n) for n in sorted(missed)[:400]))


def spans(numbers, limit=12):
    found, run = [], []
    for n in sorted(numbers):
        if run and n == run[-1] + 1:
            run.append(n)
            continue
        run = [n]
        found.append(run)
    text = ", ".join(str(r[0]) if len(r) == 1 else f"{r[0]}-{r[-1]}" for r in found[:limit])
    return text + (f", ... ({len(found) - limit} more)" if len(found) > limit else "")


# The run's own page (GitHub's "Summary" tab) shows a table of this too. Per-function runs are left out.
if ".f" not in index and tracked and os.environ.get("GITHUB_STEP_SUMMARY"):
    try:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(f"| `{target}` | {executed} of {tracked} ({round(100 * executed / tracked)}%) | {spans(missed) or 'none'} |\n")
    except OSError:
        pass
