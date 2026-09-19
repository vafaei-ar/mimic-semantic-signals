from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCHEMAS = {
    "ADMISSIONS.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","ADMITTIME","DISCHTIME","DEATHTIME",
        "ADMISSION_TYPE","ADMISSION_LOCATION","DISCHARGE_LOCATION","INSURANCE",
        "LANGUAGE","RELIGION","MARITAL_STATUS","ETHNICITY","EDREGTIME","EDOUTTIME",
        "DIAGNOSIS","HOSPITAL_EXPIRE_FLAG","HAS_CHARTEVENTS_DATA",
    ],
    "ICUSTAYS.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","ICUSTAY_ID","DBSOURCE","FIRST_CAREUNIT",
        "LAST_CAREUNIT","FIRST_WARDID","LAST_WARDID","INTIME","OUTTIME","LOS",
    ],
    "NOTEEVENTS.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","CHARTDATE","CHARTTIME","STORETIME",
        "CATEGORY","DESCRIPTION","CGID","ISERROR","TEXT",
    ],
    "D_ITEMS.csv.gz": [
        "ROW_ID","ITEMID","LABEL","ABBREVIATION","DBSOURCE","LINKSTO","CATEGORY",
        "UNITNAME","PARAM_TYPE","CONCEPTID",
    ],
    "D_LABITEMS.csv.gz": [
        "ROW_ID","ITEMID","LABEL","FLUID","CATEGORY","LOINC_CODE",
    ],
    "CHARTEVENTS.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","ICUSTAY_ID","ITEMID","CHARTTIME","STORETIME",
        "CGID","VALUE","VALUENUM","VALUEUOM","WARNING","ERROR","RESULTSTATUS","STOPPED",
    ],
    "LABEVENTS.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","ITEMID","CHARTTIME","VALUE","VALUENUM",
        "VALUEUOM","FLAG",
    ],
    "INPUTEVENTS_CV.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","ICUSTAY_ID","CHARTTIME","ITEMID","AMOUNT",
        "AMOUNTUOM","RATE","RATEUOM","STORETIME","CGID","ORDERID","LINKORDERID",
        "STOPPED","NEWBOTTLE","ORIGINALAMOUNT","ORIGINALAMOUNTUOM","ORIGINALROUTE",
        "ORIGINALRATE","ORIGINALRATEUOM","ORIGINALSITE",
    ],
    "INPUTEVENTS_MV.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","ICUSTAY_ID","STARTTIME","ENDTIME","ITEMID",
        "AMOUNT","AMOUNTUOM","RATE","RATEUOM","STORETIME","CGID","ORDERID",
        "LINKORDERID","ORDERCATEGORYNAME","SECONDARYORDERCATEGORYNAME",
        "ORDERCOMPONENTTYPEDESCRIPTION","ORDERCATEGORYDESCRIPTION","PATIENTWEIGHT",
        "TOTALAMOUNT","TOTALAMOUNTUOM","ISOPENBAG","CONTINUEINNEXTDEPT",
        "CANCELREASON","STATUSDESCRIPTION","COMMENTS_EDITEDBY","COMMENTS_CANCELEDBY",
        "COMMENTS_DATE","ORIGINALAMOUNT","ORIGINALRATE",
    ],
    "PROCEDUREEVENTS_MV.csv.gz": [
        "ROW_ID","SUBJECT_ID","HADM_ID","ICUSTAY_ID","STARTTIME","ENDTIME","ITEMID",
        "VALUE","VALUEUOM","LOCATION","LOCATIONCATEGORY","STORETIME","CGID","ORDERID",
        "LINKORDERID","ORDERCATEGORYNAME","SECONDARYORDERCATEGORYNAME",
        "ORDERCATEGORYDESCRIPTION","ISOPENBAG","CONTINUEINNEXTDEPT","CANCELREASON",
        "STATUSDESCRIPTION","COMMENTS_EDITEDBY","COMMENTS_CANCELEDBY","COMMENTS_DATE",
    ],
}

