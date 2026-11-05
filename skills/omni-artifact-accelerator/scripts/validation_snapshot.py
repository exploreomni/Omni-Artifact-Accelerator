"""Read-only operation-local byte reuse, never cached permission or live authority.

Only fixed first-party callers enter an operation. Values never cross requests;
all retained bytes and inventories are re-read before a successful return. This
is a consistency aid for local evidence, not a filesystem transaction or sandbox.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import time

MAX_RETAINED_BYTES = 80 * 1024 * 1024
MAX_FILES = 4096
MAX_DERIVATIONS = 2048
MAX_OBSERVERS = 64
_ACTIVE = ContextVar('validation_read_operation', default=None)
_VERIFYING = ContextVar('validation_fresh_observer', default=None)


class Changed(ValueError):
    """A result cannot be returned as current after observed input drift."""


class MutationDenied(ValueError):
    """Read-only operation scopes cannot confer or perform write authority."""


def _path(value):
    path = Path(value).absolute()
    if '..' in path.parts:
        raise ValueError('validation_unsafe_path')
    return path


def _read(path, maximum):
    path = _path(path)
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    handle = None
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = following
        handle = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(handle)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError('validation_bounded_regular_file_required')
        chunks, size = [], 0
        while True:
            chunk = os.read(handle, min(65536, maximum + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > maximum:
                raise ValueError('validation_file_too_large')
        after = os.fstat(handle)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise Changed('validation_input_changed_during_read')
        return b''.join(chunks)
    finally:
        if handle is not None:
            os.close(handle)
        os.close(parent)


def active():
    return _ACTIVE.get()


def read(path, maximum):
    scope = active()
    if scope is not None:
        return scope.read(path, maximum)
    raw = _read(path, maximum)
    verifying = _VERIFYING.get()
    if verifying is not None:
        verifying._counts['verification_reads'] += 1
        verifying._counts['verification_bytes'] += len(raw)
    return raw


def derive(key, build):
    scope = active()
    return scope.derive(key, build) if scope is not None else build()


@contextmanager
def uncached():
    """Run authoritative/final validation afresh; no cached value or decision."""
    verifying = _VERIFYING.set(active() or _VERIFYING.get())
    token = _ACTIVE.set(None)
    try:
        yield
    finally:
        _ACTIVE.reset(token)
        _VERIFYING.reset(verifying)


def fresh_read(path, maximum):
    raw = _read(path, maximum)
    scope = active()
    if scope is not None:
        scope._counts['verification_reads'] += 1
        scope._counts['verification_bytes'] += len(raw)
    return raw


def before_mutation():
    if active() is not None:
        raise MutationDenied('validation_read_only_operation_cannot_mutate')


def lock_wait(seconds):
    scope = active()
    if scope is not None:
        scope._counts['lock_wait_ms'] += max(0, seconds) * 1000


class Scope:
    def __init__(self, root):
        self.root = _path(root)
        self._files, self._derived, self._inventories, self._observers = {}, {}, {}, {}
        self._deadlines = set()
        self._retained = 0
        self._started = time.perf_counter()
        self._opened_at = datetime.now(timezone.utc)
        self._counts = {'file_reads': 0, 'file_bytes': 0, 'read_reuses': 0,
                        'derivation_reuses': 0, 'verification_reads': 0,
                        'verification_bytes': 0, 'validation_ms': 0.0, 'lock_wait_ms': 0.0}
        self._closed = False

    def read(self, path, maximum):
        if self._closed:
            raise ValueError('validation_scope_closed')
        path = _path(path)
        saved = self._files.get(path)
        if saved is not None:
            if len(saved['raw']) > maximum:
                raise ValueError('validation_file_too_large')
            self._counts['read_reuses'] += 1
            return saved['raw']
        raw = _read(path, maximum)
        self._counts['file_reads'] += 1
        self._counts['file_bytes'] += len(raw)
        if len(self._files) >= MAX_FILES or self._retained + len(raw) > MAX_RETAINED_BYTES:
            raise ValueError('validation_snapshot_budget_exceeded')
        self._files[path] = {'raw': raw, 'maximum': maximum, 'sha256': hashlib.sha256(raw).digest()}
        self._retained += len(raw)
        self._observe_deadlines(raw)
        return raw

    def _observe_deadlines(self, raw):
        # Scheduling only. The authoritative parser and every evidence/gate check
        # still run. This scan never supplies a pass, a grant or a parsed result.
        try:
            pending = [json.loads(raw)]
            while pending:
                value = pending.pop()
                if type(value) is dict:
                    for key, item in value.items():
                        if key in {'expires_at', 'valid_until'} and type(item) is str:
                            try:
                                deadline = datetime.fromisoformat(item)
                                if deadline.tzinfo is not None and deadline > self._opened_at:
                                    self._deadlines.add(deadline)
                            except ValueError:
                                pass
                        if type(item) in (dict, list):
                            pending.append(item)
                elif type(value) is list:
                    pending.extend(item for item in value if type(item) in (dict, list))
        except (ValueError, UnicodeError, RecursionError):
            pass

    def derive(self, key, build):
        if self._closed:
            raise ValueError('validation_scope_closed')
        if key in self._derived:
            self._counts['derivation_reuses'] += 1
            return copy.deepcopy(self._derived[key])
        value = build()
        if len(self._derived) >= MAX_DERIVATIONS:
            raise ValueError('validation_derivation_budget_exceeded')
        self._derived[key] = copy.deepcopy(value)
        return value

    def inventory(self, key, observe):
        """Track an internal deterministic path inventory, including absent files."""
        value = observe()
        prior = self._inventories.get(key)
        if prior is not None and prior[0] != value:
            raise Changed('validation_inventory_changed')
        if prior is None:
            self._inventories[key] = (copy.deepcopy(value), observe)
        return value

    def optional(self, path, maximum):
        path = _path(path)
        def present():
            # lstat keeps replacement symlinks visible; actual reads reject them.
            try:
                return stat.S_IFMT(path.lstat().st_mode)
            except FileNotFoundError:
                return None
        exists = self.inventory(('optional', str(path)), present)
        if exists is not None:
            return self.read(path, maximum)
        return None

    def observe(self, key, expected, current):
        """Re-run a fixed authoritative read; never return a saved decision."""
        if self._closed:
            raise ValueError('validation_scope_closed')
        if key in self._observers:
            if self._observers[key][0] != expected:
                raise Changed('validation_authoritative_state_changed')
            return
        if len(self._observers) >= MAX_OBSERVERS:
            raise ValueError('validation_observer_budget_exceeded')
        self._observers[key] = (copy.deepcopy(expected), current)

    def verify(self):
        if self._closed:
            raise ValueError('validation_scope_closed')
        started = time.perf_counter()
        try:
            # These callbacks are fixed first-party read functions registered by
            # wrappers, never request-supplied callables or cached permissions.
            with uncached():
                for expected, current in self._observers.values():
                    try:
                        observed = current()
                    except (OSError, ValueError) as exc:
                        raise Changed('validation_authoritative_state_unavailable') from exc
                    if observed != expected:
                        raise Changed('validation_authoritative_state_changed')
            for expected, observe in list(self._inventories.values()):
                try:
                    observed = observe()
                except (OSError, ValueError) as exc:
                    raise Changed('validation_inventory_unavailable') from exc
                if observed != expected:
                    raise Changed('validation_inventory_changed')
            for path, saved in self._files.items():
                try:
                    raw = _read(path, saved['maximum'])
                except (OSError, ValueError) as exc:
                    raise Changed('validation_evidence_unavailable') from exc
                self._counts['verification_reads'] += 1
                self._counts['verification_bytes'] += len(raw)
                if hashlib.sha256(raw).digest() != saved['sha256']:
                    raise Changed('validation_evidence_changed')
            if any(deadline <= datetime.now(timezone.utc) for deadline in self._deadlines):
                raise Changed('validation_evidence_expired_during_operation')
        finally:
            self._counts['validation_ms'] += (time.perf_counter() - started) * 1000

    def counters(self):
        return {key: round(value, 3) if isinstance(value, float) else value
                for key, value in self._counts.items()}


@contextmanager
def operation(root):
    """One read-only operation, including a final byte/inventory/freshness recheck.

    Nested scopes are isolated (for a bounded status retry); counters accumulate
    into the parent, while neither cached bytes nor derivations cross that boundary.
    No host/provider decision is memoized by this helper.
    """
    parent = active()
    scope = Scope(root)
    token = _ACTIVE.set(scope)
    try:
        # The stage reader uses descriptor-based reads of its own. Observe its
        # state as well so a changed journal/policy cannot hide behind other reuse.
        scope.optional(scope.root / 'project.json', 10 * 1024 * 1024)
        scope.optional(scope.root / 'stage-gates.json', 2 * 1024 * 1024)
        yield scope
        scope.verify()
    finally:
        _ACTIVE.reset(token)
        scope._closed = True
        if parent is not None:
            for key, value in scope._counts.items():
                parent._counts[key] += value
