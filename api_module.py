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
    for attempt in range(max_retries):
        try:
            response = requests.get(electricity_prices_api_url)
            status_code = response.status_code

            if status_code == 200:
                try:
                    logging.info("Successfully fetched electricity prices.")
                    return response.json(), status_code
                except json.JSONDecodeError as e:
                    logging.error("Error while parsing JSON response: {}".format(e))
                    break  # Break out of the loop if JSON parsing fails
            elif status_code == 401:  # Unauthorized
                logging.error("Unauthorized access to the electricity prices API. Status code: {}".format(status_code))
                break  # Break out of the loop if unauthorized
            elif status_code == 429:  # Too Many Requests
                logging.warning("Rate limit exceeded for the electricity prices API. Status code: {}".format(status_code))
                if attempt < max_retries - 1:
                    time.sleep(60)  # Wait for 60 seconds before the next attempt
            else:
                logging.warning("Failed to fetch electricity prices. Attempt {}. Status code: {}".format(attempt + 1, status_code))
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        except requests.RequestException as e:
            logging.error("An error occurred while fetching electricity prices: {}".format(e))
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

    logging.error("Failed to fetch electricity prices after {} attempts. Final status code: {}".format(max_retries, status_code))
    return None, status_code if response else 'N/A'
