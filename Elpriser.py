import requests
import pandas as pd
from datetime import datetime as dt
import pickle
import uuid
import time
import json
import logging

# Logging configuration
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Program started.")

# Read config.json file for API key and other configuration parameters
logging.info("Reading config.json file.")

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error("Configuration file not found.")
    exit(1)
except json.JSONDecodeError:
    logging.error("Error decoding the configuration file.")
    exit(1)

AUTHORIZED_IDS = config['AUTHORIZED_IDS']
api_key = config['API_KEY']
max_retries = config['MAX_RETRIES']
timeout = config['TIMEOUT']
exchange_rate_api_url = config['EXCHANGE_RATE_API_URL']
electricity_prices_api_url = config['ELECTRICITY_PRICES_API_URL']

logging.info("Successfully read config.json file.")


# Get the MAC address of the current device to check if the user is authorized to run the program
def get_mac_address():
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])


# MAC address of the current device
current_id = get_mac_address()

# If the current_id is not in AUTHORIZED_IDS, exit the program
if current_id not in AUTHORIZED_IDS:
    logging.warning(f"Unauthorized access attempt by MAC address: {current_id}")
    print("Apologies. You are not currently authorized to run this program.")
    exit(1)

logging.info(f"Authorized access by MAC address: {current_id}")

# Print the logo
print(""" 

..######..########...#######..########....########..########..####..######..########..######.
.##....##.##.....##.##.....##....##.......##.....##.##.....##..##..##....##.##.......##....##
.##.......##.....##.##.....##....##.......##.....##.##.....##..##..##.......##.......##......
..######..########..##.....##....##.......########..########...##..##.......######....######.
.......##.##........##.....##....##.......##........##...##....##..##.......##.............##
.##....##.##........##.....##....##.......##........##....##...##..##....##.##.......##....##
..######..##.........#######.....##.......##........##.....##.####..######..########..######.

""")


# Function to validate the API key for the exchange rate API. Returns True if valid, False otherwise.
def validate_exchange_rate_api_key(api_key):
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


# Function to fetch current exchange rate from DKK to EUR from ExchangeRate-API. Returns None if unsuccessful.
def fetch_exchange_rate(api_key, max_retries=3):
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


# Fetch the exchange rate if the API key is valid
if validate_exchange_rate_api_key(api_key):
    conversion_rate_dkk_to_eur = fetch_exchange_rate(api_key)
else:
    logging.error("Exiting due to invalid API key.")
    exit(1)

# Load the last specified percentiles
try:
    with open('percentiles_cache.pkl', 'rb') as f:
        x_last, y_last = pickle.load(f)
        logging.info("Successfully read from cache.")
        # Error handling for invalid values.
except FileNotFoundError:
    logging.warning("Warning: Cache file not found. Using default values.")
    x_last, y_last = None, None
except PermissionError:
    logging.warning("Warning: Permission denied while accessing the cache file. Using default values.")
    x_last, y_last = None, None
except pickle.UnpicklingError:
    logging.error("Error while reading the cache file. Using default values.")
    x_last, y_last = None, None


# Function to fetch electricity prices from EnergiDataService. Returns None if unsuccessful. Retries max_retries times.
def fetch_electricity_prices(max_retries=3):
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


# Fetch the data
data, status_code = fetch_electricity_prices()

