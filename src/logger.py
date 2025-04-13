import logging

def setup_console_and_file_logging(
    logger_name: str = "src.services.default",
    level: int = logging.INFO,
    log_file: str = "app.log"
):
    """Sets up logging to print logs on the console and write to a log file."""
    
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Define log format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Remove existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger
