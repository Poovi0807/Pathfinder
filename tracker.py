"""
Pathfinder — Customer Onboarding Tracker
IT/Ops-hardened CLI tool with:
  - Structured logging to logs/ folder
  - Timestamped backups (last 7 kept) in backups/ folder
  - Full error handling on all file I/O
  - --check health-check flag
  - Input validation, atomic writes, file permissions
"""

import json
import csv
import os
import re
import shutil
import logging
import tempfile
import argparse
import sys
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent
DATA_FILE   = BASE_DIR / "customers.json"
LOGS_DIR    = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

STAGES = ["invited", "training", "active", "completed"]
MAX_BACKUPS = 7

# ── Logging Setup ─────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    """Create logs/ directory and a timestamped log file for today's session."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_filename = LOGS_DIR / f"pathfinder_{datetime.now().strftime('%Y-%m-%d')}.log"

    logger = logging.getLogger("pathfinder")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_filename, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("  [%(levelname)s] %(message)s"))

    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger

log = setup_logging()

# ── Backup ────────────────────────────────────────────────────────────────────

def backup_data():
    """Copy customers.json into backups/ with a timestamp. Keep last MAX_BACKUPS."""
    if not DATA_FILE.exists():
        return
    try:
        BACKUPS_DIR.mkdir(exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = BACKUPS_DIR / f"customers_{ts}.json"
        shutil.copy2(DATA_FILE, dest)
        log.info(f"BACKUP: Created {dest.name}")

        backups = sorted(BACKUPS_DIR.glob("customers_*.json"))
        for old in backups[:-MAX_BACKUPS]:
            old.unlink()
            log.info(f"BACKUP: Pruned old backup {old.name}")
    except OSError as e:
        log.error(f"BACKUP: Failed — {e}")

# ── Data I/O ──────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {"name", "company", "email", "stage", "added_on", "notes"}

def is_valid_record(record) -> bool:
    if not isinstance(record, dict):
        return False
    if not REQUIRED_FIELDS.issubset(record.keys()):
        return False
    if record["stage"] not in STAGES:
        return False
    if not isinstance(record["notes"], list):
        return False
    return True

def load_data() -> list:
    if not DATA_FILE.exists():
        log.debug("LOAD: Data file not found — starting empty.")
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"LOAD: customers.json corrupt — {e}")
        print("  ⚠  Data file is corrupt. Check logs/ for details.")
        return []
    except OSError as e:
        log.error(f"LOAD: Cannot read customers.json — {e}")
        print(f"  ✗  Cannot read data file: {e}")
        return []

    valid   = [r for r in data if is_valid_record(r)]
    skipped = len(data) - len(valid)
    if skipped:
        log.warning(f"LOAD: {skipped} malformed record(s) skipped.")
        print(f"  ⚠  {skipped} malformed record(s) skipped.")
    log.debug(f"LOAD: {len(valid)} record(s) loaded.")
    return valid

