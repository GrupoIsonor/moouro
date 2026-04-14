#!/usr/bin/env python3
import subprocess
import sys


if len(sys.argv) < 2:
    print(
        "Usage: restore.py <target-path> [latest|YYYY-MM-DD|LSN] [latest|snapshot-id] [dry-run]"
    )
    print("Examples:")
    print("  restore.py /path latest")
    print("  restore.py /path latest abc123def")
    print("  restore.py /path 2026-04-08 latest")
    print("  restore.py /path 20260119-092833F abc123def")
    sys.exit(1)

target = sys.argv[1]
pg_arg = sys.argv[2] if len(sys.argv) > 2 else "latest"
rs_arg = sys.argv[3] if len(sys.argv) > 3 else "latest"
dry_run = len(sys.argv) > 4 and sys.argv[4].lower() in [
    "dry-run",
    "dryrun",
    "--dry-run",
]

# pgbackrest
if pg_arg.lower() == "latest":
    pg_cmd = [
        "pgbackrest",
        "--stanza=main",
        "restore",
        "--delta",
        "--type=immediate",
        "--target-action=promote",
    ]
else:
    pg_cmd = [
        "pgbackrest",
        "--stanza=main",
        "restore",
        "--delta",
        f"--set={pg_arg}",
        "--type=immediate",
        "--target-action=promote",
    ]

# resticprofile
if rs_arg.lower() == "latest":
    rs_cmd = [
        "resticprofile",
        "restore",
        "--target",
        target,
        "--latest",
        "--overwrite=always",
        "--delete",
    ]
else:
    rs_cmd = [
        "resticprofile",
        "restore",
        "--target",
        target,
        "--snapshot",
        rs_arg,
        "--overwrite=always",
        "--delete",
    ]

if dry_run:
    pg_cmd.append("--dry-run")
    rs_cmd.append("--dry-run")

try:
    log = ["Starting RESTORE..."]
    log.append(f"pgbackrest: {pg_arg} ({'DRY' if dry_run else 'LIVE'})")
    p1 = subprocess.run(
        pg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    log.append(p1.stdout.strip() or "No output")

    log.append(f"resticprofile: {rs_arg} to {target} ({'DRY' if dry_run else 'LIVE'})")
    p2 = subprocess.run(
        rs_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    log.append(p2.stdout.strip() or "No output")

    status = "DRY-RUN completed" if dry_run else "completed successfully"
    print(f"\n=== Restore {status} ===")
    print(f"Target: {target}\n")
    print("\n".join(log))

except Exception as e:
    print(f"\n=== Restore FAILED ===")
    print(f"Target: {target}\n")
    print(f"ERROR: {e}")
    sys.exit(1)
