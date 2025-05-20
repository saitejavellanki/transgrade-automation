import json
from utils.restructurer import restructure_student_answers

from flask import Flask, request, jsonify
from utils.enhancer import convert_pdf_to_images
from utils.json_converter import convert_to_layoutlm_format
from utils.ocr import extract_text
import os
import uuid

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to PDF Enhancer + Azure OCR API"

@app.route('/convert-pdf', methods=['POST'])
def convert_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400
    
    pdf_file = request.files['pdf']
    pdf_path = f"temp_{pdf_file.filename}"
    pdf_file.save(pdf_path)

    # Convert PDF to enhanced images
    image_paths = convert_pdf_to_images(pdf_path)
    
    return jsonify({'message': 'PDF converted successfully', 'images': image_paths})

@app.route('/extract-text', methods=['POST'])
def extract_text_line():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    image = request.files['image'].read()
    result = extract_text(image, word_level=False)
    return jsonify(result)

@app.route('/word-level', methods=['POST'])
def extract_text_word():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    image = request.files['image'].read()
    result = extract_text(image, word_level=True)
    return jsonify(result)

@app.route('/restructure-answers', methods=['POST'])
def restructure_answers():
    if 'key' not in request.files or 'student' not in request.files:
        return jsonify({'error': 'Both key and student JSON files are required'}), 400

    key_file = request.files['key']
    student_file = request.files['student']

    try:
        key_data = json.load(key_file)
        student_data = json.load(student_file)
    except Exception as e:
        return jsonify({'error': f'Invalid JSON input: {str(e)}'}), 400

    result = restructure_student_answers(key_data, student_data)
    
    # Return the raw text response
    return result

@app.route('/convert-json-to-layoutlm', methods=['POST'])
def convert_json_to_layoutlm():
    if 'json' not in request.files:
        return jsonify({'error': 'No JSON file uploaded'}), 400

    json_file = request.files['json']
    image_path = request.form.get('image_path', 'path/to/image.jpg')

    try:
        ocr_data = json.load(json_file)
    except Exception as e:
        return jsonify({'error': f'Invalid JSON file: {str(e)}'}), 400

    layoutlm_data = convert_to_layoutlm_format(ocr_data, image_path)

    # Save to JSONL format
    output_filename = f"output_{uuid.uuid4().hex}.jsonl"
    with open(output_filename, 'w') as out_file:
        json.dump(layoutlm_data, out_file)
        out_file.write("\n")

    return jsonify({'message': 'Conversion successful', 'output_file': output_filename})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5015))  # Use PORT env variable or default to 5015
    app.run(host='0.0.0.0', port=port, debug=False)
