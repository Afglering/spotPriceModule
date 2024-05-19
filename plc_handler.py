import threading
import logging
import time
from datetime import datetime, timedelta as td

from api_module import fetch_electricity_prices
from data_processing_module import calculate_price_difference, calculate_daily_average, get_current_hour_prices, calculate_percentiles, process_data, load_cached_percentiles
from config_module import MOXA_IP_ADDRESS, MOXA_PORT, scaling_factor, unit_id, electricity_prices_api_url
from plc_module import setup_plc_client, write_data_to_plc
from percentile_module import get_percentiles_from_user
from timer_module import stop_timer

plc_connected = False
client = None
data_to_write = None
auto_mode = False

def plc_update_thread(conversion_rate_dkk_to_eur, prices_df):
    global plc_connected, current_hour_price_DK1_EUR, price_diff_eur, avg_price_eur, x_max_percentile, y_min_percentile, calculate_percentiles_flag

    try:
        # Perform the first update immediately
        perform_update(conversion_rate_dkk_to_eur, prices_df)
        logging.info("Completed PLC update cycle. Next update in 1 hour.\n")
        print("Completed PLC update cycle. Next update in 1 hour.\n", flush=True)

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
            perform_update(conversion_rate_dkk_to_eur, prices_df)
            logging.info("Completed PLC update cycle. Next update in 1 hour.\n")
            print("Completed PLC update cycle. Next update in 1 hour.\n", flush=True)

    except Exception as e:
        logging.error(f"Error in PLC update thread: {e}")
        print(f"PLC Update Error: {e}")

def perform_update(conversion_rate_dkk_to_eur, prices_df):
    # Fetch and process electricity price data
    data, status_code = fetch_electricity_prices(electricity_prices_api_url)
    if data and status_code == 200:
        global current_hour_price_DK1_EUR, price_diff_eur, avg_price_eur, x_max_percentile, y_min_percentile
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
                print(f"PLC Update: Successfully updated register {address} with value {value}.", flush=True)
            else:
                logging.error(f"Failed to update register {address} with value {value}.")
    else:
        logging.error(f"Failed to fetch electricity prices. Status code: {status_code}")

def handle_plc_option(prices_df, conversion_rate_dkk_to_eur, auto=False):
    global plc_connected, client, calculate_percentiles_flag, x_max_percentile, y_min_percentile, auto_mode

    if auto:
        auto_mode = True
        calculate_percentiles_flag = False  # Using cached values, no user interaction
    else:
        auto_mode = False
        stop_timer()  # Stop the auto-connect timer since user interaction has occurred
        calculate_percentiles_flag = input("Do you want to calculate percentiles? (y/n): ").strip().lower() == 'y'

    if calculate_percentiles_flag:
        x_max_percentile, y_min_percentile = get_percentiles_from_user(prices_df)
    else:
        x_max_percentile, y_min_percentile = load_cached_percentiles()
        if x_max_percentile is None or y_min_percentile is None:
            x_max_percentile, y_min_percentile = 0.66, 0.33  # Default values if cache is empty
        else:
            x_max_percentile, y_min_percentile = calculate_percentiles(prices_df, x_max_percentile, y_min_percentile)

    if auto or input("Do you want to connect to the PLC? (y/n): ").strip().lower() == 'y':
        client = setup_plc_client(IP_ADDRESS=MOXA_IP_ADDRESS, PORT=MOXA_PORT)
        if client:
            plc_connected = True
            logging.info("Successfully connected to the PLC.")
            print("Connection to the PLC was successful.\n")

            plc_thread = threading.Thread(target=plc_update_thread, args=(conversion_rate_dkk_to_eur, prices_df))
            plc_thread.start()

            if auto:
                handle_auto_mode_exit()
            else:
                handle_manual_mode_exit()

            plc_thread.join()
            logging.info("PLC update thread has finished.")
            print("PLC updates have been stopped.\n")
        else:
            logging.error("Failed to connect to the PLC.")
            print("Failed to connect to the PLC. Please check your connection settings.\n")

    if client and client.is_socket_open():
        client.close()
        logging.info("PLC connection closed.")
        print("PLC connection has been closed.\n")

def handle_manual_mode_exit():
    global plc_connected
    while plc_connected:
        if input("Type 'exit' to stop PLC updates and return to the main menu: ").strip().lower() == 'exit':
            plc_connected = False
            print("Stopping PLC updates...\n")

def handle_auto_mode_exit():
    global plc_connected
    while plc_connected:
        if input().strip().lower() == 'exit':
            plc_connected = False
            print("Stopping PLC updates...\n")
