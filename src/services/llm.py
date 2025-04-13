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


cwd = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(cwd)

from src.models.config import Config
from src.models.extractor import Table, ShippingTariff
from src.logger import setup_console_and_file_logging

logger = setup_console_and_file_logging(level=logging.INFO,
                                        logger_name=__name__)

load_dotenv(os.path.join(cwd, '.env'))

class ParseTables:
    """
    Parse table images using OpenAI vision model.
    
    This class handles the extraction of structured data from table images
    using OpenAI's image understanding capabilities.
    
    Attributes:
        prompt_path (str): Path to the prompt file for OpenAI.
        model_name (str): Name of the OpenAI model to use.
        prompt (str): The prompt text loaded from the prompt file.
        client (OpenAI): OpenAI client instance.
    """
    def __init__(self, config: Config):
        """
        Initialize the table parser with configuration settings.
        
        Args:
            config (Config): Configuration object containing OpenAI settings.
        """
        logger.info("Initializing ParseTables with configuration")
        self.prompt_path = os.path.join(cwd, 'assets', config.openai.prompt_file)
        self.model_name = config.openai.model_name

         # Load prompt from file
        if self.prompt_path.endswith('.txt'):
            try:
                with open(self.prompt_path, 'r', encoding='utf-8') as f:
                    self.prompt = f.read()
                logger.info("Successfully loaded prompt from %s", self.prompt_path)
            except Exception as e:
                logger.error("Failed to read prompt file: %s", str(e))
                self.prompt = None
        else:
            logger.error("Invalid prompt file extension: %s", self.prompt_path)
            self.prompt = None


        # Initialize OpenAI client
        api_key = os.environ.get('OPENAI')
        if not api_key:
            logger.error("OPENAI environment variable not set")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info("Successfully initialized OpenAI client")
            except Exception as e:
                logger.error("Failed to initialize OpenAI client: %s", str(e))
                self.client = None
    
    def pil_to_base64(self, image: Image.Image) -> str:
        """
        Convert a PIL Image to base64 string for API transmission.
        
        Args:
            image (Image.Image): PIL Image object to convert.
            
        Returns:
            str: Base64-encoded string representation of the image.
            
        Raises:
            IOError: If image conversion fails.
        """
        try:
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return img_str
        except Exception as e:
            logger.error("Failed to convert image to base64: %s", str(e))
            return None
    
    def run(self, ip: Table):
        """
        Process a table image and extract structured data.
        
        This method sends the table image to OpenAI's vision model and
        parses the response into structured shipping tariff data.
        
        Args:
            ip (Table): Table object containing the image to process.
            
        Returns:
            list: List of ShippingTariff objects if successful, None otherwise.
            
        Raises:
            ValueError: If input validation fails.
            RuntimeError: If API request or processing fails.
        """
        logger.info("Processing table from %s, page %s", getattr(ip, 'pdf_file', 'unknown'), getattr(ip, 'page_no', 'unknown'))
        
        # Validate inputs
        if not self.prompt:
            logger.error("No prompt available. Cannot process table")
            return None
            
        if not self.client:
            logger.error("No OpenAI client available. Cannot process table")
            return None
            
        if not hasattr(ip, 'img') or not isinstance(ip.img, Image.Image):
            logger.error("Invalid input: not a PIL Image")
            return None
        
        try:
            # Convert image to base64
            logger.debug("Converting image to base64")
            enc_img = self.pil_to_base64(image=ip.img)
            
            # Call OpenAI API
            logger.info("Sending request to OpenAI API (model: %s)", self.model_name)
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": self.prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{enc_img}"
                                }
                            }
                        ]
                    }
                ]
            )
            logger.debug("Received response from OpenAI API")

            # Extract response text
            if hasattr(response, 'choices') and len(response.choices) > 0:
                response_text = response.choices[0].message.content
            else:
                logger.error("Unexpected response format from OpenAI API")
                return None

            # Clean and parse JSON response
            json_str = response_text.replace('```json', '').replace('```', '').strip()
            logger.debug("Parsing JSON response")
            
            try:
                json_obj = json.loads(json_str)
                resp = []
                for i in json_obj:
                    try:
                        # Explicit type casting to handle unexpected types
                        i["Bucket_1"] = int(i["Bucket_1"]) if i.get("Bucket_1") not in [None, "null", ""] else None
                        i["Bucket_2"] = int(i["Bucket_2"]) if i.get("Bucket_2") not in [None, "null", ""] else None
                        i["Bucket_3"] = int(i["Bucket_3"]) if i.get("Bucket_3") not in [None, "null", ""] else None
                        i["Free_days"] = int(i["Free_days"]) if i.get("Free_days") is not None else None

                        # Normalize missing values
                        i["Liner_Name"] = i.get("Liner_Name") or None
                        i["Port"] = i.get("Port") or None

                        resp.append(ShippingTariff(**i))
                        logger.info("Successfully extracted %d tariff entries", len(resp))
                    except Exception as e:
                        logger.warning("Skipping invalid record due to parsing error: %s", str(e))
                return resp
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON response: %s", str(e))
                logger.debug("Response content: %s", json_str[:500] + "..." if len(json_str) > 500 else json_str)
                return None
            except Exception as e:
                logger.error("Error creating ShippingTariff objects: %s", str(e))
                return None
                
        except Exception as e:
            logger.error("Error processing table: %s", str(e))
            return None
