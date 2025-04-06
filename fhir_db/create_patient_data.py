import psycopg2
import requests
import json
from faker import Faker
import random
from datetime import datetime, timedelta

FHIR_BASE = "http://localhost:8080/fhir"
DB_CONFIG = {
    'dbname': 'sleep-posture-dashboard',
    'user': 'postgres',
    'password': 'shishir',
    'host': 'localhost',
    'port': '5432'
}

faker = Faker()

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS nurses CASCADE;")
cur.execute("DROP TABLE IF EXISTS patient_units CASCADE;")

cur.execute("""
CREATE TABLE nurses (
    nurse_id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    password TEXT NOT NULL,
    unit TEXT NOT NULL,
    wing TEXT NOT NULL
);
""")
cur.execute("""
CREATE TABLE patient_units (
    patient_id TEXT PRIMARY KEY,
    unit TEXT NOT NULL,
    wing TEXT NOT NULL
);
""")
conn.commit()

nurses = [
    ("alice@hospital.org", "1234567890", "password", "UnitA", "WingA"),
    ("bob@hospital.org", "2345678901", "password", "UnitA", "WingA"),
    ("carol@hospital.org", "3456789012", "password", "UnitA", "WingB"),
    ("dan@hospital.org", "4567890123", "password", "UnitB", "WingB"),
    ("eve@hospital.org", "5678901234", "password", "UnitB", "WingB"),
]
cur.executemany("INSERT INTO nurses (email, phone, password, unit, wing) VALUES (%s, %s, %s, %s, %s);", nurses)
conn.commit()

pressure_ulcers = {
    1: ("399269003", "Pressure ulcer of sacral region"),
    2: ("1163215007", "Pressure ulcer of right hip"),
    3: ("1163219001", "Pressure ulcer of left upper arm"),
    4: ("449835005", "Pressure ulcer of right elbow")
}

for i in range(1, 14):
    fhir_id = f"patient-{i}"
    full_name = faker.name().split()
    patient = {
        "resourceType": "Patient",
        "id": fhir_id,
        "name": [{"family": full_name[-1], "given": full_name[:-1]}],
        "gender": random.choice(["male", "female"]),
        "birthDate": f"{random.randint(1950, 2005)}-01-01"
    }

    url = f"{FHIR_BASE}/Patient/{fhir_id}"
    response = requests.put(url, headers={"Content-Type": "application/fhir+json"}, data=json.dumps(patient))

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create Patient/{fhir_id}: {response.status_code}, {response.text}")
        continue
    else:
        print(f"✅ Created Patient/{fhir_id}")

    unit, wing = ("UnitA", "WingA") if i <= 6 else ("UnitB", "WingB")

    cur.execute(
        "INSERT INTO patient_units (patient_id, unit, wing) VALUES (%s, %s, %s);",
        (fhir_id, unit, wing)
    )

    height_obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8302-2", "display": "Height"}]},
        "subject": {"reference": f"Patient/{fhir_id}"},
        "effectiveDateTime": datetime.now().isoformat(),
        "valueQuantity": {
            "value": random.randint(150, 190),
            "unit": "cm",
            "system": "http://unitsofmeasure.org",
            "code": "cm"
        }
    }
    requests.post(f"{FHIR_BASE}/Observation", headers={"Content-Type": "application/fhir+json"}, data=json.dumps(height_obs))

    weight_obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Body weight"}]},
        "subject": {"reference": f"Patient/{fhir_id}"},
        "effectiveDateTime": datetime.now().isoformat(),
        "valueQuantity": {
            "value": random.randint(50, 100),
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
            "code": "kg"
        }
    }
    requests.post(f"{FHIR_BASE}/Observation", headers={"Content-Type": "application/fhir+json"}, data=json.dumps(weight_obs))

    # Conditionally add skin condition
    if i in pressure_ulcers:
        code, display = pressure_ulcers[i]
        condition = {
            "resourceType": "Condition",
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
            },
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": code, "display": display}]
            },
            "subject": {"reference": f"Patient/{fhir_id}"},
            "onsetDateTime": (datetime.now() - timedelta(days=random.randint(1, 10))).isoformat()
        }
        res = requests.post(f"{FHIR_BASE}/Condition", headers={"Content-Type": "application/fhir+json"}, data=json.dumps(condition))
        if res.status_code not in [200, 201]:
            print(f"❌ Condition failed for {fhir_id}")
        else:
            print(f"✅ Condition '{display}' added for {fhir_id}")

conn.commit()
cur.close()
conn.close()
print("✅ Successfully created 13 patients with specific pressure ulcers and no conditions for others.")
