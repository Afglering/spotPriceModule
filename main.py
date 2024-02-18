# Import required modules
from datetime import datetime
from datetime import timedelta as td
from api_module import fetch_electricity_prices, fetch_exchange_rate, validate_exchange_rate_api_key
from config_module import *
from data_processing_module import *
from excel_module import *
from logging_module import setup_logging
from plc_module import *
import threading
import time

# ---------------------------------- Init ------------------------------------------------------

# Initializing variables
global plc_connected, prices_df,current_hour_price_DK1_EUR, daily_max_eur, daily_min_eur, price_diff_eur, avg_price_eur, x_max_percentile, y_min_percentile
current_hour_price_DK1_EUR = None
current_hour_price_DK2_EUR = None
x_max_percentile = None
y_min_percentile = None
price_diff_eur = None
avg_price_eur = None
plc_connected = False
data_to_write = None
client = None
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


# ---------------------------------- Init Methods ------------------------------------------------
def percentile():
    global x_max_percentile, y_min_percentile  # Declare global variables

    # Load the last cached percentiles
    x_last, y_last = load_cached_percentiles()

    x_input = input(f"Enter the xth maximum percentile (MIN: 0.01, MAX: 0.99), or press ENTER to use last value ({x_last}): ")
    y_input = input(f"Enter the yth minimum percentile (MIN: 0.01, MAX: 0.99),, or press ENTER to use last value ({y_last}):\n")

    # Use cached/default values if user does not input anything
    x = float(x_input) if x_input else (float(x_last) if x_last is not None else 0.66)
    y = float(y_input) if y_input else (float(y_last) if y_last is not None else 0.33)

    # Save the specified percentiles to a cache file
    save_percentiles_to_cache(x, y)

    # Calculate percentiles
    calc_x_max, calc_y_min = calculate_percentiles(prices_df, x, y)

    # Update the global variables with the calculated values
    x_max_percentile, y_min_percentile = calc_x_max, calc_y_min

    print(f'The calculated x max percentile is {calc_x_max:.2f} and the minimum y is {calc_y_min:.2f}\n')

    # Return only the calculated values, as we are no longer returning the DataFrame
    return calc_x_max, calc_y_min



def info():
    print("\n*** CURRENT HOUR PRICE POINT ***")
    if current_hour_price_DK1_EUR is not None:
        print(f'The price for the current hour ({dt.now().hour}) is {current_hour_price_DK1_EUR:.2f} EUR/MWh for DK1\n')
    else:
        print("Current hour price for DK1 is not available.")

    print("*** DAILY MAX PRICE ***")
    print(f'The daily max price point is {daily_max_eur:.2f} EUR/MWh\n')

    print("*** DAILY MIN PRICE ***")
    print(f'The daily minimun price point is {daily_min_eur:.2f} EUR/MWh\n')

    print("*** SPOT PRICE DIFFERENCE ***")
    print(f'The price difference between the daily minimum and maximum is {price_diff_eur:.2f} EUR/MWh\n')

    print("*** DAILY PRICE AVERAGE ***")
    print(f'The average price for the day is {avg_price_eur:.2f} EUR/MWh\n')


def plc_update_thread():
    global prices_df, current_hour_price_DK1_EUR, price_diff_eur, avg_price_eur, x_max_percentile, y_min_percentile, calculate_percentiles_flag

    try:
        # Perform the first update immediately
        perform_update()
        logging.info("Completed PLC update cycle. Next update in 1 hour.\n")
        print("Completed PLC update cycle. Next update in 1 hour.\n", flush = True)

        while plc_connected:
            # Calculate the time until the next hour begins
            now = datetime.now()
            next_hour = now.replace(minute=0, second=0, microsecond=0) + td(hours=1)
            sleep_duration = (next_hour - now).total_seconds()

            # Sleep until the next hour, checking periodically if the thread should exit
            start_time = time.time()
            while time.time() - start_time < sleep_duration:
                time.sleep(10)  # Check every 10 seconds if the thread should exit
                if not plc_connected:
                    return  # Exit if the thread is no longer connected

            # Perform update at the start of the new hour
            perform_update()
            logging.info("Completed PLC update cycle. Next update in 1 hour.\n")
            print("Completed PLC update cycle. Next update in 1 hour.\n", flush = True)

    except Exception as e:
        logging.error(f"Error in PLC update thread: {e}")
        print(f"PLC Update Error: {e}")

