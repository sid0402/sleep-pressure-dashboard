import pickle
import torch
import numpy as np
from collections import defaultdict
import os
import psycopg2
with open("cycled_dataset.pkl", "rb") as f:
    cycled_dataset = pickle.load(f)

DB_CONFIG = {
    'dbname': 'sleep-posture-dashboard',
    'user': 'postgres',
    'password': 'shishir',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def update_pressure_durations(current_durations, new_posture, new_frame, current_posture=0,
                               num_rows=8, num_cols=4, pressure_threshold=0):
    """
    Update pressure durations per region based on the new frame and posture.

    Parameters:
        current_durations (np.ndarray): shape (num_rows, num_cols), current pressure durations
        current_posture (int): previous posture
        new_posture (int): posture of the current frame
        new_frame (np.ndarray): shape (64, 32), pressure heatmap
        num_rows (int): number of vertical splits
        num_cols (int): number of horizontal splits
        pressure_threshold (float): threshold to consider a region "under pressure"

    Returns:
        new_durations (np.ndarray): updated durations (shape: num_rows x num_cols)
    """
    if new_posture != current_posture:
        # Reset durations on posture change
        return np.zeros((num_rows, num_cols), dtype=int)

    H, W = new_frame.shape
    region_h = H // num_rows
    region_w = W // num_cols

    new_durations = current_durations.astype(float).copy()


    #new_durations = np.zeros((num_rows, num_cols), dtype=int)
    for i in range(num_rows):
        for j in range(num_cols):
            region = new_frame[i*region_h:(i+1)*region_h, j*region_w:(j+1)*region_w]
            avg_pressure = np.mean(region)
            temp = avg_pressure
            new_durations[i, j] += temp
    return new_durations

def get_last_posture(patient_id):
    file_path = f"{patient_id}_posture.pkl"
    data = None
    if os.path.exists(file_path):
        data = pickle.load(open(file_path, "rb"))
    else:
        data = 0
    pickle.dump(data, open(file_path, "wb"))
    return data

def get_sleep_position_change(patient_id):
    file_path = f"{patient_id}_sleep_position_change.pkl"
    data = None
    if os.path.exists(file_path):
        data = pickle.load(open(file_path, "rb"))
    else:
        data = 0
    pickle.dump(data, open(file_path, "wb"))
    return data

def save_sleep_position_change(patient_id, sleep_position_change):
    file_path = f"{patient_id}_sleep_position_change.pkl"
    pickle.dump(sleep_position_change, open(file_path, "wb"))

def save_last_posture(patient_id, posture):
    file_path = f"{patient_id}_posture.pkl"
    pickle.dump(posture, open(file_path, "wb"))

def safe_time_to_index(hours, minutes, seconds, data_tensor, total_hours=9):
    total_samples = len(data_tensor)
    total_duration_seconds = total_hours * 3600
    elapsed_time_seconds = (hours * 3600) + (minutes * 60) + seconds
    proportion_elapsed = elapsed_time_seconds / total_duration_seconds
    index = min(round(proportion_elapsed * (total_samples - 1)), total_samples - 1)
    return index

def get_pressure_durations(num_subjects=13, num_rows=8, num_cols=4):
    file_path = "pressure_durations.pkl"

    if os.path.exists(file_path):
        pressure_durations = pickle.load(open(file_path, "rb"))
    else:
        pressure_durations = np.zeros((num_subjects, num_rows, num_cols), dtype=int)
        with open(file_path, "wb") as f:
            pickle.dump(pressure_durations, f)
    return pressure_durations

def get_patient_positions(patient_id):
    file_path = f"{patient_id}_positions.pkl"
    data = None
    if os.path.exists(file_path):
        data = pickle.load(open(file_path, "rb"))
    else:
        data = []
    pickle.dump(data, open(file_path, "wb"))
    return data

def save_patient_positions(patient_id, positions):
    file_path = f"{patient_id}_positions.pkl"
    pickle.dump(positions, open(file_path, "wb"))

def log_event(user_id, action, resource_type=None, resource_id=None, detail=None):
    """
    Write an entry to the audit_logs table.
    :param user_id: The ID of the nurse/user performing the action
    :param action: A short keyword describing the action (e.g., 'login', 'read', 'write', 'access_denied')
    :param resource_type: Type of resource being accessed/modified (e.g., 'Patient', 'Wing', 'Dashboard')
    :param resource_id: The specific resource ID or name
    :param detail: Additional text describing the event
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, detail)
        VALUES (%s, %s, %s, %s, %s);
    """, (user_id, action, resource_type, resource_id, detail))
    conn.commit()
    cur.close()
    conn.close()