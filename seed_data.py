"""
seed_data.py — Populate the tracker with sample customers for demo purposes.
Run this once: python seed_data.py
"""

from tracker import add_customer, update_stage, add_note

print("Seeding sample customer data...\n")

add_customer("Alice Müller", "GeoVision GmbH", "alice@geovision.de")
update_stage("Alice Müller", "training")
add_note("Alice Müller", "Completed intro session. Interested in Planet Basemaps API.")

add_customer("James Okafor", "AgriSense Ltd", "j.okafor@agrisense.io")
update_stage("James Okafor", "active")
add_note("James Okafor", "Using Planet NICFI data for crop monitoring. Very engaged.")

add_customer("Priya Sharma", "UrbanTech Solutions", "priya@urbantech.in")
add_note("Priya Sharma", "Sent welcome email. Awaiting first login.")

add_customer("Carlos Rivera", "MapWorld Inc", "c.rivera@mapworld.com")
update_stage("Carlos Rivera", "completed")
add_note("Carlos Rivera", "All onboarding steps done. Handed off to Customer Success.")

add_customer("Lin Zhao", "ClimateTrack", "lin@climatetrack.org")
update_stage("Lin Zhao", "training")
add_note("Lin Zhao", "Attended first training session. Questions about data resolution.")

print("\n✓ Sample data loaded. Run: python tracker.py")
