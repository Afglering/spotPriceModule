from config_module import *
from api_module import *
from logging_module import setup_logging
from plc_module import *
from data_processing_module import *
from excel_module import *
import time

# Initializing variables
current_hour_price_DK1_EUR = None
current_hour_price_DK2_EUR = None
x_max_percentile = None
y_min_percentile = None
price_diff_eur = None
avg_price_eur = None
current_hour_price_avg_EUR = None
plc_connected = False
data_to_write = None
client = None

# Setup logging
setup_logging()

# Print the logo
print_logo()

# Validate MAC address
current_id = get_mac_address()
if current_id not in AUTHORIZED_IDS:
    logging.warning(f"Unauthorized access attempt by MAC address: {current_id}")
    print("Apologies. You are not currently authorized to run this program.")
    exit(1)
logging.info(f"Authorized access by MAC address: {current_id}")

# Ask the user if they want to connect to the PLC
connect_to_plc = input("Do you want to connect to the PLC? (y/n): ").strip().lower()
while True:
    if connect_to_plc == 'y':
        # Initialize Modbus RTU client
        client = setup_plc_client(SERIAL_PORT, BAUD_RATE, PARITY, STOP_BITS, BYTE_SIZE)

        # Connect to the PLC
        if client.connect():
            plc_connected = True
            logging.info("Successfully connected to the PLC.")
            break  # Exit the loop if the connection is successful
        else:
            logging.error("Failed to connect to the PLC.")
            choice = input("Do you want to (r)etry, (m)ove on, or (e)xit? ").strip().lower()

            if choice == 'r':
                continue  # Retry the connection
            elif choice == 'm':
                break  # Move on without connecting
            elif choice == 'e':
                exit(1)  # Exit the program
            else:
                print("Invalid choice. Please select 'r', 'm', or 'e'.")
    else:
        break  # Exit the loop if the user doesn't want to connect to the PLC

# Fetch the exchange rate if the API key is valid
if validate_exchange_rate_api_key(api_key, exchange_rate_api_url):
    conversion_rate_dkk_to_eur = fetch_exchange_rate(api_key, exchange_rate_api_url)
else:
    logging.error("Exiting due to invalid API key.")
    exit(1)

# Fetch the data
data, status_code = fetch_electricity_prices(electricity_prices_api_url)

# If response is OK, continue
if data:
    prices_df = process_data(data, conversion_rate_dkk_to_eur)

    # Get the current hour and display the price for DK1, DK2, and the average of the two prices
    current_hour_price_DK1_EUR, current_hour_price_DK2_EUR, current_hour_price_avg_EUR = get_current_hour_prices(
        prices_df)
    print("\n*** CURRENT HOUR PRICE POINT ***")
    print(
        f'The price for the current hour ({dt.now().hour}) is {current_hour_price_DK1_EUR} EUR/MWh for DK1 and '
        f'{current_hour_price_DK2_EUR} EUR/MWh for DK2. \n'
        f'The average of the two PriceAreas is {current_hour_price_avg_EUR} EUR/MWh\n')

    # Calculate price difference between daily minimum and maximum in EUR
    price_diff_eur = calculate_price_difference(prices_df)
    print("*** SPOT PRICE DIFFERENCE ***")
    print(f'The price difference between the daily minimum and maximum is {price_diff_eur} EUR/MWh\n')

    # Calculate the average price for the day in EUR
    avg_price_eur = calculate_daily_average(prices_df)
    print("*** DAILY PRICE AVERAGE ***")
    print(f'The average price for the day is {avg_price_eur} EUR/MWh\n')

    # Load the last cached percentiles
    x_last, y_last = load_cached_percentiles()

    # Calculate percentiles
    x = input(f"Enter the xth maximum percentile (e.g., 0.66 for 66%), or press ENTER to use last value ({x_last}): ")
    y = input(f"Enter the yth minimum percentile (e.g., 0.33 for 33%), or press ENTER to use last value ({y_last}):\n")


    # Use last values if user presses ENTER
    if not x:
        x = x_last
    if not y:
        y = y_last

    percentiles_df = calculate_percentiles(prices_df, x, y)

    # Ask user if they want to sort the prices
    sort_prices(prices_df)

    # Save the specified percentiles to a cache file
    save_percentiles_to_cache(x, y)

    # Write data to PLC registers 40001-40007 if the PLC is connected
    if plc_connected:
        data_to_write = {
            40001: price_diff_eur,
            40002: avg_price_eur,
            40003: current_hour_price_DK1_EUR,
            40004: current_hour_price_DK2_EUR,
            40005: current_hour_price_avg_EUR,
            40006: y_min_percentile,
            40007: x_max_percentile
        }

        for address, value in data_to_write.items():
            write_data_to_plc(client, address, value, scaling_factor, slave_id)

    if plc_connected and client is not None:
        # Close the connection to the PLC if it is connected and the client is not None
        client.close()
        logging.info("Successfully closed connection to the PLC.")

    # Export dataframes to Excel
    export_to_excel(prices_df, percentiles_df)

    logging.info("Program completed successfully.")
    print("\nProgram completed successfully. This window will close in 5 seconds.")
    time.sleep(5)

    # If response is not OK, print error message
else:
    logging.error('Error: ' + str(status_code))
    print("An error occurred. This window will close in 5 seconds.")
    time.sleep(5)
