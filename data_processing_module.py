# Purpose: This module contains functions for processing the data from the API and calculating the statistics.
import logging
import pickle
import uuid
from datetime import datetime as dt

import pandas as pd


# Process the data from the API into a DataFrame and return it if successful
def process_data(data, conversion_rate_dkk_to_eur):
    try:
        records = [record for record in data['records'] if record['PriceArea'] in ['DK1', 'DK2']]
        prices_df = pd.DataFrame(records)
        prices_df = prices_df[['HourDK', 'PriceArea', 'SpotPriceDKK']]
        if conversion_rate_dkk_to_eur:
            prices_df['SpotPriceEUR'] = prices_df['SpotPriceDKK'] * conversion_rate_dkk_to_eur
        return prices_df
    except (ValueError, TypeError) as e:
        logging.error(f"Error while parsing data into DataFrame: {e}")
        exit(1)


# Calculate the percentiles and return a DataFrame
def calculate_percentiles(prices_df, x, y):
    percentiles_df = pd.DataFrame(columns=['Percentile', 'SpotPriceEUR'])

    if x:
        try:
            x = float(x)
            x_max_percentile = prices_df['SpotPriceEUR'].quantile(1 - x)
            df_x = pd.DataFrame([{'Percentile': f'{x * 100}th Max', 'SpotPriceEUR': x_max_percentile}],
                                columns=percentiles_df.columns)
            percentiles_df = pd.concat([percentiles_df, df_x])
        except ValueError:
            logging.error("Error: Invalid input for x")

    if y:
        try:
            y = float(y)
            y_min_percentile = prices_df['SpotPriceEUR'].quantile(y)
            df_y = pd.DataFrame([{'Percentile': f'{y * 100}th Min', 'SpotPriceEUR': y_min_percentile}],
                                columns=percentiles_df.columns)
            percentiles_df = pd.concat([percentiles_df, df_y])
        except ValueError:
            logging.error("Error: Invalid input for y")

    return percentiles_df


# Calculate the price difference between the daily minimum and maximum in EUR
def calculate_price_difference(prices_df):
    daily_min_eur = prices_df['SpotPriceEUR'].min()
    daily_max_eur = prices_df['SpotPriceEUR'].max()
    return daily_max_eur - daily_min_eur


# Calculate the average price for the day in EUR
def calculate_daily_average(prices_df):
    return prices_df['SpotPriceEUR'].mean()


# Get the current hour and display the price for DK1, DK2, and the average of the two prices
def get_current_hour_prices(prices_df):
    current_hour = dt.now().hour
    current_hour_prices = prices_df[prices_df['HourDK'].str.contains(f'T{current_hour:02d}:')]
    current_hour_price_DK1_EUR = current_hour_prices[current_hour_prices['PriceArea'] == 'DK1']['SpotPriceEUR'].values[
        0]
    current_hour_price_DK2_EUR = current_hour_prices[current_hour_prices['PriceArea'] == 'DK2']['SpotPriceEUR'].values[
        0]
    current_hour_price_avg_EUR = (current_hour_price_DK1_EUR + current_hour_price_DK2_EUR) / 2
    return current_hour_price_DK1_EUR, current_hour_price_DK2_EUR, current_hour_price_avg_EUR


# Ask user if they want to sort the prices from low to high (y/n)
def sort_prices(prices_df):
    sort = input("*** SORTING PROMPT ***\nSort prices from low to high? (y/n): ")
    if sort == 'y':
        prices_df.sort_values(by=['SpotPriceEUR'], inplace=True)


# Save the specified percentiles to a cache file
def save_percentiles_to_cache(x, y):
    try:
        with open('percentiles_cache.pkl', 'wb') as f:
            pickle.dump((x, y), f)
    except (PermissionError, pickle.PicklingError) as e:
        logging.error(f"Error while saving percentiles to cache: {e}")


# Load the last cached percentiles and return them
def load_cached_percentiles():
    try:
        with open('percentiles_cache.pkl', 'rb') as f:
            x_last, y_last = pickle.load(f)
            logging.info("Successfully read from cache.")
            return x_last, y_last
    except FileNotFoundError:
        logging.warning("Warning: Cache file not found. Using default values.")
    except PermissionError:
        logging.warning("Warning: Permission denied while accessing the cache file. Using default values.")
    except pickle.UnpicklingError:
        logging.error("Error while reading the cache file. Using default values.")
    return None, None


# Get the MAC address of the computer running the program
def get_mac_address():
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])


# Print the program logo
def print_logo():
    logo = """
..######..########...#######..########....########..########..####..######..########..######.
.##....##.##.....##.##.....##....##.......##.....##.##.....##..##..##....##.##.......##....##
.##.......##.....##.##.....##....##.......##.....##.##.....##..##..##.......##.......##......
..######..########..##.....##....##.......########..########...##..##.......######....######.
.......##.##........##.....##....##.......##........##...##....##..##.......##.............##
.##....##.##........##.....##....##.......##........##....##...##..##....##.##.......##....##
..######..##.........#######.....##.......##........##.....##.####..######..########..######.
"""
    print(logo)
