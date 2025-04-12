from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TariffEntry:
    country: str
    inPdfName: str
    outPdfName: str
    inIddsPdfUuid: str
    outIddsPdfUuid: str
    content: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TariffEntry':
        return cls(
            country=data.get('country', ''),
            inPdfName=data.get('inPdfName', ''),
            outPdfName=data.get('outPdfName', ''),
            inIddsPdfUuid=data.get('inIddsPdfUuid', ''),
            outIddsPdfUuid=data.get('outIddsPdfUuid', ''),
            content=data.get('content', '')
        )
