from flask import Flask, render_template, request, session, redirect, url_for
import psycopg2
import os
import fhir_apis
import helper
import numpy as np
import json
import pickle
import torch
from sleep_posture.CNN import CNN
import torch.nn.functional as F
import requests

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Database config
DB_CONFIG = {
    'dbname': 'sleep-posture-dashboard',
    'user': 'postgres',
    'password': 'shishir',
    'host': 'localhost',
    'port': '5432'
}

model = CNN()
model.load_state_dict(torch.load("model.pth"))
model.eval()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

textbelt_key = os.environ.get('TEXTBELT_API_KEY')

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

    hours = int(request.args.get('hours', 1))
    minutes = int(request.args.get('minutes', 0))
    seconds = int(request.args.get('seconds', 0))

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
            frame_tensor = torch.tensor(frame).unsqueeze(0).to(device)

            with torch.no_grad():
                output = model(frame_tensor)
                probabilities = F.softmax(output, dim=1)         
                confidence, predicted = torch.max(probabilities, 1)
                posture = predicted.item()
                posture_map = {0: 'supine', 1: 'left', 2: 'right'}
                posture_text = posture_map.get(posture, 'unknown')
                sleep_status['posture'] = posture_text
                helper.save_last_posture(patient_id, posture)

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

@app.route('/api/patient/<patient_id>')
def api_patient_detail(patient_id):
    if 'nurse_id' not in session:
        return {"error": "Not logged in"}, 401

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM patient_units WHERE patient_id = %s AND unit = %s AND wing = %s",
        (patient_id, session['unit'], session['wing'])
    )
    if not cur.fetchone():
        conn.close()
        return {"error": "Patient not found in your unit/wing"}, 404
    conn.close()

    # Get time from query parameters (with defaults)
    hours = int(request.args.get("hours", 1))
    minutes = int(request.args.get("minutes", 0))
    seconds = int(request.args.get("seconds", 0))

    # Fetch data
    patient_data = fhir_apis.get_patient(patient_id)
    patient_conditions = fhir_apis.get_patient_conditions(patient_id)
    sleep_status = calculate_sleep_status(patient_id, hours, minutes, seconds, detailed=True)

    return {
        "patient": patient_data,
        "conditions": patient_conditions,
        "sleep_data": sleep_status
    }

def calculate_sleep_status(patient_id, hours=1, minutes=0, seconds=0, detailed=False, include_frame=False):
    patient_map = {
        'patient-1': "S1", 'patient-2': "S2", 'patient-3': "S3", 'patient-4': "S4",
        'patient-5': "S5", 'patient-6': "S6", 'patient-7': "S7", 'patient-8': "S8",
        'patient-9': "S9", 'patient-10': "S10", 'patient-11': "S11",
        'patient-12': "S12", 'patient-13': "S13",
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
    data, labels = helper.cycled_dataset[subject_id]
    current_index = helper.safe_time_to_index(hours, minutes, seconds, data)
    current_frame = data[current_index].reshape(64, 32).numpy()

    frame_tensor = torch.tensor(current_frame).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(frame_tensor)
        probabilities = F.softmax(output, dim=1)         
        confidence, predicted = torch.max(probabilities, 1)
        posture = predicted.item()
        confidence = confidence.item()
        posture_map = {0: 'supine', 1: 'left', 2: 'right'}
        posture_text = posture_map.get(posture, 'unknown')

    num_rows, num_cols = 8, 4
    pressure_durations_all = helper.get_pressure_durations()
    subject_idx = int(patient_id.split('-')[1]) - 1

    last_posture = helper.get_last_posture(patient_id)
    durations = pressure_durations_all[subject_idx]
    durations = helper.update_pressure_durations(durations, last_posture, current_frame)
    pressure_durations_all[subject_idx] = durations
    pickle.dump(pressure_durations_all, open("pressure_durations.pkl", "wb"))

    sleep_position_change = helper.get_sleep_position_change(patient_id)
    if posture != last_posture:
        sleep_position_change += 1
    helper.save_sleep_position_change(patient_id, sleep_position_change)

    max_duration = np.max(durations)
    if max_duration > 1:
        pressure_risk, alert_level = 'high', 'high'
    elif max_duration > 0.5:
        pressure_risk, alert_level = 'medium', 'medium'
    else:
        pressure_risk, alert_level = 'low', 'none'

    conditions = fhir_apis.get_patient_conditions(patient_id)
    has_existing_ulcer = any(
        'ulcer' in coding.get('display', '').lower()
        for entry in conditions.get("entry", [])
        for coding in entry.get('resource', {}).get('code', {}).get('coding', [])
    )

    if has_existing_ulcer and pressure_risk != 'low':
        alert_level = 'high'
    
    if alert_level == 'high':
        resp = requests.post('https://textbelt.com/text', {
            'phone': '4709977699',
            'message': 'Patient ' + patient_id + ' is sleeping with high pressure risk. Please check the patient.',
            'key': textbelt_key,
        })

    result = {
        'status': 'sleeping',
        'posture': posture_text,
        'pressure_risk': pressure_risk,
        'alert_level': alert_level,
        'frame': current_frame.tolist() if (detailed or include_frame) else None,
        'pressure_durations': durations.tolist() if detailed else None,
        'durations': durations.tolist(),
        'confidence': confidence,
        'sleep_position_change': sleep_position_change
    }

    return result

if __name__ == '__main__':
    app.run(debug=True)


'''
1QUECTN36NW4MNLTVQUY7Z11

'''