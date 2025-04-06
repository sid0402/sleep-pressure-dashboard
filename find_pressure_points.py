import torch
import numpy as np
from collections import defaultdict

import numpy as np

def update_pressure_durations(current_durations, current_posture, new_posture, new_frame,
                               num_rows=8, num_cols=4, pressure_threshold=125):
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

    new_durations = current_durations.copy()

    for i in range(num_rows):
        for j in range(num_cols):
            region = new_frame[i*region_h:(i+1)*region_h, j*region_w:(j+1)*region_w]
            avg_pressure = np.mean(region)

            if avg_pressure > pressure_threshold:
                new_durations[i, j] += 1
            else:
                new_durations[i, j] = 0

    return new_durations