VITAL_ITEMS = {
    "carevue": {
        "hr": (211, "Heart Rate", "bpm"),
        "map": (52, "Arterial BP Mean", "mmHg"),
        "rr": (618, "Respiratory Rate", "insp/min"),
        "spo2": (646, "SpO2", "%"),
        "temp": (678, "Temperature F", "Deg. F"),
    },
    "metavision": {
        "hr": (220045, "Heart Rate", "bpm"),
        "map": (220052, "Arterial Blood Pressure mean", "mmHg"),
        "rr": (220210, "Respiratory Rate", "insp/min"),
        "spo2": (220277, "O2 saturation pulseoxymetry", "%"),
        "temp": (223761, "Temperature Fahrenheit", "Deg. F"),
    },
}

LAB_ITEMS = {
    "lactate": (50813, "Lactate", "Blood", "Blood Gas", "mmol/L"),
    "creatinine": (50912, "Creatinine", "Blood", "Chemistry", "mg/dL"),
    "wbc": (51301, "White Blood Cells", "Blood", "Hematology", "K/uL"),
}

PRESSORS = {
    "carevue": (30047, "Levophed", "inputevents_cv"),
    "metavision": (221906, "Norepinephrine", "inputevents_mv"),
}

INTUBATION_ITEM = (224385, "Intubation")


