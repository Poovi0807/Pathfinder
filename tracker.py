"""
Pathfinder
A CLI tool to manage and track customer onboarding progress.
Security-hardened version: input validation, atomic writes, audit logging,
file permissions, JSON schema validation, path traversal protection, backups.
"""

import json
import csv
import os
import re
import shutil
import logging
import tempfile
from datetime import datetime

DATA_FILE = "customers.json"
STAGES = ["invited", "training", "active", "completed"]

# ── Logging / Audit Trail ─────────────────────────────────────────────────────

logging.basicConfig(
    filename="pathfinder_audit.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def audit(action: str):
    logging.info(action)

# ── Input Validation ──────────────────────────────────────────────────────────

def validate_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("Name cannot be empty.")
    if len(name) > 100:
        raise ValueError("Name must be 100 characters or fewer.")
    if not re.match(r"^[\w\s.\-']+$", name):
        raise ValueError("Name contains invalid characters.")
    return name

def validate_company(company: str) -> str:
    company = company.strip()
    if not company:
        raise ValueError("Company cannot be empty.")
    if len(company) > 150:
        raise ValueError("Company must be 150 characters or fewer.")
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
    if not note:
        raise ValueError("Note cannot be empty.")
    if len(note) > 1000:
        raise ValueError("Note must be 1000 characters or fewer.")
    return note

def validate_filename(filename: str) -> str:
    """
    Sanitize a CSV export filename and prevent path traversal.
    Only the basename is used; non-alphanumeric chars (except -_.) are replaced.
    The result is resolved relative to the current directory.
    """
    base = os.path.basename(filename.strip())
    safe = re.sub(r"[^\w.\-]", "_", base)
    if not safe.lower().endswith(".csv"):
        safe += ".csv"

    # Resolve to absolute path and ensure it stays within cwd
    resolved = os.path.realpath(safe)
    cwd = os.path.realpath(".")
    if not resolved.startswith(cwd + os.sep) and resolved != cwd:
        raise ValueError("Export path is outside the working directory.")
    return safe

# ── JSON Schema Validation ────────────────────────────────────────────────────

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
    # Validate individual notes
    for n in record["notes"]:
        if not isinstance(n, dict) or "date" not in n or "note" not in n:
            return False
    return True

# ── Data Helpers ──────────────────────────────────────────────────────────────

def load_data() -> list:
    """Load and validate customer data from JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("  ⚠  Data file is corrupted. A backup has been kept; starting fresh.")
        audit("ERROR: customers.json failed to parse — starting with empty dataset.")
        return []
    except OSError as e:
        print(f"  ✗  Could not read data file: {e}")
        audit(f"ERROR: Could not read customers.json — {e}")
        return []

    valid = [r for r in data if is_valid_record(r)]
    skipped = len(data) - len(valid)
    if skipped:
        print(f"  ⚠  {skipped} malformed record(s) skipped on load.")
        audit(f"WARNING: {skipped} malformed record(s) skipped during load.")
    return valid

def backup_data():
    """Keep a single rolling backup of the data file."""
    if os.path.exists(DATA_FILE):
        shutil.copy2(DATA_FILE, DATA_FILE + ".bak")

def save_data(customers: list):
    """
    Save customer data atomically (write to temp file, then rename).
    Also sets restrictive file permissions and keeps a backup.
    """
    backup_data()
    dir_name = os.path.dirname(os.path.realpath(DATA_FILE)) or "."
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8"
        ) as tmp:
            json.dump(customers, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name

        os.replace(tmp_path, DATA_FILE)          # atomic rename
        os.chmod(DATA_FILE, 0o600)               # owner read/write only
    except OSError as e:
        print(f"  ✗  Failed to save data: {e}")
        audit(f"ERROR: Failed to save customers.json — {e}")

def find_customer(customers: list, name: str):
    """Find a customer by name (case-insensitive)."""
    target = name.lower()
    for c in customers:
        if c["name"].lower() == target:
            return c
    return None

def find_by_email(customers: list, email: str):
    """Find a customer by email (case-insensitive)."""
    target = email.lower()
    for c in customers:
        if c["email"].lower() == target:
            return c
    return None

# ── Core Functions ────────────────────────────────────────────────────────────

def add_customer(name: str, company: str, email: str):
    """Add a new customer to the tracker."""
    try:
        name    = validate_name(name)
        company = validate_company(company)
        email   = validate_email(email)
    except ValueError as e:
        print(f"  ✗  {e}")
        return

    customers = load_data()

    if find_customer(customers, name):
        print(f"  ⚠  A customer named '{name}' already exists.")
        return
    if find_by_email(customers, email):
        print(f"  ⚠  A customer with email '{email}' already exists.")
        return

    customer = {
        "name":     name,
        "company":  company,
        "email":    email,
        "stage":    "invited",
        "added_on": datetime.now().strftime("%Y-%m-%d"),
        "notes":    [],
    }
    customers.append(customer)
    save_data(customers)
    audit(f"ADD: '{name}' <{email}> from {company}")
    print(f"  ✓  Added '{name}' from {company} — stage: invited")

def update_stage(name: str, new_stage: str):
    """Update the onboarding stage for a customer."""
    try:
        name      = validate_name(name)
        new_stage = validate_stage(new_stage)
    except ValueError as e:
        print(f"  ✗  {e}")
        return

    customers = load_data()
    customer  = find_customer(customers, name)
    if not customer:
        print(f"  ✗  Customer '{name}' not found.")
        return

    old_stage         = customer["stage"]
    customer["stage"] = new_stage
    save_data(customers)
    audit(f"STAGE: '{name}' {old_stage} → {new_stage}")
    print(f"  ✓  '{name}' updated: {old_stage} → {new_stage}")

def add_note(name: str, note_text: str):
    """Add a feedback note to a customer's record."""
    try:
        name      = validate_name(name)
        note_text = validate_note(note_text)
    except ValueError as e:
        print(f"  ✗  {e}")
        return

    customers = load_data()
    customer  = find_customer(customers, name)
    if not customer:
        print(f"  ✗  Customer '{name}' not found.")
        return

    note = {"date": datetime.now().strftime("%Y-%m-%d"), "note": note_text}
    customer["notes"].append(note)
    save_data(customers)
    audit(f"NOTE: Added note for '{name}'")
    print(f"  ✓  Note added for '{name}'")

def list_customers(filter_stage=None):
    """List all customers, optionally filtered by stage."""
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

def show_customer(name: str):
    """Show detailed info for a single customer."""
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
        print(f"\n  Notes:")
        for n in customer["notes"]:
            print(f"    [{n['date']}] {n['note']}")
    else:
        print("  Notes   : (none)")
    print()

def export_csv(filename="onboarding_report.csv"):
    """Export all customer data to a CSV file."""
    try:
        filename = validate_filename(filename)
    except ValueError as e:
        print(f"  ✗  {e}")
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
                writer.writerow([
                    c["name"],
                    c["company"],
                    c["email"],
                    c["stage"],
                    c["added_on"],
                    len(c["notes"]),
                ])
        os.chmod(filename, 0o600)
        audit(f"EXPORT: CSV written to '{filename}' ({len(customers)} records)")
        print(f"  ✓  Report exported to '{filename}'")
    except OSError as e:
        print(f"  ✗  Could not write CSV: {e}")
        audit(f"ERROR: CSV export failed — {e}")

def show_summary():
    """Show a summary count by onboarding stage."""
    customers = load_data()
    if not customers:
        print("  No customers yet.")
        return

    print("\n  ── Onboarding Summary ──────────────────────")
    for stage in STAGES:
        count = sum(1 for c in customers if c["stage"] == stage)
        bar   = "█" * count
        print(f"  {stage:<12} {bar} {count}")
    print(f"\n  Total: {len(customers)} customer(s)\n")

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
    """Read a line of input, stripping whitespace."""
    return input(f"  {label}: ").strip()

def main():
    audit("SESSION: Pathfinder started.")
    while True:
        print_menu()
        choice = prompt("Choose an option")

        if choice == "1":
            name    = prompt("Customer name")
            company = prompt("Company")
            email   = prompt("Email")
            add_customer(name, company, email)

        elif choice == "2":
            name  = prompt("Customer name")
            print(f"  Stages: {', '.join(STAGES)}")
            stage = prompt("New stage")
            update_stage(name, stage)

        elif choice == "3":
            name = prompt("Customer name")
            note = prompt("Note")
            add_note(name, note)

        elif choice == "4":
            list_customers()

        elif choice == "5":
            name = prompt("Customer name")
            show_customer(name)

        elif choice == "6":
            print(f"  Stages: {', '.join(STAGES)}")
            stage = prompt("Filter by stage")
            list_customers(filter_stage=stage)

        elif choice == "7":
            show_summary()

        elif choice == "8":
            fname = prompt("Filename (default: onboarding_report.csv)")
            export_csv(fname if fname else "onboarding_report.csv")

        elif choice == "0":
            audit("SESSION: Pathfinder exited cleanly.")
            print("\n  Goodbye!\n")
            break

        else:
            print("  ✗  Invalid option. Try again.")

if __name__ == "__main__":
    main()
