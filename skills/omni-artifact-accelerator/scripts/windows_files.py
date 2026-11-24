"""Private local NTFS operations for the native-Windows preview (standard library only).

Each existing component is opened relative to a held directory handle, without
following reparse points. The sharing modes pin directories against renames
and exclude concurrent reads of partial writes. No shell or PATH lookup occurs.
"""
from contextlib import contextmanager, ExitStack
import ctypes as C
from functools import lru_cache
import os
from pathlib import Path, PureWindowsPath
import re
import secrets
import sys


U32, U16, U8 = C.c_uint32, C.c_uint16, C.c_ubyte
PTR, WP = C.c_void_p, C.c_wchar_p
L32 = C.c_int32
READ_ATTR, READ_DATA, WRITE_DATA, TRAVERSE = 0x80, 1, 2, 0x20
DELETE, READ_CONTROL, SYNCHRONIZE = 0x10000, 0x20000, 0x100000
SHARE_READ, SHARE_WRITE, SHARE_DELETE = 1, 2, 4
OPEN, CREATE, OPEN_IF = 1, 2, 3
DIR, FILE, SYNC, NO_REPARSE = 1, 0x40, 0x20, 0x00200000
READ_DIR = READ_ATTR | TRAVERSE
FULL_ACCESS = 0x1F01FF
INVALID_HANDLE = PTR(-1).value


class UnicodeString(C.Structure):
    _fields_ = [('Length', U16), ('MaximumLength', U16), ('Buffer', PTR)]


class ObjectAttributes(C.Structure):
    _fields_ = [('Length', U32), ('RootDirectory', PTR), ('ObjectName', C.POINTER(UnicodeString)),
                ('Attributes', U32), ('SecurityDescriptor', PTR), ('SecurityQualityOfService', PTR)]


class IoStatus(C.Structure):
    _fields_ = [('StatusOrPointer', PTR), ('Information', C.c_size_t)]


class FileInfo(C.Structure):
    _fields_ = [('attributes', U32), ('creation', U32 * 2), ('access', U32 * 2), ('modified', U32 * 2),
                ('volume', U32), ('size_high', U32), ('size_low', U32), ('links', U32),
                ('index_high', U32), ('index_low', U32)]


class RenameInfo(C.Structure):
    _fields_ = [('Flags', U32), ('RootDirectory', PTR), ('FileNameLength', U32), ('FileName', U16 * 1)]


class Overlapped(C.Structure):
    _fields_ = [('internal', C.c_size_t), ('internal_high', C.c_size_t), ('offset', U32),
                ('offset_high', U32), ('event', PTR)]


class AclInfo(C.Structure):
    _fields_ = [('count', U32), ('used', U32), ('free', U32)]


class AllowedAce(C.Structure):
    _fields_ = [('type', U8), ('flags', U8), ('size', U16), ('rights', U32), ('sid_start', U32)]


def _ok(result):
    if not result:
        raise C.WinError(C.get_last_error())


