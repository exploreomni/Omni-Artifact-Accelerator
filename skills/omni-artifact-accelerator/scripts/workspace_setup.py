"""Read-only setup advice for the interpreter running the local workflow."""
from pathlib import Path
import sys


def inspect(workspace, route, mcp_tool, mcp_checked, loader):
    connection = loader('omni_cli_setup').local_setup(
        route, mcp_tool=mcp_tool, mcp_checked=mcp_checked)
    names = {'darwin': 'macos', 'win32': 'windows', 'linux': 'linux'}
    system = names.get(sys.platform, 'unsupported')
    result = {'platform': system, 'workflow': 'blocked', 'connection': connection,
              'native_write_authorized': False, 'qualification': 'local_setup_only'}
    root = Path(workspace).absolute()
    if not root.is_dir():
        return {**result, 'reason': 'Select the existing folder containing your checkout.'}
    if system == 'windows':
        try:
            loader('windows_files').check_workspace(root)
        except (OSError, ValueError) as exc:
            return {**result, 'reason': str(exc),
                    'next_action': 'Use a supported local workspace or continue read-only discovery.'}
        return {**result, 'workflow': 'windows_preview',
                'next_action': 'Follow the Windows setup guide; local project checks and Omni access are separate.'}
    if system in ('macos', 'linux'):
        return {**result, 'workflow': 'existing_posix_route',
                'next_action': 'Continue with the existing project or the normal intake.'}
    return {**result, 'reason': 'The local workflow targets macOS, Linux, and the Windows preview.'}
