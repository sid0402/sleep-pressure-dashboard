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

class CNN(nn.Module):
  
  def __init__(self):
    super().__init__()

    ## Convolutional Layers
    #Input channels = 1, output channels = 6
    self.conv1 = torch.nn.Conv2d(1, 6, kernel_size=3, stride=1, padding=1)
    #Input channels = 6, output channels = 18
    self.conv2 = torch.nn.Conv2d(6, 18, kernel_size=3, stride=1, padding=1)

    ## Pool Layer
    self.pool = torch.nn.MaxPool2d(kernel_size=2, stride=2, padding=0)

    ## Mulit-Layer Perceptron
    # Hidden layers
    self.h1 = nn.Linear(18 * 16 * 8, 392)
    self.h2 = nn.Linear(392, 98)

    # Output layer, 3 neurons - one for each position
    self.output = nn.Linear(98, 3)

    # ReLU activation and softmax output 
    self.relu = nn.ReLU()
    self.logsoftmax = nn.LogSoftmax(dim=1)

  def forward(self, x):

    x = x.float()
    # Add a "channel dimension"
    x = x.unsqueeze(1)

    ## Computation on convolutional and pool layers:
    # Size changes from (1, 64, 32) to (6, 64, 32)
    x = F.relu(self.conv1(x))
    # Size changes from (6, 64, 32) to (6, 32, 16)
    x = self.pool(x)
    # Size changes from (6, 32, 16) to (18, 32, 16)
    x = F.relu(self.conv2(x))
    # Size changes from (18, 32, 16) to (18, 16, 8)
    x = self.pool(x)

    # Reshape data to input to the input layer of the MLP
    # Size changes from (18, 16, 8) to (1, 2304)
    x = x.view(x.shape[0], -1)
    
    ## Computation on the MLP layers:
    x = self.h1(x)
    x = self.relu(x)
    x = self.h2(x)
    x = self.relu(x)
    x = self.output(x)
    x = self.logsoftmax(x)

    return x

