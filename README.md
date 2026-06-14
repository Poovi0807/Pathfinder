# 🛰 Pathfinder
A command-line tool built in Python to manage and track customer onboarding progress — inspired by real workflows used in customer success and onboarding roles at geospatial data companies.

---

## What It Does

- **Add customers** with company and email info
- **Track onboarding stages**: `invited → training → active → completed`
- **Log notes and feedback** for each customer
- **View summaries** by stage with visual indicators
- **Export CSV reports** for sharing with team members
- All data stored locally in a simple JSON file — no database needed

---

## Why I Built This

This project simulates the kind of onboarding workflow coordination used in customer-facing roles at companies like Planet. It demonstrates:

- Managing structured customer data with Python
- Tracking lifecycle stages across multiple customers
- Logging qualitative feedback to identify support trends
- Generating exportable reports for team communication

---

## Project Structure

```
pathfinder/
├── tracker.py        # Main CLI application
├── seed_data.py      # Script to load sample customers for demo
├── .gitignore
└── README.md
```

---

## Getting Started

**Requirements:** Python 3.7+

No external libraries needed — uses only the Python standard library.

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/pathfinder.git
cd pathfinder
```

### 2. (Optional) Load sample data

```bash
python seed_data.py
```

### 3. Run the tracker

```bash
python tracker.py
```

---

## Menu Options

```
1. Add new customer
2. Update onboarding stage
3. Add note / feedback
4. List all customers
5. View customer details
6. Filter by stage
7. Show summary
8. Export CSV report
0. Exit
```

---

## Example: Onboarding Summary View

```
── Onboarding Summary ──────────────────────
invited      █ 1
training     ██ 2
active       ██ 2
completed    █ 1

Total: 6 customer(s)
```

---

## Example: CSV Export

| Name | Company | Email | Stage | Added On | Note Count |
|---|---|---|---|---|---|
| Alice Müller | GeoVision GmbH | alice@geovision.de | training | 2025-06-14 | 1 |
| James Okafor | AgriSense Ltd | j.okafor@agrisense.io | active | 2025-06-14 | 1 |

---

## Skills Demonstrated

- Python file I/O (`json`, `csv`, `os`)
- Functions, loops, and conditional logic
- CLI menu design and user input handling
- Data filtering and summary reporting
- Real-world workflow modelling

---

## Future Ideas

- Add email reminder automation
- Connect to a Google Sheet via API
- Build a simple web UI with Flask
- Add time-in-stage tracking to flag stalled customers
