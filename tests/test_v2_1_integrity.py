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
    patient_cluster_bootstrap_row_indices,
    patient_cluster_refit_indices,
    paired_prediction_cluster_bootstrap_delta_auc,
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
context_builder = load_numbered("context_builder_v21", "114_build_preregistration_context_features_v2_1.py")
corpus_builder = load_numbered("corpus_builder_v21", "115_build_fixed_note_corpora_v2_1.py")
bootstrap_benchmark = load_numbered("bootstrap_benchmark_v21", "111_benchmark_refit_bootstrap_v2_1.py")


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

    def test_semantic_model_roster_matches_schema(self):
        roster = json.loads(
            (ROOT / "config" / "v2_1_semantic_model_roster.json").read_text(
                encoding="utf-8"
            )
        )
        expected = [x["name"] for x in load_numbered(
            "semantic_schema_v21", "semantic_schema.py"
        ).SEMANTIC_CONSTRUCTS]
        self.assertEqual(roster["primary_constructs"], expected)
        self.assertEqual(roster["primary_semantic_model"], "open_jev")
        self.assertEqual(roster["primary_corpus"], "stripped")
        self.assertEqual(
            roster["excluded_from_state_dominant"],
            ["poor_treatment_response", "escalation_considered"],
        )

    def test_refit_bootstrap_inference_freeze_is_superseded(self):
        path = ROOT / "config" / "v2_1_refit_bootstrap_inference_freeze.json"
        freeze = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(freeze["status"], "superseded_before_registration")
        self.assertEqual(freeze["bootstrap_replicates"], 500)
        self.assertEqual(
            freeze["superseded_by"],
            "config/v2_1_primary_inference_freeze.json",
        )
        self.assertEqual(freeze["runtime_benchmark_job"], "Y5R7M2Q8")
        self.assertFalse(freeze["real_outcome_performance_seen_when_frozen"])

    def test_primary_inference_freeze(self):
        path = ROOT / "config" / "v2_1_primary_inference_freeze.json"
        freeze = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            freeze["status"],
            "frozen_before_v2_1_predictive_performance",
        )
        self.assertEqual(
            freeze["primary_uncertainty"]["bootstrap_replicates"],
            5000,
        )
        self.assertFalse(freeze["formal_hypothesis_testing"])
        self.assertIn("No confirmatory p-values", freeze["multiplicity"])
        self.assertEqual(
            freeze["amendment_basis"]["runtime_benchmark_job"],
            "Y5R7M2Q8",
        )
        self.assertFalse(
            freeze["amendment_basis"]["real_v2_1_predictive_performance_seen"]
        )

    def test_refit_runtime_result_contract(self):
        path = ROOT / "config" / "v2_1_refit_runtime_result_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_job"], "Y5R7M2Q8")
        self.assertEqual(contract["validation_job"], "X4R7M2Q8")
        self.assertAlmostEqual(
            contract["ventilation_exact_refit_seconds"],
            5470.322735227644,
        )
        self.assertGreater(
            contract["ventilation_projected_500_refit_hours_serial"],
            700,
        )
        self.assertFalse(contract["real_predictors_used"])
        self.assertFalse(contract["real_outcome_labels_used"])

    def test_preregistration_power_result_contract(self):
        path = ROOT / "config" / "v2_1_preregistration_power_result_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_job"], "V9R6M4N2")
        self.assertFalse(contract["real_outcome_predictions_used"])
        self.assertFalse(contract["real_outcome_labels_read"])
        self.assertAlmostEqual(
            contract["full_cohort_80pct_mde_at_rho_0_90_holm"]["invasive_ventilation"],
            0.02327854017134698,
        )
        self.assertEqual(contract["note_available_cases"]["icu_death"], 83)

    def test_cv_split_result_contract(self):
        path = ROOT / "config" / "v2_1_cv_split_result_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_job"], "T9R6M4N2")
        self.assertEqual(
            contract["artifact_sha256"],
            "b0bac28207ca07dec3539512eda856d2ead09ab8f7f704cfe8a4d6d800e27484",
        )
        self.assertEqual(
            contract["analyses"]["invasive_ventilation"]["split_sha256"],
            "30d6d4e591bfe3ff0dc736d8619dcead94f1c3880b160dbfed7efbffce727b35",
        )
        self.assertEqual(
            contract["analyses"]["renal_replacement_therapy"]["split_sha256"],
            "1a2b8e23045ac79429bcb65b6ff3c382226be1fbab5a9460f2d8c1ca49bb5ee0",
        )
        self.assertEqual(
            contract["analyses"]["icu_death"]["split_sha256"],
            "444a0dac02358d1d4eafe83b96d3804df30134de00e4b54509beb7bbbe411658",
        )

    def test_preregistration_power_result_contract(self):
        path = ROOT / "config" / "v2_1_preregistration_power_result_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_job"], "V9R6M4N2")
        self.assertEqual(
            contract["artifact_sha256"],
            "2dcc4c23fc222f5db6aa123cfd2b33e96278ce46ae4e478adacaefb9f89ee08a",
        )
        self.assertAlmostEqual(
            contract["full_cohort_mde_80_holm"]["invasive_ventilation"]["0.90"],
            0.02327854017134698,
        )
        self.assertAlmostEqual(
            contract["full_cohort_mde_80_holm"]["renal_replacement_therapy"]["0.90"],
            0.011326027311216855,
        )
        self.assertAlmostEqual(
            contract["full_cohort_mde_80_holm"]["icu_death"]["0.90"],
            0.02413225844794707,
        )

    def test_tfidf_no_note_encoding_is_frozen(self):
        path = ROOT / "config" / "v2_1_semantic_model_roster.json"
        roster = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            roster["tfidf"]["no_note_encoding"],
            "all_zero_sparse_vector",
        )
        self.assertEqual(
            roster["tfidf"]["no_note_context_indicator"],
            "use existing has_note predictor from rich comparator",
        )
        self.assertEqual(roster["tfidf"]["corpus"], "stripped")

    def test_fixed_note_corpus_result_contract(self):
        path = ROOT / "config" / "v2_1_fixed_note_corpus_result_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_job"], "R8Q6M4N2")
        self.assertEqual(
            contract["artifact_sha256"],
            "608cf993ba080afd54e2157a94d506d9406966795f91d78be2550960c600db5c",
        )
        self.assertEqual(contract["primary_corpus"], "stripped")
        for name, info in contract["analyses"].items():
            self.assertEqual(
                info["direct_language_flagged_notes"],
                info["notes_changed_by_stripping"],
                msg=name,
            )

    def test_context_feature_result_contract(self):
        path = ROOT / "config" / "v2_1_context_feature_result_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_job"], "G8R6Q4M2")
        self.assertEqual(
            contract["artifact_sha256"],
            "04cd6ab090518ad570909e57705d1331ceefeb632327666c9c4fa238588eabbf",
        )
        primary = contract["analyses"]
        self.assertEqual(primary["invasive_ventilation"]["rows"], 11116)
        self.assertEqual(primary["renal_replacement_therapy"]["rows"], 19395)
        self.assertEqual(primary["icu_death"]["rows"], 19811)
        self.assertEqual(primary["icu_death_carevue"]["rows"], 25632)
        self.assertEqual(
            primary["icu_death"]["note_identity_sha256"],
            "9d604176b53dac81f8a5e2d08e26dedcbea1f9e604baf200565d50a2e89b97dd",
        )

    def test_corpus_hash_preparation_matches_context_representation(self):
        raw = pd.DataFrame(
            {
                "case_id": ["a", "b"],
                "subject_id": ["1", "2"],
                "hadm_id": ["11", "22"],
                "icustay_id": ["111", "222"],
                "label": ["0", "1"],
                "landmark_time": ["2026-01-01T12:00:00", "2026-01-02T12:00:00"],
                "note_time": ["", "2026-01-02T10:30:00.000000"],
                "has_note": [0, 1],
                "category": ["", "Nursing"],
            }
        )
        prepared = corpus_builder.prepare_index_for_frozen_context_hash(raw)
        expected = corpus_builder.note_identity_hash(prepared)
        self.assertNotEqual(corpus_builder.note_identity_hash(raw), expected)
        normalized, observed = (
            corpus_builder.verify_note_identity_and_normalize_has_note(
                prepared,
                expected,
                "synthetic",
            )
        )
        self.assertEqual(observed, expected)
        self.assertEqual(normalized["has_note"].tolist(), [False, True])

    def test_frozen_note_hash_checked_before_has_note_bool_conversion(self):
        df = pd.DataFrame(
            {
                "case_id": ["a", "b"],
                "icustay_id": [1, 2],
                "has_note": [0, 1],
                "note_time": ["", "2026-01-01 00:00:00"],
                "category": ["", "Nursing"],
            }
        )
        expected = corpus_builder.note_identity_hash(df)
        normalized, observed = (
            corpus_builder.verify_note_identity_and_normalize_has_note(
                df,
                expected,
                "synthetic",
            )
        )
        self.assertEqual(observed, expected)
        self.assertEqual(normalized["has_note"].tolist(), [False, True])
        bool_hash = corpus_builder.note_identity_hash(normalized)
        self.assertNotEqual(bool_hash, expected)

    def test_language_stripping_freeze_matches_cohort_patterns(self):
        path = ROOT / "config" / "v2_1_language_stripping_freeze.json"
        freeze = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(freeze["primary_corpus"], "stripped")
        self.assertEqual(freeze["replacement"], " ")
        self.assertEqual(freeze["post_replacement_normalization"], "none")
        for outcome, patterns in cohort.LANGUAGE_PATTERNS.items():
            self.assertEqual(freeze["patterns"][outcome], patterns)

    def test_fixed_note_runner_uses_frozen_contracts(self):
        text = (
            ROOT / "scripts" / "run_build_fixed_note_corpora_v2_1.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("config/v2_1_analysis_population_contract.json", text)
        self.assertIn("config/v2_1_language_stripping_freeze.json", text)
        self.assertIn("config/v2_1_context_feature_result_contract.json", text)

    def test_context_feature_freeze_excludes_vent_endpoint_items(self):
        path = ROOT / "config" / "v2_1_context_feature_freeze.json"
        freeze = json.loads(path.read_text(encoding="utf-8"))
        endpoint_ids = {
            224385, 223849, 224684, 224688,
            225306, 225585, 225588, 225590, 225592, 226431, 228069,
        }

        def collect(obj):
            out = set()
            if isinstance(obj, dict):
                for value in obj.values():
                    out |= collect(value)
            elif isinstance(obj, list):
                for value in obj:
                    if isinstance(value, int):
                        out.add(value)
            return out

        treatment_ids = collect(freeze["treatment"])
        self.assertTrue(endpoint_ids.isdisjoint(treatment_ids))
        self.assertEqual(freeze["canonical_audit_job"], "A7R4Q2M6")
        self.assertEqual(
            freeze["treatment"]["code_status"]["outcome_scope"],
            ["icu_death"],
        )

    def test_fio2_normalization(self):
        import pandas as pd
        values = pd.Series([0.21, 1.0, 20.0, 50.0, 100.0, 0.0, 1.1, 19.9, 101.0, 401.0])
        out, diag = context_builder.normalize_fio2_percent(values)
        expected = [21.0, 100.0, 20.0, 50.0, 100.0]
        self.assertEqual(out.dropna().tolist(), expected)
        self.assertEqual(diag["fraction_scale_rows_converted"], 2)
        self.assertEqual(diag["percent_scale_rows_retained"], 3)
        self.assertEqual(diag["invalid_or_out_of_range_rows_rejected"], 5)

    def test_context_itemid_collection_ignores_nonnumeric_metadata(self):
        freeze = json.loads(
            (ROOT / "config" / "v2_1_context_feature_freeze.json").read_text(
                encoding="utf-8"
            )
        )
        ids = context_builder.flatten_itemids(
            freeze["treatment"]["code_status"]
        )
        self.assertEqual(ids, {128, 223758})

    def test_context_builder_runner_uses_frozen_contracts(self):
        text = (
            ROOT / "scripts" / "run_build_preregistration_context_features_v2_1.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("config/v2_1_analysis_population_contract.json", text)
        self.assertIn("config/v2_1_context_feature_freeze.json", text)

    def test_preregistration_runners_use_analysis_population_lock(self):
        for rel in [
            "scripts/run_freeze_enhanced_structured_cv_splits_v2_1.sh",
            "scripts/run_preregistration_power_v2_1.sh",
            "scripts/run_refit_bootstrap_benchmark_v2_1.sh",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(
                "config/v2_1_analysis_population_contract.json",
                text,
                msg=rel,
            )

    def test_structured_runner_passes_expected_counts(self):
        runner = (ROOT / "scripts" / "run_enhanced_structured_baseline_v2_1.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--expected-counts", runner)
        self.assertIn(
            "config/corrected_landmark12_v2_1_expected_counts.json",
            runner,
        )

    def test_expected_count_enforcement(self):
        d = pd.DataFrame(
            {
                "subject_id": [1, 2, 3],
                "label": [1, 0, 0],
                "has_note": [1, 0, 1],
            }
        )
        expected = {
            "rows": 3,
            "unique_patients": 3,
            "cases": 1,
            "controls": 2,
            "note_available_rows": 2,
        }
        features.assert_expected_counts("synthetic", d, expected)
        bad = dict(expected)
        bad["cases"] = 2
        with self.assertRaises(RuntimeError):
            features.assert_expected_counts("synthetic", d, bad)

    def test_analysis_population_contract(self):
        path = ROOT / "config" / "v2_1_analysis_population_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        primary = contract["confirmatory_outcomes"]
        self.assertEqual(primary["invasive_ventilation"]["source"], "metavision")
        self.assertEqual(primary["renal_replacement_therapy"]["source"], "metavision")
        self.assertEqual(primary["icu_death"]["source"], "metavision")
        self.assertEqual(primary["icu_death"]["rows"], 19811)
        self.assertEqual(primary["icu_death"]["cases"], 214)
        self.assertEqual(primary["icu_death"]["controls"], 19597)
        carevue = contract["prespecified_replications"]["icu_death_carevue"]
        self.assertEqual(carevue["source"], "carevue")
        self.assertEqual(carevue["cases"], 306)

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

    def test_patient_cluster_prediction_bootstrap_is_deterministic(self):
        subject = np.array([1, 1, 2, 3, 4, 5, 6, 7])
        y = np.array([0, 0, 0, 1, 0, 1, 0, 1])
        p0 = np.array([0.05, 0.08, 0.10, 0.55, 0.20, 0.62, 0.30, 0.70])
        p1 = np.array([0.04, 0.07, 0.09, 0.60, 0.18, 0.68, 0.28, 0.76])

        a = paired_prediction_cluster_bootstrap_delta_auc(
            y, p0, p1, subject, n_boot=50, seed=123
        )
        b = paired_prediction_cluster_bootstrap_delta_auc(
            y, p0, p1, subject, n_boot=50, seed=123
        )
        self.assertEqual(a["bootstrap_replicates"], 50)
        self.assertTrue(a["conditional_on_fitted_predictions"])
        self.assertTrue(
            np.array_equal(
                a["bootstrap_delta_auroc"],
                b["bootstrap_delta_auroc"],
            )
        )
        self.assertEqual(a["ci95"], b["ci95"])

    def test_patient_cluster_bootstrap_rows_keep_whole_patients(self):
        subject = np.array([1, 1, 2, 3, 3, 3, 4])
        idx = patient_cluster_bootstrap_row_indices(
            subject,
            np.random.default_rng(7),
        )
        counts = {
            sid: int(np.sum(subject[idx] == sid))
            for sid in np.unique(subject)
        }
        original = {
            sid: int(np.sum(subject == sid))
            for sid in np.unique(subject)
        }
        for sid in counts:
            self.assertEqual(counts[sid] % original[sid], 0)

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

    def test_synthetic_null_calibration_for_centered_pvalue(self):
        result = bootstrap_benchmark.synthetic_null_calibration(
            trials=2000,
            bootstrap_replicates=500,
            seed=20260925,
        )
        self.assertGreater(result["mean_pvalue"], 0.45)
        self.assertLess(result["mean_pvalue"], 0.55)
        self.assertGreater(result["rejection_rate_alpha_0_05"], 0.03)
        self.assertLess(result["rejection_rate_alpha_0_05"], 0.07)
        self.assertGreater(
            result["rejection_rate_holm_first_0_05_over_3"],
            0.005,
        )
        self.assertLess(
            result["rejection_rate_holm_first_0_05_over_3"],
            0.03,
        )

    def test_one_sided_bootstrap_pvalue(self):
        observed = 0.02
        bootstrap = np.array([0.016, 0.018, 0.019, 0.020, 0.021, 0.023])
        p = one_sided_centered_bootstrap_pvalue(observed, bootstrap)
        expected = (1 + np.sum((bootstrap - observed) >= observed)) / (len(bootstrap) + 1)
        self.assertAlmostEqual(p, expected)
        self.assertLessEqual(p, 1.0)


if __name__ == "__main__":
    unittest.main()
