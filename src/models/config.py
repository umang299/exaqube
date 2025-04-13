from dataclasses import dataclass
from typing import Any
import yaml

@dataclass
class ScrapperConfig:
    url: str
    download_link: str
    output_dir: str

@dataclass
class ExtractorConfig:
    conf_thrs: float
    iou_thrs: float
    img_dir: str
    model_name: str

@dataclass
class OpenaiConfig:
    model_name: str
    prompt_file: str

@dataclass
class Config:
    scrapper: ScrapperConfig
    extractor: ExtractorConfig
    openai: OpenaiConfig

    @classmethod
    def from_yaml(cls, filepath: str) -> "Config":
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        return cls(scrapper=ScrapperConfig(**data["scrapper"]),
                   extractor=ExtractorConfig(**data["extractor"]),
                   openai = OpenaiConfig(**data['openai'])
                   )

    def to_dict(self) -> dict:
        return {
            "scrapper": {
                "url": self.scrapper.url,
                "download_link": self.scrapper.download_link,
                "output_dir" : self.scrapper.output_dir
            },
            "extractor": {
                "conf_thrs" : self.extractor.conf_thrs,
                "iou_thrs" : self.extractor.iou_thrs,
                "img_dir" : self.extractor.img_dir,
                "model_name" : self.extractor.model_name
            },
            "openai" : {
                "model_name" : self.openai.model_name,
                "prompt_file" : self.openai.prompt_file
            }
        }
