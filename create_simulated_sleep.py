import pickle
from collections import Counter
import torch
import numpy as np
import random
import matplotlib.pyplot as plt

patient_map = {
    'patient-1':"S1",
    'patient-2':"S2",
    'patient-3':"S3",
    'patient-4':"S4",
    'patient-5':"S5",
    'patient-6':"S6",
    'patient-7':"S7",
    'patient-8':"S8",
    'patient-9':"S9",
    'patient-10':"S10",
    'patient-11':"S11",
    'patient-12':"S12",
    'patient-13':"S13",
}

with open("dataset.pkl", "rb") as f:
    data = pickle.load(f)

label_map = {0: 'supine', 1: 'left', 2: 'right'}

CYCLE_PATTERN = [0, 1, 0, 2, 0]


def reconstruct_with_cycles(dataset, min_cycles=3, max_cycles=10, min_block=3, max_block=10):
    CYCLE_PATTERN = [0, 1, 0, 2, 0]  # supine, left, supine, right, supine
    structured_dataset = {}

    for subject, (data, labels) in dataset.items():
        total_samples = len(labels)
        
        # Prepare index pools for each posture
        index_pool = {0: [], 1: [], 2: []}
        for i, label in enumerate(labels.tolist()):
            index_pool[label].append(i)
        
        # Shuffle each posture's indices
        for indices in index_pool.values():
            random.shuffle(indices)

        new_labels, new_data = [], []
        samples_used = 0
        
        # Determine number of cycles
        num_cycles = random.randint(min_cycles, max_cycles)
        
        # Build initial cycles
        cycle_idx = 0
        while cycle_idx < num_cycles and samples_used < total_samples:
            for posture in CYCLE_PATTERN:
                block_len = random.randint(min_block, max_block)
                available_samples = len(index_pool[posture])
                samples_needed = min(block_len, available_samples, total_samples - samples_used)
                
                if samples_needed == 0:
                    continue  # skip if no data available for this posture

                selected_indices = index_pool[posture][:samples_needed]
                index_pool[posture] = index_pool[posture][samples_needed:]

                new_labels.extend([posture] * samples_needed)
                new_data.extend([data[idx].unsqueeze(0) for idx in selected_indices])

                samples_used += samples_needed

                if samples_used >= total_samples:
                    break
            cycle_idx += 1

        # After cycles, fill remaining samples with a fixed sleeping posture
        remaining_samples = total_samples - samples_used
        if remaining_samples > 0:
            # Pick posture with most remaining samples
            fixed_posture = max(index_pool.keys(), key=lambda p: len(index_pool[p]))
            available_indices = index_pool[fixed_posture]
            
            # In case insufficient data, refill indices from original pool
            if len(available_indices) < remaining_samples:
                # refill indices from all original indices
                available_indices = [
                    i for i, lbl in enumerate(labels.tolist()) if lbl == fixed_posture
                ]
                random.shuffle(available_indices)
            
            # Ensure enough indices
            #assert len(available_indices) >= remaining_samples, f"Not enough data to fill remaining for {subject}"

            selected_indices = available_indices[:remaining_samples]
            new_labels.extend([fixed_posture] * remaining_samples)
            new_data.extend([data[idx].unsqueeze(0) for idx in selected_indices])

        # Final verification
        #assert len(new_labels) == total_samples, f"Final length mismatch for {subject}"

        new_data_tensor = torch.cat(new_data, dim=0)
        new_labels_tensor = torch.tensor(new_labels)

        structured_dataset[subject] = (new_data_tensor, new_labels_tensor)

    return structured_dataset

'''
cycled_dataset = reconstruct_with_cycles(data)

with open("cycled_dataset.pkl", "wb") as f:
    pickle.dump(cycled_dataset, f)
'''

with open("cycled_dataset.pkl", "rb") as f:
    cycled_dataset = pickle.load(f)

def plot_posture_sequence(labels, subject):
    plt.figure(figsize=(12, 2))
    plt.title(f"Posture sequence for {subject}")
    plt.plot(labels.tolist(), drawstyle='steps-post')
    plt.yticks([0, 1, 2], ['supine', 'left', 'right'])
    plt.xlabel("Sample Index")
    plt.ylabel("Posture")
    plt.grid(True)
    plt.show()


def safe_time_to_index(hours, minutes, seconds, total_hours, data_tensor):
    total_samples = len(data_tensor)
    total_duration_seconds = total_hours * 3600
    elapsed_time_seconds = (hours * 3600) + (minutes * 60) + seconds
    proportion_elapsed = elapsed_time_seconds / total_duration_seconds
    index = min(round(proportion_elapsed * (total_samples - 1)), total_samples - 1)
    return index


total_hours = 9

for i in patient_map.values():
    total_samples = len(cycled_dataset[i][1])
    print(f"{i}: {total_samples}")

subject = 'S1'
total_hours = 9
hours, minutes, seconds = 10, 0, 0

data_S1, labels_S1 = cycled_dataset[subject]

index_S1 = safe_time_to_index(hours, minutes, seconds, total_hours, data_S1)

print(f"Sample index at {hours}h {minutes}m {seconds}s: {index_S1}")

data_S1, labels_S1 = cycled_dataset['S1']
data_point = data_S1[index_S1]
label_point = labels_S1[index_S1]

print(data_point.shape)

print(f"Posture at this time: {label_point.item()} (0=supine, 1=left, 2=right)")

#fig = plt.imshow(data_point.squeeze().numpy())
#plt.colorbar()
#plt.show()
