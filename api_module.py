# Purpose: This module contains functions for communicating with the API
import json
import logging
import time

import requests


# Validate the API key for the exchange rate API
def validate_exchange_rate_api_key(api_key, exchange_rate_api_url):
    try:
        response = requests.get(exchange_rate_api_url)
        if response.status_code == 401:
            logging.error("Invalid API key for the exchange rate API.")
            return False
        elif response.status_code != 200:
            logging.warning("Unable to validate API key for the exchange rate API.")
            return False
        logging.info("Successfully validated the exchange rate API key.")
        return True
    except requests.RequestException as e:
        logging.error(f"An error occurred while validating the API key: {e}")
        return False


# Fetch the exchange rate from the API
def fetch_exchange_rate(api_key, exchange_rate_api_url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(exchange_rate_api_url)
        status_code = response.status_code

        if status_code == 200:
            logging.info("Successfully fetched exchange rate.")
            return response.json()['rates']['EUR']
        elif status_code == 401:  # Unauthorized
            logging.error("Unauthorized access to the exchange rate API. Check your API key.")
            break
        elif status_code == 429:  # Too Many Requests
            logging.warning("Rate limit exceeded for the exchange rate API.")
            time.sleep(60)  # Wait for 60 seconds before the next attempt
        else:
            logging.warning(f"Failed to fetch exchange rate. Attempt {attempt + 1}. Status code: {status_code}. "
                            f"Retrying...")
            time.sleep(2 ** attempt)

    logging.info(f"Failed to fetch exchange rate after {max_retries} attempts.")
    return None


# Fetch the electricity prices from the API
def fetch_electricity_prices(electricity_prices_api_url, max_retries=3):
    response = None  # Initialize response to None
    status_code = 'N/A'  # Initialize status_code to 'N/A'
    for attempt in range(max_retries):
        try:
            response = requests.get(electricity_prices_api_url)
            status_code = response.status_code

            if status_code == 200:
                try:
                    logging.info("Successfully fetched electricity prices.")
                    return response.json(), status_code
                except json.JSONDecodeError:
                    logging.error("Error while parsing JSON response.")
                    break
            elif status_code == 401:  # Unauthorized
                logging.error("Unauthorized access to the electricity prices API.")
                break
            elif status_code == 429:  # Too Many Requests
                logging.warning("Rate limit exceeded for the electricity prices API.")
                time.sleep(60)  # Wait for 60 seconds before the next attempt
            else:
                logging.warning(
                    f"Failed to fetch electricity prices. Attempt {attempt + 1}. Status code: {status_code}. Retrying...")
                time.sleep(2 ** attempt)
        except requests.RequestException as e:
            logging.error(f"An error occurred: {e}")

    logging.error(f"Failed to fetch electricity prices after {max_retries} attempts.")
    return None, status_code if response else 'N/A'