def save_data(customers: list):
    backup_data()
    dir_name = DATA_FILE.parent
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8"
        ) as tmp:
            json.dump(customers, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name
        os.replace(tmp_path, DATA_FILE)
        os.chmod(DATA_FILE, 0o600)
        log.debug(f"SAVE: {len(customers)} record(s) written.")
    except OSError as e:
        log.error(f"SAVE: Failed — {e}")
        print(f"  ✗  Could not save data: {e}")

# ── Input Validation ──────────────────────────────────────────────────────────

def validate_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("Name must be 1–100 characters.")
    if not re.match(r"^[\w\s.\-']+$", name):
        raise ValueError("Name contains invalid characters.")
    return name

def validate_company(company: str) -> str:
    company = company.strip()
    if not company or len(company) > 150:
        raise ValueError("Company must be 1–150 characters.")
    return company

def validate_email(email: str) -> str:
    email = email.strip().lower()
    if not re.match(r"^[\w.\-+]+@[\w.\-]+\.\w{2,}$", email):
        raise ValueError(f"'{email}' is not a valid email address.")
    return email

def validate_stage(stage: str) -> str:
    stage = stage.strip().lower()
    if stage not in STAGES:
        raise ValueError(f"Stage must be one of: {', '.join(STAGES)}")
    return stage

def validate_note(note: str) -> str:
    note = note.strip()
    if not note or len(note) > 1000:
        raise ValueError("Note must be 1–1000 characters.")
    return note

def validate_filename(filename: str) -> str:
    base     = os.path.basename(filename.strip())
    safe     = re.sub(r"[^\w.\-]", "_", base)
    if not safe.lower().endswith(".csv"):
        safe += ".csv"
    resolved = os.path.realpath(safe)
    cwd      = os.path.realpath(".")
    if not resolved.startswith(cwd + os.sep) and resolved != cwd:
        raise ValueError("Export path must be within the working directory.")
    return safe

# ── Finders ───────────────────────────────────────────────────────────────────

def find_customer(customers, name):
    return next((c for c in customers if c["name"].lower() == name.lower()), None)

def find_by_email(customers, email):
    return next((c for c in customers if c["email"].lower() == email.lower()), None)

# ── Core Actions ──────────────────────────────────────────────────────────────

def add_customer(name, company, email):
    try:
        name    = validate_name(name)
        company = validate_company(company)
        email   = validate_email(email)
    except ValueError as e:
        print(f"  ✗  {e}")
        log.warning(f"ADD: Validation failed — {e}")
        return

    customers = load_data()
    if find_customer(customers, name):
        print(f"  ⚠  Customer '{name}' already exists.")
        log.warning(f"ADD: Duplicate name '{name}'")
        return
    if find_by_email(customers, email):
        print(f"  ⚠  Email '{email}' already registered.")
        log.warning(f"ADD: Duplicate email '{email}'")
        return

    customers.append({
        "name":     name,
        "company":  company,
        "email":    email,
        "stage":    "invited",
        "added_on": datetime.now().strftime("%Y-%m-%d"),
        "notes":    [],
    })
    save_data(customers)
    log.info(f"ADD: '{name}' <{email}> from {company}")
    print(f"  ✓  Added '{name}' from {company} — stage: invited")

def update_stage(name, new_stage):
    try:
        name      = validate_name(name)
        new_stage = validate_stage(new_stage)
    except ValueError as e:
        print(f"  ✗  {e}")
        log.warning(f"STAGE: Validation failed — {e}")
        return

    customers = load_data()
    customer  = find_customer(customers, name)
    if not customer:
        print(f"  ✗  Customer '{name}' not found.")
        log.warning(f"STAGE: '{name}' not found.")
        return

    old_stage         = customer["stage"]
    customer["stage"] = new_stage
    save_data(customers)
    log.info(f"STAGE: '{name}' {old_stage} → {new_stage}")
    print(f"  ✓  '{name}' updated: {old_stage} → {new_stage}")

def add_note(name, note_text):
    try:
        name      = validate_name(name)
        note_text = validate_note(note_text)
    except ValueError as e:
        print(f"  ✗  {e}")
        log.warning(f"NOTE: Validation failed — {e}")
        return

    customers = load_data()
    customer  = find_customer(customers, name)
    if not customer:
        print(f"  ✗  Customer '{name}' not found.")
        log.warning(f"NOTE: '{name}' not found.")
        return

    customer["notes"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "note": note_text,
    })
    save_data(customers)
    log.info(f"NOTE: Added note for '{name}'")
    print(f"  ✓  Note added for '{name}'")

def list_customers(filter_stage=None):
    if filter_stage:
        try:
            filter_stage = validate_stage(filter_stage)
        except ValueError as e:
            print(f"  ✗  {e}")
            return

    customers = load_data()
    if filter_stage:
        customers = [c for c in customers if c["stage"] == filter_stage]
    if not customers:
        print("  No customers found.")
        return

    print(f"\n  {'NAME':<20} {'COMPANY':<20} {'STAGE':<12} {'ADDED':<12}")
    print("  " + "-" * 65)
    for c in customers:
        print(f"  {c['name']:<20} {c['company']:<20} {c['stage']:<12} {c['added_on']:<12}")
    print()

def show_customer(name):
    try:
        name = validate_name(name)
    except ValueError as e:
        print(f"  ✗  {e}")
        return

    customers = load_data()
    customer  = find_customer(customers, name)
    if not customer:
        print(f"  ✗  Customer '{name}' not found.")
        return

    print(f"\n  ── {customer['name']} ──────────────────────────")
    print(f"  Company : {customer['company']}")
    print(f"  Email   : {customer['email']}")
    print(f"  Stage   : {customer['stage']}")
    print(f"  Added   : {customer['added_on']}")
    if customer["notes"]:
        print("  Notes:")
        for n in customer["notes"]:
            print(f"    [{n['date']}] {n['note']}")
    else:
        print("  Notes   : (none)")
    print()

def export_csv(filename="onboarding_report.csv"):
    try:
        filename = validate_filename(filename)
    except ValueError as e:
        print(f"  ✗  {e}")
        log.warning(f"EXPORT: Invalid filename — {e}")
        return

    customers = load_data()
    if not customers:
        print("  No data to export.")
        return

    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Company", "Email", "Stage", "Added On", "Note Count"])
            for c in customers:
                writer.writerow([c["name"], c["company"], c["email"],
                                  c["stage"], c["added_on"], len(c["notes"])])
        os.chmod(filename, 0o600)
        log.info(f"EXPORT: '{filename}' written ({len(customers)} records)")
        print(f"  ✓  Report exported to '{filename}'")
    except OSError as e:
        log.error(f"EXPORT: Failed — {e}")
        print(f"  ✗  Could not write CSV: {e}")

