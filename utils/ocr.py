import requests
import time

subscription_key = '6b2uM74mq58QMzHkU50QsZwJXDVoUuklAi6fqiob6b7XiaCMR4zUJQQJ99BDACYeBjFXJ3w3AAAFACOGki3V'
endpoint = 'https://vellan.cognitiveservices.azure.com/'
read_url = endpoint + "vision/v3.2/read/analyze"

def poll_result(op_url, headers):
    while True:
        result = requests.get(op_url, headers=headers).json()
        if result["status"] in ["succeeded", "failed"]:
            return result
        time.sleep(1)

def convert_bbox_format(bounding_box):
    x_coords = bounding_box[::2]
    y_coords = bounding_box[1::2]
    x0, y0 = min(x_coords), min(y_coords)
    x1, y1 = max(x_coords), max(y_coords)
    return [x0, y0, x1, y1]

def extract_text(image_data, word_level=False):
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(read_url, headers=headers, data=image_data)
    if response.status_code != 202:
        return {'error': 'Azure OCR failed', 'details': response.text}

    operation_url = response.headers["Operation-Location"]
    result = poll_result(operation_url, headers)

    if result["status"] != "succeeded":
        return {'error': 'OCR analysis failed'}

    output = []

    for page_result in result["analyzeResult"]["readResults"]:
        for line in page_result["lines"]:
            if word_level:
                line_text = line["text"]
                if "words" in line:
                    for idx, word in enumerate(line["words"]):
                        output.append({
                            "id": idx,
                            "text": word["text"],
                            "boundingBox": convert_bbox_format(word["boundingBox"]),
                            "confidence": word.get("confidence", None),
                            "line_text": line_text
                        })
            else:
                line_obj = {
                    "text": line["text"],
                    "boundingBox": convert_bbox_format(line["boundingBox"]),
                    "confidence": None
                }
                if "words" in line:
                    confidences = [word.get("confidence", 0) for word in line["words"] if "confidence" in word]
                    if confidences:
                        line_obj["confidence"] = sum(confidences) / len(confidences)
                output.append(line_obj)

    return output
