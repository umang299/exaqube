# Shipping Tariff Extractor

This project automates the extraction of shipping line tariffs from multiple sources, including websites and PDF documents. It leverages web scraping, PDF processing, computer vision, and AI technologies to retrieve, extract, and store structured tariff data.

## Overview

The Shipping Tariff Extractor is designed to:

1. Scrape shipping tariff data from multiple sources:
   - COSCO Shipping - Task 2

2. Process different data formats:
   - PDF documents from COSCO Shipping

3. Extract structured tariff information including:
   - Country, port, and shipping line details
   - Equipment types and specifications
   - Free days and demurrage charges across different time buckets
   - Currency information

4. Store the extracted data in a SQLite database with a standardized schema

## Architecture

The project follows a modular architecture with the following components:

- **API Layer**: FastAPI endpoints for triggering data extraction and retrieval
- **Scraper Service**: Handles web interaction and file downloads
- **Extractor Service**: Converts PDFs to images and identifies tables using computer vision
- **LLM Service**: Uses OpenAI to parse tables and extract structured data
- **Database Service**: Manages storage and retrieval of processed data

### Key Technologies

- **Python 3.11**: Core programming language
- **FastAPI**: Web framework for API endpoints
- **YOLOv11**: Object detection for identifying tables in documents
- **OpenAI GPT-4o**: Vision model for parsing table data
- **SQLite**: Database for storing structured tariff information
- **Docker**: Containerization for deployment

## Prerequisites

Before setting up the project, ensure you have:

- Python 3.11 or higher
- [Poppler](https://poppler.freedesktop.org/) (PDF rendering library required by pdf2image)
- OpenAI API key
- Docker (optional, for containerized deployment)

## Installation

### Option 1: Pre-built Docker Image (Recommended)

The easiest way to get started is with the pre-built Docker image:

1. Pull the Docker image:
   ```bash
   docker pull umang299/shipping-tariff-scraper
   ```

2. Run the container with your OpenAI API key:
   ```bash
   docker run -p 8000:8000 -e OPENAI=your_openai_api_key_here umang299/shipping-tariff-scraper
   ```

3. Access the API at `http://localhost:8000`

This option requires no setup beyond Docker installation and provides all dependencies pre-configured.

### Option 2: Local Setup

If you prefer to run the application locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/umang299/exaqube.git
   cd exaqube
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Poppler:
   - **Linux**: `sudo apt-get install poppler-utils`
   - **macOS**: `brew install poppler`
   - **Windows**: Download binaries from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases/)
     - Extract to a directory (e.g., `./poppler-24.08.0/`)
     - Add the `bin` directory to your PATH

5. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI=your_openai_api_key_here
   ```

### Option 3: Build Your Own Docker Image

If you need to customize the Docker setup:

1. Clone the repository:
   ```bash
   git clone <your-repository-url>
   cd shipping-tariff-extractor
   ```

2. Build the Docker image:
   ```bash
   docker build --build-arg OPENAI_API_KEY=your_openai_api_key_here -t shipping-tariff-extractor .
   ```

3. Run the container:
   ```bash
   docker run -p 8000:8000 shipping-tariff-extractor
   ```

## Project Structure

```
.
├── assets/                        # Static assets
│   ├── countries.txt              # List of countries for scraping
│   └── prompt.txt                 # Prompt for OpenAI image analysis
├── src/                           # Source code
│   ├── models/                    # Data models
│   │   ├── config.py              # Configuration models
│   │   ├── extractor.py           # Extractor models
│   │   └── scrapper.py            # Scraper models
│   ├── services/                  # Service implementations
│   │   ├── extractor.py           # PDF/image processing service
│   │   ├── llm.py                 # OpenAI integration service
│   │   ├── scrapper.py            # Web scraping service
│   │   └── sqlite.py              # Database service
│   ├── config.yaml                # Configuration settings
│   └── logger.py                  # Logging setup
├── downloads/                     # Downloaded files (created at runtime)
├── output_images/                 # Processed images (created at runtime)
├── main.py                        # FastAPI application entry point
├── Dockerfile                     # Docker configuration
├── requirements.txt               # Python dependencies
└── README.md                      # Project documentation
```

## Configuration

The project configuration is stored in `src/config.yaml`. Key configuration options include:

- **Scraper settings**: URLs for COSCO shipping data and download links
- **Extractor settings**: YOLO model parameters and image paths
- **OpenAI settings**: Model name and prompt file location
- **Database settings**: SQLite database file name

You can modify these settings to adjust the behavior of the application.

## Usage

### Running the API Server

Start the FastAPI server:

```bash
# Local setup
uvicorn main:app --reload

