"""Run evals/cases.json against the running /enrich endpoint and print a score."""
import json
import urllib.request
import urllib.error
from pathlib import Path

ENDPOINT = "http://localhost:8000/enrich"
CASES_PATH = Path(__file__).parent / "cases.json"


def call_enrich(input_payload):
    data = json.dumps(input_payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return body, e.code


def main():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    correct = 0
    failures = []

    for case in cases:
        result, status = call_enrich(case["input"])
        actual_category = result.get("category")
        expected_category = case["expected_category"]
        passed = status == 200 and actual_category == expected_category

        if passed:
            correct += 1
            print(f"PASS  {case['id']}  ->  {actual_category}")
        else:
            failures.append(case["id"])
            print(f"FAIL  {case['id']}  ->  status={status}  got={actual_category!r}  expected={expected_category!r}")

    total = len(cases)
    print(f"\nScore: {correct}/{total}")
    if failures:
        print("Failed cases:", ", ".join(failures))


if __name__ == "__main__":
    main()