class WindowsAPI:
    def __init__(self):
        if os.name != 'nt' or C.sizeof(PTR) not in (4, 8) or C.sizeof(C.c_wchar) != 2:
            raise ValueError('native_windows_api_unavailable')
        # Restrict resolution of every system DLL to Windows' system directory.
        k, a, n = [C.WinDLL(name, use_last_error=True, winmode=0x800)
                   for name in ('kernel32.dll', 'advapi32.dll', 'ntdll.dll')]

        def bind(dll, name, result, *args):
            function = getattr(dll, name)
            function.argtypes, function.restype = list(args), result
            setattr(self, name, function)

        bind(k, 'GetDriveTypeW', U32, WP)
        bind(k, 'GetVolumeInformationW', L32, WP, WP, U32, PTR, PTR, C.POINTER(U32), WP, U32)
        bind(k, 'CreateFileW', PTR, WP, U32, U32, PTR, U32, U32, PTR)
        bind(k, 'GetFinalPathNameByHandleW', U32, PTR, WP, U32, U32)
        bind(k, 'GetFileType', U32, PTR)
        bind(k, 'GetFileInformationByHandle', L32, PTR, C.POINTER(FileInfo))
        bind(k, 'CloseHandle', L32, PTR)
        bind(k, 'GetCurrentThread', PTR)
        bind(k, 'GetCurrentProcess', PTR)
        bind(k, 'IsWow64Process2', L32, PTR, C.POINTER(U16), C.POINTER(U16))
        bind(k, 'ReadFile', L32, PTR, PTR, U32, C.POINTER(U32), PTR)
        bind(k, 'WriteFile', L32, PTR, PTR, U32, C.POINTER(U32), PTR)
        bind(k, 'FlushFileBuffers', L32, PTR)
        bind(k, 'LockFileEx', L32, PTR, U32, U32, U32, U32, C.POINTER(Overlapped))
        bind(k, 'UnlockFileEx', L32, PTR, U32, U32, U32, C.POINTER(Overlapped))
        bind(k, 'LocalFree', PTR, PTR)
        bind(a, 'OpenThreadToken', L32, PTR, U32, L32, C.POINTER(PTR))
        bind(a, 'OpenProcessToken', L32, PTR, U32, C.POINTER(PTR))
        bind(a, 'GetTokenInformation', L32, PTR, U32, PTR, U32, C.POINTER(U32))
        bind(a, 'ConvertSidToStringSidW', L32, PTR, C.POINTER(PTR))
        bind(a, 'ConvertStringSecurityDescriptorToSecurityDescriptorW', L32, WP, U32, C.POINTER(PTR), PTR)
        bind(a, 'GetSecurityInfo', U32, PTR, U32, U32, C.POINTER(PTR), PTR, C.POINTER(PTR), PTR, C.POINTER(PTR))
        bind(a, 'GetSecurityDescriptorControl', L32, PTR, C.POINTER(U16), C.POINTER(U32))
        bind(a, 'GetAclInformation', L32, PTR, PTR, U32, U32)
        bind(a, 'GetAce', L32, PTR, U32, C.POINTER(PTR))
        bind(a, 'EqualSid', L32, PTR, PTR)
        bind(n, 'RtlNtStatusToDosError', U32, L32)
        bind(n, 'NtCreateFile', L32, C.POINTER(PTR), U32, C.POINTER(ObjectAttributes), C.POINTER(IoStatus),
             PTR, U32, U32, U32, U32, PTR, U32)
        bind(n, 'NtSetInformationFile', L32, PTR, C.POINTER(IoStatus), PTR, U32, U32)

    def nt(self, status):
        if status != 0:
            raise C.WinError(self.RtlNtStatusToDosError(status))


@lru_cache(maxsize=1)
def _api():
    try:
        return WindowsAPI()
    except (AttributeError, OSError) as exc:
        raise ValueError('required_windows_filesystem_api_unavailable') from exc


@lru_cache(maxsize=1)
def _supported_host():
    if sys.version_info < (3, 9):
        raise ValueError('python_3_9_or_later_required_for_windows_preview')
    api = _api()
    version = sys.getwindowsversion()
    process, native = U16(), U16()
    _ok(api.IsWow64Process2(api.GetCurrentProcess(), C.byref(process), C.byref(native)))
    if ((version.major, version.build) < (10, 22000) or version.product_type != 1 or C.sizeof(PTR) != 8
            or native.value != 0x8664 or process.value != 0):
        raise ValueError('native_windows_11_x64_with_64_bit_python_required')


def _component(name):
    if (not name or name in ('.', '..') or name[-1] in ' .' or any(ord(c) < 32 for c in name)
            or any(c in '<>:"/\\|?*' for c in name) or len(name.encode('utf-16-le')) > 510
            or re.fullmatch(r'(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[0-9¹²³])',
                            name.split('.')[0].rstrip(' '), re.IGNORECASE)):
        raise ValueError('unsafe_windows_path_component')
    return name


def canonical_path(value):
    original = PureWindowsPath(value)
    if ('..' in original.parts or (original.anchor and not re.fullmatch(r'[A-Za-z]:\\', original.anchor))):
        raise ValueError('local_absolute_windows_drive_required')
    path = Path(value).absolute()
    if not re.fullmatch(r'[A-Za-z]:\\', path.anchor):
        raise ValueError('local_absolute_windows_drive_required')
    for part in path.parts[1:]:
        _component(part)
    return path


def _parts(relative):
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('canonical_windows_relative_path_required')
    return [_component(part) for part in relative.split('/')]


