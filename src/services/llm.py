import os
import sys
import json
import base64
import logging
from PIL import Image
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, Any, Union


# Setup logging to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',        # Logs will be saved to 'app.log'
    filemode='a'               # Append mode (use 'w' to overwrite on each run)
)

logger = logging.getLogger(__name__)

cwd = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(cwd)

load_dotenv(os.path.join(cwd, '.env'))

def extract_from_table(prompt_path: str, 
                       img: Union[Image.Image, str]
                       ) -> Dict[str, Any]:
    """
    Extract structured data from a table in an image using OpenAI's vision capabilities.

    Args:
        prompt_path: Path to the text file containing the prompt
        img: PIL Image object or path to an image file

    Returns:
        Dictionary containing the extracted table data
    """
    def pil_to_base64(image: Image.Image) -> str:
        """Convert a PIL Image to base64 string."""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str

    # Check if img is a file path or PIL Image
    if isinstance(img, str):
        try:
            img = Image.open(img)
        except Exception as e:
            logger.error("Failed to open image at %s: %s", 
                        img, str(e) )
            return None

    # Validate image format
    if not isinstance(img, Image.Image):
        logger.error("Expected PIL Image or path to image file")
        return None

    try:
        # Get API key with a more reliable approach
        api_key = os.environ.get('OPENAI')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return None

        client = OpenAI(api_key=api_key)
        base64_image = pil_to_base64(image=img)

        # Read prompt from file with error handling
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
        except Exception as e:
            logger.error("Failed to read prompt file at %s: %s", prompt_path, str(e))
            return None

        # Correct API call syntax
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )

        # Extract response text with proper error handling
        if hasattr(response, 'choices') and len(response.choices) > 0:
            response_text = response.choices[0].message.content
        else:
            logger.error("Unexpected response format from OpenAI API")
            return None

        # Clean the response to extract JSON
        json_str = response_text
        # Remove code block markers if present
        json_str = json_str.replace('```json', '').replace('```', '').strip()

        try:
            # Parse JSON with error handling
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s\nResponse: %s", str(e), json_str)
            return None

    except Exception as e:
        # Provide more context in the error
        logger.error("Error extracting data from table: %s", str(e))
        return None
