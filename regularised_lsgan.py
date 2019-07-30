# -*- coding: utf-8 -*-
"""VLong Lin LS GAN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ga-F8JI0C3q57r4sCsUk8ILjgTNE_TCz
"""

!nvidia-smi

import random
import torch
from pathlib import Path
import numpy as np

import torch.nn.parallel
import torch.backends.cudnn as cudnn

seed = 123
random.seed(seed)
torch.cuda.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.manual_seed(seed)
np.random.seed(seed)
print("My seed:", seed)

DATA_PATH = Path('./data')
PATH = DATA_PATH / 'celeba'
PATH.mkdir(parents=True, exist_ok=True)

# Number of worker threads
workers = 2 # 2 cores available in colab

# Batch size
b_size = 128

# Spatial size of the training images. Resize to this size
image_size = 64

# Number of channels (Here it's 3 since RGB images)
nc = 3

# Size of latent vector
nz = 100

# Size of feature maps in generator
ngf = 64

# Size of feature maps in discriminator
ndf = 64

# Number of training epocs
num_epochs = 5

# Number of GPUs available. Use 0 for CPU mode.
ngpu = 1

!wget https://s3-us-west-1.amazonaws.com/udacity-dlnfd/datasets/celeba.zip

from google.colab import drive
drive.mount('/content/drive')

!cp ./celeba.zip ./data/celeba

!unzip ./data/celeba/celeba.zip -d {PATH}

!ls {PATH/'img_align_celeba'} | wc -l

"""##Creating the dataset"""

from torch.utils.data import DataLoader
import torchvision.datasets as dset
import torchvision.transforms as transforms

dataset = dset.ImageFolder(root=PATH,
                           transform=transforms.Compose([
                               transforms.Resize(image_size),
                               transforms.CenterCrop(image_size),
                               transforms.ToTensor(),
                               transforms.Normalize((.5,.5,.5), (.5,.5,.5)),
                           ]))
  
dataloader = DataLoader(dataset, batch_size=b_size, 
                        shuffle=True, num_workers=workers)

# Important! The following line sets the device.
device = torch.device("cuda:0" if (torch.cuda.is_available() and ngpu > 0) else "cpu")

import matplotlib.pyplot as plt
import numpy as np
import torchvision.utils as vision_utils

real_batch = next(iter(dataloader))
plt.figure(figsize=(8,8))
plt.axis("off")
plt.title("Training Images")
plt.imshow(np.transpose(vision_utils.make_grid(real_batch[0].to(device)[:64], padding=2, normalize=True).cpu(),(1,2,0)))

import torch.nn as nn

# Will be called by the Generator and Discriminator networks
def weights_init(m):
  classname = m.__class__.__name__ # Nice trick!
  if classname.find('Conv') != -1:
    nn.init.normal_(m.weight.data, 0., .02)
  elif classname.find('BatchNorm') != -1:
    nn.init.normal_(m.weight.data, 1., .02)
    nn.init.constant_(m.bias.data, 0)

class Generator(nn.Module):
  def __init__(self, ngpu):
    super(Generator, self).__init__()
    self.ngpu = ngpu
    self.main = nn.Sequential(
      nn.ConvTranspose2d(nz, ngf * 8, 4, 1, 0, bias=False),
      nn.BatchNorm2d(ngf * 8),
      nn.ReLU(True),
       
      nn.ConvTranspose2d(ngf * 8, ngf * 4, 4, 2, 1, bias=False),
      nn.BatchNorm2d(ngf * 4),
      nn.ReLU(True),
        
      nn.ConvTranspose2d(ngf * 4, ngf * 2, 4, 2, 1, bias=False),
      nn.BatchNorm2d(ngf * 2),
      nn.ReLU(True),
      
      nn.ConvTranspose2d(ngf * 2, ngf, 4, 2, 1, bias=False),
      nn.BatchNorm2d(ngf),
      nn.ReLU(True),
        
      nn.ConvTranspose2d(ngf, nc, 4, 2, 1, bias=False),
      nn.Tanh()
      # state size. (nc) x 64 x 64 
    )
    
  def forward(self, input):
    return self.main(input)