# If response is OK, continue
if data:
    try:
        logging.info("Successfully fetched electricity prices.")
        # Extract data from JSON
        records = [record for record in data['records'] if record['PriceArea'] in ['DK1', 'DK2']]
        # Create a dataframe from the records
        prices_df = pd.DataFrame(records)
        # Keep only the columns we need
        prices_df = prices_df[['HourDK', 'PriceArea', 'SpotPriceDKK']]
    except (ValueError, TypeError) as e:
        logging.error(f"Error while parsing data into DataFrame: {e}")
        exit(1)

    # Convert SpotPriceDKK to EUR if conversion rate is available
    if conversion_rate_dkk_to_eur:
        logging.info("Converting prices from DKK to EUR.")
        prices_df['SpotPriceEUR'] = prices_df['SpotPriceDKK'] * conversion_rate_dkk_to_eur

    # Create a new column with Extrema (min or max).
    # Show only the first one if there are more than one.
    # Default is empty string.
    prices_df['PriceExtrema'] = ''
    prices_df.loc[prices_df['SpotPriceEUR'].idxmin(), 'PriceExtrema'] = 'Daily Minimum'
    prices_df.loc[prices_df['SpotPriceEUR'].idxmax(), 'PriceExtrema'] = 'Daily Maximum'

    # Calculate price difference between daily minimum and maximum in EUR
    if conversion_rate_dkk_to_eur:
        daily_min_eur = prices_df['SpotPriceEUR'].idxmin()
        daily_max_eur = prices_df['SpotPriceEUR'].idxmax()
        price_diff_eur = prices_df.loc[daily_max_eur, 'SpotPriceEUR'] - prices_df.loc[daily_min_eur, 'SpotPriceEUR']
        print("\n*** SPOT PRICE DIFFERENCE ***")
        print(f'The price difference between the daily minimum and maximum is {price_diff_eur} EUR/MWh\n')

    # Calculate the average price for the day in EUR
    if conversion_rate_dkk_to_eur:
        avg_price_eur = prices_df['SpotPriceEUR'].mean()

        print("*** DAILY PRICE AVERAGE ***")
        print(f'The average price for the day is {avg_price_eur} EUR/MWh\n')

    # Get the current hour and display the price.
    # DK1, DK2 and the average of the two prices are displayed.
    current_hour = dt.now().hour
    current_hour_prices = prices_df[prices_df['HourDK'].str.contains(f'T{current_hour:02d}:')]

    # Calculate the average price for the current hour in EUR
    if conversion_rate_dkk_to_eur:
        logging.info("Calculating average price for the current hour.")
        current_hour_price_DK1_EUR = \
            current_hour_prices[current_hour_prices['PriceArea'] == 'DK1']['SpotPriceEUR'].values[0]
        current_hour_price_DK2_EUR = \
            current_hour_prices[current_hour_prices['PriceArea'] == 'DK2']['SpotPriceEUR'].values[0]
        current_hour_price_avg_EUR = (current_hour_price_DK1_EUR + current_hour_price_DK2_EUR) / 2

        logging.info("Displaying current hour prices.")
        print("*** CURRENT HOUR PRICE POINT ***")
        print(
            f'The price for the current hour ({current_hour}) is {current_hour_price_DK1_EUR} EUR/MWh for DK1 and '
            f'{current_hour_price_DK2_EUR} EUR/MWh for DK2. \n'
            f'The average of the two PriceAreas is {current_hour_price_avg_EUR} EUR/MWh\n')

    # Sort prices from low to high if prompted by user
    sort = input("*** SORTING PROMPT ***\nSort prices from low to high? (y/n): ")
    if sort == 'y':
        logging.info(f"User chose to sort: {sort}")
        prices_df = prices_df.sort_values(by=['SpotPriceEUR'])

    # Ask user for x and y percentiles
    logging.info("Asking user for x and y percentiles.")
    x = input(f"Enter the xth maximum percentile (e.g., 0.66 for 66%), or press ENTER to use last value ({x_last}): ")
    y = input(f"Enter the yth minimum percentile (e.g., 0.33 for 33%), or press ENTER to use last value ({y_last}): ")

    # Use last values if user presses ENTER
    if not x:
        x = x_last
    if not y:
        y = y_last

    # Create a DataFrame for percentiles

    logging.info("Creating DataFrame for percentiles.")
    percentiles_df = pd.DataFrame(columns=['Percentile', 'SpotPriceEUR'])

    # Calculate x and y percentiles
    logging.info("Calculating x and y percentiles.")
    print('\nCalculating percentiles...')

    if x:
        try:
            x = float(x)
            logging.info(f"User entered x percentile: {x}")

            # Handling of invalid input for x
            if 0 <= x <= 1:
                x_max_percentile = prices_df['SpotPriceEUR'].quantile(1 - x)
                print('\nThe ' + str(x * 100) + 'th maximum percentile is ' + str(x_max_percentile) + ' EUR/MWh')

                # Append x_max_percentile to percentiles_df
                df_x = pd.DataFrame([{'Percentile': f'{x * 100}th Max', 'SpotPriceEUR': x_max_percentile}],
                                    columns=percentiles_df.columns)
                percentiles_df = pd.concat([percentiles_df, df_x])

            else:
                print("Error: x should be a number between 0 and 1")
        except ValueError:
            logging.error("Error: Invalid input for x")

    if y:
        try:
            y = float(y)
            logging.info(f"User entered y percentile: {y}")

            # Handling of invalid input for y
            if 0 <= y <= 1:
                y_min_percentile = prices_df['SpotPriceEUR'].quantile(y)
                print('The ' + str(y * 100) + 'th minimum percentile is ' + str(y_min_percentile) + ' EUR/MWh')

                # Append y_min_percentile to percentiles_df
                df_y = pd.DataFrame([{'Percentile': f'{y * 100}th Min', 'SpotPriceEUR': y_min_percentile}],
                                    columns=percentiles_df.columns)
                percentiles_df = pd.concat([percentiles_df, df_y])

            else:
                print("Error: y should be a number between 0 and 1")
        except ValueError:
            logging.error("Error: Invalid input for y")

    # Save the specified percentiles to a pickle (pkl) file for caching purposes in case of system failure
    try:
        logging.info("Saving percentiles to cache file.")
        with open('percentiles_cache.pkl', 'wb') as f:
            pickle.dump((x, y), f)
            # Error handling for invalid values.
    except PermissionError:
        logging.warning("Warning: Permission denied while writing to the cache file.")
    except pickle.PicklingError:
        logging.error("Warning: Error while writing to the cache file.")

    # Export dataframes to Excel
    try:
        logging.info("Exporting dataframes to Excel.")
        with pd.ExcelWriter('Elpriser.xlsx') as writer:
            prices_df.to_excel(writer, sheet_name='Prices', index=False)
            percentiles_df.to_excel(writer, sheet_name='Percentiles', index=False)
    except Exception as e:
        logging.error(f"Error while exporting dataframes to Excel: {e}")

    logging.info("Program completed successfully.")

    # If response is not OK, print error message
else:
    logging.error('Error: ' + str(status_code))
