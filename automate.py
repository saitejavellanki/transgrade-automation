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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/css/all.min.css">
    <style>
        /* Apple-inspired Design System */
        :root {
            --primary: #0071e3;
            --primary-dark: #0051a3;
            --light-gray: #f5f5f7;
            --mid-gray: #d2d2d7;
            --dark-gray: #86868b;
            --text: #1d1d1f;
            --radius: 12px;
            --transition: all 0.3s ease;
            --shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            --shadow-hover: 0 8px 20px rgba(0, 0, 0, 0.12);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "San Francisco", "Helvetica Neue", Helvetica, Arial, sans-serif;
            background-color: white;
            color: var(--text);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            padding: 0;
            margin: 0;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        h1 {
            font-weight: 600;
            font-size: 32px;
            letter-spacing: -0.5px;
            margin-bottom: 12px;
        }
        
        h2 {
            font-weight: 500;
            font-size: 24px;
            margin-bottom: 20px;
            letter-spacing: -0.3px;
        }
        
        h3 {
            font-weight: 500;
            font-size: 20px;
            margin-bottom: 16px;
            letter-spacing: -0.3px;
        }
        
        .subheading {
            color: var(--dark-gray);
            font-weight: 400;
            font-size: 18px;
        }
        
        /* Upload Container */
        .card {
            background-color: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 30px;
            margin-bottom: 30px;
            transition: var(--transition);
            border: 1px solid var(--mid-gray);
        }
        
        .card:hover {
            box-shadow: var(--shadow-hover);
        }
        
        .upload-container {
            text-align: center;
        }
        
        .upload-area {
            border: 2px dashed var(--mid-gray);
            border-radius: var(--radius);
            padding: 40px 20px;
            margin: 20px 0;
            transition: var(--transition);
            cursor: pointer;
            background-color: var(--light-gray);
        }
        
        .upload-area:hover {
            border-color: var(--primary);
            background-color: rgba(0, 113, 227, 0.05);
        }
        
        .upload-icon {
            font-size: 36px;
            color: var(--primary);
            margin-bottom: 16px;
        }
        
        .upload-text {
            font-size: 16px;
            color: var(--dark-gray);
            margin-bottom: 16px;
        }
        
        .file-input {
            display: none;
        }
        
        .file-name {
            font-size: 14px;
            color: var(--text);
            margin-top: 10px;
            display: none;
        }
        
        /* Button Styles */
        .btn {
            background-color: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            display: inline-block;
            text-align: center;
            text-decoration: none;
        }
        
        .btn:hover {
            background-color: var(--primary-dark);
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background-color: var(--light-gray);
            color: var(--text);
            border: 1px solid var(--mid-gray);
        }
        
        .btn-secondary:hover {
            background-color: var(--mid-gray);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        /* Loading Animation */
        .loading {
            display: none;
            text-align: center;
            margin: 30px 0;
        }
        
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(0, 113, 227, 0.1);
            border-radius: 50%;
            border-top-color: var(--primary);
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .loading-text {
            color: var(--dark-gray);
            font-size: 16px;
        }
        
        /* Results Section */
        .results-container {
            display: none;
            margin-top: 40px;
            opacity: 0;
            transform: translateY(10px);
            transition: opacity 0.4s ease, transform 0.4s ease;
        }
        
        .results-container.visible {
            opacity: 1;
            transform: translateY(0);
        }
        
        .page-results {
            border-radius: var(--radius);
            background-color: white;
            box-shadow: var(--shadow);
            padding: 24px;
            margin-bottom: 24px;
            transition: var(--transition);
            border: 1px solid var(--mid-gray);
        }
        
        .page-results:hover {
            box-shadow: var(--shadow-hover);
        }
        
        .page-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }
        
        .page-image-container {
            margin: 16px 0;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        }
        
        .page-image {
            width: 100%;
            height: auto;
            display: block;
            border-radius: 8px;
            transition: var(--transition);
        }
        
        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 16px;
        }
        
        .download-btn {
            padding: 10px 16px;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .download-icon {
            font-size: 14px;
        }
        
        /* Status Badge */
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            background-color: var(--primary);
            color: white;
        }
        
        /* Responsive Styles */
        @media (max-width: 768px) {
            .container {
                padding: 20px 16px;
            }
            
            h1 {
                font-size: 28px;
            }
            
            h2 {
                font-size: 20px;
            }
            
            .card {
                padding: 20px;
            }
            
            .upload-area {
                padding: 30px 15px;
            }
            
            .btn {
                padding: 10px 18px;
                font-size: 15px;
                width: 100%;
                margin-bottom: 8px;
            }
            
            .actions {
                flex-direction: column;
                gap: 8px;
            }
            
            .download-btn {
                width: 100%;
                justify-content: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>PDF Processing Tool</h1>
            <p class="subheading">Process PDFs with advanced document analysis</p>
        </header>
        
        <div class="card">
            <div class="upload-container">
                <h2>Upload Document</h2>
                <p class="upload-text">Maximum 2 pages per PDF file</p>
                
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="upload-area" id="uploadArea">
                        <i class="fas fa-file-pdf upload-icon"></i>
                        <p>Drag & drop your PDF here or</p>
                        <button type="button" class="btn btn-secondary" id="browseBtn">Browse Files</button>
                        <input type="file" id="pdfFile" name="pdf" accept=".pdf" class="file-input">
                        <p class="file-name" id="fileName"></p>
                    </div>
                    
                    <button type="submit" class="btn" id="processBtn" disabled>Process PDF</button>
                </form>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="loading-spinner"></div>
            <p class="loading-text">Processing your document...</p>
            <p class="subheading">This may take a minute</p>
        </div>
        
        <div class="results-container" id="results">
            <h2>Processing Results</h2>
            <div id="resultsContent"></div>
        </div>
    </div>
    
    <script>
        // DOM Elements
        const uploadForm = document.getElementById('uploadForm');
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('pdfFile');
        const browseBtn = document.getElementById('browseBtn');
        const fileName = document.getElementById('fileName');
        const processBtn = document.getElementById('processBtn');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const resultsContent = document.getElementById('resultsContent');
        
        // File Upload Handling
        browseBtn.addEventListener('click', () => {
            fileInput.click();
        });
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = var(--primary);
            uploadArea.style.backgroundColor = 'rgba(0, 113, 227, 0.05)';
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '';
            uploadArea.style.backgroundColor = '';
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '';
            uploadArea.style.backgroundColor = '';
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileName();
            }
        });
        
        fileInput.addEventListener('change', updateFileName);
        
        function updateFileName() {
            if (fileInput.files.length > 0) {
                fileName.textContent = fileInput.files[0].name;
                fileName.style.display = 'block';
                processBtn.disabled = false;
            } else {
                fileName.style.display = 'none';
                processBtn.disabled = true;
            }
        }
        
        // Form Submission
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!fileInput.files[0]) {
                alert('Please select a PDF file');
                return;
            }
            
            const formData = new FormData();
            formData.append('pdf', fileInput.files[0]);
            
            // Show loading indicator
            loading.style.display = 'block';
            results.style.display = 'none';
            processBtn.disabled = true;
            
            // Send the request
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading indicator
                loading.style.display = 'none';
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    processBtn.disabled = false;
                    return;
                }
                
                // Display results
                resultsContent.innerHTML = '';
                
                data.results.forEach(result => {
                    const pageDiv = document.createElement('div');
                    pageDiv.className = 'page-results';
                    
                    pageDiv.innerHTML = `
                        <div class="page-header">
                            <h3>Page ${result.page}</h3>
                            <span class="status-badge">Processed</span>
                        </div>
                        <div class="page-image-container">
                            <img src="${result.image_path}" class="page-image" alt="Page ${result.page}">
                        </div>
                        <div class="actions">
                            <a href="/download/${result.ocr_data_path}" class="btn download-btn">
                                <i class="fas fa-file-download download-icon"></i>
                                OCR Data
                            </a>
                            <a href="/download/${result.layoutlm_path}" class="btn download-btn">
                                <i class="fas fa-file-download download-icon"></i>
                                LayoutLM Format
                            </a>
                        </div>
                    `;
                    
                    resultsContent.appendChild(pageDiv);
                });
                
                // Show results container with animation
                results.style.display = 'block';
                setTimeout(() => {
                    results.classList.add('visible');
                }, 50);
                
                processBtn.disabled = false;
            })
            .catch(error => {
                loading.style.display = 'none';
                alert('Error: ' + error);
                processBtn.disabled = false;
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