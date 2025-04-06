import requests

FHIR_BASE = "http://localhost:8080/fhir"

def delete_all_resources(resource_type):
    print(f"⏳ Deleting all {resource_type} resources...")
    r = requests.get(f"{FHIR_BASE}/{resource_type}?_count=1000")
    entries = r.json().get("entry", [])
    for entry in entries:
        resource_id = entry["resource"]["id"]
        del_url = f"{FHIR_BASE}/{resource_type}/{resource_id}"
        del_response = requests.delete(del_url)
        if del_response.status_code in [200, 204]:
            print(f"✅ Deleted {resource_type}/{resource_id}")
        else:
            print(f"❌ Failed to delete {resource_type}/{resource_id}: {del_response.status_code}")

# Delete in order (observations/conditions before patients due to references)
delete_all_resources("Observation")
delete_all_resources("Condition")
delete_all_resources("Patient")

print("✅ All records deleted from HAPI FHIR.")