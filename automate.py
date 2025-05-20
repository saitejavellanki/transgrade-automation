import os
import json
import requests
import argparse
import base64
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, url_for

app = Flask(__name__)

# Configuration
API_BASE_URL = "http://localhost:5015"  # Your main API
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
TEMP_FOLDER = "temp"

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(os.path.join("static", "images"), exist_ok=True)

def save_pdf(pdf_file):
    """Save the uploaded PDF file and return its path"""
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
    pdf_file.save(pdf_path)
    return pdf_path

def convert_pdf_to_images(pdf_path):
    """Convert PDF to enhanced images via API"""
    with open(pdf_path, 'rb') as f:
        files = {'pdf': f}
        response = requests.post(f"{API_BASE_URL}/convert-pdf", files=files)
    
    if response.status_code == 200:
        return response.json()['images']
    else:
        raise Exception(f"Failed to convert PDF: {response.json()}")

def extract_text_word_level(image_path):
    """Extract text from an image at word level via API"""
    with open(image_path, 'rb') as f:
        files = {'image': f}
        response = requests.post(f"{API_BASE_URL}/word-level", files=files)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to extract text: {response.json()}")

def convert_to_layoutlm(ocr_data, image_path):
    """Convert OCR data to LayoutLM format"""
    temp_json_path = os.path.join(TEMP_FOLDER, f"ocr_data_{os.path.basename(image_path)}.json")
    
    # Save OCR data to a temporary JSON file
    with open(temp_json_path, 'w') as f:
        json.dump(ocr_data, f)
    
    with open(temp_json_path, 'rb') as f:
        files = {'json': f}
        form_data = {'image_path': image_path}
        response = requests.post(
            f"{API_BASE_URL}/convert-json-to-layoutlm", 
            files=files,
            data=form_data
        )
    
    if response.status_code == 200:
        result_file = response.json()['output_file']
        
        # Read the content of the output file
        with open(result_file, 'r') as f:
            layoutlm_data = json.load(f)
            
        # Save to output folder with a meaningful name
        output_path = os.path.join(OUTPUT_FOLDER, f"layoutlm_{os.path.basename(image_path)}.json")
        with open(output_path, 'w') as f:
            json.dump(layoutlm_data, f, indent=2)
            
        return output_path
    else:
        raise Exception(f"Failed to convert to LayoutLM: {response.json()}")

def process_pdf(pdf_path):
    """Process a PDF file through the entire pipeline"""
    results = []
    
    # Step 1: Convert PDF to enhanced images
    image_paths = convert_pdf_to_images(pdf_path)
    
    # Step 2 & 3: For each image, extract text and convert to LayoutLM format
    for idx, image_path in enumerate(image_paths):
        print(f"Processing page {idx+1} from {image_path}")
        
        # Extract text at word level
        ocr_data = extract_text_word_level(image_path)
        
        # Save OCR data
        ocr_output_path = os.path.join(OUTPUT_FOLDER, f"ocr_page_{idx+1}.json")
        with open(ocr_output_path, 'w') as f:
            json.dump(ocr_data, f, indent=2)
            
        # Convert to LayoutLM format
        layoutlm_path = convert_to_layoutlm(ocr_data, image_path)
        
        # Copy image to static folder for display
        target_image = os.path.join("static", "images", f"page_{idx+1}.jpg")
        with open(image_path, 'rb') as src, open(target_image, 'wb') as dst:
            dst.write(src.read())
            
        results.append({
            'page': idx + 1,
            'image_path': target_image,
            'ocr_data_path': ocr_output_path,
            'layoutlm_path': layoutlm_path
        })
        
    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400
    
    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return jsonify({'error': 'No PDF file selected'}), 400
    
    try:
        # Save and process the PDF
        pdf_path = save_pdf(pdf_file)
        results = process_pdf(pdf_path)
        
        return jsonify({
            'message': 'PDF processed successfully',
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filepath>')
def download_file(filepath):
    """Download a file from the output folder"""
    return send_file(filepath, as_attachment=True)

def create_templates():
    """Create the HTML template file"""
    templates_dir = os.path.join(os.getcwd(), "templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Processing Tool</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .upload-container {
            border: 2px dashed #ccc;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
        }
        .results-container {
            display: none;
            margin-top: 30px;
        }
        .page-results {
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }
        .page-image {
            max-width: 100%;
            margin-bottom: 10px;
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .download-btn {
            background-color: #4CAF50;
            color: white;
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
            text-decoration: none;
            display: inline-block;
        }
    </style>
</head>
<body>
    <h1>PDF Processing Tool</h1>
    
    <div class="upload-container">
        <h2>Upload PDF (Max 2 pages)</h2>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="pdfFile" name="pdf" accept=".pdf">
            <button type="submit">Process PDF</button>
        </form>
    </div>
    
    <div class="loading" id="loading">
        <p>Processing PDF... This may take a minute.</p>
        <img src="https://cdnjs.cloudflare.com/ajax/libs/galleriffic/2.0.1/css/loader.gif" alt="Loading...">
    </div>
    
    <div class="results-container" id="results">
        <h2>Processing Results</h2>
        <div id="resultsContent"></div>
    </div>
    
    <script>
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('pdfFile');
            if (!fileInput.files[0]) {
                alert('Please select a PDF file');
                return;
            }
            
            const formData = new FormData();
            formData.append('pdf', fileInput.files[0]);
            
            // Show loading indicator
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            // Send the request
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading indicator
                document.getElementById('loading').style.display = 'none';
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                // Display results
                const resultsContainer = document.getElementById('resultsContent');
                resultsContainer.innerHTML = '';
                
                data.results.forEach(result => {
                    const pageDiv = document.createElement('div');
                    pageDiv.className = 'page-results';
                    
                    pageDiv.innerHTML = `
                        <h3>Page ${result.page}</h3>
                        <img src="${result.image_path}" class="page-image" alt="Page ${result.page}">
                        <div>
                            <a href="/download/${result.ocr_data_path}" class="download-btn">Download OCR Data</a>
                            <a href="/download/${result.layoutlm_path}" class="download-btn">Download LayoutLM Format</a>
                        </div>
                    `;
                    
                    resultsContainer.appendChild(pageDiv);
                });
                
                // Show results container
                document.getElementById('results').style.display = 'block';
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                alert('Error: ' + error);
            });
        });
    </script>
</body>
</html>
"""
    
    with open(os.path.join(templates_dir, "index.html"), "w") as f:
        f.write(template_content)

def main():
    parser = argparse.ArgumentParser(description="PDF Processing Tool")
    parser.add_argument("--port", type=int, default=5016, help="Port to run the web app")
    args = parser.parse_args()
    
    # Create template files
    create_templates()
    
    # Run the Flask app
    print(f"Starting PDF Processing Tool on port {args.port}")
    app.run(debug=True, port=args.port)

if __name__ == "__main__":
    main()