# Docker setup
# If using the pre-built image or your own Docker image, the server starts automatically
```

The API will be available at `http://localhost:8000`.

You can also access the interactive API documentation at `http://localhost:8000/docs`.

### API Endpoints

1. **Upload Tariff Data**:
   ```
   POST /upload?country={country_name}
   ```
   This endpoint initiates the scraping, extraction, and storage process for the specified country.

2. **Fetch All Records**:
   ```
   GET /fetch
   ```
   This endpoint retrieves all processed tariff records from the database.

### Example Usage

Here's how to use the API with cURL:

```bash
# Upload tariff data for India
curl -X POST "http://localhost:8000/upload?country=India"

# Fetch all records
curl -X GET "http://localhost:8000/fetch"
```

Or using Python:

```python
import requests

# Upload tariff data for India
response = requests.post("http://localhost:8000/upload", params={"country": "India"})
print(response.json())

# Fetch all records
response = requests.get("http://localhost:8000/fetch")
print(response.json())
```
## Task 2: COSCO Shipping (Implemented)

Task 2 extracts tariff data from COSCO Shipping PDFs:

1. The scraper retrieves PDF documents from COSCO's website
2. PDFs are converted to images
3. Computer vision (YOLO) detects table regions in the images
4. OpenAI's vision model parses the tables into structured data
5. The parsed data is stored in SQLite

## Extending the Project

To extend the project for additional shipping lines:

1. Create a new scraper service in `src/services/`
2. Add appropriate data models in `src/models/`
3. Update the FastAPI endpoints in `main.py`
4. Configure the new services in `src/config.yaml`

## Troubleshooting

### Common Issues

1. **PDF Conversion Errors**:
   - Ensure Poppler is correctly installed and in your PATH (only for local setup)
   - Check the conversion parameters in `extractor.py`
   - When using Docker, these dependencies are pre-installed

2. **OpenAI API Errors**:
   - Verify your API key is correctly set (in the `.env` file for local setup or as an environment variable for Docker)
   - Check API usage limits and quotas
   - Ensure your OpenAI account has access to the GPT-4o model

3. **YOLO Model Loading Errors**:
   - Ensure sufficient disk space for the model download (approximately 500MB)
   - Check GPU availability with `torch.cuda.is_available()`
   - The Docker image comes with necessary CUDA libraries for GPU support

4. **Website Structure Changes**:
   - The scraper depends on specific website structures. If websites change, update the selectors in the scraper service

5. **Docker-Specific Issues**:
   - If using the pre-built image and encountering errors, try building your own image for more control
   - For permission issues with volume mounts, ensure proper permissions are set

### Logs

Logs are stored in `app.log` and are also printed to the console. When using Docker, you can view logs with:

```bash
# For the pre-built image
docker logs <container_id>

# Or stream logs in real-time
docker logs -f <container_id>
```

Check these logs for detailed information about any issues.

## License

[Specify your license here]

## Acknowledgements

- YOLOv11 Document Layout Analysis: https://github.com/moured/YOLOv11-Document-Layout-Analysis
- OpenAI for API access
- COSCO Shipping and Emirates Line for the tariff data