def show_summary():
    customers = load_data()
    if not customers:
        print("  No customers yet.")
        return
    print("\n  ── Onboarding Summary ──────────────────────")
    for stage in STAGES:
        count = sum(1 for c in customers if c["stage"] == stage)
        print(f"  {stage:<12} {'█' * count} {count}")
    print(f"\n  Total: {len(customers)} customer(s)\n")

# ── Health Check ──────────────────────────────────────────────────────────────

def run_health_check():
    print("\n  ── Pathfinder Health Check ─────────────────")
    issues = 0

    # 1. Data file
    if DATA_FILE.exists():
        print(f"  ✓  Data file found: {DATA_FILE}")
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            valid   = [r for r in data if is_valid_record(r)]
            invalid = len(data) - len(valid)
            print(f"  ✓  JSON is valid")
            if invalid:
                print(f"  ⚠  Records: {len(valid)} valid, {invalid} malformed")
                issues += 1
            else:
                print(f"  ✓  Records: {len(valid)} valid")
            for stage in STAGES:
                count = sum(1 for r in valid if r["stage"] == stage)
                print(f"       {stage:<12} {count}")
        except json.JSONDecodeError as e:
            print(f"  ✗  JSON is CORRUPT: {e}")
            log.error(f"HEALTH: JSON corrupt — {e}")
            issues += 1
        except OSError as e:
            print(f"  ✗  Cannot read file: {e}")
            log.error(f"HEALTH: Cannot read — {e}")
            issues += 1
    else:
        print(f"  ⚠  Data file not found — no customers added yet.")

    # 2. Backups
    BACKUPS_DIR.mkdir(exist_ok=True)
    backups = sorted(BACKUPS_DIR.glob("customers_*.json"))
    if backups:
        print(f"  ✓  Backups: {len(backups)} found (latest: {backups[-1].name})")
    else:
        print("  ⚠  No backups found yet.")

    # 3. Logs
    LOGS_DIR.mkdir(exist_ok=True)
    log_files = sorted(LOGS_DIR.glob("pathfinder_*.log"))
    if log_files:
        print(f"  ✓  Logs: {len(log_files)} log file(s) in logs/")
    else:
        print("  ⚠  No log files yet.")

    print()
    if issues == 0:
        print("  ✅  All checks passed.\n")
        log.info("HEALTH: All checks passed.")
        sys.exit(0)
    else:
        print(f"  ❌  {issues} issue(s) found. Check logs/ for details.\n")
        log.warning(f"HEALTH: {issues} issue(s) found.")
        sys.exit(1)

# ── Menu ──────────────────────────────────────────────────────────────────────

def print_menu():
    print("""
╔══════════════════════════════════════╗
║        🛰  PathFinder  (secure)      ║
╚══════════════════════════════════════╝
  1. Add new customer
  2. Update onboarding stage
  3. Add note / feedback
  4. List all customers
  5. View customer details
  6. Filter by stage
  7. Show summary
  8. Export CSV report
  0. Exit
""")

def prompt(label: str) -> str:
    return input(f"  {label}: ").strip()

def main():
    parser = argparse.ArgumentParser(description="Pathfinder — Customer Onboarding Tracker")
    parser.add_argument("--check", action="store_true",
                        help="Run a health check on the data file and exit.")
    args = parser.parse_args()

    if args.check:
        run_health_check()
        return

    log.info("SESSION: Pathfinder started.")
    while True:
        print_menu()
        choice = prompt("Choose an option")

        if choice == "1":
            add_customer(prompt("Customer name"), prompt("Company"), prompt("Email"))
        elif choice == "2":
            print(f"  Stages: {', '.join(STAGES)}")
            update_stage(prompt("Customer name"), prompt("New stage"))
        elif choice == "3":
            add_note(prompt("Customer name"), prompt("Note"))
        elif choice == "4":
            list_customers()
        elif choice == "5":
            show_customer(prompt("Customer name"))
        elif choice == "6":
            print(f"  Stages: {', '.join(STAGES)}")
            list_customers(filter_stage=prompt("Filter by stage"))
        elif choice == "7":
            show_summary()
        elif choice == "8":
            fname = prompt("Filename (default: onboarding_report.csv)")
            export_csv(fname if fname else "onboarding_report.csv")
        elif choice == "0":
            log.info("SESSION: Pathfinder exited cleanly.")
            print("\n  Goodbye!\n")
            break
        else:
            print("  ✗  Invalid option. Try again.")

if __name__ == "__main__":
    main()