@contextmanager
def _current_sid():
    api, token = _api(), PTR()
    if not api.OpenThreadToken(api.GetCurrentThread(), 8, True, C.byref(token)):  # TOKEN_QUERY
        if C.get_last_error() != 1008:  # ERROR_NO_TOKEN
            raise C.WinError(C.get_last_error())
        _ok(api.OpenProcessToken(api.GetCurrentProcess(), 8, C.byref(token)))
    try:
        size = U32()
        if api.GetTokenInformation(token, 1, None, 0, C.byref(size)) or C.get_last_error() != 122:
            raise ValueError('current_windows_user_unavailable')
        buffer = C.create_string_buffer(size.value)
        _ok(api.GetTokenInformation(token, 1, buffer, size, C.byref(size)))  # TokenUser starts with PSID
        yield PTR.from_buffer(buffer).value
    finally:
        api.CloseHandle(token)


@contextmanager
def _private_sd(directory):
    api, sid_text, descriptor = _api(), PTR(), PTR()
    with _current_sid() as sid:
        _ok(api.ConvertSidToStringSidW(sid, C.byref(sid_text)))
        try:
            user = C.wstring_at(sid_text)
            flags = 'OICI' if directory else ''
            sddl = 'O:' + user + 'D:P(A;' + flags + ';FA;;;' + user + ')'
            _ok(api.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, C.byref(descriptor), None))
            try:
                yield descriptor
            finally:
                api.LocalFree(descriptor)
        finally:
            api.LocalFree(sid_text)


def _private(handle, directory):
    api, owner, acl, sd = _api(), PTR(), PTR(), PTR()
    status = api.GetSecurityInfo(handle, 1, 5, C.byref(owner), None, C.byref(acl), None, C.byref(sd))
    if status:
        raise C.WinError(status)
    try:
        control, revision, info = U16(), U32(), AclInfo()
        _ok(api.GetSecurityDescriptorControl(sd, C.byref(control), C.byref(revision)))
        if not acl or not (control.value & 0x1000):  # protected DACL
            raise ValueError('private_windows_dacl_required')
        _ok(api.GetAclInformation(acl, C.byref(info), C.sizeof(info), 2))
        if info.count != 1:
            raise ValueError('current_user_only_windows_acl_required')
        address = PTR()
        _ok(api.GetAce(acl, 0, C.byref(address)))
        ace = AllowedAce.from_address(address.value)
        with _current_sid() as sid:
            if (not api.EqualSid(owner, sid) or ace.type != 0 or ace.rights != FULL_ACCESS
                    or ace.flags != (3 if directory else 0)
                    or not api.EqualSid(address.value + AllowedAce.sid_start.offset, sid)):
                raise ValueError('current_user_only_windows_acl_required')
    finally:
        api.LocalFree(sd)


def _info(handle, *, directory=None, after_read=False):
    info = FileInfo()
    _ok(_api().GetFileInformationByHandle(handle, C.byref(info)))
    is_dir = bool(info.attributes & 0x10)
    if after_read and not is_dir and info.links == 0:
        raise ReadChanged('windows_input_replaced_during_read')
    if (_api().GetFileType(handle) != 1 or info.attributes & 0x400 or (directory is not None and directory != is_dir)
            or (not is_dir and info.links != 1)):
        raise ValueError('plain_unlinked_windows_disk_object_required')
    return info


@contextmanager
def _child(parent, name, access, *, directory=None, disposition=OPEN, private=False, share=SHARE_READ | SHARE_WRITE):
    api = _api()
    text = C.create_unicode_buffer(_component(name))
    length = len(name.encode('utf-16-le'))
    string = UnicodeString(length, length + 2, C.cast(text, PTR))
    obj = ObjectAttributes(C.sizeof(ObjectAttributes), parent, C.pointer(string), 0x1040, None, None)
    # OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE. Each call receives exactly one component.
    handle, ios = PTR(), IoStatus()
    with ExitStack() as before_open:
        if private:
            obj.SecurityDescriptor = before_open.enter_context(_private_sd(directory is True)).value
            access |= READ_CONTROL
            if disposition == CREATE:
                access |= DELETE  # remove a failed exclusive creation by handle
        kind = DIR if directory is True else FILE if directory is False else 0
        status = api.NtCreateFile(C.byref(handle), access | SYNCHRONIZE, C.byref(obj), C.byref(ios), None,
            0 if directory else 0x80, share, disposition, kind | SYNC | NO_REPARSE, None, 0)
        api.nt(status)
    try:
        try:
            _info(handle, directory=directory)
            if private:
                _private(handle, directory is True)
        except BaseException:
            if private and disposition == CREATE and ios.Information == 2:  # FILE_CREATED
                _remove(handle)
            raise
        yield handle
    finally:
        api.CloseHandle(handle)


