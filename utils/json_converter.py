# utils/json_converter.py
import json

def convert_to_layoutlm_format(ocr_data, image_path="path/to/image.jpg"):
    words = []
    bboxes = []
    confidences = []

    # Directly loop over the list
    for item in ocr_data:
        word = item["text"]
        box = item["boundingBox"]  # [x0, y0, x1, y1]
        conf = item.get("confidence", 1.0)

        # Normalize bounding box to 0–1000 scale (assuming A4 2480x3508)
        normalized_box = [
            int(box[0] / 2480 * 1000),
            int(box[1] / 3508 * 1000),
            int(box[2] / 2480 * 1000),
            int(box[3] / 3508 * 1000)
        ]

        words.append(word)
        bboxes.append(normalized_box)
        confidences.append(conf)

    return {
        "id": "sample-id",
        "words": words,
        "bboxes": bboxes,
        "confidence": confidences,
        "image_path": image_path
    }
