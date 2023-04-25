import torch
import numpy as np
import cv2
from time import time


def run_model(image, model_name):
    image = cv2.resize(image, (640,640))

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = torch.hub.load('yolov5', 'custom', path=model_name, source='local', force_reload=True)

    model.to(device)
    image = [image]
    results = model(image)
    return results


def coordinate_box(results, frame):
    labels, cord = results.xyxyn[0][:, -1], results.xyxyn[0][:, :-1]
    n = len(labels)
    x_shape, y_shape = frame.shape[1], frame.shape[0]
    coordinate = []
    for i in range(n):
        row = cord[i]
        # accuration for label
        # if  >= 0.1:
        x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape)
        coordinate.append([labels[i], x1, y1, x2, y2, row[4]])

    return coordinate