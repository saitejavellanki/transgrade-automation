import json
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

BACKEND_URL = "http://localhost:5015"

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return render_template('upload.html', result="No PDF uploaded")
    
    pdf_file = request.files['pdf']
    
    # Step 1: Send to backend to convert PDF to images
    files = {'pdf': (pdf_file.filename, pdf_file.stream, 'application/pdf')}
    convert_response = requests.post(f"{BACKEND_URL}/convert-pdf", files=files)

    if convert_response.status_code != 200:
        return render_template('upload.html', result="PDF conversion failed")

    image_paths = convert_response.json().get('images', [])

    extracted_data = []
    layoutlm_data = []

    for image_path in image_paths:
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            files = {'image': ('image.png', img_data, 'image/png')}
            ocr_response = requests.post(f"{BACKEND_URL}/word-level", files=files)
            
            if ocr_response.status_code == 200:
                word_data = ocr_response.json()
                extracted_data.append(word_data)

                # Step 2: Convert OCR to LayoutLM format
                json_payload = {'image_path': image_path}
                layoutlm_response = requests.post(
                    f"{BACKEND_URL}/convert-json-to-layoutlm",
                    files={'json': ('ocr.json', json.dumps(word_data), 'application/json')},
                    data=json_payload
                )

                if layoutlm_response.status_code == 200:
                    layoutlm_data.append(layoutlm_response.json())
                else:
                    layoutlm_data.append({'error': 'LayoutLM conversion failed'})
            else:
                extracted_data.append({'error': f"Failed to extract text from {image_path}"})
                layoutlm_data.append({'error': f"LayoutLM conversion skipped for {image_path}"})

    # Pack both OCR and LayoutLM for each page
    page_results = [
        {
            'page': idx + 1,
            'ocr': extracted_data[idx],
            'layoutlm': layoutlm_data[idx]
        }
        for idx in range(len(extracted_data))
    ]
    return render_template('upload.html', result=page_results)


if __name__ == '__main__':
    app.run(debug=False, port=5000)

