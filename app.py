from flask import Flask, render_template, request, session, redirect, url_for, flash
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
import psycopg2

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

@app.route('/login', methods=['GET', 'POST'])
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
            session['email'] = email
            session['unit'] = nurse[1]
            session['wing'] = nurse[2]
            return redirect(url_for('dashboard'))

            helper.log_event(user_id=nurse[0],
                      action="login",
                      resource_type="User",
                      resource_id=str(nurse[0]),
                      detail=f"User {email} logged in successfully")
        else:
            flash("Invalid login credentials", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/select-unit')
def select_unit():
    if 'nurse_id' not in session:
        return redirect(url_for('login'))

    # Fetch the units this nurse has access to from the nurses table
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT unit FROM nurses WHERE nurse_id = %s",
        (session['nurse_id'],)
    )
    accessible_units = [row[0] for row in cur.fetchall()]
    conn.close()
    
    if not accessible_units:
        flash("You do not have access to any units", "danger")
        return redirect(url_for('login'))
    
    return render_template('select_unit.html', units=accessible_units)

@app.route('/select-wing/<unit>')
def select_wing(unit):
    if 'nurse_id' not in session:
        return redirect(url_for('login'))

    # Check if the nurse has access to this unit
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM nurses WHERE nurse_id = %s AND unit = %s",
        (session['nurse_id'], unit)
    )
    has_access = cur.fetchone()[0] > 0
    
    if not has_access:
        conn.close()
        flash("You do not have access to this unit", "danger")
        return redirect(url_for('select_unit'))
    
    # Get wings the nurse has access to in this unit
    cur.execute(
        "SELECT wing FROM nurses WHERE nurse_id = %s AND unit = %s",
        (session['nurse_id'], unit)
    )
    accessible_wings = [row[0] for row in cur.fetchall()]
    conn.close()
    
    if not accessible_wings:
        flash("You do not have access to any wings in this unit", "danger")
        return redirect(url_for('select_unit'))
    
    session['unit'] = unit
    return render_template('select_wing.html', unit=unit, wings=accessible_wings)
    
@app.route('/dashboard')
def dashboard():
    if 'nurse_id' not in session:
        return redirect(url_for('login'))
    
    # Make sure unit and wing are in session
    if 'unit' not in session or 'wing' not in session:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', 
                          unit=session['unit'], 
                          wing=session['wing'])

@app.route('/set-wing/<wing>')
def set_wing(wing):
    if 'nurse_id' not in session:
        return redirect(url_for('login'))
    
    if 'unit' not in session:
        return redirect(url_for('select_unit'))
    
    # Check if the nurse has access to this wing in this unit
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM nurses WHERE nurse_id = %s AND unit = %s AND wing = %s",
        (session['nurse_id'], session['unit'], wing)
    )
    has_access = cur.fetchone()[0] > 0
    conn.close()
    
    if not has_access:
        flash("You do not have access to this wing", "danger")
        return redirect(url_for('select_wing', unit=session['unit']))
    
    session['wing'] = wing
    return redirect(url_for('dashboard'))

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

    helper.log_event(user_id=session['nurse_id'],
                      action="read",
                      resource_type="Patient",
                      resource_id=patient_id,
                      detail=f"Nurse {session['nurse_id']} viewed patient {patient_id}")

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
    sleep_status = calculate_sleep_status(patient_id, hours, minutes, seconds, detailed=True)

    return {
        "patient": patient_data,
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
    durations = helper.update_pressure_durations(durations, posture, current_frame, last_posture)
    pressure_durations_all[subject_idx] = durations
    pickle.dump(pressure_durations_all, open("pressure_durations.pkl", "wb"))

    positions = helper.get_patient_positions(patient_id)
    positions.append(posture)
    helper.save_patient_positions(patient_id, positions)

    sleep_position_change = helper.get_sleep_position_change(patient_id)
    if posture != last_posture:
        sleep_position_change += 1
    helper.save_sleep_position_change(patient_id, sleep_position_change)

    max_duration = np.max(durations)
    if max_duration > 1:
        pressure_risk, alert_level = 'high', 'high'
    elif max_duration > 1:
        pressure_risk, alert_level = 'medium', 'medium'
    else:
        pressure_risk, alert_level = 'low', 'none'

    conditions = fhir_apis.get_patient_conditions(patient_id)
    # Instead of just checking for existence, let's capture the actual ulcer descriptions
    ulcer_descriptions = [
        coding.get('display', '')
        for entry in conditions.get("entry", [])
        for coding in entry.get('resource', {}).get('code', {}).get('coding', [])
        if 'ulcer' in coding.get('display', '').lower()
    ]
    
    has_existing_ulcer = len(ulcer_descriptions) > 0
    
    # You can access the specific descriptions if needed
    ulcer_text = '; '.join(ulcer_descriptions) if ulcer_descriptions else "None"

    if has_existing_ulcer and pressure_risk != 'low':
        alert_level = 'high'
    
    if alert_level == 'high':
        resp = requests.post('https://textbelt.com/text', {
            'phone': '4709977699',
            'message': 'Patient ' + patient_id + ' is sleeping with high pressure risk. Please check the patient.',
            'key': textbelt_key,
        })

        helper.log_event(user_id=session['nurse_id'],
                    action="send_alert",
                    resource_type="Patient",
                    resource_id=patient_id,
                    detail="Textbelt alert triggered for high pressure risk")

    additional_notes = f"Position changes: {sleep_position_change}. "
    if has_existing_ulcer:
        additional_notes += f"Patient has existing ulcers: {ulcer_text}. "
    if alert_level == 'high':
        additional_notes += "Alert sent to nursing staff."

    # Create the FHIR observation for this sleep position reading
    observation_result = fhir_apis.create_sleep_position_observation(
        patient_id=patient_id,
        position=posture_text,
        pressure_risk=pressure_risk,
        additional_notes=additional_notes
    )
    
    # We can add the observation ID to our result if we want to reference it
    observation_id = observation_result.get('id') if observation_result else None

    result = {
        'status': 'sleeping',
        'posture': posture_text,
        'pressure_risk': pressure_risk,
        'alert_level': alert_level,
        'frame': current_frame.tolist() if (detailed or include_frame) else None,
        'pressure_durations': durations.tolist() if detailed else None,
        'durations': durations.tolist(),
        'confidence': confidence,
        'sleep_position_change': sleep_position_change,
        'ulcer_text': ulcer_text,
        'positions': positions
    }

    return result

@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)


'''
1QUECTN36NW4MNLTVQUY7Z11

'''