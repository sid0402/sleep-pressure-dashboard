import requests
import json

FHIR_BASE = "http://localhost:8080/fhir"

# --- Patient APIs ---

def get_patient(patient_id):
    """Retrieve a specific patient by ID"""
    try:
        response = requests.get(f"{FHIR_BASE}/Patient/{patient_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving Patient/{patient_id}: {e}")
        return None

def get_patients(params=None):
    """Retrieve all patients with optional filters"""
    try:
        response = requests.get(f"{FHIR_BASE}/Patient", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving Patients: {e}")
        return None

# --- Observation APIs ---

def get_observation(observation_id):
    """Retrieve a specific observation by ID"""
    try:
        response = requests.get(f"{FHIR_BASE}/Observation/{observation_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving Observation/{observation_id}: {e}")
        return None

def get_observations(params=None):
    """Retrieve observations, optionally filtered by patient or code"""
    try:
        response = requests.get(f"{FHIR_BASE}/Observation", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving Observations: {e}")
        return None

def get_patient_observations(patient_id):
    """Get all observations for a specific patient"""
    return get_observations({"patient": f"Patient/{patient_id}"})


# --- Condition APIs ---

def get_condition(condition_id):
    """Retrieve a specific condition by ID"""
    try:
        response = requests.get(f"{FHIR_BASE}/Condition/{condition_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving Condition/{condition_id}: {e}")
        return None

def get_conditions(params=None):
    """Retrieve conditions, optionally filtered by patient or code"""
    try:
        response = requests.get(f"{FHIR_BASE}/Condition", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving Conditions: {e}")
        return None

def get_patient_conditions(patient_id):
    """Get all conditions for a specific patient"""
    return get_conditions({"patient": f"Patient/{patient_id}"})


# --- Debug Example ---

if __name__ == "__main__":
    # List all patients
    all_patients = get_patients()
    if all_patients:
        entries = all_patients.get("entry", [])
        print(f"Found {len(entries)} patients.")

        # Fetch resources for first patient
        if entries:
            pid = entries[0]["resource"]["id"]
            print(f"Patient ID: {pid}")

            print("\n📌 Observations:")
            obs = get_patient_observations(pid)
            print(json.dumps(obs, indent=2) if obs else "None")

            print("\n📌 Conditions:")
            cond = get_patient_conditions(pid)
            print(json.dumps(cond, indent=2) if cond else "None")

def create_sleep_position_observation(patient_id, position, pressure_risk=None, additional_notes=None):
    """
    Create an observation for a patient's sleep position
    
    Args:
        patient_id (str): FHIR patient ID
        position (str): Patient's sleep position (e.g. 'supine', 'prone', 'left lateral', 'right lateral')
        pressure_risk (str, optional): Risk level ('low', 'medium', 'high')
        additional_notes (str, optional): Any additional notes about the observation
        
    Returns:
        dict: Created observation resource or None if creation failed
    """
    from datetime import datetime
    import uuid
    
    # Generate unique ID for this observation
    observation_id = f"sleep-position-{uuid.uuid4()}"
    
    # Create timestamp for the observation
    timestamp = datetime.now().isoformat()
    
    # Build the observation resource
    observation = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "32739-0",  # "Body position" LOINC code
                    "display": "Sleep Position"
                }
            ],
            "text": "Patient Sleep Position"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": timestamp,
        "issued": timestamp,
        "valueString": position
    }
    
    # Add pressure risk if provided
    if pressure_risk:
        observation["component"] = [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationValue",
                            "code": "RISK",
                            "display": "Risk"
                        }
                    ],
                    "text": "Pressure Ulcer Risk"
                },
                "valueString": pressure_risk
            }
        ]
    
    # Add additional notes if provided
    if additional_notes:
        if "component" not in observation:
            observation["component"] = []
        
        observation["component"].append({
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "48767-8",
                        "display": "Annotation comment"
                    }
                ],
                "text": "Additional Notes"
            },
            "valueString": additional_notes
        })
    
    try:
        # Create the observation using a POST request
        response = requests.post(
            f"{FHIR_BASE}/Observation",
            headers={"Content-Type": "application/fhir+json"},
            json=observation
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating sleep position observation: {e}")
        return None
