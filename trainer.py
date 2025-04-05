import os
import numpy as np

# PyTorch (modeling)
import torch
from torch import nn
import torch.nn.functional as F
from torch import optim
from torch.utils.data.sampler import SubsetRandomSampler
from torchvision import transforms
import torchvision.transforms.functional as TF
from torch.utils.data import random_split
from torch.utils.data import DataLoader

# Visualization
import matplotlib.pyplot as plt

from dataloader import Mat_Dataset, datasets
from CNN import CNN

torch.manual_seed(123)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = CNN()
criterion = nn.NLLLoss()
optimizer = optim.Adam(model.parameters(), lr = 0.0001)
model.to(device)

trainset_exp_i = Mat_Dataset(["Base"], ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"])

valset_exp_i = Mat_Dataset(["Base"], ["S10", "S11", "S12", "S13"])

trainloader = DataLoader(trainset_exp_i, batch_size=64, shuffle=True)
testloader = DataLoader(valset_exp_i, batch_size=64, shuffle=False)

epochs = 5
running_loss = 0

train_losses, test_losses = [], []

for epoch in range(epochs):
  for inputs, labels in trainloader:
  
    inputs, labels = inputs.to(device), labels.to(device)
  
    optimizer.zero_grad()

    logps = model.forward(inputs)
    loss = criterion(logps, labels)
    loss.backward()
    optimizer.step()

    running_loss += loss.item()

  else:
    
    test_loss = 0
    accuracy = 0
    model.eval()
    
    with torch.no_grad():
      for inputs, labels in testloader:
        inputs, labels = inputs.to(device), labels.to(device)
        logps = model.forward(inputs)
        test_loss += criterion(logps, labels)
        
        ps = torch.exp(logps)
        top_p, top_class = ps.topk(1, dim=1)
        equals = top_class == labels.view(*top_class.shape)
        accuracy += torch.mean(equals.type(torch.FloatTensor))
    
    train_losses.append(running_loss/len(trainloader))
    test_losses.append(test_loss/len(testloader))

    print(f"Epoch {epoch+1}/{epochs}.. "
          f"Train loss: {running_loss/len(trainloader):.3f}.. "
          f"Test loss: {test_loss/len(testloader):.3f}.. "
          f"Test accuracy: {accuracy/len(testloader):.3f}")
    
    running_loss = 0
    model.train()

def class_position(img, ps, label):
  ''' Function for viewing an position and it's predicted classes.
  '''
  ps = ps.data.numpy().squeeze()

  fig, (ax1, ax2) = plt.subplots(figsize=(6,9), ncols=2)
  ax1.imshow(img.resize_(1, 64, 32).numpy().squeeze())
  ax1.axis('off')
  ax1.set_title(f'Class: {label}') 
  ax2.barh(np.arange(3), ps)
  ax2.set_aspect(0.1)
  ax2.set_yticks(np.arange(3))

  ax2.set_yticklabels(['supine', 'left', 'right'], size='small');
  ax2.set_title('Class Probability')
  ax2.set_xlim(0, 1.1)

  plt.tight_layout()
  plt.show()

i = 1
for inputs, labels in testloader:
  inputs, labels = inputs.to(device), labels.to(device)
  class_position(inputs[0].unsqueeze(0).cpu(), torch.exp(model.forward(inputs[0].unsqueeze(0))).cpu(), labels[0].cpu())
  if i >= 15:
    break
  i += 1