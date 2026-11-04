"""Original neutral stdlib fixtures; synthetic guards do not qualify a host."""
import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'assembly_under_test', ROOT / 'skills/omni-artifact-accelerator/scripts/assembly_provenance.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
S, P = A._helpers(None)


class AssemblyProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        self.root.mkdir()
        for folder in ('inputs', 'contracts', 'evidence', 'deliverables'):
            (self.root / folder).mkdir()
        self.data = {
            'layout': ('component', b'<main aria-label="Study">Original observations</main>'),
            'styles': ('styles', b'<style>main { color: #123456; }</style>'),
            'query': ('query', b'{"fields":["sample_id","measurement"]}'),
            'asset': ('asset', b'original fixture bytes\x00\xff'),
            'runtime': ('runtime', b'{"events":["ready"],"network":false}'),
        }
        self.manifest = {'schema_version': 1, 'kind': 'assembly_manifest', 'mode': 'utf8',
                         'separator_utf8': '\n', 'parts': ['layout', 'styles'], 'dependencies': []}
        for ident, (kind, data) in self.data.items():
            path = 'inputs/' + ident + '.dat'
            self.write(path, data)
            self.manifest['dependencies'].append({
                'id': ident, 'kind': kind, **A._pin(path, data, P), 'scopes': ['ui_ux'],
                'freshness': {'mode': 'until' if kind == 'runtime' else 'immutable',
                              'checked_at': '2000-01-01T00:00:00+00:00',
                              'expires_at': '2099-01-01T00:00:00+00:00' if kind == 'runtime' else None}})
        self.save_manifest('one')

    def write(self, path, value):
        raw = P.canonical(value) if type(value) is dict else value
        (self.root / path).write_bytes(raw)

    def save_manifest(self, name):
        path = 'contracts/assembly-' + name + '.json'
        self.write(path, self.manifest)
        return path

    def build(self, name='one'):
        request = {'manifest': self.save_manifest(name), 'output': 'deliverables/' + name + '.html',
                   'record': 'evidence/' + name + '.json'}
        with patch.object(S, 'require_action', return_value={}) as guard:
            result = A.build(self.root, request, P=P)
        guard.assert_called_once_with(self.root, 'build', P=P, provider=None)
        return result

    def verify(self, name='one'):
        return A.verify(self.root, {'record': 'evidence/' + name + '.json'}, P=P)

    def compare(self):
        return A.compare(self.root, {'previous': 'evidence/one.json', 'current': 'evidence/two.json'}, P=P)

    def replace_dependency(self, ident, data):
        row = next(d for d in self.manifest['dependencies'] if d['id'] == ident)
        self.write(row['path'], data)
        row.update(A._pin(row['path'], data, P))

    def rewrite_record(self, transform, name='one'):
        path = 'evidence/' + name + '.json'
        record = json.loads((self.root / path).read_bytes())
        transform(record)
        record['sha256'] = P.digest(P.canonical({k: v for k, v in record.items() if k != 'sha256'}))
        self.write(path, record)

    def test_exact_bytes_snapshots_and_immutable_new_paths(self):
        result = self.build()
        expected = self.data['layout'][1] + b'\n' + self.data['styles'][1]
        self.assertEqual((self.root / 'deliverables/one.html').read_bytes(), expected)
        self.assertEqual(result['output'], A._pin('deliverables/one.html', expected, P))
        self.assertEqual(self.verify()['status'], 'verified')
        record = json.loads((self.root / 'evidence/one.json').read_bytes())
        self.assertEqual([v['id'] for v in record['inputs']], list(self.data))
        self.assertEqual(base64.b64decode(record['inputs'][3]['content_base64']), self.data['asset'][1])
        self.assertEqual({v['name'] for v in record['builder']['sources']},
                         {'assembler', 'project_helpers', 'path_helpers'})
        self.assertEqual((self.root / 'evidence/one.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'deliverables/one.html').stat().st_mode & 0o777, 0o600)
        before = (self.root / 'evidence/one.json').read_bytes()
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual((self.root / 'evidence/one.json').read_bytes(), before)
        self.assertEqual((self.root / 'deliverables/one.html').read_bytes(), expected)
        self.assertFalse(result['publication_authorized'])
        self.assertFalse(result['review_scope_reduction_allowed'])

    def test_real_guard_denies_build_before_writing(self):
        request = {'manifest': 'contracts/assembly-one.json', 'output': 'deliverables/one.html',
                   'record': 'evidence/one.json'}
        with self.assertRaises((ValueError, OSError)):
            A.build(self.root, request, P=P)
        self.assertFalse((self.root / request['output']).exists())
        self.assertFalse((self.root / request['record']).exists())

    def test_changed_styles_never_narrows_review_and_old_snapshot_reproduces(self):
        self.build()
        self.replace_dependency('styles', b'<style>main { color: #654321; }</style>')
        self.build('two')
        result = self.compare()
        self.assertEqual(result['status'], 'changed')
        self.assertEqual(result['changed_dependency_ids'], ['styles'])
        self.assertEqual(result['scope_hints'], {'styles': ['ui_ux']})
        self.assertTrue(result['output_changed'])
        self.assertEqual(set(result['review_required_scopes']), set(A.SCOPES))
        self.assertFalse(result['review_scope_reduction_allowed'])
        self.assertEqual(self.verify()['status'], 'unknown')
        self.assertIn('stale_dependency:styles', self.verify()['findings'])

    def test_unemitted_query_and_runtime_changes_are_still_reported(self):
        self.build()
        self.replace_dependency('query', b'{"fields":["sample_id","revised_measurement"]}')
        self.replace_dependency('runtime', b'{"events":["ready","changed"],"network":false}')
        self.build('two')
        result = self.compare()
        self.assertEqual(result['changed_dependency_ids'], ['query', 'runtime'])
        self.assertFalse(result['output_changed'])
        self.assertEqual(result['status'], 'changed')

    def test_recipe_order_and_fixed_separator_are_bound(self):
        self.build()
        self.manifest['parts'] = ['styles', 'layout', 'styles']
        self.manifest['separator_utf8'] = '\r\n<!-- fixed -->\r\n'
        self.build('two')
        result = self.compare()
        self.assertEqual(result['changed_dependency_ids'], [])
        self.assertTrue(result['recipe_changed'])
        self.assertTrue(result['output_changed'])
        expected = self.manifest['separator_utf8'].encode().join([
            self.data['styles'][1], self.data['layout'][1], self.data['styles'][1]])
        self.assertEqual((self.root / 'deliverables/two.html').read_bytes(), expected)

    def test_unchanged_records_remain_full_review(self):
        self.build()
        self.build('two')
        result = self.compare()
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(result['changed_dependency_ids'], [])
        self.assertEqual(set(result['review_required_scopes']), set(A.SCOPES))
        self.assertFalse(result['claims_authenticated'])

    def test_edited_output_and_stale_current_manifest_fail_safe(self):
        self.build()
        self.build('two')
        self.write('deliverables/one.html', b'<main>Unmapped manual edit</main>')
        result = self.compare()
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('previous:unmapped_output_change', result['findings'])
        self.write('contracts/assembly-two.json', {'changed': True})
        self.assertIn('stale_manifest', self.verify('two')['findings'])

    def test_forged_output_hash_cannot_hide_unmapped_bytes(self):
        self.build()
        changed = b'<main>Manually replaced</main>'
        self.write('deliverables/one.html', changed)
        self.rewrite_record(lambda record: record['output'].update(
            A._pin('deliverables/one.html', changed, P)))
        result = self.verify()
        self.assertEqual(result['status'], 'unknown')
        self.assertTrue(any('unmapped_output_bytes' in f for f in result['findings']))

    def test_snapshot_corruption_and_record_hash_tampering_fail_safe(self):
        self.build()
        self.rewrite_record(lambda record: record['inputs'][0].update(content_base64=A._b64(b'other bytes')))
        self.assertTrue(any('input_snapshot_mismatch' in f for f in self.verify()['findings']))
        self.build('two')
        path = self.root / 'evidence/two.json'
        record = json.loads(path.read_bytes())
        record['output']['bytes'] += 1
        self.write('evidence/two.json', record)
        self.assertTrue(any('record_hash_mismatch' in f for f in self.verify('two')['findings']))

    def test_current_builder_change_and_unknown_dependency_fail_safe(self):
        self.build()
        actual = A._builder(S, P)
        changed = copy.deepcopy(actual)
        changed['sources'][0]['sha256'] = '0' * 64
        with patch.object(A, '_builder', return_value=changed):
            self.assertIn('stale_builder', self.verify()['findings'])
        self.manifest['dependencies'][2]['kind'] = 'unknown'
        self.build('two')
        result = self.compare()
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('current:unknown_dependency:query', result['findings'])
        self.assertIn('dependency_mapping_changed:query', result['findings'])

    def test_expired_or_future_runtime_blocks_build_and_invalidates_old_record(self):
        runtime = self.manifest['dependencies'][-1]
        runtime['freshness']['expires_at'] = '2001-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError, 'stale_dependencies'):
            self.build()
        runtime['freshness']['checked_at'] = '2098-01-01T00:00:00+00:00'
        runtime['freshness']['expires_at'] = '2099-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError, 'stale_dependencies'):
            self.build()
        runtime['freshness']['checked_at'] = '2000-01-01T00:00:00+00:00'
        self.build()
        class Later:
            @staticmethod
            def now(tz):
                return A._stamp('2100-01-01T00:00:00+00:00')
        with patch.object(A, 'datetime', Later):
            # Preserve timestamp parsing while controlling only the observation time.
            Later.fromisoformat = staticmethod(__import__('datetime').datetime.fromisoformat)
            self.assertIn('expired_evidence:runtime', self.verify()['findings'])

    def test_pins_and_dependency_inventory_are_mandatory(self):
        self.manifest['dependencies'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'dependency_pin_mismatch:layout'):
            self.build()
        self.manifest['dependencies'][0]['sha256'] = P.digest(self.data['layout'][1])
        self.build()
        self.manifest['dependencies'].pop(3)
        self.build('two')
        self.assertIn('dependency_inventory_changed', self.compare()['findings'])
        self.assertEqual(self.compare()['changed_dependency_ids'], ['asset'])

    def test_path_traversal_and_symlink_sources_outputs_and_records_are_denied(self):
        for bad in ('../outside.dat', '/absolute.dat', 'inputs/../outside.dat', 'inputs\\outside.dat'):
            with self.subTest(path=bad):
                self.manifest['dependencies'][0]['path'] = bad
                with self.assertRaises(ValueError):
                    self.build()
        self.manifest['dependencies'][0]['path'] = 'inputs/layout.dat'
        outside = Path(self.temp.name) / 'outside.dat'
        outside.write_bytes(self.data['layout'][1])
        original = self.root / 'inputs/layout.dat'
        original.unlink()
        original.symlink_to(outside)
        with self.assertRaises((ValueError, OSError)):
            self.build()
        original.unlink()
        original.write_bytes(self.data['layout'][1])
        (self.root / 'deliverables').rmdir()
        (self.root / 'deliverables').symlink_to(Path(self.temp.name), target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            self.build()
        self.assertFalse((Path(self.temp.name) / 'one.html').exists())
        (self.root / 'evidence/one.json').symlink_to(outside)
        self.assertEqual(self.verify()['status'], 'unknown')

    def test_existing_record_never_leaves_an_output_or_changes_existing_record(self):
        self.write('evidence/one.json', b'keep me')
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertFalse((self.root / 'deliverables/one.html').exists())
        self.assertEqual((self.root / 'evidence/one.json').read_bytes(), b'keep me')

    def test_non_regular_file_is_rejected_without_blocking(self):
        path = self.root / 'inputs/layout.dat'
        path.unlink()
        os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'bounded_regular_file'):
            self.build()

    def test_no_templating_or_execution_and_utf8_bytes_modes(self):
        literal = b'{{ untouched }} ${value} __import__("missing_package")\x00\xff'
        self.replace_dependency('layout', literal)
        with self.assertRaisesRegex(ValueError, 'invalid_utf8:layout'):
            self.build()
        self.manifest['mode'] = 'bytes'
        self.build()
        self.assertEqual((self.root / 'deliverables/one.html').read_bytes(), literal + b'\n' + self.data['styles'][1])
        self.assertEqual(self.verify()['status'], 'verified')

    def test_bounded_inputs_output_parts_and_separators(self):
        initial = copy.deepcopy(self.manifest)
        self.replace_dependency('layout', b'x' * (A.MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, 'input_too_large'):
            self.build()
        self.manifest = copy.deepcopy(initial)
        self.replace_dependency('layout', b'x' * A.MAX_INPUT_BYTES)
        self.manifest['parts'] = ['layout'] * 6
        with self.assertRaisesRegex(ValueError, 'output_too_large'):
            self.build()
        self.manifest['parts'] = ['layout'] * (A.MAX_DEPENDENCIES + 1)
        with self.assertRaisesRegex(ValueError, 'unmapped_part'):
            self.build()
        self.manifest['parts'] = ['layout']
        self.manifest['separator_utf8'] = 'x' * (A.MAX_SEPARATOR_BYTES + 1)
        with self.assertRaisesRegex(ValueError, 'separator_too_large'):
            self.build()

    def test_missing_unknown_or_malformed_records_fall_back_to_full_review(self):
        self.write('evidence/one.json', b'{"schema_version":99}')
        result = self.compare()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(set(result['review_required_scopes']), set(A.SCOPES))
        self.assertFalse(result['review_scope_reduction_allowed'])
        self.assertEqual(result['changed_dependency_ids'], [])

    def test_duplicate_json_keys_extra_fields_and_unmapped_parts_are_rejected(self):
        request = {'manifest': 'contracts/assembly-one.json', 'output': 'deliverables/one.html',
                   'record': 'evidence/one.json'}
        self.write(request['manifest'], b'{"schema_version":1,"schema_version":2}')
        with patch.object(S, 'require_action', return_value={}):
            with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                A.build(self.root, request, P=P)
        self.manifest['builder_command'] = 'arbitrary-command'
        with self.assertRaisesRegex(ValueError, 'invalid_manifest'):
            self.build()
        self.manifest.pop('builder_command')
        self.manifest['parts'] = ['undeclared']
        with self.assertRaisesRegex(ValueError, 'unmapped_part'):
            self.build()


if __name__ == '__main__':
    unittest.main()
