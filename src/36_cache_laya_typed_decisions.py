from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import snapshot_download


DEFAULT_REPO = "convaiinnovations/laya-typed-decisions"
DEFAULT_REVISION = "f9ab0b228f0fc0f14d873dbc99038f135c2da1b2"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Cache the pinned public Laya typed-decisions checkpoint before any "
            "credentialed clinical-note inference is run."
        )
    )
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--revision", default=DEFAULT_REVISION)
    ap.add_argument(
        "--output",
        default="~/.cache/mimic-semantic-signals/laya-typed-decisions-f9ab0b2",
    )
    args = ap.parse_args()

    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    resolved = snapshot_download(
        repo_id=args.repo,
        revision=args.revision,
        local_dir=str(out),
    )

    manifest = {
        "repo": args.repo,
        "revision": args.revision,
        "local_path": str(Path(resolved).resolve()),
        "clinical_data_read": False,
        "purpose": "public model cache only",
    }
    manifest_path = out / "local_model_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
