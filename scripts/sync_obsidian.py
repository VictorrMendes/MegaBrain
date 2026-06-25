#!/usr/bin/env python3
"""
Sync Obsidian vault to Khonshu.

Usage:
  python sync_obsidian.py --workspace <workspace_id>

Defaults (edit below or pass as arguments):
  --vault    C:/Users/victo/Documents/obsidian/Obsidian
  --api      http://192.168.1.26:8100
  --manifest ./obsidian_sync_manifest.json

Examples:
  # First sync (no manifest yet):
  python sync_obsidian.py --workspace abc123

  # Force re-sync of everything:
  python sync_obsidian.py --workspace abc123 --force
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests not installed. Run: pip install requests")

DEFAULT_VAULT = "C:/Users/victo/Documents/obsidian/Obsidian"
DEFAULT_API = "http://192.168.1.26:8100"
DEFAULT_MANIFEST = Path(__file__).parent / "obsidian_sync_manifest.json"

SKIP_DIRS = {".obsidian", ".git", ".claude", "node_modules"}
SKIP_FILES = {"SKILLS-INSTALLED.md", "skills-integration-plan.md"}


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def collect_notes(vault: Path, manifest: dict, force: bool) -> list[dict]:
    notes = []
    for md_file in vault.rglob("*.md"):
        # Skip hidden / system directories
        if any(part in SKIP_DIRS for part in md_file.parts):
            continue
        if md_file.name in SKIP_FILES:
            continue

        rel_path = md_file.relative_to(vault).as_posix()
        mtime = md_file.stat().st_mtime

        if not force and manifest.get(rel_path, {}).get("mtime", 0) >= mtime:
            continue

        content = md_file.read_text(encoding="utf-8", errors="replace")
        last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        notes.append({"path": rel_path, "content": content, "last_modified": last_modified})

    return notes


def sync(vault_path: str, workspace_id: str, api_url: str, manifest_path: Path, force: bool) -> None:
    vault = Path(vault_path)
    if not vault.is_dir():
        sys.exit(f"Vault not found: {vault}")

    manifest = load_manifest(manifest_path)
    notes = collect_notes(vault, manifest, force)

    if not notes:
        print("Nothing to sync — vault is up to date.")
        return

    print(f"Syncing {len(notes)} note(s) to {api_url} ...")

    try:
        resp = requests.post(
            f"{api_url}/workspaces/{workspace_id}/obsidian/sync",
            json={"notes": notes},
            timeout=300,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        sys.exit(f"Cannot connect to Khonshu API at {api_url}")
    except requests.exceptions.HTTPError as e:
        sys.exit(f"API error: {e.response.status_code} — {e.response.text}")

    result = resp.json()
    print(f"  Added:     {result['added']}")
    print(f"  Updated:   {result['updated']}")
    print(f"  Unchanged: {result['unchanged']}")
    if result["errors"]:
        print(f"  Errors ({len(result['errors'])}):")
        for err in result["errors"]:
            print(f"    - {err}")

    # Update manifest for successfully synced notes
    for note in notes:
        mtime = (vault / note["path"]).stat().st_mtime
        manifest[note["path"]] = {"mtime": mtime}
    save_manifest(manifest_path, manifest)
    print(f"Manifest saved: {manifest_path}")


def get_or_create_workspace(api_url: str) -> str:
    """List workspaces and return the first one, or create a default."""
    resp = requests.get(f"{api_url}/workspaces", timeout=30)
    resp.raise_for_status()
    workspaces = resp.json()
    if workspaces:
        ws = workspaces[0]
        print(f"Using workspace: {ws['name']} ({ws['id']})")
        return ws["id"]
    # Create default workspace
    resp = requests.post(
        f"{api_url}/workspaces",
        json={"name": "Principal", "description": "Workspace principal"},
        timeout=30,
    )
    resp.raise_for_status()
    ws = resp.json()
    print(f"Created workspace: {ws['name']} ({ws['id']})")
    return ws["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Obsidian vault to Khonshu")
    parser.add_argument("--vault", default=DEFAULT_VAULT, help="Path to Obsidian vault")
    parser.add_argument("--workspace", default=None, help="Workspace ID (auto-detected if omitted)")
    parser.add_argument("--api", default=DEFAULT_API, help="Khonshu API URL")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to manifest file")
    parser.add_argument("--force", action="store_true", help="Re-sync all notes ignoring manifest")
    args = parser.parse_args()

    workspace_id = args.workspace
    if not workspace_id:
        try:
            workspace_id = get_or_create_workspace(args.api)
        except Exception as e:
            sys.exit(f"Could not resolve workspace: {e}")

    sync(
        vault_path=args.vault,
        workspace_id=workspace_id,
        api_url=args.api,
        manifest_path=Path(args.manifest),
        force=args.force,
    )


if __name__ == "__main__":
    main()
