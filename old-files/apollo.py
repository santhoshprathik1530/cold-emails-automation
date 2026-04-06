import requests
import csv
import sys

APOLLO_API_KEY = "l8TMBu3V3n6o8aDuENZcNA"

HEADERS = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "accept": "application/json",
    "x-api-key": APOLLO_API_KEY,
}

HR_TITLES = [
    "hr", "talent acquisition", "hiring", "recruiter",
    "recruiting", "recruitment", "resource", "sourcer", "sourcing",
]


# ── STEP 1: Search for HR people by org ID (all pages) ───────────────────────
def search_people(org_id, location="chicago"):
    print(f"\n[1/2] Searching org {org_id} in {location}...")

    all_people = []
    page = 1
    MAX_PAGES = 500

    while page <= MAX_PAGES:
        res = requests.post(
            "https://api.apollo.io/api/v1/mixed_people/api_search",
            headers=HEADERS,
            json={
                "organization_ids":     [org_id],
                "contact_email_status": ["verified"],
                "person_titles":        HR_TITLES,
                "person_locations":     [location],
                "page":                 page,
                "per_page":             100,
            }
        )

        if res.status_code != 200:
            print(f"Search error on page {page} — {res.status_code}: {res.text}")
            break

        data   = res.json()
        people = data.get("people", [])

        if not people:
            break  # no more results

        all_people.extend(people)
        print(f"  Page {page}: +{len(people)} people (total so far: {len(all_people)})")

        # Stop if this page wasn't full — means we've hit the last page
        if len(people) < 100:
            break

        page += 1

    print(f"  ✓ {len(all_people)} verified HR contacts across {page} page(s)")
    return all_people


# ── STEP 2: Enrich with bulk_match to get actual emails ───────────────────────
def enrich_people(people):
    if not people:
        return []

    print(f"\n[2/2] Enriching {len(people)} contacts to get emails...")

    # bulk_match accepts up to 10 records per call — chunk to avoid rejections
    all_matches = []
    for i in range(0, len(people), 10):
        chunk = people[i:i+10]
        res = requests.post(
            "https://api.apollo.io/api/v1/people/bulk_match",
            headers=HEADERS,
            json={"details": [{"id": p["id"]} for p in chunk]}
        )
        if res.status_code != 200:
            print(f"Enrichment error (chunk {i//10 + 1}): {res.status_code}: {res.text}")
            continue
        all_matches.extend(res.json().get("matches", []))

    print(f"  Enriched {len(all_matches)} contacts")
    return all_matches



# ── BUILD CONTACTS ─────────────────────────────────────────────────────────────
def build_contacts(matches, org_id):
    contacts = []
    for p in matches:
        city    = p.get("city") or ""
        state   = p.get("state") or ""
        country = p.get("country") or ""
        location_str = ", ".join(filter(None, [city, state, country]))

        first = (p.get("first_name") or "").lower().title()
        last  = (p.get("last_name")  or "").lower().title()
        name  = (p.get("name") or f"{first} {last}").strip().lower().title()

        org = p.get("organization") or {}

        contacts.append({
            "name":         name,
            "first_name":   first,
            "last_name":    last,
            "title":        p.get("title", ""),
            "email":        p.get("email", ""),
            "email_status": p.get("email_status", ""),
            "company":      org.get("name", ""),
            "org_id":       org_id,
            "location":     location_str,
            "linkedin_url": p.get("linkedin_url", ""),
        })
    return contacts


# ── SAVE CSV ──────────────────────────────────────────────────────────────────
def save_to_csv(contacts, filename="hr_contacts.csv"):
    if not contacts:
        print("\nNo contacts to save.")
        return

    fields = ["name", "first_name", "last_name", "title", "email",
              "email_status", "company", "org_id", "location", "linkedin_url"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(contacts)

    print(f"\n✅ Saved {len(contacts)} contacts to {filename}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    org_ids = sys.argv[1:] if len(sys.argv) > 1 else []

    if not org_ids:
        raw = input("Enter Apollo org ID(s) separated by comma: ")
        org_ids = [o.strip() for o in raw.split(",")]

    all_contacts = []

    for org_id in org_ids:
        people   = search_people(org_id)
        matches  = enrich_people(people)
        contacts = build_contacts(matches, org_id)
        all_contacts.extend(contacts)
        print(f"  → {len(contacts)} contacts ready for org {org_id}")

    save_to_csv(all_contacts)
    print(f"\nTotal: {len(all_contacts)} contacts across {len(org_ids)} orgs")
