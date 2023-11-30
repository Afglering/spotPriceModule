# Import required modules
from api_module import *
from config_module import *
from data_processing_module import *
from excel_module import *
from logging_module import setup_logging
from plc_module import *

# ---------------------------------- Init ------------------------------------------------------

# Initializing variables
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

    # Get the current hour and the price for DK1, DK2 as well as the average of the two prices
    current_hour_price_DK1_EUR = get_current_hour_prices(prices_df)


    # Calculate price difference between daily minimum and maximum in EUR
    price_diff_eur = calculate_price_difference(prices_df)

    # Calculate the average price for the day in EUR
    avg_price_eur = calculate_daily_average(prices_df)

    # Load the last cached percentiles
    x_last, y_last = load_cached_percentiles()


# ---------------------------------- Init Methods ------------------------------------------------
def percentile():
    # Load the last cached percentiles
    x_last, y_last = load_cached_percentiles()

    # Get percentiles from user or cache
    x = input(f"Enter the xth maximum percentile (e.g., 0.66 for 66%), or press ENTER to use last value ({x_last}): ")
    y = input(f"Enter the yth minimum percentile (e.g., 0.33 for 33%), or press ENTER to use last value ({y_last}):\n")

    # Use last values if user presses ENTER
    if not x:
        x = x_last
    if not y:
        y = y_last

    # Save the specified percentiles to a cache file
    save_percentiles_to_cache(x, y)

    percentiles_df, x_max_percentile, y_min_percentile = calculate_percentiles(prices_df, x, y)

    print(f'The calculated x max percentile is {x_max_percentile:.2f} and the minimum y is {y_min_percentile:.2f}\n')

    return percentiles_df, x_max_percentile, y_min_percentile


def info():
    print("\n*** CURRENT HOUR PRICE POINT ***")
    if current_hour_price_DK1_EUR is not None:
        print(f'The price for the current hour ({dt.now().hour}) is {current_hour_price_DK1_EUR:.2f} EUR/MWh for DK1\n')
    else:
        print("Current hour price for DK1 is not available.")

    print("*** SPOT PRICE DIFFERENCE ***")
    print(f'The price difference between the daily minimum and maximum is {price_diff_eur:.2f} EUR/MWh\n')

    print("*** DAILY PRICE AVERAGE ***")
    print(f'The average price for the day is {avg_price_eur:.2f} EUR/MWh\n')


def handle_plc_option():
    plc_connected = False

    connect_to_plc = input("Do you want to connect to the PLC? (y/n): ").strip().lower()

    if connect_to_plc == 'y':
        client = setup_plc_client(IP_ADDRESS=MOXA_IP_ADDRESS, PORT=MOXA_PORT)

        # Check if the client has been successfully created
        if client is not None:
            try:
                if client.connect():
                    plc_connected = True
                    logging.info("Successfully connected to the PLC.")

                    data_to_write = {
                        0: round(price_diff_eur, 2),
                        1: round(avg_price_eur, 2),
                        2: round(current_hour_price_DK1_EUR, 2),
                        3: round(y_min_percentile, 2),
                        4: round(x_max_percentile, 2)
                    }

                    print("\n*** Register Data Preview ***")
                    for address, value in data_to_write.items():
                        print(f"Register Address: {address}, Data to be written: {value}")

                    write_to_registers = input("Do you want to write the data to the registers? (y/n): ").strip().lower()
                    if write_to_registers == 'y':
                        for address, value in data_to_write.items():
                            write_data_to_plc(client, address, value, scaling_factor, unit_id)
                    print("Successfully wrote to registers.")
                    logging.info("Successfully wrote to registers.")

                else:
                    logging.error("Failed to connect to the PLC.")
                    raise Exception("Failed to connect to the PLC.")

            except Exception as e:
                logging.error(f"An error occurred: {e}")
                retry = input("An error occurred. Do you want to retry? (y/n): ").strip().lower()
                if retry.lower() == 'y':
                    handle_plc_option()  # Attempt to reconnect
                else:
                    print("Exiting PLC connection attempt.")
                    logging.info("Exiting PLC connection attempt.")

            finally:
                if client:  # Close the client if it's open
                    client.close()
                    logging.info("PLC connection closed.")

        else:
            logging.error("PLC client could not be set up.")
            print("PLC client setup failed.")

    return plc_connected


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
    print("4. Quit (q)")

    user_choice = input("\nPlease enter your choice: ").lower()
    logging.info("Prompting user choice.")

    if user_choice == 'p':
        print("\nBefore continuing please enter the desired upper and lower percentile of the data\n")
        percentiles_df, x_max_percentile, y_min_percentile = percentile()
        plc_connected = handle_plc_option()
        logging.info("User chose to initiate plc connection.")

    elif user_choice == 'i':
        info()
        logging.info("User chose to see daily info.")

    elif user_choice == 'x':
        print("\nBefore continuing please enter the desired upper and lower percentile of the data\n")
        percentiles_df, x_max_percentile, y_min_percentile = percentile()
        handle_excel_option(prices_df, percentiles_df)
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