@contextmanager
def _volume(path):
    _supported_host()
    api = _api()
    drive = path.anchor
    if api.GetDriveTypeW(drive) != 3:
        raise ValueError('fixed_local_ntfs_volume_required')
    filesystem, flags = C.create_unicode_buffer(64), U32()
    _ok(api.GetVolumeInformationW(drive, None, 0, None, None, C.byref(flags), filesystem, len(filesystem)))
    if filesystem.value.upper() != 'NTFS' or not flags.value & 8:  # FILE_PERSISTENT_ACLS
        raise ValueError('fixed_local_ntfs_with_acls_required')
    handle = api.CreateFileW(drive, READ_DIR | SYNCHRONIZE, SHARE_READ | SHARE_WRITE, None, 3, 0x02200000, None)
    if handle == INVALID_HANDLE:
        raise C.WinError(C.get_last_error())
    handle = PTR(handle)
    try:
        final = C.create_unicode_buffer(512)
        size = api.GetFinalPathNameByHandleW(handle, final, len(final), 0)
        if not size or size >= len(final) or final.value.rstrip('\\').casefold() != ('\\\\?\\' + drive).rstrip('\\').casefold():
            raise ValueError('direct_local_windows_drive_required')
        _info(handle, directory=True)
        yield handle
    finally:
        api.CloseHandle(handle)


class ReadChanged(ValueError):
    """A pinned native read changed before completion."""


class Directory:
    def __init__(self, path, handle):
        self.path, self.handle = path, handle


@contextmanager
def pinned_directory(path, *, private_root=False):
    path = canonical_path(path)
    with ExitStack() as stack:
        current = stack.enter_context(_volume(path))
        for index, name in enumerate(path.parts[1:], 1):
            private = private_root and index == len(path.parts) - 1
            current = stack.enter_context(_child(current, name, READ_DIR | (READ_CONTROL if private else 0), directory=True))
            if private:
                _private(current, True)
        if private_root and not path.parts[1:]:
            raise ValueError('private_windows_directory_required')
        yield Directory(path, current)


def check_workspace(parent):
    with pinned_directory(parent):
        return {'filesystem': 'NTFS', 'scope': 'fixed_local_drive', 'status': 'preview'}


def check_private_project(root):
    with pinned_directory(root, private_root=True) as directory:
        return directory.path


def no_links(path):
    path = canonical_path(path)
    with ExitStack() as stack:
        current = stack.enter_context(_volume(path))
        for index, part in enumerate(path.parts[1:], 1):
            try:
                current = stack.enter_context(_child(current, part,
                    READ_DIR if index < len(path.parts) - 1 else READ_ATTR,
                    directory=True if index < len(path.parts) - 1 else None))
            except FileNotFoundError:
                break
    return path


def mkdir_private(path):
    path = canonical_path(path)
    with pinned_directory(path.parent) as parent:
        with _child(parent.handle, path.name, READ_DIR, directory=True, disposition=CREATE, private=True):
            pass


@contextmanager
def _parent(root, relative):
    parts = _parts(relative)
    with ExitStack() as stack:
        current = root.handle
        for part in parts[:-1]:
            current = stack.enter_context(_child(current, part, READ_DIR, directory=True))
        yield current, parts[-1]


def read(root, relative, maximum):
    with _parent(root, relative) as (parent, name):
        # A writer can atomically install a new name while this read pins the
        # old object. In-place writes still conflict with this sharing mode.
        with _child(parent, name, READ_DATA | READ_ATTR, directory=False, share=SHARE_READ | SHARE_DELETE) as handle:
            before = _info(handle, directory=False)
            size = (before.size_high << 32) | before.size_low
            if size > maximum:
                raise ValueError('windows_bounded_regular_file_required')
            result = bytearray()
            buffer = C.create_string_buffer(min(65536, maximum + 1))
            while True:
                count = U32()
                _ok(_api().ReadFile(handle, buffer, min(len(buffer), maximum + 1 - len(result)), C.byref(count), None))
                if not count.value:
                    break
                result.extend(buffer.raw[:count.value])
                if len(result) > maximum:
                    raise ValueError('windows_file_too_large')
            after = _info(handle, directory=False, after_read=True)
            if (len(result) != size or before.size_low != after.size_low or before.size_high != after.size_high
                    or tuple(before.modified) != tuple(after.modified)):
                raise ReadChanged('windows_input_changed_during_read')
            return bytes(result)


