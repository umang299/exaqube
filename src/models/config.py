from dataclasses import dataclass
from typing import Any
import yaml

@dataclass
class ScrapperConfig:
    url: str
    download_link: str
    output_dir: str

@dataclass
class Config:
    scrapper: ScrapperConfig

    @classmethod
    def from_yaml(cls, filepath: str) -> "Config":
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        return cls(scrapper=ScrapperConfig(**data["scrapper"]))

    def to_dict(self) -> dict:
        return {
            "scrapper": {
                "url": self.scrapper.url,
                "download_link": self.scrapper.download_link,
                "output_dir" : self.scrapper.output_dir
            }
        }
