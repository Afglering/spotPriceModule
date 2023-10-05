# Purpose: Setup logging for the application

import logging


# Setup logging to file app.log
def setup_logging():
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


setup_logging()
