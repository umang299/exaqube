import os
import sys
import torch
import easyocr
import numpy as np
from PIL import Image
from ultralytics import YOLO
from pdf2image import convert_from_path
import logging
from typing import List, Dict, Tuple, Any, Optional


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

from src.models.config import Config

cfg = Config.from_yaml(filepath=os.path.join(
                cwd, 'src', 'config.yaml'
            ))

class Extractor:
    """
    Class for extracting text from tables in PDF documents using object detection and OCR.
    
    This class implements a pipeline to:
    1. Convert PDF pages to images
    2. Detect tables or regions of interest using a YOLO model
    3. Extract text from these regions using EasyOCR
    """

    def __init__(self, config: Config):
        """
        Initialize the extractor with model and OCR settings.
        
        Args:
            config: Configuration object (optional)
        """
        # Use provided config or import if not provided
        self.cfg = config
            
        # Check for GPU availability
        self.is_gpu_available = torch.cuda.is_available()
        logger.info(f"GPU available: {self.is_gpu_available}")

        # Set configuration values
        self.conf_thrs = self.cfg.extractor.conf_thrs
        self.iou_thrs = self.cfg.extractor.iou_thrs

        # Setup directories
        self.output_dir = os.path.join(cwd, self.cfg.extractor.img_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        # Load model
        model_path = os.path.join(cwd, 'assets', self.cfg.extractor.model_name)
        logger.info(f"Loading YOLO model from: {model_path}")
        self.model = self.load_model(model_path=model_path)

        # Setup OCR
        logger.info("Initializing EasyOCR")
        self.ocr = self.setup_ocr()

    def convert_pdf2img(self,
                        pdf_path: str
                    ) -> List[str]:
        """
        Convert PDF pages to images.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of paths to the generated images
        """
        try:
            logger.info(f"Converting PDF to images: {pdf_path}")

            # Get poppler path from config or use default
            poppler_path = r'C:\2025\exaqube\poppler-24.08.0\Library\bin'

            # Convert PDF to images with appropriate parameters
            conversion_kwargs = {'dpi': 300}
            if poppler_path:
                conversion_kwargs['poppler_path'] = poppler_path

            images = convert_from_path(pdf_path, **conversion_kwargs)

            image_paths = []
            for i, img in enumerate(images):
                # Use a consistent naming convention with page numbers
                image_path = os.path.join(self.output_dir, f"page_{i+1}.png")
                img.save(image_path, 'PNG')
                image_paths.append(image_path)

            logger.info("Converted %s pages to images", len(images))
            return True

        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return None

    def load_model(self, model_path: str) -> YOLO:
        """
        Load the YOLO model for object detection.
        
        Args:
            model_path: Path to the YOLO model file
            
        Returns:
            Loaded YOLO model
        """
        try:
            if self.is_gpu_available:
                model = YOLO(model_path).to(device='cuda')
                logger.info("Model loaded on GPU")
            else:
                model = YOLO(model_path)
                logger.info("Model loaded on CPU")
            return model
        except Exception as e:
            logger.error("Error loading model: %s", str(e))
            return None

    def setup_ocr(self) -> easyocr.Reader:
        """
        Set up the OCR reader.
        
        Returns:
            Configured EasyOCR Reader object
        """
        try:
            # Get languages from config if available, otherwise default to English
            languages = getattr(self.cfg.extractor, 'ocr_languages', ['en'])

            reader = easyocr.Reader(
                lang_list=languages,
                gpu=self.is_gpu_available,
                # Add any additional parameters from config if needed
                detector=getattr(self.cfg.extractor, 'detector', True),
                recognizer=getattr(self.cfg.extractor, 'recognizer', True)
            )
            return reader
        except Exception as e:
            logger.error("Error setting up OCR: %s", str(e))
            return None

    def prediction(self, 
                   image_path: str
                ) -> Tuple[Any, Image.Image]:
        """
        Perform object detection on an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple containing detection boxes and the PIL image
        """
        try:
            logger.info("Running detection on: %s", image_path)
            
            # Load image
            image = Image.open(image_path)
            
            # Run inference
            results = self.model(
                image_path, 
                conf=self.conf_thrs, 
                iou=self.iou_thrs
            )[0]
            
            logger.info("Detection found %s potential regions", len(results.boxes))
            return results.boxes, image

        except Exception as e:
            logger.error("Error during prediction: %s", str(e))
            return None
    
    def extract_boxes(self, image: Image.Image, detections: Any) -> Dict[int, str]:
        """
        Extract text from detected regions using OCR.
        
        Args:
            image: PIL Image object
            detections: Detection boxes from YOLO model
            
        Returns:
            Dictionary mapping region indices to extracted text
        """
        try:
            response = {}
            
            # Process each detection
            for i, conf in enumerate(detections.conf):
                # Skip low confidence detections
                conf_value = conf.detach().cpu().numpy()
                if conf_value < self.conf_thrs:
                    continue
                
                # Get bounding box coordinates
                xyxy = detections.xyxy[i].detach().cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)
                
                # Crop the region
                cropped_region = image.crop((x1, y1, x2, y2))
                
                # Apply OCR to the cropped region
                ocr_result = self.ocr.readtext(np.array(cropped_region))
                
                # Extract and join the text
                if ocr_result:
                    response[i] = "\n".join([text for _, text, _ in ocr_result])
                    logger.debug(f"Region {i} text: {response[i][:50]}...")
                else:
                    logger.warning(f"No text detected in region {i}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error extracting text from boxes: {e}")
            raise
    
    def run(self, pdf_file: str) -> Dict[str, Dict[int, str]]:
        """
        Run the complete extraction pipeline on a PDF file.
        
        Args:
            pdf_file: Path to the PDF file
            
        Returns:
            Dictionary mapping page filenames to extracted text regions
        """
        try:
            logger.info("Processing PDF file: %s", pdf_file)
            # Check if PDF file exists
            if not os.path.exists(pdf_file):
                raise FileNotFoundError("PDF file not found: %s", pdf_file)

            # Clear output directory
            for file in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            # Convert PDF to images
            conversion_status = self.convert_pdf2img(pdf_path=pdf_file)
            if not conversion_status:
                logger.error('Failed to convert pdf file %s to images.', pdf_file)
                return None

            # Process each image
            resp = {}
            for filename in os.listdir(self.output_dir):
                logger.info(f"Processing image: {filename}")
                img_path = os.path.join(self.output_dir, filename)

                # Run detection and OCR
                predictions = self.prediction(image_path=img_path)
                if predictions is None:
                    return None

                text = self.extract_boxes(image=predictions[1],
                                          detections=predictions[0])

                # Store results
                resp[filename] = text
                
                # Clean up
                os.remove(img_path)
                logger.debug(f"Removed temporary image: {img_path}")
            
            logger.info(f"Completed processing PDF: {pdf_file}")
            return resp

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            # Attempt to clean up any temporary files
            for file in os.listdir(self.output_dir):
                try:
                    file_path = os.path.join(self.output_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except:
                    pass
            return None