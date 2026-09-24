from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

CSV_ENCODINGS=["utf-8-sig","utf-8","gb18030"]


def read_csv_robust(path: Path) -> pd.DataFrame:
    last=None
    for enc in CSV_ENCODINGS:
        try:
            return pd.read_csv(path,encoding=enc,low_memory=False)
        except UnicodeDecodeError as exc:
            last=exc
    if last is not None:
        raise last
    return pd.read_csv(path,low_memory=False)


def norm(x: str) -> str:
    return re.sub(r"[^a-z0-9]+","",str(x).lower())


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    root=Path(args.root).expanduser().resolve()
    out=Path(args.output).expanduser().resolve()
    matches=[p for p in root.rglob("datDictionary.csv") if not p.name.startswith("._")]
    if len(matches)!=1:
        raise RuntimeError(f"Expected exactly one datDictionary.csv, found {len(matches)}")
    df=read_csv_robust(matches[0])
    required={"table_name","column_name","description"}
    if not required.issubset(df.columns):
        raise RuntimeError(f"Dictionary missing columns: {sorted(required-set(df.columns))}")

    df=df.copy()
    df["_table_norm"]=df["table_name"].map(norm)
    df["_col_norm"]=df["column_name"].map(norm)

    targets=[
        ("dtnursingchart","charttime"),
        ("dtnursingchart","nursingdesc"),
        ("dtdrugs","drugtime"),
        ("dtdrugs","drugname"),
        ("dttransfer","starttime"),
        ("dttransfer","stoptime"),
        ("dttransfer","transferdept"),
        ("dtbaseline","icudischargetime"),
        ("dtbaseline","dischargedatetime"),
    ]
    rows=[]
    for table,col in targets:
        hit=df[(df["_table_norm"].str.contains(table,regex=False)) & (df["_col_norm"].str.contains(col,regex=False))]
        for r in hit[["table_name","column_name","description"]].itertuples(index=False):
            rows.append({"target_table":table,"target_column":col,"table_name":str(r.table_name),"column_name":str(r.column_name),"description":str(r.description)})

    time_like=df[df["_col_norm"].str.contains("time",regex=False)][["table_name","column_name","description"]]
    time_rows=[
        {"table_name":str(r.table_name),"column_name":str(r.column_name),"description":str(r.description)}
        for r in time_like.itertuples(index=False)
    ]

    report={
        "dataset":"Zigong Fourth People's Hospital critical care infection database v1.1",
        "analysis":"Local data-dictionary timing metadata audit",
        "local_only":True,
        "contains_note_text":False,
        "contains_patient_identifiers":False,
        "dictionary_rows_total":int(len(df)),
        "unique_table_names":sorted(df["table_name"].astype(str).unique().tolist()),
        "target_rows":rows,
        "all_time_like_rows":time_rows,
        "guardrail":"Metadata only. Do not infer or apply any clock correction unless the dictionary and empirical audits jointly support it."
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
