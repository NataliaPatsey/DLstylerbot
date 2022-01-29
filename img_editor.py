import torchvision.transforms as transforms
import torch
from PIL import Image
import torchvision.models as models

import copy
import torch.nn as nn
import torch.optim as optim

from model_config import device, imsize, content_layers_default, style_layers_default, cnn_normalization_std,cnn_normalization_mean
from styler import Normalization, ContentLoss, StyleLoss

class Img_editor:
    def __init__(self, imsize=imsize):
        self.imsize = imsize


    def image_loader(self,image_name):
        loader = transforms.Compose([  # нормируем размер изображения
            transforms.Resize(self.imsize),
            transforms.CenterCrop(self.imsize),
            transforms.ToTensor()])
        image = Image.open(image_name)
        image = loader(image).unsqueeze(0)
        return image.to(device, torch.float)

    def image_unloader(self,image_tensor):
        unloader = transforms.ToPILImage()
        return unloader(image_tensor)

