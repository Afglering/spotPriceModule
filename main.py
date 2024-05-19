# main.py

import logging
import time

from api_module import fetch_electricity_prices, fetch_exchange_rate, validate_exchange_rate_api_key
from config_module import *
from data_processing_module import *
from logging_module import setup_logging
from timer_module import start_timer, stop_timer, auto_connect_to_plc
from plc_handler import handle_plc_option, auto_mode
from info_module import display_info
from excel_module import export_to_excel

# ---------------------------------- Init ------------------------------------------------------

# Initializing variables
global plc_connected, prices_df, current_hour_price_DK1_EUR, daily_max_eur, daily_min_eur, price_diff_eur, avg_price_eur, x_max_percentile, y_min_percentile
current_hour_price_DK1_EUR = None
current_hour_price_DK2_EUR = None
x_max_percentile = None
y_min_percentile = None
price_diff_eur = None
avg_price_eur = None
plc_connected = False
prices_df = None
calculate_percentiles_flag = True 

# Setup logging
setup_logging()

# Validate MAC address
current_id = get_mac_address()
if current_id not in AUTHORIZED_IDS:
    logging.warning(f"Unauthorized access attempt by MAC address: {current_id}")
    print("Apologies. You are not currently authorized to run this program.")
    exit(1)
logging.info(f"Authorized access by MAC address: {current_id}")

# Fetch the exchange rate if the API key is valid
if validate_exchange_rate_api_key(api_key, exchange_rate_api_url):
    conversion_rate_dkk_to_eur = fetch_exchange_rate(api_key, exchange_rate_api_url)
else:
    logging.error("Exiting due to invalid API key.")
    exit(1)

# ---------------------------------- Fetch Data -----------------------------------------------------

data, status_code = fetch_electricity_prices(electricity_prices_api_url)

# If response is OK, continue
if data:
    prices_df = process_data(data, conversion_rate_dkk_to_eur)

    # Get the current hour price for DK1
    current_hour_price_DK1_EUR = get_current_hour_prices(prices_df)

    # Calculate price difference and daily max/min
    price_diff_eur, daily_max_eur, daily_min_eur = calculate_price_difference(prices_df)

    # Calculate the average price for the day in EUR
    avg_price_eur = calculate_daily_average(prices_df)

    # Load the last cached percentiles
    x_last, y_last = load_cached_percentiles()

# ---------------------------------- Main Methods ------------------------------------------------

def handle_excel_option(prices_df, percentiles_df):
    # Ask user if they want to sort the prices
    sort_prices(prices_df)
    print("\nExporting to xlsx.")
    time.sleep(1)
    print("Exporting to xlsx..")
    time.sleep(1)
    print("Exporting to xlsx...")

    # Export dataframes to excel
    export_to_excel(prices_df, percentiles_df)
    print("Successfully exported data!")

def exit_program():
    print("Exiting program.")
    logging.info("Existing program.")
    exit()

# ---------------------------------- Main program flow -------------------------------------------

if __name__ == "__main__":
    start_timer(lambda: auto_connect_to_plc(handle_plc_option, prices_df, conversion_rate_dkk_to_eur))

    while True:
        if auto_mode:
            time.sleep(1)
            continue

        print_logo()
        print("\n           This program is the intellectual property of Alexander Flor Glering "
              "\n                                 All Rights Reserved.")

        print("\n*** Main Menu ***")
        print("1. See current prices (i)")
        print("2. Connect to PLC (p)")
        print("3. Save to Excel (x)")
        print("4. Quit (q)\n")
        print("INFO: THIS PROGRAM ONLY RUNS FOR AS LONG AS THIS WINDOW IS OPEN. IF YOU CLOSE IT, THE PROGRAM WILL STOP.\n")

        user_choice = input("\nPlease enter your choice: ").lower()
        logging.info("Prompting user choice.")

        # Stop the timer once the user interacts
        stop_timer()

        if user_choice == 'p':
            handle_plc_option(prices_df, conversion_rate_dkk_to_eur)
            logging.info("User chose to initiate PLC connection.")

        elif user_choice == 'i':
            display_info(current_hour_price_DK1_EUR, daily_max_eur, daily_min_eur, price_diff_eur, avg_price_eur)
            logging.info("User chose to see daily info.")

        elif user_choice == 'x':
            handle_excel_option(prices_df, None)
            logging.info("User chose to print to Excel.")

        elif user_choice == 'q':
            confirm_exit = input("Are you sure you want to exit? (y/n): ").lower()
            if confirm_exit == 'y':
                logging.info("Exiting program.")
                print("Goodbye!")
                break

        else:
            print("Invalid option. Please enter 'p', 'x', or 'q'.")

        after_process_choice = input("\nDo you want to return to the main menu (m) or quit (q)? ").lower()
        if after_process_choice == 'q':
            print("Goodbye!")
            logging.info("Exiting program.")
            break
