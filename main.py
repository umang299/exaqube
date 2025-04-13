import os
from fastapi import FastAPI, Query
from src.services.scrapper import Scraper
from src.services.extractor import Extractor
from src.services.llm import ParseTables
from src.services.sqlite import TariffDB
from src.models.config import Config

app = FastAPI(
    title="Shipping Tariff Extractor",
    description="API to scrape, extract, parse and store shipping tariff data",
    version="1.0.0"
)

# Load config
cfg = Config.from_yaml(filepath=os.path.join(
    os.getcwd(),
    'src', 'config.yaml'
))


# Initialize services
scrap_serv = Scraper()
ex_serv = Extractor(config=cfg)
parser = ParseTables(config=cfg)
db = TariffDB(config=cfg)


@app.post("/upload")
def upload_data(country: str):
    """
    Scrape, extract and store tariff data for a given country.
    """
    scrap_serv.run(country=country)
    tables = ex_serv.run(country=country)
    ex_serv.clear_images()

    count = 0
    for tab in tables:
        parsed = parser.run(ip=tab)
        if not parsed:
            continue
        for i in parsed:
            status = db.insert_record(data=i.values())
            if status:
                count += 1
    return {"inserted_records": count}


@app.get("/fetch")
def fetch_records():
    """
    Fetch all records from the database.
    """
    records = db.fetch_records()
    return {"records": records}
