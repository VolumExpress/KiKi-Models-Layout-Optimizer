"""OS adapters to run existing JSX from a persistent Tk dashboard.

Windows: COM via a tiny cscript VBS (no pywin32 dependency).
macOS: Illustrator AppleScript support, requires macOS Automation permission.
No machine/toolpath commands are issued by this adapter.
"""
from __future__ import annotations
import subprocess
import sys
import json
import uuid
import time
from pathlib import Path
from .gui_jobs import project_root

SCRIPTS={
    "export":"export_selection.jsx",
    "apply":"apply_layout.jsx",
    "language":"set_language.jsx",
}

class IllustratorAutomationError(RuntimeError):
    pass

def get_action_command(action: str, platform: str | None = None, root: Path | None = None) -> list[str]:
    if action not in SCRIPTS:
        raise ValueError(f"Unknown Illustrator action: {action}")
    base = Path(root or project_root())
    script = base / "illustrator" / SCRIPTS[action]
    platform = platform or sys.platform
    if not script.is_file():
        raise IllustratorAutomationError(f"Missing Illustrator script: {script}")
    if platform == "win32":
        return ["cscript.exe", "//nologo", str(base / "illustrator" / "run_action_windows.vbs"), str(script)]
    if platform == "darwin":
        # AppleScript passes a POSIX file value, not the text of JSX itself.
        return ["osascript", "-e", "on run argv", "-e",
                'tell application "Adobe Illustrator"', "-e", "activate", "-e",
                "do javascript file (POSIX file (item 1 of argv))", "-e", "end tell",
                "-e", "end run", str(script)]
    raise IllustratorAutomationError("Illustrator automation supports Windows and macOS only")

def run_action(action: str, *, platform: str | None = None, root: Path | None = None,
               runner=subprocess.run, verify: bool = False) -> dict | None:
    """Invoke Illustrator. verify=True requires an explicit ack from the JSX script.

    Avoid false-positive success when COM returns 0 but Illustrator silently
    ignores the JSX or the exporter catches an exception and displays an alert.
    """
    base = Path(root or project_root())
    cmd = get_action_command(action, platform=platform, root=base)
    receipt_file = None
    request_file = None
    if verify and action in ('export', 'apply'):
        bridge_dir = base / 'workspace' / '_bridge'
        bridge_dir.mkdir(parents=True, exist_ok=True)
        nonce = uuid.uuid4().hex
        request_file = bridge_dir / 'request.json'
        receipt_file = bridge_dir / (nonce + '.json')
        request_file.write_text(json.dumps({'nonce': nonce, 'action': action}), encoding='utf-8')
    try:
        try:
            completed = runner(cmd, capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IllustratorAutomationError(str(exc)) from exc
        if completed.returncode:
            details = (completed.stderr or completed.stdout or 'unknown error').strip()
            raise IllustratorAutomationError(details)
        if receipt_file is None:
            return None
        # Some platforms return from the automation command slightly before
        # the filesystem flush. Do not wait more than 3 seconds for a receipt.
        deadline = time.monotonic() + 3
        while not receipt_file.exists() and time.monotonic() < deadline:
            time.sleep(.075)
        if not receipt_file.exists():
            raise IllustratorAutomationError(
                'Illustrator did not confirm the operation. COM/AppleScript returned '
                'without a JSX receipt. Automation output: '+(completed.stdout or '').strip()+' '+(completed.stderr or '').strip()+'. Run export_selection.jsx from Illustrator '
                'File > Scripts > Other Script and inspect any Adobe error.')
        try:
            receipt = json.loads(receipt_file.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            raise IllustratorAutomationError('Invalid Illustrator receipt: '+str(exc)) from exc
        if receipt.get('nonce') != nonce or receipt.get('action') != action:
            raise IllustratorAutomationError('Illustrator receipt does not match the request')
        if receipt.get('status') == 'error':
            raise IllustratorAutomationError('Illustrator: '+receipt.get('detail','unknown JSX error'))
        if receipt.get('status') == 'cancelled':
            return {'status':'cancelled', 'action': action}
        if receipt.get('status') != 'ok':
            raise IllustratorAutomationError('Unknown Illustrator receipt status')
        if action == 'export':
            out_path = Path(receipt.get('path',''))
            if not out_path.is_file() or out_path.stat().st_size < 10:
                raise IllustratorAutomationError('Illustrator reported export but the JSON file is missing: '+str(out_path))
        return receipt
    finally:
        if receipt_file is not None:
            receipt_file.unlink(missing_ok=True)
        if request_file is not None:
            request_file.unlink(missing_ok=True)
