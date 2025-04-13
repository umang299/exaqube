import os
import sys
import torch
import logging
from PIL import Image
from ultralytics import YOLO
from pdf2image import convert_from_path


cwd = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(cwd)

from src.models.config import Config
from src.models.extractor import Table
from src.logger import setup_console_and_file_logging

cfg = Config.from_yaml(filepath=os.path.join(
                cwd, 'src', 'config.yaml'
            ))
logger = setup_console_and_file_logging(
                    level=logging.INFO, 
                    logger_name=__name__
                )

class Extractor:
    """
    Extract tables from PDF documents using YOLO object detection.
    
    This class provides functionality to convert PDFs to images, detect tables
    using a YOLO model, and extract the detected tables as cropped images.
    
    Attributes:
        cfg (Config): Configuration object containing extraction settings.
        is_gpu_available (bool): Whether GPU is available for processing.
        conf_thrs (float): Confidence threshold for object detection.
        iou_thrs (float): IoU threshold for object detection.
        output_dir (str): Directory to store extracted images.
        model (YOLO): Loaded YOLO model for table detection.
    """
    def __init__(self, config: Config):
        """
        Initialize the Extractor with configuration settings.
        
        Args:
            config (Config): Configuration object with extraction parameters.
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
                    ):
        """
        Convert PDF document to high-resolution PNG images.
        
        Args:
            pdf_path (str): Path to the input PDF file.
            
        Returns:
            bool: True if conversion was successful, None if failed.
            
        Raises:
            Exception: Any error that occurs during PDF conversion.
        """
        try:
            logger.info("Converting PDF to images: %s", pdf_path)

            # Get poppler path from config or use default
            poppler_path = r'C:\2025\exaqube\poppler-24.08.0\Library\bin'

            # Convert PDF to images with appropriate parameters
            conversion_kwargs = {'dpi': 300}
            if poppler_path:
                conversion_kwargs['poppler_path'] = poppler_path

            images = convert_from_path(pdf_path, **conversion_kwargs)

            count = 0
            filename = os.path.basename(pdf_path).replace('.pdf', '')
            filename = filename.replace(' ', '_')
            for i, img in enumerate(images):
                # Use a consistent naming convention with page numbers
                image_path = os.path.join(
                                    self.output_dir, 
                                    f"{filename}_page_{i+1}.png"
                                )
                img.save(image_path, 'PNG')
                count += 1

            logger.info("Converted %s pages to images", count)
            del count
            return True

        except Exception as e:
            logger.error("Error converting PDF to images: %s", str(e))
            return None

    def load_model(self, model_path: str) -> YOLO:
        """
        Load and initialize the YOLO model.
        
        Args:
            model_path (str): Path to the YOLO model weights file.
            
        Returns:
            YOLO: Initialized YOLO model, or None if loading failed.
            
        Raises:
            Exception: Any error that occurs during model loading.
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
                ):
        """
        Perform object detection on an image to identify tables.
        
        Args:
            image_path (str): Path to the input image file.
            
        Returns:
            object: Detection boxes from YOLO model, or None if detection failed.
            
        Raises:
            Exception: Any error that occurs during prediction.
        """
        try:
            logger.info("Running detection on: %s", image_path)
            results = self.model(
                image_path, 
                conf=self.conf_thrs, 
                iou=self.iou_thrs
            )[0]
            logger.info("Detection found %s potential regions", len(results.boxes))
            return results.boxes

        except Exception as e:
            logger.error("Error during prediction: %s", str(e))
            return None
    
    def extract_tables(self,
                    image,
                    detections):
        """
        Extract table regions from detection results.
        
        Args:
            image (PIL.Image.Image): Original image to crop from.
            detections (object): Detection boxes from the YOLO model.
            
        Returns:
            list: List of cropped PIL Image objects containing tables,
                 or None if no tables were found or extraction failed.
            
        Raises:
            Exception: Any error that occurs during table extraction.
        """
        try:
            response = []
            # Process each detection
            logger.info("Processing %s potential detections", len(detections))

            for i, conf in enumerate(detections.conf):
                # Skip low confidence detections
                conf_value = conf.detach().cpu().numpy()
                label = detections.cls.detach().cpu().numpy()
                
                # Check if this is a table (class 8) with sufficient confidence
                if conf_value >= 0.2 and label[i] == 8:
                    # Get bounding box coordinates
                    xyxy = detections.xyxy[i].detach().cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)
                    cropped_region = image.crop((x1, y1, x2, y2))
                    response.append(cropped_region)
                    # logger.info(f"Extracted table from {filename}: {x1}_{y1}_{x2}_{y2}")
            
            # Return the list of tables if any were found, otherwise None
            if response:
                logger.info("Extracted %s tables", len(response))
                return response
            else:
                logger.info("No tables found")
                return None

        except Exception as e:
            logger.error("Error extracting patches: %s",str(e))
            return None
    
    def clear_pdfs(self, country: str):
        """
        Remove all PDF files for a specified country.
        
        Args:
            country (str): Country name, corresponding to the directory name.
        """
        pdf_dir = os.path.join(cwd, 'downloads', country)
        for filename in os.listdir(pdf_dir):
            file_path = os.path.join(pdf_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)

    def clear_images(self):
        """
        Remove all temporary image files from the output directory.
        """
        for filename in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)


    def run(self, country: str):
        """
        Execute the complete extraction pipeline for all PDFs of a country.
        
        This method:
        1. Converts all PDFs to images
        2. Detects and extracts tables from each image
        3. Creates Table objects with extracted information
        
        Args:
            country (str): Country name, used to locate PDF files.
            
        Returns:
            list: List of Table objects containing extracted tables,
                 or empty list if no tables were found or extraction failed.
        """
        pdf_dir = os.path.join(cwd, 'downloads', country)
        conv_status = list()
        for filename in os.listdir(pdf_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(pdf_dir, filename)
                temp = self.convert_pdf2img(pdf_path=file_path)
            else:
                temp = False
            conv_status.append(temp)

        ## if conversion successfull
        result = list()
        if all(conv_status):
            self.clear_pdfs(country=country)
            for filename in os.listdir(self.output_dir):    # [pdf_file_basename_page_1.png]
                img_path = os.path.join(self.output_dir, filename)
                if img_path.endswith('.png'):
                    img = Image.open(img_path)
                    dets = self.prediction(image_path=img_path)
                    tables = self.extract_tables(image=img, detections=dets)    # [PIL OBJ, PIL OBJ]
                    if tables is not None:
                        if len(tables) > 1:
                            for tab in tables:
                                table_info = {
                                    "img" : tab,     # PIL OBJ
                                    "pdf_file" : f"{filename[:-10]}.pdf",
                                    "page_no" : f"{filename[-10:].replace('.png', '')}"
                                }
                                result.append(Table(**table_info))
                        else:
                            result.append(Table(**{
                                "img" : tables[0],     # PIL OBJ
                                "pdf_file" : f"{filename[:-10]}.pdf",
                                "page_no" : f"{filename[-10:].replace('.png', '')}"
                            }))

                    else:
                        logger.info('No tables found')
                else:
                    logger.info('Invalid Input')
            
            if len(result) == 0:
                logger.info('No table found')
        else:
            logger.info('Failed to convert to images')
        return result
