"""Install NanToken auto-tracking hook into Claude Code settings.

Usage:
    python -m nantoken.hooks.install          # Print config + prompt to install
    python -m nantoken.hooks.install --auto   # Auto-merge into settings.json
"""

import json
import os
import sys
from pathlib import Path


def detect_hook_script_path() -> Path:
    """Find the absolute path to stop_track.py."""
    return Path(__file__).resolve().parent / "stop_track.py"


def generate_hook_config(script_path: Path) -> dict:
    """Generate the Claude Code hook configuration."""
    return {
        "hooks": {
            "Stop": [
                {
                    "type": "command",
                    "command": f"python \"{script_path}\""
                }
            ]
        }
    }


def get_settings_path() -> Path:
    """Return the Claude Code settings.json path."""
    return Path.home() / ".claude" / "settings.json"


def load_settings(settings_path: Path) -> dict:
    """Load existing settings or return empty dict."""
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def merge_hook(settings: dict, hook_config: dict) -> dict:
    """Merge NanToken hook into existing settings without clobbering."""
    if "hooks" not in settings:
        settings["hooks"] = {}

    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []

    stop_hooks = settings["hooks"]["Stop"]

    # Check if NanToken hook already exists
    for i, hook in enumerate(stop_hooks):
        if isinstance(hook, dict) and "nantoken" in hook.get("command", ""):
            # Update existing
            stop_hooks[i] = hook_config["hooks"]["Stop"][0]
            return settings

    # Append new
    stop_hooks.append(hook_config["hooks"]["Stop"][0])
    return settings


def save_settings(settings_path: Path, settings: dict) -> None:
    """Atomic write settings."""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = settings_path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(str(tmp_path), str(settings_path))


def install_hook(auto: bool = False) -> None:
    """Main installation flow."""
    script_path = detect_hook_script_path()
    hook_config = generate_hook_config(script_path)
    settings_path = get_settings_path()

    print("NanToken Auto-Tracking Hook Installer")
    print("=" * 50)
    print()
    print(f"Hook script: {script_path}")
    print(f"Settings file: {settings_path}")
    print()
    print("Add this to your ~/.claude/settings.json:")
    print()
    print(json.dumps(hook_config, indent=2))
    print()

    if auto:
        do_install = True
    else:
        try:
            answer = input("Install automatically? [y/N] ").strip().lower()
            do_install = answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print("\nSkipped.")
            return

    if do_install:
        settings = load_settings(settings_path)
        settings = merge_hook(settings, hook_config)
        save_settings(settings_path, settings)
        print(f"Installed! Hook added to {settings_path}")
        print("Restart Claude Code to activate auto-tracking.")
    else:
        print("Copy the JSON above into your ~/.claude/settings.json manually.")


def main() -> None:
    """CLI entry point."""
    auto = "--auto" in sys.argv
    install_hook(auto=auto)


if __name__ == "__main__":
    main()
