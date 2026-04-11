#!/usr/bin/env python3
# === USAGE ===
# python3 check.py [--notify]
#
# Examples:
#   python3 check.py          # run check and print to console only
#   python3 check.py --notify # run check and send notification via apprise
import subprocess
import sys


def notify(title, body):
    subprocess.run(["apprise", "-t", title, "-b", body], check=False)


notify_mode = "--notify" in sys.argv
log = []

try:
    log.append("=== Starting Backup Check ===")

    # pgbackrest check
    log.append("Running pgbackrest check...")
    p1 = subprocess.run(
        ["pgbackrest", "--stanza=main", "check"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    log.append(p1.stdout.strip() or "No output")

    # resticprofile check
    log.append("Running resticprofile check...")
    p2 = subprocess.run(
        ["resticprofile", "check"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    log.append(p2.stdout.strip() or "No output")

    output = "\n".join(log)

    if notify_mode:
        notify("Check OK", "Backup check completed successfully\n\n" + output)
    else:
        print(output)

except subprocess.CalledProcessError as e:
    output = "\n".join(log) + f"\nERROR: {e}"
    if notify_mode:
        notify("Check ERROR", "Backup check failed\n\n" + output)
    else:
        print(output)
    sys.exit(1)
