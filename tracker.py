"""
Pathfinder
A CLI tool to manage and track customer onboarding progress.
"""

import json
import csv
import os
from datetime import datetime

DATA_FILE = "customers.json"

STAGES = ["invited", "training", "active", "completed"]


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_data():
    """Load customer data from JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(customers):
    """Save customer data to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(customers, f, indent=2)


def find_customer(customers, name):
    """Find a customer by name (case-insensitive)."""
    for c in customers:
        if c["name"].lower() == name.lower():
            return c
    return None


# ── Core functions ────────────────────────────────────────────────────────────

def add_customer(name, company, email):
    """Add a new customer to the tracker."""
    customers = load_data()

    if find_customer(customers, name):
        print(f"  ⚠  Customer '{name}' already exists.")
        return

    customer = {
        "name": name,
        "company": company,
        "email": email,
        "stage": "invited",
        "added_on": datetime.now().strftime("%Y-%m-%d"),
        "notes": []
    }
    customers.append(customer)
    save_data(customers)
    print(f"  ✓  Added '{name}' from {company} — stage: invited")


def update_stage(name, new_stage):
    """Update the onboarding stage for a customer."""
    if new_stage not in STAGES:
        print(f"  ✗  Invalid stage. Choose from: {', '.join(STAGES)}")
        return

    customers = load_data()
    customer = find_customer(customers, name)

    if not customer:
        print(f"  ✗  Customer '{name}' not found.")
        return

    old_stage = customer["stage"]
    customer["stage"] = new_stage
    save_data(customers)
    print(f"  ✓  '{name}' updated: {old_stage} → {new_stage}")


def add_note(name, note_text):
    """Add a feedback note to a customer's record."""
    customers = load_data()
    customer = find_customer(customers, name)

    if not customer:
        print(f"  ✗  Customer '{name}' not found.")
        return

    note = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "note": note_text
    }
    customer["notes"].append(note)
    save_data(customers)
    print(f"  ✓  Note added for '{name}'")


def list_customers(filter_stage=None):
    """List all customers, optionally filtered by stage."""
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
    """Show detailed info for a single customer."""
    customers = load_data()
    customer = find_customer(customers, name)

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
    customers = load_data()

    if not customers:
        print("  No data to export.")
        return

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Company", "Email", "Stage", "Added On", "Note Count"])
        for c in customers:
            writer.writerow([
                c["name"],
                c["company"],
                c["email"],
                c["stage"],
                c["added_on"],
                len(c["notes"])
            ])

    print(f"  ✓  Report exported to '{filename}'")


def show_summary():
    """Show a summary count by onboarding stage."""
    customers = load_data()

    if not customers:
        print("  No customers yet.")
        return

    print("\n  ── Onboarding Summary ──────────────────────")
    for stage in STAGES:
        count = sum(1 for c in customers if c["stage"] == stage)
        bar = "█" * count
        print(f"  {stage:<12} {bar} {count}")
    print(f"\n  Total: {len(customers)} customer(s)\n")


# ── Menu ──────────────────────────────────────────────────────────────────────

def print_menu():
    print("""
  ╔══════════════════════════════════════╗
  ║     🛰  PathFinder                   ║
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


def main():
    while True:
        print_menu()
        choice = input("  Choose an option: ").strip()

        if choice == "1":
            name = input("  Customer name: ").strip()
            company = input("  Company: ").strip()
            email = input("  Email: ").strip()
            add_customer(name, company, email)

        elif choice == "2":
            name = input("  Customer name: ").strip()
            print(f"  Stages: {', '.join(STAGES)}")
            stage = input("  New stage: ").strip()
            update_stage(name, stage)

        elif choice == "3":
            name = input("  Customer name: ").strip()
            note = input("  Note: ").strip()
            add_note(name, note)

        elif choice == "4":
            list_customers()

        elif choice == "5":
            name = input("  Customer name: ").strip()
            show_customer(name)

        elif choice == "6":
            print(f"  Stages: {', '.join(STAGES)}")
            stage = input("  Filter by stage: ").strip()
            list_customers(filter_stage=stage)

        elif choice == "7":
            show_summary()

        elif choice == "8":
            export_csv()

        elif choice == "0":
            print("\n  Goodbye!\n")
            break

        else:
            print("  ✗  Invalid option. Try again.")


if __name__ == "__main__":
    main()
