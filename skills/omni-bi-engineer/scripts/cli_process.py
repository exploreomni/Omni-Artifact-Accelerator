"""Original bounded POSIX child transport. Not a sandbox or approval verifier."""
import hashlib
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time

MAX_EXECUTABLE = 128 * 1024 * 1024
MAX_STDERR = 64 * 1024


class ProcessError(ValueError):
    pass


def pinned_file(path, expected, executable=False):
    """Host-selected bytes only; pins are integrity, never permission to execute."""
    if not isinstance(path, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ProcessError("CLI path and SHA256 must be explicitly configured")
    p = Path(path)
    if not p.is_absolute() or ".." in p.parts or any(x.is_symlink() for x in (p, *p.parents)):
        raise ProcessError("CLI path must be absolute and canonical without links")
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_EXECUTABLE
                or before.st_mode & 0o022 or (executable and not os.access(p, os.X_OK))):
            raise ProcessError("CLI file must be bounded, regular and not group/world writable")
        digest, size, prefix = hashlib.sha256(), 0, b""
        while True:
            raw = os.read(fd, min(65536, MAX_EXECUTABLE + 1 - size))
            if not raw:
                break
            if not prefix:
                prefix = raw[:2]
            size += len(raw)
            if size > MAX_EXECUTABLE:
                raise ProcessError("CLI file exceeds byte limit")
            digest.update(raw)
        after = os.fstat(fd)
        if (size != before.st_size or (before.st_mtime_ns, before.st_ctime_ns, before.st_size)
                != (after.st_mtime_ns, after.st_ctime_ns, after.st_size) or digest.hexdigest() != expected):
            raise ProcessError("CLI executable/runtime pin mismatch or file changed")
        return prefix
    finally:
        os.close(fd)


def command(environment):
    """Resolve no PATH entries, shell startup, shebang interpreter or packages."""
    path, sha = environment.get("OAA_OMNI_CLI_PATH"), environment.get("OAA_OMNI_CLI_SHA256")
    runtime, runtime_sha = environment.get("OAA_OMNI_RUNTIME_PATH"), environment.get("OAA_OMNI_RUNTIME_SHA256")
    prefix = pinned_file(path, sha, executable=not runtime)
    if runtime or runtime_sha:
        if pinned_file(runtime, runtime_sha, executable=True) == b"#!":
            raise ProcessError("CLI runtime must be a native executable, not a shebang wrapper")
        return [runtime, path]
    if prefix == b"#!":
        raise ProcessError("CLI script requires an explicitly pinned interpreter")
    return [path]


def environment(directory, token=None):
    """Fresh config/home prevents accidental ambient profile credential loading."""
    result = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "HOME": str(directory),
              "XDG_CONFIG_HOME": str(directory), "TMPDIR": str(directory)}
    if token is not None:
        result["OMNI_API_TOKEN"] = token
    return result


def run(argv, *, input=None, env, cwd, timeout=60, max_stdout=8 * 1024 * 1024,
        max_stderr=MAX_STDERR):
    """Drain all pipes concurrently, stop at byte/deadline limits, reap leader.

    POSIX process groups clean up cooperating descendants. A compromised child
    can escape a process group; this function is not host isolation.
    """
    if os.name != "posix" or not hasattr(os, "killpg"):
        raise ProcessError("Bounded CLI transport requires a qualified POSIX host")
    if input is not None and (not isinstance(input, bytes) or len(input) > max_stdout):
        raise ProcessError("CLI request exceeds bounded size")
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE if input else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd,
                            shell=False, close_fds=True, start_new_session=True, bufsize=0)
    stdout, stderr_bytes, sent = bytearray(), 0, 0
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for stream, name in ((proc.stdout, "stdout"), (proc.stderr, "stderr")):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            if proc.stdin:
                os.set_blocking(proc.stdin.fileno(), False)
                selector.register(proc.stdin, selectors.EVENT_WRITE, "stdin")
            while selector.get_map() or proc.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProcessError("CLI deadline exceeded; reconcile any write intent")
                for key, _ in selector.select(min(remaining, .1)):
                    stream = key.fileobj
                    if key.data == "stdin":
                        try:
                            sent += os.write(stream.fileno(), memoryview(input)[sent:sent + 65536])
                        except BlockingIOError:
                            continue
                        except BrokenPipeError:
                            raise ProcessError("CLI input closed before delivery; reconcile any write intent") from None
                        if sent == len(input):
                            selector.unregister(stream)
                            stream.close()
                        continue
                    try:
                        chunk = os.read(stream.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                    elif key.data == "stdout":
                        if len(stdout) + len(chunk) > max_stdout:
                            raise ProcessError("CLI stdout limit exceeded; reconcile any write intent")
                        stdout.extend(chunk)
                    else:
                        stderr_bytes += len(chunk)
                        if stderr_bytes > max_stderr:
                            raise ProcessError("CLI stderr limit exceeded; reconcile any write intent")
        return subprocess.CompletedProcess(argv, proc.returncode, bytes(stdout), b"")
    finally:
        # Never retain stderr or echo command/input/environment values.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()
            proc.wait()
