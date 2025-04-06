import requests
import json

FHIR_BASE = "http://localhost:8080/fhir"

# Get a patient by ID
def get_patient(patient_id):
    """Retrieve a patient by ID"""
    try:
        response = requests.get(f"{FHIR_BASE}/Patient/{patient_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving patient: {e}")
        return None

# Get all patients, with optional search parameters
def get_patients(params=None):
    """Retrieve patients with optional search parameters"""
    try:
        response = requests.get(f"{FHIR_BASE}/Patient", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving patients: {e}")
        return None

# Get an observation by ID
def get_observation(observation_id):
    """Retrieve an observation by ID"""
    try:
        response = requests.get(f"{FHIR_BASE}/Observation/{observation_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving observation: {e}")
        return None

# Get observations, with optional search parameters
def get_observations(params=None):
    """Retrieve observations with optional search parameters"""
    try:
        response = requests.get(f"{FHIR_BASE}/Observation", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving observations: {e}")
        return None

# Get a condition by ID
def get_condition(condition_id):
    """Retrieve a condition by ID"""
    try:
        response = requests.get(f"{FHIR_BASE}/Condition/{condition_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving condition: {e}")
        return None

# Get conditions, with optional search parameters
def get_conditions(params=None):
    """Retrieve conditions with optional search parameters"""
    try:
        response = requests.get(f"{FHIR_BASE}/Condition", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving conditions: {e}")
        return None

# Example usage
'''
if __name__ == "__main__":
    # Get all patients
    patients = get_patients()
    if patients:
        print(f"Found {len(patients.get('entry', []))} patients")
    
    # Get patient observations
    if patients and 'entry' in patients and len(patients['entry']) > 0:
        patient_id = patients['entry'][0]['resource']['id']
        observations = get_observations({"patient": patient_id})
        if observations:
            print(f"Found {len(observations.get('entry', []))} observations for patient {patient_id}")
    
    # Get patient conditions
    if patients and 'entry' in patients and len(patients['entry']) > 0:
        patient_id = patients['entry'][0]['resource']['id']
        conditions = get_conditions({"patient": patient_id})
        if conditions:
            print(f"Found {len(conditions.get('entry', []))} conditions for patient {patient_id}")
'''
