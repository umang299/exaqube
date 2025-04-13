from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from PIL import Image

class ShippingTariff(BaseModel):
    Country: str
    Type: str  # Inbound or outbound i.e. IB/OB
    Liner_Name: Optional[str] = None  # return null if not found in table
    Port: Optional[str] = None        # return null if not found in table
    Equipment_Type: str              # Equipment code
    Currency: str
    Free_days: int                   # Number of free days
    Bucket_1: Optional[int] = None   # $min/$max
    Bucket_2: Optional[int] = None   # $min/$max
    Bucket_3: Optional[int] = None   # $min/$max

    def values(self) -> tuple:
        return (
            self.Country,
            self.Type,
            self.Liner_Name,
            self.Port,
            self.Equipment_Type,
            self.Currency,
            self.Free_days,
            self.Bucket_1,
            self.Bucket_2,
            self.Bucket_3,
        )

class Table(BaseModel):
    img: Any
    pdf_file: str
    page_no: str
    tariff: Optional[List[ShippingTariff]] = None