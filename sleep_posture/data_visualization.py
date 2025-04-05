import dataset_creation
import pickle
import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

exp_i_path = './dataset/experiment-i/'
#dataset = dataset_creation.load_exp_i(exp_i_path)

subjects_i = [file for file in os.listdir(exp_i_path) if os.path.isdir(os.path.join(exp_i_path, file))]

with open('dataset/experiment-i/dataset.pkl', 'rb') as f:
    dataset_exp_i = pickle.load(f)
    f.close()

exp_ii_air_path = './dataset/experiment-ii/'
dataset_creation.load_exp_ii(exp_ii_air_path)

with open('dataset/experiment-ii/dataset_air.pkl', 'rb') as f:
    dataset_exp_ii_air = pickle.load(f)
    f.close()

with open('dataset/experiment-ii/dataset_spo.pkl', 'rb') as f:
    dataset_exp_ii_spo = pickle.load(f)
    f.close()

'''
for subject in subjects_i:

  # read the subject
  size = dataset_exp_i[subject][0].shape[0]
  # sample
  sample = np.random.choice(range(0, size), 24, replace = False)
  # data
  data = dataset_exp_i[subject][0].numpy()
  # plots
  f, arr = plt.subplots(3, 8, figsize = (15, 8))
  f.suptitle(f'Random chosen images of subject: \'{subject}\'', y = 0.95)
  fig = 0
  for r in range(3):
      for c in range(8):
          arr[r, c].imshow(data[sample[fig]].reshape(64, 32), aspect = 'auto')
          arr[r, c].axis('off')
          fig += 1
  plt.show()
'''

mats = ['Experiment I', 'Experiment II - Air Mat', 'Experiment II - Sponge Mat']

def plot_hist(data_dict, mat):
  keys = list(data_dict.keys())
  data = data_dict[keys[0]][1].numpy()
  for x in keys[1:]:
      data = np.append(data, data_dict[x][1], axis = 0)
  fig, ax = plt.subplots()
  numbers=[x for x in range(0,3)]
  labels=map(lambda x: str(x), numbers)
  plt.xticks(numbers, labels)
  plt.xlim(-0.5,3)
  plt.hist(data, bins=np.arange(4)-0.5)
  labels = ['Supine', 'Left', 'Right']
  ax.set_xticklabels(labels)
  plt.title('Label count for: {}'.format(mat))
  plt.xlabel('Classes')
  plt.ylabel('Counts')
  plt.show()


# Activate seaborn for this visualization
sns.set()
plot_hist(dataset_exp_i, mats[0])