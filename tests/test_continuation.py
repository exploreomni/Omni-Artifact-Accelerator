"""Bounded synthetic continuation imports; no network, native execution or dispatch."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/omni-backend-handoff/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("continuation_test_module", SCRIPTS / "continuation.py")
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)
dma = c.dma


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.packet_dir = self.root / "packet"
        self.packet_dir.mkdir()
        self.project = self.root / "frontend"
        self.snapshot = {"domain": {"id": "orders", "name": "Orders", "status": "complete"},
            "entity_ids": ["orders", "customer"], "design": {"entities": [{"id": "orders"}, {"id": "customer"}]},
            "inputs": {"repo": "a" * 64}, "source_coverage": "conservative_global_input_pins", "naming": None}
        self.state = {"engagement_id": "engagement-1", "revision": 1, "state_sha256": "b" * 64,
            "inputs": {"repo": "original"}, "answers": {"migration_scope": "full_dashboard"},
            "workflow": {"design": {"revision": 1}, "domain_journey": {"active_domain_id": "service"}},
            "snapshot": self.snapshot}
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        (self.runtime / "frontend_continuation.py").write_text(
            'def scoped_context(state, domain_id):\n    return state["snapshot"]\n')
        (self.runtime / "source_roots.py").write_text('def ensure_output(state, output):\n    pass\n')
        self.gw = SimpleNamespace(load_engagement=lambda run: copy.deepcopy(self.state),
                                  assess_engagement=lambda run: copy.deepcopy(self.state))
        self.review = {"schema_version": 1, "kind": "omni_semantic_handoff", "version": "omni-handoff-v1",
            "pins": {"source_fingerprint": "1" * 64, "context_sha256": "2" * 64,
                "model_candidate_sha256": "3" * 64, "model_context_sha256": "4" * 64,
                "target": {"warehouse": "snowflake", "framework": "dbt"}},
            "topics": [{"id": "orders", "base_view": "orders"}],
            "metrics": [{"id": "orders.revenue", "topic": "orders", "definition_sha256": "5" * 64}],
            "dictionary": [{"id": "orders.revenue", "topic": "orders", "kind": "measure", "definition_sha256": "5" * 64}],
            "dependencies": [], "decisions": [], "unknowns": []}
        self.review["handoff_sha256"] = dma.digest(dma.canonical(self.review))
        self.packet_path = self.packet_dir / "continuation.json"
        self.packet = self.make_packet()

    def write(self, name, obj):
        target = self.packet_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(obj))
        return dma.digest(target.read_bytes())

    def make_packet(self, mode="independent", review=True):
        context_sha = self.write("context/domain.json", self.snapshot)
        review_sha = self.write("semantic/review.json", self.review) if review else None
        value = {"schema_version": 1, "kind": "dma_frontend_continuation", "continuation_id": "continuation-1",
            "engagement_id": "engagement-1", "domain_id": self.snapshot["domain"]["id"] if self.snapshot["domain"] else None,
            "mode": mode, "choice": "continue_now", "request_reference": "synthetic:user-choice",
            "scope_sha256": dma.digest(dma.canonical(self.snapshot)),
            "semantic_review": {"path": "semantic/review.json", "sha256": review_sha} if review else None,
            "files": [{"path": "context/domain.json", "sha256": context_sha, "purpose": "domain_context"}] +
                ([{"path": "semantic/review.json", "sha256": review_sha, "purpose": "semantic_review"}] if review else []),
            "dashboard_ids": ["orders-report"], "topic_names": ["orders"] if review else [],
            "destination": {"base_url": "https://synthetic.omniapp.co", "model_id": "model-1", "branch_id": None},
            "source_migration_scope": "full_dashboard" if mode == "integrated" else "model_semantic",
            "unresolved": ["Native Topic readback is unavailable"], "allowed_actions": ["design", "candidate_artifacts"],
            "authorizes_target_write": False, "disclosure_reference": "synthetic:host-review",
            "disclosure_assurance": "host_reported_not_authenticated"}
        self.save(value)
        return value

    def save(self, value=None):
        value = value or self.packet
        value.pop("sha256", None)
        value.update(dma.seal(value))
        self.packet_path.write_text(json.dumps(value))

    def initiate(self):
        with patch.object(dma, "trusted_dma", return_value=self.gw):
            return c.initiate(self.packet_path, self.project, run_dir=self.root / "run", dma_scripts=self.runtime)

    def v2(self, surfaces, task_mode='net-new', review=True):
        self.packet = self.make_packet(review=review)
        self.packet.update(schema_version=2, target_surfaces=surfaces, task_mode=task_mode, app_ids=['app-source'],
                           native_validation=None, topic_readback=None,
                           destination={'base_url':'https://example.invalid', 'model_id':'model-1', 'branch_id':'branch-1',
                                        'model_version_id':'version-1'})
        self.save()

    def evidence(self, purpose, body):
        name = 'source/' + purpose + '.json'
        pin = {'path': name, 'sha256': self.write(name, body)}
        self.packet[purpose] = pin
        self.packet['files'].append(dict(pin, purpose=purpose))
        self.save()

    def test_app_selection_is_project_relative_and_resume_rechecks_all_inputs(self):
        self.v2(['app'])
        self.evidence('topic_readback', {'fixture': 'supplied readback'})
        self.evidence('native_validation', {'schema_version':1,'kind':'omni_native_receipt',
            'contract_version':'omni-native-v1-2026-10-05','operation':'validate', 'status':'simulated_passed',
            'execution_mode':'simulation','native_verified':False,'target':{'instance_url':'https://example.invalid',
                'model_id':'model-1','branch_id':'branch-1'},'candidate_sha256':'3' * 64,'context_sha256':'4' * 64})
        receipt = self.initiate()
        project = json.loads((self.project / 'project.json').read_bytes())
        self.assertEqual(project['surfaces'], ['app'])
        self.assertEqual(project['mode'], 'net-new')
        self.assertEqual(project['dma_topic_policy'], 'selected-topic-v1')
        selection = c.project_selection(self.project)
        self.assertEqual(selection, project['dma_continuation_selection'])
        self.assertEqual(selection['destination']['model_version_id'], 'version-1')
        for key in ('packet','semantic_review','native_validation','topic_readback'):
            pin = selection[key]
            self.assertEqual(pin['sha256'], dma.digest((self.project / pin['path']).read_bytes()))
        self.assertEqual(receipt['native_validation_assurance'], 'supplied_unverified')
        self.assertFalse(receipt['native_verified'])
        self.assertTrue(self.initiate()['reused'])
        (self.project / selection['topic_readback']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'retained input changed'):
            c.project_selection(self.project)

    def test_both_surfaces_no_catalogue_still_marks_the_project(self):
        self.v2(['dashboard','app'], 'enhancement', review=False)
        self.packet['topic_names'] = []
        self.save()
        self.initiate()
        project = json.loads((self.project / 'project.json').read_bytes())
        self.assertEqual(project['surfaces'], ['dashboard','app'])
        self.assertEqual(project['mode'], 'enhancement')
        self.assertEqual(project['dma_topic_policy'], 'selected-topic-v1')
        expected = c.project_selection(self.project)
        self.assertIsNone(expected['semantic_review'])
        self.assertEqual(expected['topic_names'], [])
        project['dma_continuation_selection']['topic_names'] = ['substituted']
        (self.project / 'project.json').write_text(json.dumps(project))
        with self.assertRaisesRegex(ValueError, 'selection changed'):
            c.project_selection(self.project)
        with self.assertRaisesRegex(ValueError, 'selection changed'):
            self.initiate()

    def test_v1_historical_selection_derived_without_rewriting_project(self):
        self.initiate()
        project = json.loads((self.project / 'project.json').read_bytes())
        self.assertEqual(project.pop('dma_topic_policy'), 'selected-topic-v1')
        (self.project / 'project.json').write_text(json.dumps(project))
        previous = (self.project / 'project.json').read_bytes()
        self.assertTrue(self.initiate()['reused'])
        selection = c.project_selection(self.project)
        self.assertEqual((selection['protocol_version'], selection['target_surfaces'], selection['task_mode']),
                         (1, ['dashboard'], 'migration'))
        self.assertEqual(previous, (self.project / 'project.json').read_bytes())

    def test_v2_candidate_or_destination_substitution_blocks_initial_import(self):
        self.v2(['app'])
        self.evidence('native_validation', {'schema_version':1,'kind':'omni_native_receipt',
            'contract_version':'omni-native-v1-2026-10-05','operation':'validate','status':'simulated_passed',
            'execution_mode':'simulation','native_verified':False,'target':{'instance_url':'https://example.invalid',
                'model_id':'other','branch_id':'branch-1'},'candidate_sha256':'3' * 64,'context_sha256':'4' * 64})
        with self.assertRaisesRegex(ValueError, 'destination mismatch'):
            self.initiate()
        self.assertFalse(self.project.exists())

    def test_integrated_v2_rechecks_saved_surface_and_evidence_selection(self):
        self.v2(['dashboard','app'], 'migration')
        self.packet.update(mode='integrated', source_migration_scope='full_dashboard')
        self.evidence('topic_readback', {'fixture':'pinned readback'})
        request = {k: copy.deepcopy(self.packet[k]) for k in ('schema_version','domain_id','choice','request_reference',
                   'target_surfaces','task_mode','dashboard_ids','app_ids','topic_names','destination')}
        request['context_files'] = [{'path':'supplied.json','purpose':'topic_readback','sha256':self.packet['topic_readback']['sha256']}]
        self.state['workflow']['frontend_continuations'] = {'items':[{'id':self.packet['continuation_id'],
            'scope_sha256':self.packet['scope_sha256'],'mode':'integrated','request':request}]}
        self.assertIsNotNone(self.initiate()['backend_context'])
        self.assertTrue(self.initiate()['reused'])
        request['target_surfaces'] = ['dashboard']
        with self.assertRaisesRegex(ValueError, 'selection changed'):
            self.initiate()
        request['target_surfaces'] = ['dashboard','app']
        request['context_files'][0]['sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'evidence selection changed'):
            self.initiate()
        self.packet['mode'] = 'independent'
        self.save()
        with self.assertRaisesRegex(ValueError, 'mode differs'):
            self.initiate()

    def test_independent_exact_retry_keeps_one_project_import_and_no_authority(self):
        first = self.initiate()
        project_before = (self.project / "project.json").read_bytes()
        second = self.initiate()
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["project_id"], second["project_id"])
        self.assertEqual(project_before, (self.project / "project.json").read_bytes())
        for key in ("agents_dispatched", "native_verified", "authorizes_target_write", "scope_registered", "business_accepted"):
            self.assertIs(second[key], False)
        receipt = json.loads((self.project / "continuation-receipt.json").read_text())
        dma.check_seal(receipt, "analyst_frontend_continuation_receipt")
        self.assertEqual(first["receipt_sha256"], receipt["sha256"])
        obj = json.loads(project_before)
        self.assertEqual(len(obj["sources"]), 3)
        self.assertTrue(Path(obj["dma_import"]["original_path"]).is_file())
        self.assertFalse((self.project / "evidence/migration-scope.json").exists())

    def test_interrupted_import_does_not_publish_partial_project(self):
        ap = c._analyst()
        real_write = ap.write_json
        def fail_catalog(target, value, **kwargs):
            if target.name == "dma-catalog.json":
                raise OSError("synthetic interruption")
            return real_write(target, value, **kwargs)
        with patch.object(c, "_analyst", return_value=ap), patch.object(ap, "write_json", side_effect=fail_catalog):
            with self.assertRaisesRegex(OSError, "interruption"):
                self.initiate()
        self.assertFalse(self.project.exists())
        self.assertFalse(list(self.root.glob(".dma-continuation-*")))
        self.assertFalse(self.initiate()["reused"])

    def test_changed_same_id_or_retained_bytes_refuse_overwrite(self):
        self.initiate()
        original = (self.project / "project.json").read_bytes()
        self.packet["choice"] = "prepare_handoff"
        self.save()
        with self.assertRaisesRegex(ValueError, "another continuation"):
            self.initiate()
        self.assertEqual(original, (self.project / "project.json").read_bytes())
        self.packet["choice"] = "continue_now"
        self.save()
        target = self.project / "inputs/continuations/continuation-1/files/context/domain.json"
        target.write_text('{}')
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.initiate()

    def test_packet_and_retained_symlinks_tampering_and_scope_mismatch_reject(self):
        payload = self.packet_dir / "context/domain.json"
        original = payload.read_bytes()
        payload.write_text('{}')
        with self.assertRaisesRegex(ValueError, "retained input changed"):
            self.initiate()
        payload.write_bytes(original)
        self.packet["scope_sha256"] = "f" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "copied domain context"):
            self.initiate()
        self.assertFalse(self.project.exists())
        self.packet["scope_sha256"] = dma.digest(dma.canonical(self.snapshot))
        self.save()
        self.initiate()
        retained = self.project / "inputs/continuations/continuation-1/packet.json"
        retained.unlink()
        retained.symlink_to(self.packet_path)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.initiate()

    def test_forged_receipt_cannot_claim_dispatch_or_native_validation(self):
        self.initiate()
        target = self.project / "continuation-receipt.json"
        value = json.loads(target.read_text())
        value.pop("sha256")
        value["agents_dispatched"] = True
        value["native_verified"] = True
        target.write_text(json.dumps(dma.seal(value)))
        with self.assertRaisesRegex(ValueError, "receipt changed"):
            self.initiate()

    def test_authority_scope_and_destination_reject_before_project_write(self):
        for key, value in (("authorizes_target_write", True), ("mode", "integrated"),
                           ("destination", {"base_url": "https://token:secret@example.test", "model_id": "m", "branch_id": None})):
            with self.subTest(key=key):
                original = copy.deepcopy(self.packet)
                self.packet[key] = value
                self.save()
                with self.assertRaises(ValueError):
                    self.initiate()
                self.assertFalse(self.project.exists())
                self.packet = original
                self.save()

    def test_missing_semantic_candidate_stays_provisional_and_prepare_does_not_dispatch(self):
        self.packet = self.make_packet(review=False)
        self.packet["choice"] = "prepare_handoff"
        self.save()
        result = self.initiate()
        self.assertEqual(result["status"], "handoff_prepared")
        self.assertEqual(result["topic_readiness"], "not_assessed")
        self.assertNotIn("dma_import", json.loads((self.project / "project.json").read_text()))
        self.assertFalse(result["scope_registered"])

    def test_integrated_completed_selector_uses_scoped_material_and_detects_drift(self):
        self.packet = self.make_packet(mode="integrated")
        first = self.initiate()
        context = json.loads((self.project / first["backend_context"]["path"]).read_text())
        self.assertEqual(context["snapshot_contract"], "dma-scoped-context-v1")
        self.assertEqual(context["selected_domain"]["id"], "orders")
        self.state["workflow"]["design"]["unrelated"] = "changed service domain"
        self.state["revision"] += 1
        self.assertTrue(self.initiate()["reused"])
        self.state["snapshot"]["inputs"]["repo"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "scoped material changed"):
            self.initiate()

    def test_null_selector_uses_scoped_contract_and_legacy_export_is_unchanged(self):
        self.snapshot["domain"] = None
        self.packet = self.make_packet(mode="integrated")
        result = self.initiate()
        context = json.loads((self.project / result["backend_context"]["path"]).read_text())
        self.assertIsNone(context["domain_id"])
        self.assertEqual(context["material"], self.snapshot)
        legacy = self.root / "legacy-context.json"
        self.state["workflow"]["domain_journey"] = None
        with patch.object(dma, "trusted_dma", return_value=self.gw):
            dma.export(self.root / "run", legacy, dma_scripts=self.runtime)
        value = json.loads(legacy.read_text())
        self.assertNotIn("snapshot_contract", value)
        self.assertEqual(value["material"], dma.material(self.state))
        dma.check_context(value, self.state)

    def test_missing_installed_sibling_stops_before_creating_project(self):
        with patch.object(c, "REQUIRED_SKILLS", ("synthetic-missing-sibling",)):
            with self.assertRaisesRegex(ValueError, "missing required companion"):
                self.initiate()
        self.assertFalse(self.project.exists())

    def test_refresh_detects_source_drift_without_saved_state_change(self):
        self.packet = self.make_packet(mode="integrated")
        refreshed = copy.deepcopy(self.state)
        refreshed["snapshot"]["inputs"]["repo"] = "e" * 64
        with patch.object(self.gw, "assess_engagement", return_value=refreshed) as refresh:
            with self.assertRaisesRegex(ValueError, "scoped material changed"):
                self.initiate()
        refresh.assert_called_once()
        self.assertFalse(self.project.exists())

    def test_unknown_topics_and_unmanaged_existing_project_reject(self):
        self.packet["topic_names"] = ["not-in-candidate"]
        self.save()
        with self.assertRaisesRegex(ValueError, "Topic is absent"):
            self.initiate()
        self.packet["topic_names"] = ["orders"]
        self.save()
        c._analyst().init(self.project, "Existing independent project", "migration", "dashboard")
        original = (self.project / "project.json").read_bytes()
        with self.assertRaises(ValueError):
            self.initiate()
        self.assertEqual(original, (self.project / "project.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
