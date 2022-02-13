import torchvision.transforms as transforms
import torch
from PIL import Image


from MODEL_CONFIG import imsize


class Img_editor:
    imsize = imsize

    @classmethod
    def image_loader(cls,image_name):
        loader = transforms.Compose([  # нормируем размер изображения
            transforms.Resize(imsize),
            transforms.CenterCrop(imsize),
            transforms.ToTensor()])
        image = Image.open(image_name)
        image = loader(image).unsqueeze(0)
        return image.to('cpu', torch.float)

    @staticmethod
    def image_unloader(image_tensor):
        unloader = transforms.ToPILImage()
        return unloader(image_tensor)

