import os
import sys
import torch
import numpy as np
from PIL import Image
from ultralytics import YOLO
from pdf2image import convert_from_path
import logging
from typing import List, Dict, Tuple, Any


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
    Extracts tables from PDF documents using YOLO object detection and image processing.
    
    This class implements a pipeline to:
    1. Convert PDF pages to high-resolution images
    2. Detect tables or regions of interest using a pre-trained YOLO model
    3. Extract table regions as cropped image patches
    
    The extractor focuses on identifying specific table structures based on 
    object detection confidence thresholds and class labels.
    """
    def __init__(self, config: Config):
        """
        Initialize the extractor with configuration settings and model resources.
        
        Args:
            config: Configuration object containing settings for extraction
                   parameters, file paths, and model configurations
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

    def convert_pdf2img(self,
                        pdf_path: str
                    ) -> List[str]:
        """
        Convert PDF document pages to high-resolution PNG images.
        
        Args:
            pdf_path: Path to the input PDF file
            
        Returns:
            bool: True if conversion was successful, None otherwise
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
        Load and initialize the YOLO object detection model.
        
        Args:
            model_path: Path to the YOLO model weights file
            
        Returns:
            YOLO: Initialized model object if successful, None otherwise
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

    def prediction(self, 
                   image_path: str
                ) -> Tuple[Any, Image.Image]:
        """
        Perform object detection to identify table regions in an image.
        
        Args:
            image_path: Path to the input image file
            
        Returns:
            Tuple containing detection boxes and the original PIL image,
            or None if detection failed
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
        Extract table regions from detected bounding boxes.
        
        Args:
            image: Original PIL Image object
            detections: Detection boxes from YOLO model
            
        Returns:
            List of cropped image regions containing detected tables,
            filtered by confidence threshold and class ID 8
        """
        try:
            response = list()
            # Process each detection
            for i, conf in enumerate(detections.conf):
                # Skip low confidence detections
                conf_value = conf.detach().cpu().numpy()
                label = detections.cls.detach().cpu().numpy()
                if conf_value >= 0.2 and label[i] == 8:
                    # Get bounding box coordinates
                    xyxy = detections.xyxy[i].detach().cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)

                    # Crop the region
                    cropped_region = image.crop((x1, y1, x2, y2))
                    response.append(cropped_region)
            return response
            
        except Exception as e:
            logger.error("Error extracting patches from images: %s", str(e))
            return None
    
    def run(self, pdf_file: str) -> Dict[str, Dict[int, str]]:
        """
        Execute the complete table extraction pipeline on a PDF document.
        
        Process includes converting PDF to images, detecting tables, and 
        extracting table regions as image patches.
        
        Args:
            pdf_file: Path to the input PDF file
            
        Returns:
            Dictionary mapping page filenames to lists of extracted table images,
            or None if processing failed at any stage
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
                logger.info("Processing image: %s", filename)
                img_path = os.path.join(self.output_dir, filename)

                # Run detection and OCR
                predictions = self.prediction(image_path=img_path)
                if predictions is None:
                    return None

                table_patches = self.extract_boxes(
                                        image=predictions[1],
                                        detections=predictions[0]
                                    )

                # Store results
                resp[filename] = table_patches
                
                # Clean up
                os.remove(img_path)
                logger.debug("Removed temporary image: %s", img_path)
            
            logger.info("Completed processing PDF: %s",pdf_file)
            return resp

        except Exception as e:
            logger.error("Error processing PDF: %s",str(e))
            # Attempt to clean up any temporary files
            for file in os.listdir(self.output_dir):
                try:
                    file_path = os.path.join(self.output_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except:
                    pass
            return None