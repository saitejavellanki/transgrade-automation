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
    if 'pdf' not in request.files or 'key_json' not in request.files:
        return render_template('upload.html', result="PDF and Key JSON are required")

    pdf_file = request.files['pdf']
    key_file = request.files['key_json']

    # Step 1: Convert PDF to images
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

                layoutlm_response = requests.post(
                    f"{BACKEND_URL}/convert-json-to-layoutlm",
                    files={'json': ('ocr.json', json.dumps(word_data), 'application/json')},
                    data={'image_path': image_path}
                )

                if layoutlm_response.status_code == 200:
                    layoutlm_data.append(layoutlm_response.json())
                else:
                    layoutlm_data.append({'error': 'LayoutLM conversion failed'})
            else:
                extracted_data.append({'error': f"Failed to extract text from {image_path}"})
                layoutlm_data.append({'error': f"LayoutLM conversion skipped for {image_path}"})

    # Combine OCRs for all pages into one student script
    combined_student_ocr = {
        "pages": extracted_data  # Optional: you can flatten this if needed
    }

    # Call restructure-answers endpoint
    restructure_files = {
        'key': (key_file.filename, key_file.stream, 'application/json'),
        'student': ('student.json', json.dumps(combined_student_ocr), 'application/json')
    }

    restructure_response = requests.post(
        f"{BACKEND_URL}/restructure-answers",
        files=restructure_files
    )

    restructure_result = None
    if restructure_response.status_code == 200:
        # Try to parse as JSON if possible, otherwise keep as text
        try:
            restructure_result = restructure_response.json()
        except json.JSONDecodeError:
            # If it's not JSON, store the raw text
            restructure_result = {
                "raw_response": restructure_response.text
            }
    else:
        restructure_result = {
            "error": f"Status {restructure_response.status_code}",
            "details": restructure_response.text
        }

    page_results = [
        {
            'page': idx + 1,
            'ocr': extracted_data[idx],
            'layoutlm': layoutlm_data[idx]
        }
        for idx in range(len(extracted_data))
    ]

    return render_template('upload.html', page_results=page_results, restructure_result=restructure_result)

if __name__ == '__main__':
    app.run(debug=False, port=5000)
