import json
from google.generativeai import GenerativeModel, configure

# Configure Gemini API key
configure(api_key='AIzaSyDx7TtYxDvHBIyIjXd1i9MsDmnkQWpg2Nw')

def generate_prompt(key_data, student_data):
    return f"""You are given two JSON files:

1. `key.json`: This contains the official question structure. It defines the **correct number and order** of questions.
2. `student_answer.json`: This contains student answers. These may have:
   - Missing or incorrect question numbers.
   - Extra entries caused by **unintended splits** in a single answer (e.g., bullet points or continuation of an answer detected as a separate one).

Your task is to:
- Match each student answer to the correct question **by order**, using the order in the key as reference.
- If the student answer is **split across multiple entries** (e.g., a multi-line or multi-point answer mistakenly treated as separate answers), **merge them into one**.
- Do **not** invent or modify any content.
- Do **not** assign more student answers than actually exist.
- If the student answered fewer questions than expected, **leave out the unmatched questions**.
- The number of student answers in the final output should be equal to the number of **complete, merged answers** the student actually wrote (not the number of questions in the key).
- If there are extra answers due to split points, they must be **combined with their correct earlier parts**.
- **IMPORTANT**: The output must preserve both the question number AND section information exactly as shown in the key.json structure.

Your goal is to output a corrected `student_answer.json` where:
- Question numbers and section identifiers are inferred from the key order.
- The content is kept unchanged.
- Only the correct number of student answers is present, aligned properly by question.
- Format the output as a valid JSON array with no markdown.

### Key JSON:
{json.dumps(key_data, indent=2)}

### Student Answer JSON:
{json.dumps(student_data, indent=2)}

Return ONLY the corrected JSON with aligned and merged answers, making sure to include both section and question numbering that matches the key structure. The output must be a properly formatted JSON array with no additional text."""

def restructure_student_answers(key_data, student_data):
    prompt = generate_prompt(key_data, student_data)
    model = GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    
    # Extract the response text
    response_text = response.text
    
    # Clean up the response to ensure it's valid JSON
    # Remove any potential markdown code blocks or extra text
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    # Attempt to parse the JSON
    try:
        # Parse as JSON and return as a Python object
        parsed_json = json.loads(response_text)
        return parsed_json
    except json.JSONDecodeError:
        # If parsing fails, return a dictionary with an error message and the raw text
        return {"error": "Failed to parse Gemini response as JSON", "raw_response": response_text}