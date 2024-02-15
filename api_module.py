# Purpose: This module contains functions for communicating with the API
import logging
import time

import requests


def make_api_request(url, api_key=None, max_retries=3):
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            status_code = response.status_code

            if status_code == 200:
                logging.info(f"Successfully fetched data from {url}.")
                return response.json(), status_code
            elif status_code == 401:  # Unauthorized
                logging.error(f"Unauthorized access to the API {url}. Check your API key.")
                break
            elif status_code == 429:  # Too Many Requests
                logging.warning(f"Rate limit exceeded for the API {url}.")
                if attempt < max_retries - 1:
                    time.sleep(60)  # Wait for 60 seconds before the next attempt
            else:
                logging.warning(f"Failed to fetch data from {url}. Attempt {attempt + 1}. Status code: {status_code}. Retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        except requests.RequestException as e:
            logging.error(f"An error occurred while fetching data from {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

    logging.error(f"Failed to fetch data from {url} after {max_retries} attempts.")
    return None, status_code if 'status_code' in locals() else 'N/A'


# Validate the API key for the exchange rate API
def validate_exchange_rate_api_key(api_key, exchange_rate_api_url):
    response, status_code = make_api_request(exchange_rate_api_url, api_key)
    if status_code == 200:
        logging.info("Successfully validated the exchange rate API key.")
        return True
    elif status_code == 401:
        logging.error("Invalid API key for the exchange rate API.")
    else:
        logging.warning("Unable to validate API key for the exchange rate API.")
    return False


# Fetch the exchange rate from the API
def fetch_exchange_rate(api_key, exchange_rate_api_url):
    response, status_code = make_api_request(exchange_rate_api_url, api_key)
    if response and 'rates' in response and 'EUR' in response['rates']:
        logging.info("Successfully fetched exchange rate.")
        return response['rates']['EUR']
    logging.info(f"Failed to fetch exchange rate.")
    return None


# Fetch the electricity prices from the API
def fetch_electricity_prices(electricity_prices_api_url):
    response, status_code = make_api_request(electricity_prices_api_url)
    if response:
        logging.info("Successfully fetched electricity prices.")
        return response, status_code
    logging.error("Failed to fetch electricity prices.")
    return None, status_code