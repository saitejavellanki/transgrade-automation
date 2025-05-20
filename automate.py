import os
import json
import requests
import argparse
import base64
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, url_for

app = Flask(__name__)

# Configuration
API_BASE_URL = "http://127.0.0.1:5015"  # Your main API
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
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #4361ee;
            --primary-dark: #3a56d4;
            --secondary: #3f37c9;
            --accent: #4895ef;
            --success: #4cc9f0;
            --danger: #f72585;
            --warning: #f8961e;
            --light: #f8f9fa;
            --dark: #212529;
            --gray: #6c757d;
            --light-gray: #e9ecef;
            --border-radius: 8px;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--dark);
            background-color: #f4f7fc;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 15px;
            color: var(--primary);
            font-weight: 700;
        }
        
        .header p {
            color: var(--gray);
            font-size: 1.1rem;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .card {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 30px;
            margin-bottom: 30px;
            transition: var(--transition);
        }
        
        .card:hover {
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
            transform: translateY(-5px);
        }
        
        .upload-container {
            text-align: center;
        }
        
        .upload-container h2 {
            margin-bottom: 20px;
            color: var(--secondary);
            font-size: 1.5rem;
        }
        
        .file-drop-area {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            border: 2px dashed var(--light-gray);
            border-radius: var(--border-radius);
            background-color: var(--light);
            transition: var(--transition);
            cursor: pointer;
        }
        
        .file-drop-area:hover {
            border-color: var(--accent);
            background-color: rgba(72, 149, 239, 0.05);
        }
        
        .file-drop-area i {
            font-size: 3rem;
            color: var(--primary);
            margin-bottom: 15px;
        }
        
        .file-message {
            margin-bottom: 15px;
            font-size: 1.1rem;
            color: var(--gray);
        }
        
        #fileInput {
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            width: 100%;
            opacity: 0;
            cursor: pointer;
        }
        
        .file-info {
            display: none;
            margin-top: 15px;
            padding: 10px 15px;
            background-color: var(--light);
            border-radius: var(--border-radius);
            text-align: left;
            width: 100%;
        }
        
        .file-name {
            font-weight: bold;
            color: var(--dark);
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .remove-file {
            color: var(--danger);
            cursor: pointer;
            font-size: 1.2rem;
        }
        
        .btn {
            display: inline-block;
            font-weight: 500;
            text-align: center;
            white-space: nowrap;
            vertical-align: middle;
            user-select: none;
            border: none;
            padding: 10px 20px;
            font-size: 1rem;
            line-height: 1.5;
            border-radius: var(--border-radius);
            transition: var(--transition);
            cursor: pointer;
            text-decoration: none;
        }
        
        .btn-primary {
            color: white;
            background-color: var(--primary);
        }
        
        .btn-primary:hover {
            background-color: var(--primary-dark);
        }
        
        .btn-success {
            color: white;
            background-color: var(--success);
        }
        
        .btn-success:hover {
            background-color: #3ab5d9;
        }
        
        .btn-danger {
            color: white;
            background-color: var(--danger);
        }
        
        .btn-danger:hover {
            background-color: #d61a6c;
        }
        
        .btn-lg {
            padding: 12px 30px;
            font-size: 1.1rem;
        }
        
        .btn-block {
            display: block;
            width: 100%;
        }
        
        .loading {
            display: none;
        }
        
        .spinner {
            margin: 20px auto;
            width: 70px;
            text-align: center;
        }
        
        .spinner > div {
            width: 18px;
            height: 18px;
            background-color: var(--primary);
            border-radius: 100%;
            display: inline-block;
            animation: sk-bouncedelay 1.4s infinite ease-in-out both;
        }
        
        .spinner .bounce1 {
            animation-delay: -0.32s;
        }
        
        .spinner .bounce2 {
            animation-delay: -0.16s;
        }
        
        @keyframes sk-bouncedelay {
            0%, 80%, 100% { 
                transform: scale(0);
            } 40% { 
                transform: scale(1.0);
            }
        }
        
        .loading-text {
            text-align: center;
            color: var(--gray);
            margin: 10px 0;
            font-size: 1.1rem;
        }
        
        .progress-container {
            margin: 20px 0;
            background-color: var(--light-gray);
            border-radius: 100px;
            height: 8px;
            overflow: hidden;
        }
        
        .progress-bar {
            height: 100%;
            width: 0;
            background-color: var(--primary);
            border-radius: 100px;
            transition: width 0.3s ease;
        }
        
        .results-container {
            display: none;
        }
        
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .results-header h2 {
            color: var(--secondary);
            font-size: 1.5rem;
        }
        
        .page-results {
            margin-bottom: 30px;
            border: 1px solid var(--light-gray);
            border-radius: var(--border-radius);
            overflow: hidden;
        }
        
        .page-header {
            background-color: var(--light);
            padding: 15px 20px;
            border-bottom: 1px solid var(--light-gray);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .page-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--dark);
        }
        
        .page-badge {
            padding: 5px 10px;
            background-color: var(--accent);
            color: white;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .page-content {
            padding: 20px;
        }
        
        .page-image-container {
            position: relative;
            margin-bottom: 20px;
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .page-image {
            display: block;
            width: 100%;
            height: auto;
            transition: var(--transition);
        }
        
        .page-image:hover {
            transform: scale(1.02);
        }
        
        .download-options {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .download-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 15px;
            color: white;
            background-color: var(--success);
            text-decoration: none;
            border-radius: var(--border-radius);
            transition: var(--transition);
            font-weight: 500;
        }
        
        .download-btn:hover {
            background-color: #3ab5d9;
            transform: translateY(-2px);
        }
        
        .download-btn i {
            font-size: 1rem;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: var(--gray);
            font-size: 0.9rem;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .card {
                padding: 20px;
            }
            
            .file-drop-area {
                padding: 20px;
            }
            
            .download-options {
                flex-direction: column;
            }
            
            .download-btn {
                width: 100%;
            }
        }
        
        /* Toast notification */
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        
        .toast {
            padding: 15px 20px;
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            animation: slideIn 0.3s ease forwards;
            max-width: 350px;
        }
        
        .toast.success {
            border-left: 4px solid var(--success);
        }
        
        .toast.error {
            border-left: 4px solid var(--danger);
        }
        
        .toast.warning {
            border-left: 4px solid var(--warning);
        }
        
        .toast-icon {
            margin-right: 15px;
            font-size: 1.5rem;
        }
        
        .toast.success .toast-icon {
            color: var(--success);
        }
        
        .toast.error .toast-icon {
            color: var(--danger);
        }
        
        .toast.warning .toast-icon {
            color: var(--warning);
        }
        
        .toast-content {
            flex: 1;
        }
        
        .toast-title {
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .toast-message {
            color: var(--gray);
            font-size: 0.9rem;
        }
        
        .toast-close {
            color: var(--gray);
            background: none;
            border: none;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0;
            margin-left: 10px;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>PDF Processing Tool</h1>
        <p>Convert your PDF documents into machine-readable formats with OCR and LayoutLM processing</p>
    </div>
    
    <div class="card upload-container">
        <h2>Upload Your PDF</h2>
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="file-drop-area">
                <i class="fas fa-file-pdf"></i>
                <p class="file-message">Drag & drop your PDF here or click to browse</p>
                <p class="file-limits">Maximum 2 pages per PDF</p>
                <input type="file" id="fileInput" name="pdf" accept=".pdf">
            </div>
            
            <div class="file-info" id="fileInfo">
                <div class="file-name">
                    <span id="fileName">No file selected</span>
                    <i class="fas fa-times remove-file" id="removeFile"></i>
                </div>
                <div id="fileSize" class="file-size"></div>
            </div>
            
            <button type="submit" class="btn btn-primary btn-lg btn-block" id="processBtn" style="margin-top: 20px;" disabled>
                <i class="fas fa-cogs"></i> Process PDF
            </button>
        </form>
    </div>
    
    <div class="card loading" id="loading">
        <div class="loading-text">Processing your PDF...</div>
        <div class="spinner">
            <div class="bounce1"></div>
            <div class="bounce2"></div>
            <div class="bounce3"></div>
        </div>
        <div class="progress-container">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <p class="loading-text">This may take a minute. Please wait.</p>
    </div>
    
    <div class="card results-container" id="results">
        <div class="results-header">
            <h2>Processing Results</h2>
            <button class="btn btn-danger" id="newUploadBtn">
                <i class="fas fa-upload"></i> Process Another PDF
            </button>
        </div>
        <div id="resultsContent"></div>
    </div>
    
    
    
    <div class="toast-container" id="toastContainer"></div>
    
    <script>
        // File handling
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const removeFile = document.getElementById('removeFile');
        const processBtn = document.getElementById('processBtn');
        const uploadForm = document.getElementById('uploadForm');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const resultsContent = document.getElementById('resultsContent');
        const newUploadBtn = document.getElementById('newUploadBtn');
        const progressBar = document.getElementById('progressBar');
        const toastContainer = document.getElementById('toastContainer');
        
        // File drop handling
        const dropArea = document.querySelector('.file-drop-area');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropArea.classList.add('highlighted');
        }
        
        function unhighlight() {
            dropArea.classList.remove('highlighted');
        }
        
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect();
            }
        }
        
        // File selection handling
        fileInput.addEventListener('change', handleFileSelect);
        
        function handleFileSelect() {
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                
                // Check if it's a PDF
                if (file.type !== 'application/pdf') {
                    showToast('Invalid File Type', 'Please select a PDF file.', 'error');
                    resetFileInput();
                    return;
                }
                
                // Update file info
                fileName.textContent = file.name;
                fileSize.textContent = formatFileSize(file.size);
                fileInfo.style.display = 'block';
                processBtn.disabled = false;
            }
        }
        
        // Format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // Remove file
        removeFile.addEventListener('click', resetFileInput);
        
        function resetFileInput() {
            fileInput.value = "";
            fileInfo.style.display = 'none';
            processBtn.disabled = true;
        }
        
        // Process PDF
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!fileInput.files[0]) {
                showToast('No File Selected', 'Please select a PDF file to process.', 'warning');
                return;
            }
            
            const formData = new FormData();
            formData.append('pdf', fileInput.files[0]);
            
            // Show loading indicator
            loading.style.display = 'block';
            results.style.display = 'none';
            
            // Simulate progress
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += Math.random() * 5;
                if (progress > 90) {
                    progress = 90;
                    clearInterval(progressInterval);
                }
                progressBar.style.width = progress + '%';
            }, 300);
            
            // Send the request
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                
                return response.json();
            })
            .then(data => {
                // Hide loading indicator after a slight delay
                setTimeout(() => {
                    loading.style.display = 'none';
                    
                    if (data.error) {
                        showToast('Processing Error', data.error, 'error');
                        return;
                    }
                    
                    showToast('Success', 'PDF processed successfully!', 'success');
                    
                    // Display results
                    displayResults(data.results);
                    
                    // Show results container
                    results.style.display = 'block';
                }, 500);
            })
            .catch(error => {
                clearInterval(progressInterval);
                loading.style.display = 'none';
                showToast('Error', 'An error occurred during processing.', 'error');
                console.error(error);
            });
        });
        
        // Display results
        function displayResults(results) {
            resultsContent.innerHTML = '';
            
            results.forEach(result => {
                const pageDiv = document.createElement('div');
                pageDiv.className = 'page-results';
                
                pageDiv.innerHTML = `
                    <div class="page-header">
                        <div class="page-title">Document Page</div>
                        <div class="page-badge">Page ${result.page}</div>
                    </div>
                    <div class="page-content">
                        <div class="page-image-container">
                            <img src="${result.image_path}" class="page-image" alt="Page ${result.page}">
                        </div>
                        <div class="download-options">
                            <a href="/download/${result.ocr_data_path}" class="download-btn">
                                <i class="fas fa-file-alt"></i> Download OCR Data
                            </a>
                            <a href="/download/${result.layoutlm_path}" class="download-btn">
                                <i class="fas fa-file-code"></i> Download LayoutLM Format
                            </a>
                        </div>
                    </div>
                `;
                
                resultsContent.appendChild(pageDiv);
            });
        }
        
        // New upload button
        newUploadBtn.addEventListener('click', function() {
            results.style.display = 'none';
            resetFileInput();
            progressBar.style.width = '0%';
        });
        
        // Toast notifications
        function showToast(title, message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            let icon = 'check-circle';
            if (type === 'error') icon = 'exclamation-circle';
            if (type === 'warning') icon = 'exclamation-triangle';
            
            toast.innerHTML = `
                <div class="toast-icon">
                    <i class="fas fa-${icon}"></i>
                </div>
                <div class="toast-content">
                    <div class="toast-title">${title}</div>
                    <div class="toast-message">${message}</div>
                </div>
                <button class="toast-close">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            toastContainer.appendChild(toast);
            
            // Auto close after 5 seconds
            setTimeout(() => {
                closeToast(toast);
            }, 5000);
            
            // Close button handler
            toast.querySelector('.toast-close').addEventListener('click', function() {
                closeToast(toast);
            });
        }
        
        function closeToast(toast) {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }
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
    app.run(debug=False, host='0.0.0.0', port=args.port)

if __name__ == "__main__":
    main()