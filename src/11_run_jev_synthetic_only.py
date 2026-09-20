from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if case.get("synthetic_only") is not True:
                raise RuntimeError(
                    "Refusing to send a case not explicitly marked synthetic_only=true."
                )
            if not str(case.get("case_id", "")).startswith("syn_"):
                raise RuntimeError(
                    "Refusing to send a case whose case_id is not synthetic."
                )
            cases.append(case)
    return cases


def to_jev_questions(case: dict) -> dict:
    questions = {}
    for q in case["questions"]:
        qtype = q["type"]
        if qtype != "noul":
            raise ValueError(
                f"Current synthetic runner supports noul only; got {qtype!r}."
            )
        item = {
            "type": "noul",
            "instructions": q["question"],
        }
        if isinstance(q.get("criteria"), dict):
            item["criteria"] = q["criteria"]
        questions[q["name"]] = item
    return questions


def call_jev(
    api_key: str,
    endpoint: str,
    model: str,
    case: dict,
    timeout: float,
) -> dict:
    payload = {
        "model": model,
        "state": case["model_state"],
        "questions": to_jev_questions(case),
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run Jev only on explicitly synthetic cases. "
            "This script intentionally refuses unmarked or real-data cases."
        )
    )
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--sleep", type=float, default=0.0)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate cases and show the first request without sending it.",
    )
    args = ap.parse_args()

    cases_path = Path(args.cases).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    cases = load_cases(cases_path)
    if args.limit > 0:
        cases = cases[: args.limit]

    if not cases:
        raise RuntimeError("No synthetic cases found.")

    first_payload = {
        "model": args.model,
        "state": cases[0]["state"],
        "questions": to_jev_questions(cases[0]),
    }

    if args.dry_run:
        print(json.dumps(first_payload, indent=2))
        print(f"Validated {len(cases)} synthetic cases. Nothing was sent.")
        return

    api_key = (
        os.environ.get("TYPESAFE_API_KEY")
        or os.environ.get("JEV_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "Set TYPESAFE_API_KEY (preferred) or JEV_API_KEY in the environment."
        )

    completed = 0
    failed = 0
    with output.open("w", encoding="utf-8") as f:
        for case in cases:
            record = {
                "case_id": case["case_id"],
                "synthetic_only": True,
                "model_state": case.get("model_state", {}),
                "metadata": case.get("metadata", {}),
                "gold": case.get("gold"),
                "model": args.model,
            }
            try:
                response = call_jev(
                    api_key=api_key,
                    endpoint=args.endpoint,
                    model=args.model,
                    case=case,
                    timeout=args.timeout,
                )
                record["response"] = response
                record["status"] = "ok"
                completed += 1
            except urllib.error.HTTPError as exc:
                payload = exc.read().decode("utf-8", errors="replace")
                record["status"] = "http_error"
                record["error"] = f"HTTP {exc.code}: {payload}"
                failed += 1
            except Exception as exc:
                record["status"] = "error"
                record["error"] = repr(exc)
                failed += 1

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()

            if args.sleep > 0:
                time.sleep(args.sleep)

    print(
        json.dumps(
            {
                "synthetic_cases_attempted": len(cases),
                "completed": completed,
                "failed": failed,
                "output": str(output),
            },
            indent=2,
        )
    )

    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