# Create the generator
random.seed(seed)
torch.cuda.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.manual_seed(seed)
np.random.seed(seed)
netG = Generator(ngpu).to(device)

# In multi-gpu : Important!
if (device.type == 'cuda') and (ngpu > 1):
  netG = nn.DataParallel(netG, list(range(ngpu)))

netG.load_state_dict(torch.load('drive/My Drive/netG-vxlls-95000.pth'))
netG.train()

# Apply the weights_init function to randomly initialize all weights
#  to mean=0, stdev=0.2.
random.seed(seed)
torch.cuda.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.manual_seed(seed)
np.random.seed(seed)
netG.apply(weights_init)
print(netG)

class Critic(nn.Module):
  def __init__(self, ngpu):
    super(Critic, self).__init__()
    self.ngpu = ngpu
    self.main = nn.Sequential(
      nn.Conv2d(nc, ndf, 4, 2, 1, bias=False),
      nn.LeakyReLU(0.2, inplace=True),
        
      nn.Conv2d(ndf, ndf * 2, 4, 2, 1, bias=False),
      nn.BatchNorm2d(ndf * 2),
      nn.LeakyReLU(0.2, inplace=True),
        
      nn.Conv2d(ndf * 2, ndf * 4, 4, 2, 1, bias=False),
      nn.BatchNorm2d(ndf * 4),
      nn.LeakyReLU(0.2, inplace=True),
        
      nn.Conv2d(ndf * 4, ndf * 8, 4, 2, 1, bias=False),
      nn.BatchNorm2d(ndf * 8),
      nn.LeakyReLU(0.2, inplace=True),
        
      nn.Conv2d(ndf * 8, 1, 4, 1, 0, bias=False),
    )
    
  def forward(self, input):
    return self.main(input).view(-1)

# Create the critic
random.seed(seed)
torch.cuda.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.manual_seed(seed)
np.random.seed(seed)
netC = Critic(ngpu).to(device)

# In multi-gpu : Important!
if (device.type == 'cuda') and (ngpu > 1):
  netC = nn.DataParallel(netG, list(range(ngpu)))

netC.load_state_dict(torch.load('drive/My Drive/netC-vxlls-95000.pth'))
netC.train()

random.seed(seed)
torch.cuda.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.manual_seed(seed)
np.random.seed(seed)
netC.apply(weights_init)
print(netC)

import torch.optim as optim

# Fixed batch of latent vectors for visualizing
# The dimensions are this way because remember that when we are upscaling 
# we have 128 channels with 1x1 feature map
fixed_noise = torch.randn(64, nz, 1, 1, device=device)

real_label = 1
fake_label = 0

# Learning rate for optimizers
lr = 4e-4

optimizerC = optim.RMSprop(netC.parameters(), lr=lr)
optimizerG = optim.RMSprop(netG.parameters(), lr=lr)

def get_infinite_batches(data_loader):
  while True:
      for i, (images, _) in enumerate(data_loader):
          yield images

"""## Random Seed Checker"""

x = np.random.randn(2,2)
y = torch.randn(2, 2, 1, 1, device=device)
print(x)
print(y)

"""## Training Loop"""

from torch.autograd import Variable

b_size = 128

max_iters = 100000
weight_clip = 0.01
gen_iters = 2
crit_iters = 1

# Lists to keep track of progress
img_list = []
G_losses = []
C_losses_fake = []
C_losses_real = []
C_losses = []
diff_G_loss = []
diff_C_loss = []
# real_C_res = np.ndarray(max_iters * b_size + 1, dtype=np.float16)
# fake_C_res = np.ndarray(max_iters * b_size + 1, dtype=np.float16)

