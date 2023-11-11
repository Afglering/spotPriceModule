# Purpose: Setup logging for the application and read the config file.
import json


# Read config file
def read_config(filename='config.json'):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError:
        raise


config = read_config()

# Get config values
AUTHORIZED_IDS = config['AUTHORIZED_IDS']
api_key = config['API_KEY']
max_retries = config['MAX_RETRIES']
timeout = config['TIMEOUT']
exchange_rate_api_url = config['EXCHANGE_RATE_API_URL']
electricity_prices_api_url = config['ELECTRICITY_PRICES_API_URL']

# PLC config
scaling_factor = config['SCALING_FACTOR']
unit_id = config['UNIT_ID']
