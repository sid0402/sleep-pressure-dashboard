from flask import Flask, render_template, request, session, redirect, url_for
import psycopg2
import os
import fhir_apis
import helper
import numpy as np
import json
import pickle
import torch
from sleep_posture.CNN import CNN  # Import your model class


app = Flask(__name__)
app.secret_key = 'super_secret_key'  # use secure method in production

# Database config
DB_CONFIG = {
    'dbname': 'sleep-posture-dashboard',
    'user': 'postgres',
    'password': 'shishir',
    'host': 'localhost',
    'port': '5432'
}

model = CNN()  # Create model instance
model.load_state_dict(torch.load("model.pth"))  # Load weights
model.eval()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT nurse_id, unit, wing FROM nurses WHERE email = %s AND password = %s", (email, password))
        nurse = cur.fetchone()
        conn.close()

        if nurse:
            session['nurse_id'] = nurse[0]
            session['unit'] = nurse[1]
            session['wing'] = nurse[2]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid login."

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'nurse_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', 
                          unit=session['unit'], 
                          wing=session['wing'])

@app.route('/api/patients')
def api_patients():
    if 'nurse_id' not in session:
        return {"error": "Not logged in"}, 401

    # Get time from query params (default to 1:00:00 if not provided)
    hours = int(request.args.get('hours', 1))
    minutes = int(request.args.get('minutes', 0))
    seconds = int(request.args.get('seconds', 0))

    # Get patients for this nurse's unit and wing
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT patient_id FROM patient_units WHERE unit = %s AND wing = %s",
        (session['unit'], session['wing'])
    )
    patient_ids = [row[0] for row in cur.fetchall()]
    conn.close()

    patients = []
    for patient_id in patient_ids:
        patient_data = fhir_apis.get_patient(patient_id)
        if patient_data:
            sleep_status = calculate_sleep_status(patient_id, hours, minutes, seconds, include_frame=True)
            frame = sleep_status['frame']
            frame = torch.tensor(frame).unsqueeze(0).to(device)
            with torch.no_grad():
                output = model(frame)
                _, predicted = torch.max(output.data, 1)
                posture = predicted.item()
                posture_map = {0: 'supine', 1: 'left', 2: 'right'}
                posture_text = posture_map.get(posture, 'unknown')
                sleep_status['posture'] = posture_text
            
            patients.append({
                'id': patient_id,
                'name': f"{patient_data.get('name', [{}])[0].get('given', [''])[0]} {patient_data.get('name', [{}])[0].get('family', '')}",
                'status': sleep_status['status'],
                'posture': sleep_status['posture'],
                'pressure_risk': sleep_status['pressure_risk'],
                'alert_level': sleep_status['alert_level'],
                'frame': sleep_status['frame']
            })

    return {"patients": patients}

@app.route('/patient/<patient_id>')
def patient_detail(patient_id):
    if 'nurse_id' not in session:
        return redirect(url_for('login'))
    
    # Check if patient is in nurse's unit/wing
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM patient_units WHERE patient_id = %s AND unit = %s AND wing = %s",
        (patient_id, session['unit'], session['wing'])
    )
    if not cur.fetchone():
        conn.close()
        return "Patient not found in your unit/wing", 404
    
    conn.close()
    return render_template('patient_detail.html', patient_id=patient_id)


@app.route('/api/patient/<patient_id>')
def api_patient_detail(patient_id):
    if 'nurse_id' not in session:
        return {"error": "Not logged in"}, 401
    
    # Check if patient is in nurse's unit/wing
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM patient_units WHERE patient_id = %s AND unit = %s AND wing = %s",
        (patient_id, session['unit'], session['wing'])
    )
    if not cur.fetchone():
        conn.close()
        return {"error": "Patient not found in your unit/wing"}, 404
    
    # Get patient data
    patient_data = fhir_apis.get_patient(patient_id)
    #patient_conditions = fhir_apis.get_patient_conditions(patient_id)
    patient_conditions = fhir_apis.get_condition(168)
    # Get detailed sleep data
    sleep_status = calculate_sleep_status(patient_id, detailed=True)
    
    conn.close()
    return {
        "patient": patient_data,
        "conditions": patient_conditions,
        "sleep_data": sleep_status
    }

def calculate_sleep_status(patient_id, hours=1, minutes=0, detailed=False, include_frame=False):
    """Calculate the sleep status, posture, and risks for a patient"""
    # Map FHIR patient ID to local dataset subject ID
    patient_map = {
        'patient-1': "S1",
        'patient-2': "S2",
        'patient-3': "S3",
        'patient-4': "S4",
        'patient-5': "S5",
        'patient-6': "S6",
        'patient-7': "S7",
        'patient-8': "S8",
        'patient-9': "S9",
        'patient-10': "S10",
        'patient-11': "S11",
        'patient-12': "S12",
        'patient-13': "S13",
    }
    
    if patient_id not in patient_map:
        return {
            'status': 'unknown',
            'posture': 'unknown',
            'pressure_risk': 'unknown',
            'alert_level': 'none',
            'frame': None
        }
    
    subject_id = patient_map[patient_id]

    # Get the data for this time point
    data, labels = helper.cycled_dataset[subject_id]
    current_index = helper.safe_time_to_index(hours, minutes, 0, data)
    
    # Get current pressure data and posture
    current_frame = data[current_index].reshape(64, 32).numpy()
    current_posture = int(labels[current_index].item())
    
    # Map posture number to text
    posture_map = {0: 'supine', 1: 'left', 2: 'right'}
    posture_text = posture_map.get(current_posture, 'unknown')
    
    # Calculate pressure risks
    # For simplicity, simulate duration of pressure at this point
    # In a real application, you'd track this over time
    num_rows, num_cols = 8, 4
    pressure_durations_all = helper.get_pressure_durations()
    subject_idx = int(patient_id.split('-')[1])-1

    durations = pressure_durations_all[subject_idx]
    durations = helper.update_pressure_durations(
            durations, current_posture, current_frame)
    pressure_durations_all[subject_idx] = durations

    pickle.dump(pressure_durations_all, open("pressure_durations.pkl", "wb"))
    
    # Check for pressure risk
    max_duration = np.max(pressure_durations_all[subject_idx])
    if max_duration > 25:  # High risk if pressure in one spot for >25 consecutive frames
        pressure_risk = 'high'
        alert_level = 'high'
    elif max_duration > 15:
        pressure_risk = 'medium'
        alert_level = 'medium'
    else:
        pressure_risk = 'low'
        alert_level = 'none'
    
    patient_id = 159

    conditions = fhir_apis.get_condition(patient_id)
    has_existing_ulcer = False
    if has_existing_ulcer and pressure_risk != 'low':
        alert_level = 'high'  # Escalate alert for patients with existing ulcers
    
    # If this is a detailed request, include more information
    result = {
        'status': 'sleeping',
        'posture': posture_text,
        'pressure_risk': pressure_risk,
        'alert_level': alert_level,
        'frame': current_frame.tolist() if (detailed or include_frame) else None,
        'pressure_durations': pressure_durations_all[subject_idx].tolist() if detailed else None,
    }
    
    return result


if __name__ == '__main__':
    app.run(debug=True)