def read_path(path, maximum):
    path = canonical_path(path)
    with pinned_directory(path.parent) as parent:
        return read(parent, path.name, maximum)


def _write(handle, data):
    view = memoryview(data)
    while view:
        buf, count = bytes(view[:65536]), U32()
        _ok(_api().WriteFile(handle, buf, len(buf), C.byref(count), None))
        if not count.value:
            raise OSError('windows_write_failed')
        view = view[count.value:]
    _ok(_api().FlushFileBuffers(handle))


def _remove(handle):
    marked, ios = U8(1), IoStatus()
    _api().nt(_api().NtSetInformationFile(handle, C.byref(ios), C.byref(marked), 1, 13))


def _rename(source, name, replace):
    # Every caller moves the source within its pinned parent. With a single
    # component and NULL RootDirectory the target is relative to that parent.
    # Win11 NTFS supports FileRenameInformationEx. POSIX_SEMANTICS permits
    # replacement with existing share-delete readers, without closing their handles.
    encoded = _component(name).encode('utf-16-le')
    offset = RenameInfo.FileName.offset
    buf = C.create_string_buffer(max(C.sizeof(RenameInfo), offset + len(encoded)))
    info = RenameInfo.from_buffer(buf)
    info.Flags = 3 if replace else 0  # REPLACE_IF_EXISTS | POSIX_SEMANTICS
    info.RootDirectory, info.FileNameLength = None, len(encoded)
    C.memmove(C.addressof(buf) + offset, encoded, len(encoded))
    ios = IoStatus()
    _api().nt(_api().NtSetInformationFile(source, C.byref(ios), buf, len(buf), 65))


def atomic_write(root, name, data, *, replace, require_existing=False):
    name = _component(name)
    if replace:
        try:
            with _child(root.handle, name, READ_ATTR, directory=False):
                pass
        except FileNotFoundError:
            if require_existing:
                raise
    temp = '.oaa-' + secrets.token_hex(16)
    with _child(root.handle, temp, DELETE | WRITE_DATA | READ_ATTR, directory=False, disposition=CREATE,
                private=True, share=0) as handle:
        try:
            _write(handle, data)
            _rename(handle, name, replace)
        except BaseException:
            _remove(handle)
            raise


def private_write(path, data, replace=False):
    path = canonical_path(path)
    with pinned_directory(path.parent) as parent:
        atomic_write(parent, path.name, data, replace=replace, require_existing=replace)


def write_pair(root, first_relative, first_bytes, second_relative, second_bytes):
    with ExitStack() as stack:
        if not hasattr(root, 'handle'):
            root = stack.enter_context(pinned_directory(root, private_root=True))
        created = []
        try:
            for relative in (first_relative, second_relative):
                parent, name = stack.enter_context(_parent(root, relative))
                created.append(stack.enter_context(_child(parent, name, DELETE | WRITE_DATA | READ_ATTR,
                    directory=False, disposition=CREATE, private=True, share=0)))
            _write(created[0], first_bytes)
            _write(created[1], second_bytes)
        except BaseException:
            for handle in created:
                _remove(handle)
            raise


def publish_directory(staged, destination):
    staged, destination = canonical_path(staged), canonical_path(destination)
    if staged.parent != destination.parent or staged == destination:
        raise ValueError('same_parent_distinct_private_windows_directories_required')
    with pinned_directory(staged.parent) as parent:
        with _child(parent.handle, staged.name, DELETE | READ_ATTR | READ_CONTROL, directory=True, share=0) as handle:
            _private(handle, True)
            _rename(handle, destination.name, False)


@contextmanager
def locked(root, name, *, shared=False, wait=False):
    with _child(root.handle, name, READ_DATA | WRITE_DATA | READ_ATTR, directory=False,
                disposition=OPEN_IF, private=True) as handle:
        overlap = Overlapped()
        flags = (0 if shared else 2) | (0 if wait else 1)
        if not _api().LockFileEx(handle, flags, 0, 1, 0, C.byref(overlap)):
            error = C.get_last_error()
            if error in (32, 33):
                raise BlockingIOError('windows_lock_busy') from C.WinError(error)
            raise C.WinError(error)
        try:
            yield handle
        finally:
            _ok(_api().UnlockFileEx(handle, 0, 1, 0, C.byref(overlap)))


@contextmanager
def locked_path(path, *, shared=False, wait=False):
    path = canonical_path(path)
    with pinned_directory(path.parent) as parent, locked(parent, path.name, shared=shared, wait=wait):
        yield
