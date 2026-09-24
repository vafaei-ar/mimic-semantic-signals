from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

from runrelay_progress import update_progress


def load_dg_helpers():
    path=Path(__file__).with_name("66_run_diffusiongemma_hf_native_multitask.py")
    spec=importlib.util.spec_from_file_location("dg_multitask_helpers_for_zigong",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen DiffusionGemma helpers.")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def load_cases_without_labels(path: Path) -> list[dict]:
    out=[]
    seen=set()
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec=json.loads(line)
            if rec.get("synthetic_only") is True or rec.get("local_only") is not True:
                raise RuntimeError("Frozen Zigong cohort contains an invalid local/synthetic flag.")
            case_id=str(rec.get("case_id"))
            note=rec.get("model_state",{}).get("clinical_note")
            if not case_id or case_id=="None" or case_id in seen:
                raise RuntimeError("Missing or duplicate case_id in frozen Zigong cohort.")
            if not isinstance(note,str) or not note.strip():
                raise RuntimeError("Blank clinical note in frozen Zigong cohort.")
            seen.add(case_id)
            # Deliberately retain only case_id and note. Do not inspect metadata labels.
            out.append({"case_id":case_id,"clinical_note":note})
    if not out:
        raise RuntimeError("No frozen Zigong notes found.")
    return out


def existing_success_ids(path: Path) -> set[str]:
    ids=set()
    if not path.exists():
        return ids
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec=json.loads(line)
            except Exception:
                continue
            if rec.get("status")=="ok" and rec.get("case_id") is not None:
                ids.add(str(rec["case_id"]))
    return ids


def main():
    ap=argparse.ArgumentParser(description="Frozen DiffusionGemma inference on direct-Chinese Zigong ventilation notes.")
    ap.add_argument("--cases",required=True)
    ap.add_argument("--model-dir",required=True)
    ap.add_argument("--raw-output",required=True)
    ap.add_argument("--report",required=True)
    ap.add_argument("--expected-total",type=int,default=340)
    ap.add_argument("--chunk-tokens",type=int,default=977)
    ap.add_argument("--chunk-overlap",type=int,default=97)
    ap.add_argument("--max-chunks",type=int,default=8)
    ap.add_argument("--max-new-tokens",type=int,default=256)
    ap.add_argument("--parse-retries",type=int,default=2)
    ap.add_argument("--seed",type=int,default=20260924)
    args=ap.parse_args()

    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    os.environ["HF_DATASETS_OFFLINE"]="1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"

    import torch
    import transformers
    from transformers import AutoProcessor, DiffusionGemmaForBlockDiffusion

    if not torch.cuda.is_available() or torch.cuda.device_count()<2:
        raise RuntimeError("Frozen DiffusionGemma Zigong inference requires two visible GPUs.")

    helper=load_dg_helpers()
    cases=load_cases_without_labels(Path(args.cases).expanduser().resolve())
    if len(cases)!=args.expected_total:
        raise RuntimeError(f"Expected {args.expected_total} Zigong notes, found {len(cases)}")

    model_dir=Path(args.model_dir).expanduser().resolve()
    raw_path=Path(args.raw_output).expanduser().resolve()
    report_path=Path(args.report).expanduser().resolve()
    raw_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.parent.mkdir(parents=True,exist_ok=True)

    existing=existing_success_ids(raw_path)
    valid_case_ids={x["case_id"] for x in cases}
    if not existing.issubset(valid_case_ids):
        raise RuntimeError("Raw output contains case IDs outside the frozen Zigong cohort.")

    load_started=time.perf_counter()
    processor=AutoProcessor.from_pretrained(str(model_dir),local_files_only=True)
    model=DiffusionGemmaForBlockDiffusion.from_pretrained(
        str(model_dir),
        dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
        local_files_only=True,
        attn_implementation="sdpa",
    )
    model.eval()
    model_load_seconds=time.perf_counter()-load_started
    tok=processor.tokenizer
    first_device=next(model.parameters()).device

    new_success=0
    new_failures=0
    truncated=0
    retries_total=0
    chunks_retry=0
    note_tokens=[]
    chunk_counts=[]
    seconds=[]
    error_types=Counter()
    all_scores={name:[] for name in helper.EXPECTED}
    started=time.perf_counter()

    def safe_report(status:str):
        scores={}
        for name,vals in all_scores.items():
            scores[name]={
                "n_new":len(vals),
                "unique_values_new":sorted(set(vals)),
                "mean_new":statistics.fmean(vals) if vals else None,
                "intermediate_fraction_new":(
                    sum(1 for v in vals if 0.0<v<1.0)/len(vals) if vals else None
                ),
            }
        return {
            "analysis":"Frozen direct-Chinese Zigong DiffusionGemma semantic inference v1",
            "protocol":"docs/zigong_diffusiongemma_external_transport_protocol_v1.md",
            "eligibility_freeze":"docs/zigong_direct_chinese_model_eligibility_freeze.md",
            "status":status,
            "local_only":True,
            "network_required":False,
            "clinical_note_inference_performed":True,
            "zigong_outcome_labels_read_or_used":False,
            "contains_note_text":False,
            "contains_case_ids":False,
            "contains_patient_level_scores":False,
            "row_level_predictions_shared":False,
            "model":"google/diffusiongemma-26B-A4B-it",
            "backend":"transformers_native_bf16",
            "score_definition":"Prompted zero-shot 0-1 support scores for the frozen eight semantic constructs; not Jev noul probabilities.",
            "aggregation_across_chunks":"maximum for seven concern constructs; minimum for reassuring_stability",
            "torch_version":torch.__version__,
            "torch_cuda_version":torch.version.cuda,
            "transformers_version":transformers.__version__,
            "seed":args.seed,
            "seed_schedule":"base_seed + frozen_note_ordinal*1000 + chunk_index*10 + attempt",
            "expected_total":args.expected_total,
            "resumed_successes":len(existing),
            "new_successes":new_success,
            "new_failures":new_failures,
            "successful_rows_available":len(existing)+new_success,
            "truncated_by_max_chunks":truncated,
            "parse_retries_used_total":retries_total,
            "chunks_using_parse_retry":chunks_retry,
            "note_tokens_summary_new":helper.safe_summary(note_tokens),
            "chunks_summary_new":helper.safe_summary(chunk_counts),
            "seconds_per_new_attempt_summary":helper.safe_summary(seconds),
            "error_type_counts":dict(error_types),
            "context_policy":{
                "note_chunk_tokens":args.chunk_tokens,
                "chunk_overlap_tokens":args.chunk_overlap,
                "max_chunks":args.max_chunks,
                "max_new_tokens":args.max_new_tokens,
            },
            "parse_retry_policy":{
                "max_retries_after_initial_generation":args.parse_retries,
                "prompt_changes_on_retry":False,
                "acceptance":"first completion containing all eight numeric scores in [0,1]",
            },
            "per_construct_new_score_summary":scores,
            "model_load_seconds":model_load_seconds,
            "run_elapsed_seconds":time.perf_counter()-started,
            "next_gate":"External transport evaluation only after all 340 frozen Zigong notes have successful local scores.",
        }

    mode="a" if raw_path.exists() else "w"
    with raw_path.open(mode,encoding="utf-8") as out:
        for ordinal,case in enumerate(cases):
            if case["case_id"] in existing:
                continue
            attempt_started=time.perf_counter()
            try:
                ids=tok(case["clinical_note"],add_special_tokens=False)["input_ids"]
                chunks,is_truncated=helper.chunk_token_ids(
                    ids,size=args.chunk_tokens,overlap=args.chunk_overlap,max_chunks=args.max_chunks
                )
                if is_truncated:
                    truncated += 1
                chunk_scores=[]
                retry_counts=[]
                for chunk_index,chunk_ids in enumerate(chunks):
                    chunk_text=tok.decode(chunk_ids,skip_special_tokens=True)
                    inputs=processor.apply_chat_template(
                        [{"role":"user","content":helper.build_prompt(chunk_text)}],
                        tokenize=True,
                        add_generation_prompt=True,
                        return_dict=True,
                        return_tensors="pt",
                        enable_thinking=False,
                    )
                    inputs={k:v.to(first_device) if hasattr(v,"to") else v for k,v in inputs.items()}
                    input_len=inputs["input_ids"].shape[-1]
                    parsed=None
                    used=0
                    last_error=None
                    for attempt in range(args.parse_retries+1):
                        seed=args.seed+ordinal*1000+chunk_index*10+attempt
                        torch.manual_seed(seed)
                        torch.cuda.manual_seed_all(seed)
                        with torch.inference_mode():
                            generated=model.generate(**inputs,max_new_tokens=args.max_new_tokens)
                        sequences=getattr(generated,"sequences",generated)
                        if sequences.ndim!=2 or sequences.shape[0]!=1:
                            raise RuntimeError(f"Unexpected generated shape {tuple(sequences.shape)}")
                        completion=sequences[0,input_len:].detach().cpu().tolist()
                        decoded=tok.decode(completion,skip_special_tokens=True)
                        try:
                            parsed=helper.extract_scores(decoded)
                            used=attempt
                            break
                        except ValueError as exc:
                            last_error=exc
                    if parsed is None:
                        raise RuntimeError(f"Parse retry exhausted: {last_error}")
                    chunk_scores.append(parsed)
                    retry_counts.append(used)
                aggregated=helper.aggregate_scores(chunk_scores)
                answers={
                    name:{
                        "score":float(aggregated[name]),
                        "chunk_values":[float(x[name]) for x in chunk_scores],
                    }
                    for name in helper.EXPECTED
                }
                rec={
                    "case_id":case["case_id"],
                    "local_only":True,
                    "status":"ok",
                    "model":"google/diffusiongemma-26B-A4B-it",
                    "backend":"transformers_native_bf16_prompted_semantic_scores",
                    "metadata":{
                        "note_tokens":len(ids),
                        "chunks_evaluated":len(chunks),
                        "truncated_by_max_chunks":bool(is_truncated),
                        "parse_retries_by_chunk":retry_counts,
                    },
                    "response":{"answers":answers},
                }
                out.write(json.dumps(rec,ensure_ascii=False)+"\n")
                out.flush()
                new_success += 1
                retries_total += sum(retry_counts)
                chunks_retry += sum(x>0 for x in retry_counts)
                note_tokens.append(len(ids))
                chunk_counts.append(len(chunks))
                seconds.append(time.perf_counter()-attempt_started)
                for name,val in aggregated.items():
                    all_scores[name].append(float(val))
            except Exception as exc:
                new_failures += 1
                error_types[type(exc).__name__] += 1
                out.write(json.dumps({
                    "case_id":case["case_id"],
                    "local_only":True,
                    "status":"error",
                    "error_type":type(exc).__name__,
                })+"\n")
                out.flush()

            current=len(existing)+new_success+new_failures
            if current%10==0 or current==args.expected_total:
                update_progress(
                    current=current,total=args.expected_total,
                    phase="zigong_diffusiongemma_inference",
                    message=f"Processed {current}/{args.expected_total} frozen Zigong notes",
                    unit="note",
                )
            if current%25==0:
                report_path.write_text(json.dumps(safe_report("running"),indent=2)+"\n",encoding="utf-8")

    final=safe_report("completed" if new_failures==0 and len(existing)+new_success==args.expected_total else "incomplete")
    report_path.write_text(json.dumps(final,indent=2)+"\n",encoding="utf-8")
    if final["status"]!="completed":
        raise RuntimeError(f"Zigong DiffusionGemma inference incomplete: {final}")


if __name__=="__main__":
    main()