def perform_update():
    # Fetch and process electricity price data
    data, status_code = fetch_electricity_prices(electricity_prices_api_url)
    if data and status_code == 200:
        global prices_df, current_hour_price_DK1_EUR, price_diff_eur, avg_price_eur, x_max_percentile, y_min_percentile
        prices_df = process_data(data, conversion_rate_dkk_to_eur)
        current_hour_price_DK1_EUR = get_current_hour_prices(prices_df)
        price_diff_eur, daily_max_eur, daily_min_eur = calculate_price_difference(prices_df)
        avg_price_eur = calculate_daily_average(prices_df)

        if not calculate_percentiles_flag:
            x_max_percentile, y_min_percentile = 0, 0  # Bypass values for percentiles
        else:
            x_cached, y_cached = load_cached_percentiles()
            if x_cached is not None and y_cached is not None:
                x_max_percentile, y_min_percentile = calculate_percentiles(prices_df, x_cached, y_cached)

        data_to_write = {
            0: round(price_diff_eur, 2) if price_diff_eur is not None else 0,
            1: round(avg_price_eur, 2) if avg_price_eur is not None else 0,
            2: round(current_hour_price_DK1_EUR, 2) if current_hour_price_DK1_EUR is not None else 0,
            3: 0 if x_max_percentile == 0 and y_min_percentile == 0 else round(y_min_percentile, 2),
            4: 0 if x_max_percentile == 0 and y_min_percentile == 0 else round(x_max_percentile, 2),
            5: round(daily_max_eur, 2) if daily_max_eur is not None else 0,
            6: round(daily_min_eur, 2) if daily_min_eur is not None else 0,
        }

        # Write the data to the PLC
        for address, value in data_to_write.items():
            success = write_data_to_plc(client, address, value, scaling_factor, unit_id)
            if success:
                logging.info(f"Successfully updated register {address} with value {value}.")
                print(f"PLC Update: Successfully updated register {address} with value {value}.", flush = True)
            else:
                logging.error(f"Failed to update register {address} with value {value}.")
    else:
        logging.error(f"Failed to fetch electricity prices. Status code: {status_code}")


def handle_plc_option():
    global plc_connected, client, calculate_percentiles_flag, x_max_percentile, y_min_percentile
    plc_connected = False

    # First, ask if the user wants to calculate percentiles
    calculate_percentiles_decision = input("Do you want to calculate percentiles? (y/n): ").strip().lower()
    calculate_percentiles_flag = (calculate_percentiles_decision == 'y')

    # If the user wants to calculate percentiles, then proceed to ask for the specific values
    if calculate_percentiles_flag:
        percentile()  # Call the function that prompts for x and y values and processes them
    else:
        flush_cache() 
        # If not calculating percentiles, set default values or indicate bypass
        x_max_percentile, y_min_percentile = None, None  # Indicating bypass or default state

    # Proceed with the PLC connection process
    connect_to_plc = input("Do you want to connect to the PLC? (y/n): ").strip().lower()
    if connect_to_plc == 'y':
        client = setup_plc_client(IP_ADDRESS=MOXA_IP_ADDRESS, PORT=MOXA_PORT)
        if client:
            plc_connected = True
            logging.info("Successfully connected to the PLC.")
            print("Connection to the PLC was successful.\n")

            # Start the PLC update thread
            plc_thread = threading.Thread(target=plc_update_thread)
            plc_thread.start()

            # Keep the PLC updates running until the user decides to stop
            while True:
                user_input = input("Type 'exit' to stop PLC updates and return to the main menu: \n\n").strip().lower()
                if user_input == 'exit':
                    plc_connected = False
                    print("Stopping PLC updates...\n")
                    break

            # Ensure the PLC update thread is properly closed
            plc_thread.join()
            logging.info("PLC update thread has finished.")
            print("PLC updates have been stopped.\n")
        else:
            logging.error("Failed to connect to the PLC.")
            print("Failed to connect to the PLC. Please check your connection settings.\n")
    else:
        print("PLC connection canceled by user.")

    # Cleanup or finalize actions if necessary before exiting the function
    if client and client.is_socket_open():
        client.close()
        logging.info("PLC connection closed.")
        print("PLC connection has been closed.\n")

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


while True:
    # Print the logo
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

    if user_choice == 'p':
        plc_connected = handle_plc_option()  # This function now includes percentile decision making
        logging.info("User chose to initiate PLC connection.")

    elif user_choice == 'i':
        info()
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
            continue  # Return to the main menu if the user decides not to exit

    else:
        print("Invalid option. Please enter 'p', 'x', or 'q'.")
        continue  # Return to the main menu to prompt the user again

    # After each process, ask the user if they want to return to the main menu or exit
    after_process_choice = input("\nDo you want to return to the main menu (m) or quit (q)? ").lower()
    if after_process_choice == 'q':
        print("Goodbye!")
        logging.info("Exiting program.")
        break  # Exit the program
