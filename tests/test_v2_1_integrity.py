from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from preregistration_stats import (
    one_sided_centered_bootstrap_pvalue,
    patient_cluster_refit_indices,
)
from registration_gate import require_osf_registration


ROOT = Path(__file__).resolve().parents[1]


def load_numbered(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "src" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


cohort = load_numbered("cohort_v21", "104_build_corrected_landmark12_v2_1_cohorts.py")
features = load_numbered("features_v21", "105_build_enhanced_structured_baseline_v2_1.py")


class V21IntegrityTests(unittest.TestCase):
    def test_adult_threshold_and_nicu(self):
        age = pd.Series([17.99, 18.0, 45.0, 300.0, np.nan])
        unit = pd.Series(["MICU", "MICU", "NICU", "MICU", "MICU"])
        keep = cohort.adult_eligibility_mask(age, unit).tolist()
        self.assertEqual(keep, [False, True, False, True, False])

    def test_deidentified_extreme_age_is_computable(self):
        age = cohort.age_years_at_icu(pd.Timestamp("2100-01-01"), pd.Timestamp("1800-01-01"))
        self.assertGreater(age, 299)

    def test_gcs_airway_values_missing_rule(self):
        self.assertTrue(features.is_gcs_verbal_airway_value("1.0 ET/Trach"))
        self.assertTrue(features.is_gcs_verbal_airway_value("No Response-ETT"))
        self.assertFalse(features.is_gcs_verbal_airway_value("1"))
        self.assertFalse(features.is_gcs_verbal_airway_value("No Response"))

    def test_language_regexes(self):
        vent = cohort.compile_rx(cohort.LANGUAGE_PATTERNS["invasive_ventilation"])
        rrt = cohort.compile_rx(cohort.LANGUAGE_PATTERNS["renal_replacement_therapy"])
        death = cohort.compile_rx(cohort.LANGUAGE_PATTERNS["icu_death"])

        self.assertRegex("patient was reintubated overnight", vent)
        self.assertIsNone(vent.search("BiPAP continued overnight"))

        self.assertRegex("started hemodialysis today", rrt)
        self.assertIsNone(rrt.search("HD stable"))
        self.assertIsNone(rrt.search("HD#3"))
        self.assertIsNone(rrt.search("rapid response team called"))

        self.assertRegex("withdrawal of care discussed", death)

    def test_control_event_time_is_blank(self):
        event = pd.Series(pd.to_datetime(["2026-01-01", "2026-01-02"]))
        case = pd.Series([True, False])
        masked = cohort.case_only_event_time(event, case)
        self.assertFalse(pd.isna(masked.iloc[0]))
        self.assertTrue(pd.isna(masked.iloc[1]))

    def test_registration_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                require_osf_registration(td)

            p = Path(td) / "docs" / "registration" / "osf_registration.json"
            p.parent.mkdir(parents=True)
            p.write_text(
                json.dumps(
                    {
                        "status": "registered",
                        "registration_id": "abcd1",
                        "registered_at": "2026-10-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            data = require_osf_registration(td)
            self.assertEqual(data["registration_id"], "abcd1")

    def test_expected_count_contract(self):
        path = ROOT / "config" / "corrected_landmark12_v2_1_expected_counts.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_job"], "K7Q3M8R4")
        self.assertEqual(
            contract["artifact_sha256"],
            "662afa8b5535d44037e2e7dc07cc02f32a2356caef7369294591db7996b67b19",
        )
        primary = contract["outcomes"]
        self.assertEqual(primary["invasive_ventilation"]["rows"], 11116)
        self.assertEqual(primary["invasive_ventilation"]["cases"], 279)
        self.assertEqual(primary["renal_replacement_therapy"]["cases"], 314)
        self.assertEqual(primary["icu_death"]["cases"], 521)
        explicit = contract["sensitivity_outcomes"]["invasive_ventilation_explicit_evidence"]
        self.assertEqual(
            explicit["controls"],
            primary["invasive_ventilation"]["controls"],
        )

    def test_patient_bootstrap_keeps_fixed_fold(self):
        subject = np.array([1, 1, 2, 3, 3, 4, 5, 5])
        folds = np.array([1, 1, 2, 1, 1, 2, 1, 1])
        rng = np.random.default_rng(7)
        splits = patient_cluster_refit_indices(subject, folds, rng)
        for fold, (tr, te) in splits.items():
            if len(tr):
                self.assertTrue(np.all(folds[tr] != fold))
            if len(te):
                self.assertTrue(np.all(folds[te] == fold))
            self.assertTrue(set(subject[tr]).isdisjoint(set(subject[te])))

    def test_one_sided_bootstrap_pvalue(self):
        observed = 0.02
        bootstrap = np.array([0.016, 0.018, 0.019, 0.020, 0.021, 0.023])
        p = one_sided_centered_bootstrap_pvalue(observed, bootstrap)
        expected = (1 + np.sum((bootstrap - observed) >= observed)) / (len(bootstrap) + 1)
        self.assertAlmostEqual(p, expected)
        self.assertLessEqual(p, 1.0)


if __name__ == "__main__":
    unittest.main()