one = torch.FloatTensor([1])
mone = one * -1
one = one.cuda()
m_one = mone.cuda()

real_C_res = np.load('./drive/My Drive/exlls-real_C_res.npy')
fake_C_res = np.load('./drive/My Drive/exlls-fake_C_res.npy')
G_losses = list(np.load('./drive/My Drive/exlls-G_losses.npy'))
C_losses = list(np.load('./drive/My Drive/exlls-C_losses.npy'))
img_list = list(np.load('./drive/My Drive/exlls-img_list.npy'))
C_losses_fake = list(np.load('./drive/My Drive/exlls-C_losses_fake.npy')
C_losses_real = list(np.load('./drive/My Drive/exlls-C_losses_real.npy')

Tensor = torch.cuda.FloatTensor
target_real = Variable(Tensor(b_size).fill_(1.), requires_grad=False)
target_fake = Variable(Tensor(b_size).fill_(0.), requires_grad=False)

data = get_infinite_batches(dataloader)

"""## Regularising Factor"""

# Regularising Factor
def alpha(it, maxIters, maxAlpha):
      if(it >= 10000):
        ret = (maxAlpha / (maxIters - 10000)) * (it - 10000)
        if ret > maxAlpha:
          return maxAlpha
        else:
          return ret
      else:
        return 0.0

test = []
for i in range(200000):
  test.append(alpha(i, 100000, 0.9))

plt.figure(figsize=(20,10))
plt.title("Regularising Factor vs iterations")
plt.plot(test)
plt.xlabel("iterations")
plt.ylabel("Regularising Factor")
plt.legend()
plt.show()



"""## Random Seed Checker 2"""

x = np.random.randn(2,2)
y = torch.randn(2, 2, 1, 1, device=device)
print(x)
print(y)

import os
import shutil

for i in range(1, max_iters + 1):
  
  # Since, Critic will be updated first.
  for p in netC.parameters():
    p.requires_grad = True
    
  C_loss = 0.
  for j in range(1, crit_iters + 1):
    # Update Critic network.
      
    netC.zero_grad()
        
    # Sample data from real distribution
    real_data = next(data).cuda()
    
    # Sample data from fake distribution
    noise = torch.randn(b_size, nz, 1, 1, device=device)
    fake_data = netG(noise) 
    
    # Getting the outputs of Critic
    C_real = netC(real_data)
    C_fake = netC(fake_data.detach()) # To remove it from the graph
    
    # Finding the errors
    C_loss_real = 0.5 * ((C_real - 1.0)**2).mean().view(1) # mean along rows
    C_loss_real.backward()
    
    C_loss_fake = 0.5 * ((C_fake - 0.0 - alpha(i, max_iters, 0.5))**2).mean().view(1)
    C_loss_fake.backward()
    
    
    C_loss = C_loss_fake + C_loss_real # -V(D,G)
    optimizerC.step()
  
  G_loss = 0.    
  # Update Generator network.
  for p in netC.parameters():
     p.requires_grad = False  # to avoid computation

  for j in range(1, gen_iters + 1):
    # Update Generator network.
    netG.zero_grad()

    # Sample data from fake distribution
    noise = torch.randn(b_size, nz, 1, 1, device=device)
    fake_data = netG(noise)

    # Finding the error
    C_G_noise = netC(fake_data)
    G_loss = 0.5 * ((C_G_noise - 1.0)**2).mean().view(1)
    G_loss.backward()
    G_cost = G_loss
    optimizerG.step()   
    
  # Display Results
  if i % 50 == 0:
    print('[%d/%d]\tLoss_C: %.4f\tLoss_C_fake: %.4f\tLoss_C_real: %.4f\tLoss_G: %.4f\t alpha: %.4f'
#         % (i, max_iters, C_loss.item(), C_loss_fake.item(), C_loss_real.item(), G_loss.item(), alpha(i, max_iters, 0.5)))

  # Save Losses for plotting later
  G_losses.append(G_loss.item())
  C_losses.append(C_loss.item())  
  C_losses_fake.append(C_loss_fake.item())
  C_losses_real.append(C_loss_real.item())

  # Display images
  # Check how the generator is doing by saving G's output on fixed_noise
  if (i % 1000 == 0):
    with torch.no_grad():
       fake = netG(fixed_noise).detach().cpu()
    img_list.append(vision_utils.make_grid(fake, padding=2, normalize=True))
    plt.imshow(np.transpose(vision_utils.make_grid(img_list[-1].to(device)[:64], padding=2, normalize=True).cpu(),(1,2,0)))
    
  if i % 5000 == 0:
    torch.save(netC.state_dict(), "./netC-vxlls-{}.pth".format(i))
    torch.save(netG.state_dict(), "./netG-vxlls-{}.pth".format(i))
    shutil.copy("./netC-vxlls-{}.pth".format(i), './drive/My Drive/')
    shutil.copy("./netG-vxlls-{}.pth".format(i), './drive/My Drive/')

"""## Saving Values and Models"""

torch.save(netC.state_dict(), "./netC-vxlls-final.pth".format(i))
torch.save(netG.state_dict(), "./netG-vxlls-final.pth".format(i))
shutil.copy("./netC-vxlls-final.pth".format(i), './drive/My Drive/')
shutil.copy("./netG-vxlls-final.pth".format(i), './drive/My Drive/')

np.save('vxlls-G_losses_1.npy', np.array(G_losses))
np.save('vxlls-C_losses_1.npy', np.array(C_losses))
np.save('vxlls-C_losses_fake_1.npy', C_losses_fake)
np.save('vxlls-C_losses_real_1.npy', C_losses_real)

shutil.copy('vxlls-G_losses_1.npy', './drive/My Drive/')
shutil.copy('vxlls-C_losses_1.npy', './drive/My Drive/')
shutil.copy('vxlls-C_losses_real_1.npy', './drive/My Drive/')
shutil.copy('vxlls-C_losses_fake_1.npy', './drive/My Drive/')

for i in range(len(img_list)):
  img_list[i] = img_list[i].numpy()

np.save('vxlls-img_list_1.npy', img_list)
shutil.copy('vxlls-img_list_1.npy', './drive/My Drive/')

"""# Graphs

## Error graphs
"""

plt.figure(figsize=(20,10))
plt.title("Generator and Discriminator Loss During Training")
plt.plot(G_losses,label="G")
plt.plot(C_losses,label="D")
plt.xlabel("iterations")
plt.ylabel("Loss")
plt.ylim(0,5)
plt.legend()
plt.show()
plt.savefig('1.png')

plt.figure(figsize=(20,10))
plt.title("Generator and Discriminator Loss During Training")
plt.plot(G_losses,label="G")
plt.plot(C_losses,label="D")
plt.xlabel("iterations")
plt.ylabel("Loss")
plt.ylim(0,2)
plt.legend()
plt.show()
plt.savefig('1.png')

plt.figure(figsize=(20,10))
plt.title("Generator and Discriminator Loss During Training")
plt.plot(G_losses,label="G")
plt.plot(C_losses,label="D")
plt.xlabel("iterations")
plt.ylabel("Loss")
plt.ylim(0,1)
plt.legend()
plt.show()
plt.savefig('1.png')

"""## Results"""

import matplotlib.animation as animation
from IPython.display import HTML

#%%capture
fig = plt.figure(figsize=(16,16))
plt.axis("off")
ims = [[plt.imshow(np.transpose(i,(1,2,0)), animated=True)] for i in img_list[-20:]]
ani = animation.ArtistAnimation(fig, ims, interval=1000, repeat_delay=1000, blit=True)

HTML(ani.to_jshtml())

