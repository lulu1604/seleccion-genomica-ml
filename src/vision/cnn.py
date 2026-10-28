"""La red: ResNet18 de torchvision (transfer learning) con 5 salidas.

Cada animal tiene dos fotos. Las dos pasan por la MISMA ResNet18 (pesos
compartidos) y sus vectores de 512 numeros se pegan en uno de 1024; una capa
lineal final lo convierte en las 5 medidas:

    foto lateral   -> ResNet18 -> 512 \\
                                       concat (1024) -> Linear -> 5 medidas
    foto posterior -> ResNet18 -> 512 /

La lateral aporta largo y altura; la posterior, el ancho del cuerpo. Por eso se
usan las dos y no una sola.
"""
from __future__ import annotations

import torch
from torch import nn
from torchvision import models

N_SALIDAS = 5
DIM_FEATURES = 512  # tamano del vector que sale de la ResNet18 (antes de su fc)


class RedMedidas(nn.Module):
    def __init__(self, preentrenada: bool = True, congelar_backbone: bool = True):
        super().__init__()
        pesos = models.ResNet18_Weights.DEFAULT if preentrenada else None
        self.backbone = models.resnet18(weights=pesos)
        self.backbone.fc = nn.Identity()  # quitamos la capa de 1000 clases de ImageNet
        self.cabeza = nn.Linear(2 * DIM_FEATURES, N_SALIDAS)
        self.congelar_backbone = congelar_backbone
        if congelar_backbone:
            for p in self.backbone.parameters():
                p.requires_grad = False

    def train(self, modo: bool = True):
        super().train(modo)
        if self.congelar_backbone:
            # Con el backbone congelado, sus capas BatchNorm tambien se quedan
            # quietas: si no, sus estadisticas seguirian cambiando con 57 fotos.
            self.backbone.eval()
        return self

    def forward(self, lateral: torch.Tensor, posterior: torch.Tensor) -> torch.Tensor:
        f = torch.cat([self.backbone(lateral), self.backbone(posterior)], dim=1)
        return self.cabeza(f)


def construir(preentrenada: bool = True, congelar_backbone: bool = True) -> RedMedidas:
    return RedMedidas(preentrenada=preentrenada, congelar_backbone=congelar_backbone)