def _fmt(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _note_text(
    level: int,
    event_type: str,
    discordant: bool,
    rng: np.random.Generator,
) -> str:
    stable = [
        "Patient resting comfortably. No acute change during this shift. Breathing appears unlabored and current plan continues.",
        "Clinical status remains similar to earlier assessment. Patient is comfortable and no escalation is being considered.",
        "Patient remains stable on current support. No new concern was raised during the bedside assessment.",
    ]
    intermediate = [
        "Patient appears more tired than earlier. Respiratory effort is intermittently increased. Team updated and watching the trajectory closely.",
        "Patient looks somewhat less well than the prior assessment. Response to the current plan is incomplete and closer observation is planned.",
        "There is a subtle change from earlier in the shift. The patient needs more attention, although measured vital signs remain near the previous range.",
    ]
    high_general = [
        "Patient is increasingly difficult to arouse compared with the prior assessment. Breathing is more labored and response to recent treatment has been limited. Team is considering escalation.",
        "Clinical appearance is worsening despite the current plan. The bedside team has growing concern and is discussing a higher level of support.",
        "Patient looks substantially worse than earlier. Current treatment has not produced the expected response and escalation is being considered.",
    ]
    high_by_event = {
        "vasopressor": [
            "Patient appears poorly perfused with cool extremities and lower urine output. Blood pressure has not yet changed substantially, but the team is concerned about hemodynamic deterioration.",
            "Bedside appearance raises concern for evolving circulatory instability. The team is reassessing response to fluids and discussing vasoactive support.",
        ],
        "intubation": [
            "Work of breathing is progressively increasing and the patient looks fatigued. Oxygen measurements are not yet severely abnormal, but the team is concerned respiratory support may need escalation.",
            "Respiratory effort has worsened and the patient is tiring. The team is discussing whether invasive airway support will be needed.",
        ],
        "death": [
            "Overall clinical condition is worsening with reduced responsiveness and poor reserve. The team is concerned that the patient may deteriorate further despite current treatment.",
            "The patient appears increasingly frail and less responsive to treatment. Clinical concern is high despite only modest changes in recorded measurements.",
        ],
    }

    if level <= 0:
        return str(rng.choice(stable))
    if level == 1:
        return str(rng.choice(intermediate))

    text = str(rng.choice(high_by_event.get(event_type, []) + high_general))
    if discordant and "not yet" not in text and "measured" not in text:
        text += " Recorded physiology remains less abnormal than the bedside appearance suggests."
    return text


def _physiology(
    hours_before: float | None,
    event_type: str,
    discordant: bool,
    rng: np.random.Generator,
) -> dict[str, float]:
    values = {
        "hr": 80 + rng.normal(0, 5),
        "map": 80 + rng.normal(0, 4),
        "rr": 18 + rng.normal(0, 2),
        "spo2": 97 + rng.normal(0, 1),
        "temp": 98.6 + rng.normal(0, 0.5),
        "lactate": max(0.7, 1.4 + rng.normal(0, 0.3)),
        "creatinine": max(0.4, 1.0 + rng.normal(0, 0.2)),
        "wbc": max(2.0, 9.0 + rng.normal(0, 1.5)),
    }

    if hours_before is None or hours_before < 0:
        return values

    structured_onset = 3.0 if discordant else 10.0
    severity = np.clip(
        (structured_onset - hours_before) / max(structured_onset, 0.1),
        0,
        1,
    )
    if severity <= 0:
        return values

    if event_type == "vasopressor":
        values["map"] -= 25 * severity
        values["hr"] += 25 * severity
        values["lactate"] += 2.5 * severity
    elif event_type == "intubation":
        values["rr"] += 14 * severity
        values["spo2"] -= 10 * severity
        values["hr"] += 15 * severity
    elif event_type == "death":
        values["map"] -= 18 * severity
        values["rr"] += 8 * severity
        values["spo2"] -= 6 * severity
        values["lactate"] += 2.0 * severity
        values["creatinine"] += 0.8 * severity

    return values


def _write(df: pd.DataFrame, columns: list[str], path: Path) -> None:
    for col in columns:
        if col not in df:
            df[col] = np.nan
    df[columns].to_csv(path, index=False, compression="gzip")


def generate(root: Path, n_admissions: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    mimic = root / "mimiciii" / "1.4"
    mimic.mkdir(parents=True, exist_ok=True)

    admissions = []
    icustays = []
    notes = []
    charts = []
    labs = []
    input_mv = []
    input_cv = []
    procedures = []
    truth = []

    row = {name: 1 for name in SCHEMAS}
    start0 = pd.Timestamp("2100-01-01 08:00:00")

    event_types = np.array(["none", "vasopressor", "intubation", "death"])
    event_probabilities = np.array([0.40, 0.20, 0.20, 0.20])

    for i in range(n_admissions):
        subject_id = 900000 + i
        hadm_id = 1900000 + i
        icustay_id = 2900000 + i

        dbsource = "carevue" if rng.random() < 0.58 else "metavision"
        event_type = str(rng.choice(event_types, p=event_probabilities))
        if event_type == "intubation":
            dbsource = "metavision"

        admit = start0 + pd.Timedelta(days=i * 2)
        icu_in = admit + pd.Timedelta(hours=float(rng.integers(1, 5)))
        discordant = bool(event_type != "none" and rng.random() < 0.35)

        event_time = None
        if event_type != "none":
            event_time = icu_in + pd.Timedelta(hours=float(rng.integers(36, 73)))
            if event_type == "death":
                discharge = event_time
            else:
                discharge = event_time + pd.Timedelta(
                    hours=float(rng.integers(12, 31))
                )
        else:
            discharge = icu_in + pd.Timedelta(hours=float(rng.integers(60, 97)))

        death_time = event_time if event_type == "death" else None

        admissions.append(
            {
                "ROW_ID": row["ADMISSIONS.csv.gz"],
                "SUBJECT_ID": subject_id,
                "HADM_ID": hadm_id,
                "ADMITTIME": _fmt(admit),
                "DISCHTIME": _fmt(discharge),
                "DEATHTIME": _fmt(death_time),
                "ADMISSION_TYPE": "EMERGENCY",
                "ADMISSION_LOCATION": "EMERGENCY ROOM ADMIT",
                "DISCHARGE_LOCATION": "DEAD/EXPIRED"
                if event_type == "death"
                else "HOME",
                "INSURANCE": "Synthetic",
                "LANGUAGE": "ENGL",
                "RELIGION": "UNOBTAINABLE",
                "MARITAL_STATUS": "SINGLE",
                "ETHNICITY": "SYNTHETIC",
                "EDREGTIME": _fmt(admit - pd.Timedelta(hours=2)),
                "EDOUTTIME": _fmt(admit),
                "DIAGNOSIS": "SYNTHETIC CRITICAL ILLNESS",
                "HOSPITAL_EXPIRE_FLAG": int(event_type == "death"),
                "HAS_CHARTEVENTS_DATA": 1,
            }
        )
        row["ADMISSIONS.csv.gz"] += 1

        los_days = (discharge - icu_in).total_seconds() / 86400
        icustays.append(
            {
                "ROW_ID": row["ICUSTAYS.csv.gz"],
                "SUBJECT_ID": subject_id,
                "HADM_ID": hadm_id,
                "ICUSTAY_ID": icustay_id,
                "DBSOURCE": dbsource,
                "FIRST_CAREUNIT": "MICU",
                "LAST_CAREUNIT": "MICU",
                "FIRST_WARDID": 1,
                "LAST_WARDID": 1,
                "INTIME": _fmt(icu_in),
                "OUTTIME": _fmt(discharge),
                "LOS": round(los_days, 4),
            }
        )
        row["ICUSTAYS.csv.gz"] += 1

        series_end = event_time if event_time is not None else discharge

        t = icu_in
        while t <= series_end:
            hours_before = (
                None
                if event_time is None
                else (event_time - t).total_seconds() / 3600
            )
            physiology = _physiology(
                hours_before,
                event_type,
                discordant,
                rng,
            )
            for key in ["hr", "map", "rr", "spo2", "temp"]:
                itemid, _, unit = VITAL_ITEMS[dbsource][key]
                value = round(float(physiology[key]), 2)
                charts.append(
                    {
                        "ROW_ID": row["CHARTEVENTS.csv.gz"],
                        "SUBJECT_ID": subject_id,
                        "HADM_ID": hadm_id,
                        "ICUSTAY_ID": icustay_id,
                        "ITEMID": itemid,
                        "CHARTTIME": _fmt(t),
                        "STORETIME": _fmt(t + pd.Timedelta(minutes=5)),
                        "CGID": 70000 + (i % 50),
                        "VALUE": str(value),
                        "VALUENUM": value,
                        "VALUEUOM": unit,
                        "WARNING": 0,
                        "ERROR": 0,
                        "RESULTSTATUS": "",
                        "STOPPED": "",
                    }
                )
                row["CHARTEVENTS.csv.gz"] += 1
            t += pd.Timedelta(hours=2)

        t = icu_in
        while t <= series_end:
            hours_before = (
                None
                if event_time is None
                else (event_time - t).total_seconds() / 3600
            )
            physiology = _physiology(
                hours_before,
                event_type,
                discordant,
                rng,
            )
            for key in ["lactate", "creatinine", "wbc"]:
                itemid, _, _, _, unit = LAB_ITEMS[key]
                value = round(float(physiology[key]), 2)
                labs.append(
                    {
                        "ROW_ID": row["LABEVENTS.csv.gz"],
                        "SUBJECT_ID": subject_id,
                        "HADM_ID": hadm_id,
                        "ITEMID": itemid,
                        "CHARTTIME": _fmt(t),
                        "VALUE": str(value),
                        "VALUENUM": value,
                        "VALUEUOM": unit,
                        "FLAG": "abnormal"
                        if key == "lactate" and value > 2.0
                        else "",
                    }
                )
                row["LABEVENTS.csv.gz"] += 1
            t += pd.Timedelta(hours=12)

        t = icu_in + pd.Timedelta(hours=3)
        note_index = 0
        while t < series_end:
            hours_before = (
                None
                if event_time is None
                else (event_time - t).total_seconds() / 3600
            )

            if event_time is None or hours_before is None or hours_before > 24:
                concern_level = 0
            elif hours_before > 12:
                concern_level = 1
            else:
                concern_level = 2

            if (
                event_type != "none"
                and discordant
                and hours_before is not None
                and 3 < hours_before <= 18
            ):
                concern_level = 2

            if dbsource == "carevue":
                category = "Nursing/other" if note_index % 4 != 3 else "General"
            else:
                category = "Nursing" if note_index % 4 != 3 else "General"

            note_text = _note_text(
                concern_level,
                event_type,
                discordant,
                rng,
            )
            notes.append(
                {
                    "ROW_ID": row["NOTEEVENTS.csv.gz"],
                    "SUBJECT_ID": subject_id,
                    "HADM_ID": hadm_id,
                    "CHARTDATE": pd.Timestamp(t).strftime("%Y-%m-%d"),
                    "CHARTTIME": _fmt(t),
                    "STORETIME": _fmt(t + pd.Timedelta(minutes=20)),
                    "CATEGORY": category,
                    "DESCRIPTION": "Synthetic bedside note",
                    "CGID": 70000 + (i % 50),
                    "ISERROR": "",
                    "TEXT": note_text,
                }
            )
            row["NOTEEVENTS.csv.gz"] += 1

            if note_index % 4 == 0:
                physician_text = _note_text(
                    max(0, concern_level - 1),
                    event_type,
                    discordant,
                    rng,
                )
                notes.append(
                    {
                        "ROW_ID": row["NOTEEVENTS.csv.gz"],
                        "SUBJECT_ID": subject_id,
                        "HADM_ID": hadm_id,
                        "CHARTDATE": pd.Timestamp(t).strftime("%Y-%m-%d"),
                        "CHARTTIME": _fmt(t),
                        "STORETIME": _fmt(t + pd.Timedelta(minutes=30)),
                        "CATEGORY": "Physician",
                        "DESCRIPTION": "Synthetic progress note",
                        "CGID": 71000 + (i % 20),
                        "ISERROR": "",
                        "TEXT": physician_text,
                    }
                )
                row["NOTEEVENTS.csv.gz"] += 1

            truth.append(
                {
                    "SUBJECT_ID": subject_id,
                    "HADM_ID": hadm_id,
                    "ICUSTAY_ID": icustay_id,
                    "DBSOURCE": dbsource,
                    "EVENT_TYPE": event_type,
                    "EVENT_TIME": _fmt(event_time),
                    "NOTE_TIME": _fmt(t),
                    "HOURS_BEFORE_EVENT": hours_before
                    if hours_before is not None
                    else np.nan,
                    "GOLD_CONCERN_LEVEL": concern_level,
                    "GOLD_HIGH_CONCERN": int(concern_level >= 2),
                    "GOLD_DISCORDANT": int(discordant),
                }
            )

            note_index += 1
            t += pd.Timedelta(hours=6)

        if event_type == "vasopressor" and event_time is not None:
            itemid, _, table = PRESSORS[dbsource]
            if table == "inputevents_mv":
                input_mv.append(
                    {
                        "ROW_ID": row["INPUTEVENTS_MV.csv.gz"],
                        "SUBJECT_ID": subject_id,
                        "HADM_ID": hadm_id,
                        "ICUSTAY_ID": icustay_id,
                        "STARTTIME": _fmt(event_time),
                        "ENDTIME": _fmt(event_time + pd.Timedelta(hours=6)),
                        "ITEMID": itemid,
                        "AMOUNT": 6.0,
                        "AMOUNTUOM": "mg",
                        "RATE": 0.1,
                        "RATEUOM": "mcg/kg/min",
                        "STORETIME": _fmt(
                            event_time + pd.Timedelta(minutes=2)
                        ),
                        "CGID": 72000,
                        "ORDERID": 800000 + i,
                        "LINKORDERID": 800000 + i,
                        "ORDERCATEGORYNAME": "Continuous Med",
                        "SECONDARYORDERCATEGORYNAME": "",
                        "ORDERCOMPONENTTYPEDESCRIPTION": "",
                        "ORDERCATEGORYDESCRIPTION": "",
                        "PATIENTWEIGHT": 80.0,
                        "TOTALAMOUNT": 6.0,
                        "TOTALAMOUNTUOM": "mg",
                        "ISOPENBAG": 0,
                        "CONTINUEINNEXTDEPT": 0,
                        "CANCELREASON": 0,
                        "STATUSDESCRIPTION": "FinishedRunning",
                        "COMMENTS_EDITEDBY": "",
                        "COMMENTS_CANCELEDBY": "",
                        "COMMENTS_DATE": "",
                        "ORIGINALAMOUNT": 6.0,
                        "ORIGINALRATE": 0.1,
                    }
                )
                row["INPUTEVENTS_MV.csv.gz"] += 1
            else:
                input_cv.append(
                    {
                        "ROW_ID": row["INPUTEVENTS_CV.csv.gz"],
                        "SUBJECT_ID": subject_id,
                        "HADM_ID": hadm_id,
                        "ICUSTAY_ID": icustay_id,
                        "CHARTTIME": _fmt(event_time),
                        "ITEMID": itemid,
                        "AMOUNT": 6.0,
                        "AMOUNTUOM": "mg",
                        "RATE": 0.1,
                        "RATEUOM": "mcg/kg/min",
                        "STORETIME": _fmt(
                            event_time + pd.Timedelta(minutes=2)
                        ),
                        "CGID": 72000,
                        "ORDERID": 800000 + i,
                        "LINKORDERID": 800000 + i,
                        "STOPPED": "",
                        "NEWBOTTLE": 1,
                        "ORIGINALAMOUNT": 6.0,
                        "ORIGINALAMOUNTUOM": "mg",
                        "ORIGINALROUTE": "IV Drip",
                        "ORIGINALRATE": 0.1,
                        "ORIGINALRATEUOM": "mcg/kg/min",
                        "ORIGINALSITE": "",
                    }
                )
                row["INPUTEVENTS_CV.csv.gz"] += 1

        if event_type == "intubation" and event_time is not None:
            procedures.append(
                {
                    "ROW_ID": row["PROCEDUREEVENTS_MV.csv.gz"],
                    "SUBJECT_ID": subject_id,
                    "HADM_ID": hadm_id,
                    "ICUSTAY_ID": icustay_id,
                    "STARTTIME": _fmt(event_time),
                    "ENDTIME": _fmt(
                        event_time + pd.Timedelta(minutes=20)
                    ),
                    "ITEMID": INTUBATION_ITEM[0],
                    "VALUE": 1.0,
                    "VALUEUOM": "",
                    "LOCATION": "",
                    "LOCATIONCATEGORY": "",
                    "STORETIME": _fmt(
                        event_time + pd.Timedelta(minutes=3)
                    ),
                    "CGID": 72001,
                    "ORDERID": 900000 + i,
                    "LINKORDERID": 900000 + i,
                    "ORDERCATEGORYNAME": "Procedures",
                    "SECONDARYORDERCATEGORYNAME": "",
                    "ORDERCATEGORYDESCRIPTION": "",
                    "ISOPENBAG": 0,
                    "CONTINUEINNEXTDEPT": 0,
                    "CANCELREASON": 0,
                    "STATUSDESCRIPTION": "FinishedRunning",
                    "COMMENTS_EDITEDBY": "",
                    "COMMENTS_CANCELEDBY": "",
                    "COMMENTS_DATE": "",
                }
            )
            row["PROCEDUREEVENTS_MV.csv.gz"] += 1

    d_items = []
    item_row = 1

    for dbsource, vital_map in VITAL_ITEMS.items():
        for _, (itemid, label, unit) in vital_map.items():
            d_items.append(
                {
                    "ROW_ID": item_row,
                    "ITEMID": itemid,
                    "LABEL": label,
                    "ABBREVIATION": label,
                    "DBSOURCE": dbsource,
                    "LINKSTO": "chartevents",
                    "CATEGORY": "Routine Vital Signs",
                    "UNITNAME": unit,
                    "PARAM_TYPE": "Numeric",
                    "CONCEPTID": "",
                }
            )
            item_row += 1

    for dbsource, (itemid, label, linksto) in PRESSORS.items():
        d_items.append(
            {
                "ROW_ID": item_row,
                "ITEMID": itemid,
                "LABEL": label,
                "ABBREVIATION": label,
                "DBSOURCE": dbsource,
                "LINKSTO": linksto,
                "CATEGORY": "Medications",
                "UNITNAME": "mg",
                "PARAM_TYPE": "Solution",
                "CONCEPTID": "",
            }
        )
        item_row += 1

    d_items.append(
        {
            "ROW_ID": item_row,
            "ITEMID": INTUBATION_ITEM[0],
            "LABEL": INTUBATION_ITEM[1],
            "ABBREVIATION": INTUBATION_ITEM[1],
            "DBSOURCE": "metavision",
            "LINKSTO": "procedureevents_mv",
            "CATEGORY": "1-Intubation/Extubation",
            "UNITNAME": "",
            "PARAM_TYPE": "Process",
            "CONCEPTID": "",
        }
    )

    d_labitems = []
    for item_row, (_, (itemid, label, fluid, category, _)) in enumerate(
        LAB_ITEMS.items(),
        start=1,
    ):
        d_labitems.append(
            {
                "ROW_ID": item_row,
                "ITEMID": itemid,
                "LABEL": label,
                "FLUID": fluid,
                "CATEGORY": category,
                "LOINC_CODE": "",
            }
        )

    frames = {
        "ADMISSIONS.csv.gz": pd.DataFrame(admissions),
        "ICUSTAYS.csv.gz": pd.DataFrame(icustays),
        "NOTEEVENTS.csv.gz": pd.DataFrame(notes),
        "D_ITEMS.csv.gz": pd.DataFrame(d_items),
        "D_LABITEMS.csv.gz": pd.DataFrame(d_labitems),
        "CHARTEVENTS.csv.gz": pd.DataFrame(charts),
        "LABEVENTS.csv.gz": pd.DataFrame(labs),
        "INPUTEVENTS_MV.csv.gz": pd.DataFrame(input_mv),
        "INPUTEVENTS_CV.csv.gz": pd.DataFrame(input_cv),
        "PROCEDUREEVENTS_MV.csv.gz": pd.DataFrame(procedures),
    }

    for filename, frame in frames.items():
        _write(frame, SCHEMAS[filename], mimic / filename)

    pd.DataFrame(truth).to_csv(
        root / "synthetic_truth.csv",
        index=False,
    )

    manifest = {
        "synthetic": True,
        "seed": seed,
        "n_admissions": n_admissions,
        "note": (
            "All records and note text are independently generated. "
            "No source clinical text or patient-level data are used."
        ),
        "mimiciii_version_shape": "1.4-compatible study subset",
        "tables": {
            filename: int(len(frame))
            for filename, frame in frames.items()
        },
    }

    (root / "synthetic_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/synthetic_mimic")
    ap.add_argument("--n-admissions", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260919)
    args = ap.parse_args()

    output = Path(args.output).expanduser().resolve()
    generate(output, args.n_admissions, args.seed)
    print(f"Synthetic sandbox written to {output}")


if __name__ == "__main__":
    main()
