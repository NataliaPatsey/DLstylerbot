import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision.models as models

from MODEL_CONFIG import content_layers_default, style_layers_default, cnn_normalization_std,\
    cnn_normalization_mean,num_steps,style_weight,content_weight


class ContentLoss(nn.Module):
    def __init__(self, target, ):
        super(ContentLoss, self).__init__()
        self.target = target.detach()  # это константа. Убираем ее из дерева вычеслений
        self.loss = F.mse_loss(self.target, self.target)  # to initialize with something

    def forward(self, input):
        self.loss = F.mse_loss(input, self.target)
        return input

def gram_matrix(input):
    batch_size, h, w, f_map_num = input.size()  # batch size(=1)
    features = input.view(batch_size * h, w * f_map_num)  # resise F_XL into \hat F_XL
    G = torch.mm(features, features.t())  # compute the gram product
    return G.div(batch_size * h * w * f_map_num)

class StyleLoss(nn.Module):
    def __init__(self, target_feature):
        super(StyleLoss, self).__init__()
        self.target = gram_matrix(target_feature).detach()
        self.loss = F.mse_loss(self.target, self.target)  # to initialize with something

    def forward(self, input):
        G = gram_matrix(input)
        self.loss = F.mse_loss(G, self.target )
        return input

class Normalization(nn.Module):
    def __init__(self, mean, std):
        super(Normalization, self).__init__()
        self.mean = mean.clone().detach().view(-1, 1, 1)
        self.std = std.clone().detach().view(-1, 1, 1)

    def forward(self, img):
        return (img - self.mean) / self.std


class Styler:
    def __init__(self,content_img,style_img):
        self.cnn = models.vgg19(pretrained=True).features.eval()
        self.optimizer = optim.LBFGS
        self.normalization_mean =cnn_normalization_mean
        self.normalization_std = cnn_normalization_std
        self.content_layers = content_layers_default
        self.style_layers = style_layers_default
        self.num_steps = num_steps
        self.style_weight = style_weight
        self.content_weight = content_weight
        self.content_img = content_img
        self.style_img = style_img
        self.input_img = content_img.clone()

    def weight_setter(self,style_weight,content_weight):
        self.content_weight = content_weight
        self.style_weight = style_weight

    def get_style_model_and_losses(self):
        #cnn = copy.deepcopy(self.cnn)
        torch.save(self.cnn[:11],'new_cnn.pth')
        cnn = torch.load('new_cnn.pth')

        # normalization module
        normalization = Normalization(self.normalization_mean, self.normalization_std)
        content_losses = []
        style_losses = []

        model = nn.Sequential(normalization)

        i = 0  # increment every time we see a conv
        for layer in cnn.children():
            if isinstance(layer, nn.Conv2d):
                i += 1
                name = 'conv_{}'.format(i)
            elif isinstance(layer, nn.ReLU):
                name = 'relu_{}'.format(i)
                layer = nn.ReLU(inplace=False)
            elif isinstance(layer, nn.MaxPool2d):
                name = 'pool_{}'.format(i)
            elif isinstance(layer, nn.BatchNorm2d):
                name = 'bn_{}'.format(i)
            else:
                raise RuntimeError('Unrecognized layer: {}'.format(layer.__class__.__name__))

            model.add_module(name, layer)

            if name in self.content_layers:
                # add content loss:
                target = model(self.content_img).detach()
                content_loss = ContentLoss(target)
                model.add_module("content_loss_{}".format(i), content_loss)
                content_losses.append(content_loss)

            if name in self.style_layers:
                # add style loss:
                target_feature = model(self.style_img).detach()
                style_loss = StyleLoss(target_feature)
                model.add_module("style_loss_{}".format(i), style_loss)
                style_losses.append(style_loss)

        # выбрасываем все уровни после последенего styel loss или content loss
        for i in range(len(model) - 1, -1, -1):
            if isinstance(model[i], ContentLoss) or isinstance(model[i], StyleLoss):
                break
        model = model[:(i + 1)]
        return model, style_losses, content_losses


    def run_style_transfer(self):
        """Run the style transfer."""
        model, style_losses, content_losses = self.get_style_model_and_losses()
        optimizer = self.optimizer([self.input_img.requires_grad_()])


        run = [0]
        while run[0] <= self.num_steps:

            def closure():
                # это для того, чтобы значения тензора картинки не выходили за пределы [0;1]
                self.input_img.data.clamp_(0, 1)
                optimizer.zero_grad()

                model(self.input_img)
                style_score = 0
                content_score = 0

                for sl in style_losses:
                    style_score += sl.loss
                for cl in content_losses:
                    content_score += cl.loss

                # взвешивание ощибки
                style_score *= self.style_weight
                content_score *= self.content_weight

                loss = style_score + content_score
                loss.backward()

                run[0] += 1

                return style_score + content_score

            optimizer.step(closure)

        # a last correction...
        self.input_img.data.clamp_(0, 1)

        return self.input_img, {'content_weight':self.content_weight, 'style_weight':self.style_weight}

