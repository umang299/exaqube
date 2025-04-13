from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from PIL import Image

class Table(BaseModel):
    img: Any
    pdf_file: str
    page_no: str
