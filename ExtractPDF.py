from pdf2image import convert_from_bytes, convert_from_path
import os

def extract_pdf(doc):
    poppler_path = r'D:\AI\document validation\ToJepri\poppler-22.04.0\Library\bin'
    pdf_path= doc
    images = convert_from_bytes(pdf_path.read(),poppler_path=poppler_path)
    results = []
    for i in range(len(images)):  
        results.append(images[i])
        # if i==len(images)-page:
        #     return images[i]
    return results

def extract_pdf_path(doc):
    poppler_path = r'D:\AI\document validation\ToJepri\poppler-22.04.0\Library\bin'
    pdf_path= doc
    images = convert_from_path(pdf_path,poppler_path=poppler_path)
    results = []
    for i in range(len(images)):  
        results.append(images[i])
        # if i==len(images)-page:
        #     return images[i]
    return results