import cv2
import os
import numpy as np
import matplotlib.pyplot as plt


def preprocessing(img):
    img = np.asarray(img)
    
    # grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # sharpening
    kernel = np.array([[-1,-1,-1],
                    [-1,9,-1],
                    [-1,-1,-1]])
    sharpen = cv2.filter2D(gray,-1,kernel)

    # gausian blur
    gausian_blur = cv2.GaussianBlur(sharpen,(5,5),0)

    return gausian_blur

def normalize(img, size):
    img = np.asarray(img)
    # normalize        
    width = size[0]
    height = size[1]
    dim = (width, height)

    # # resize image
    resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    return resized

