import os
from pdf2image import convert_from_path
from PIL import ImageEnhance, ImageFilter
from PIL import Image

def enhance_image(image, contrast=1.5, sharpness=1.5, brightness=1.2):
    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Sharpness(image).enhance(sharpness)
    return image

def convert_pdf_to_images(pdf_path, output_dir='static/enhanced_images', dpi=300,
                          contrast=1.5, sharpness=1.5, brightness=1.2, fmt='PNG'):
    os.makedirs(output_dir, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=dpi)
    paths = []

    for i, img in enumerate(images):
        enhanced = enhance_image(img, contrast, sharpness, brightness)
        path = os.path.join(output_dir, f'page_{i + 1}.{fmt.lower()}')
        enhanced.save(path, format=fmt)
        paths.append(path)
    
    return paths
