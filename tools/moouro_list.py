#!/usr/bin/env python3
import subprocess

print("=== pgBackRest Backups ===")
subprocess.run(["pgbackrest", "--stanza=main", "info"])

print("\n=== Restic Snapshots ===")
subprocess.run(["resticprofile", "snapshots"])
