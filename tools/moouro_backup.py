#!/usr/bin/env python3
# === USAGE ===
# python3 backup.py <full|incr> [dry-run] [--notify]
#
# Examples:
#   python3 backup.py full                  # normal backup
#   python3 backup.py incr                  # incremental backup
#   python3 backup.py full dry-run          # dry run (no changes)
#   python3 backup.py full --notify         # with notification
#   python3 backup.py incr dry-run --notify # combined
import subprocess
import sys

def notify(title, body):
    subprocess.run(["apprise", "-t", title, "-b", body], check=False)

backup_type = "full"
dry_run = False
notify_mode = False

for arg in sys.argv[1:]:
    if arg in ["full", "incr"]:
        backup_type = arg
    elif arg.lower() in ["dry-run", "dryrun", "--dry-run"]:
        dry_run = True
    elif arg == "--notify":
        notify_mode = True

if backup_type not in ["full", "incr"]:
    print("Error: Invalid type. Use full or incr")
    sys.exit(1)

log = []

try:
    mode = "DRY-RUN" if dry_run else "BACKUP"
    log.append(f"Starting {mode} ({backup_type})...")

    # pgbackrest
    log.append(f"pgbackrest {backup_type} backup...")
    pg_cmd = ["pgbackrest", "--stanza=main", "backup", f"--type={backup_type}"]
    if dry_run:
        pg_cmd.append("--dry-run")
    p1 = subprocess.run(pg_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        universal_newlines=True,
        check=False)
    log.append(p1.stdout.strip() or "No output")
    if p1.stderr:
        log.append("pgbackrest stderr: " + p1.stderr.strip())

    # resticprofile
    log.append(f"resticprofile backup ({backup_type})...")
    rs_cmd = ["resticprofile", "backup"]
    if backup_type == "full":
        rs_cmd.append("--force")
    if dry_run:
        rs_cmd.append("--dry-run")

    p2 = subprocess.run(rs_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        universal_newlines=True,
        check=False)
    log.append(p2.stdout.strip() or "No output")
    if p2.stderr:
        log.append("restic stderr: " + p2.stderr.strip())

    output = "\n".join(log)
    status = "DRY-RUN completed" if dry_run else "completed successfully"

    if notify_mode:
        notify(f"Backup {status.upper()}", f"Backup {backup_type}\n\n{output}")
    else:
        print(f"\n=== Backup {status} ===\n")
        print(output)

except subprocess.CalledProcessError as e:
    log.append(f"ERROR in {e.cmd[0]}")
    output = "\n".join(log)
    if notify_mode:
        notify("Backup ERROR", f"Backup {backup_type} failed\n\n{output}")
    else:
        print(f"\n=== Backup FAILED ===\n")
        print(output)
    sys.exit(1)
