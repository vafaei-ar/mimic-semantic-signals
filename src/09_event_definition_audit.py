from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from common import find_file, lower_columns, module_path, resolve_root, safe_write_csv

# Canonical vasopressor ITEMIDs used in the MIT-LCP MIMIC-III concept code.
CANONICAL_VASO = {
    30047: "norepinephrine_cv",
    30120: "norepinephrine_cv",
    221906: "norepinephrine_mv",
    30044: "epinephrine_cv",
    30119: "epinephrine_cv",
    30309: "epinephrine_cv",
    221289: "epinephrine_mv",
    30127: "phenylephrine_cv",
    30128: "phenylephrine_cv",
    221749: "phenylephrine_mv",
    30051: "vasopressin_cv",
    222315: "vasopressin_mv",
    30043: "dopamine_cv",
    30307: "dopamine_cv",
    30125: "dopamine_cv",
    221662: "dopamine_mv",
    30046: "isuprel_cv",
    227692: "isuprel_mv",
}

VASO_TERMS = [
    "norepinephrine", "noradrenaline", "epinephrine", "adrenaline",
    "vasopressin", "phenylephrine", "dopamine", "dobutamine",
]
INTUBATION_TERMS = ["intubation", "endotracheal intubation"]


def _match(df: pd.DataFrame, terms: list[str], kind: str) -> pd.DataFrame:
    if df.empty or "label" not in df:
        return pd.DataFrame()
    pat = "|".join(re.escape(x) for x in terms)
    m = df["label"].fillna("").astype(str).str.lower().str.contains(pat, regex=True)
    x = df.loc[m].copy()
    x["audit_kind"] = kind
    return x


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)
    f = find_file(
        module_path(root, "mimiciii"),
        ["D_ITEMS.csv.gz", "D_ITEMS.csv", "d_items.csv.gz", "d_items.csv"],
    )
    if f is None:
        safe_write_csv(pd.DataFrame([{"status": "d_items_not_found"}]), out / "event_definition_item_audit.csv")
        return

    d = lower_columns(pd.read_csv(f, low_memory=False))
    keep = [c for c in ["itemid","label","abbreviation","dbsource","linksto","category","unitname","param_type"] if c in d.columns]
    d = d[keep].copy()
    d["itemid"] = pd.to_numeric(d["itemid"], errors="coerce")
    d = d.dropna(subset=["itemid"])
    d["itemid"] = d["itemid"].astype("int64")

    vaso = _match(d, VASO_TERMS, "text_match_vasopressor")
    intu = _match(d, INTUBATION_TERMS, "text_match_intubation")
    audit = pd.concat([vaso, intu], ignore_index=True)
    audit["canonical_vasopressor"] = audit["itemid"].isin(CANONICAL_VASO)
    audit["canonical_vasopressor_name"] = audit["itemid"].map(CANONICAL_VASO).fillna("")
    safe_write_csv(audit, out / "event_definition_item_audit.csv")

    canonical_rows = []
    indexed = d.set_index("itemid", drop=False)
    for itemid, name in sorted(CANONICAL_VASO.items()):
        if itemid in indexed.index:
            row = indexed.loc[itemid]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            canonical_rows.append({
                "itemid": itemid,
                "canonical_name": name,
                "present_in_local_d_items": True,
                "label": row.get("label", ""),
                "dbsource": row.get("dbsource", ""),
                "linksto": row.get("linksto", ""),
                "category": row.get("category", ""),
            })
        else:
            canonical_rows.append({
                "itemid": itemid,
                "canonical_name": name,
                "present_in_local_d_items": False,
                "label": "",
                "dbsource": "",
                "linksto": "",
                "category": "",
            })
    safe_write_csv(pd.DataFrame(canonical_rows), out / "canonical_vasopressor_itemids.csv")

    summary = []
    if not audit.empty:
        for (kind, dbsource, linksto), g in audit.groupby(
            ["audit_kind","dbsource","linksto"], dropna=False
        ):
            summary.append({
                "audit_kind": kind,
                "dbsource": str(dbsource),
                "linksto": str(linksto),
                "matched_itemids": int(g["itemid"].nunique()),
                "canonical_vasopressor_itemids": int(g["canonical_vasopressor"].sum()),
            })
    safe_write_csv(pd.DataFrame(summary), out / "event_definition_audit_summary.csv")


if __name__ == "__main__":
    main()
