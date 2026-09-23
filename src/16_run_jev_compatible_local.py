from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from runrelay_progress import update_progress


DEFAULT_ENDPOINT = "http://127.0.0.1:8011/v1/systemone"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def ensure_local_endpoint(endpoint: str) -> None:
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname
    if host not in LOCAL_HOSTS:
        raise RuntimeError(
            "Refusing non-local endpoint. This runner is intentionally local-only. "
            "Use 127.0.0.1, localhost, or ::1."
        )


def to_questions(case: dict) -> dict:
    questions = {}
    for q in case["questions"]:
        item = {
            "type": q["type"],
            "instructions": q["question"],
        }
        if "criteria" in q:
            item["criteria"] = q["criteria"]
        questions[q["name"]] = item
    return questions


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run a Jev-compatible structured-decision server locally. "
            "The endpoint is restricted to localhost."
        )
    )
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--progress-offset", type=int, default=0)
    ap.add_argument("--progress-total", type=int, default=0)
    ap.add_argument("--progress-phase", default="djev_inference")
    args = ap.parse_args()

    ensure_local_endpoint(args.endpoint)

    cases_path = Path(args.cases).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    cases = []
    with cases_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            if "model_state" not in case:
                raise RuntimeError(
                    "Case is missing model_state; rebuild cases with the current pipeline."
                )
            cases.append(case)

    if args.limit > 0:
        cases = cases[: args.limit]

    completed = 0
    failed = 0

    with output.open("w", encoding="utf-8") as f:
        for case in cases:
            payload = {
                "model": args.model,
                "state": case["model_state"],
                "questions": to_questions(case),
            }
            request = urllib.request.Request(
                args.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )

            record = {
                "case_id": case.get("case_id"),
                "synthetic_only": case.get("synthetic_only"),
                "model_state": case.get("model_state", {}),
                "metadata": case.get("metadata", {}),
                "gold": case.get("gold"),
                "model": args.model,
                "backend": "jev_compatible_local",
                "endpoint": args.endpoint,
            }

            try:
                with urllib.request.urlopen(
                    request,
                    timeout=args.timeout,
                ) as response:
                    record["response"] = json.loads(
                        response.read().decode("utf-8")
                    )
                record["status"] = "ok"
                completed += 1
            except urllib.error.HTTPError as exc:
                payload_text = exc.read().decode("utf-8", errors="replace")
                record["status"] = "http_error"
                record["error"] = f"HTTP {exc.code}: {payload_text}"
                failed += 1
            except Exception as exc:
                record["status"] = "error"
                record["error"] = repr(exc)
                failed += 1

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            attempted = completed + failed
            if attempted % 25 == 0 or attempted == len(cases):
                total = args.progress_total if args.progress_total > 0 else len(cases)
                current = args.progress_offset + attempted
                update_progress(
                    current=current,
                    total=total,
                    phase=args.progress_phase,
                    message=f"Local DiffusionGemma-Jev completed {current}/{total} frozen benchmark notes",
                    unit="note",
                )

    print(
        json.dumps(
            {
                "cases_attempted": len(cases),
                "completed": completed,
                "failed": failed,
                "backend": "jev_compatible_local",
                "endpoint": args.endpoint,
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
