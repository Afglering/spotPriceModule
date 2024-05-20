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

class PLCProgram:
    def __init__(self):
        self.current_hour_price_DK1_EUR = None
        self.current_hour_price_DK2_EUR = None
        self.x_max_percentile = None
        self.y_min_percentile = None
        self.price_diff_eur = None
        self.avg_price_eur = None
        self.plc_connected = False
        self.prices_df = None
        self.calculate_percentiles_flag = True

        setup_logging()
        self.initialize()

    def initialize(self):
        current_id = get_mac_address()
        if current_id not in AUTHORIZED_IDS:
            logging.warning(f"Unauthorized access attempt by MAC address: {current_id}")
            print("Apologies. You are not currently authorized to run this program.")
            exit(1)
        logging.info(f"Authorized access by MAC address: {current_id}")

        if validate_exchange_rate_api_key(api_key, exchange_rate_api_url):
            self.conversion_rate_dkk_to_eur = fetch_exchange_rate(api_key, exchange_rate_api_url)
        else:
            logging.error("Exiting due to invalid API key.")
            exit(1)

        data, status_code = fetch_electricity_prices(electricity_prices_api_url)
        if data:
            self.prices_df = process_data(data, self.conversion_rate_dkk_to_eur)
            self.current_hour_price_DK1_EUR = get_current_hour_prices(self.prices_df)
            self.price_diff_eur, self.daily_max_eur, self.daily_min_eur = calculate_price_difference(self.prices_df)
            self.avg_price_eur = calculate_daily_average(self.prices_df)
            self.x_last, self.y_last = load_cached_percentiles()

    def handle_excel_option(self, prices_df, percentiles_df):
        sort_prices(prices_df)
        print("\nExporting to xlsx.")
        time.sleep(1)
        print("Exporting to xlsx..")
        time.sleep(1)
        print("Exporting to xlsx...")

        export_to_excel(prices_df, percentiles_df)
        print("Successfully exported data!")

    def run(self):
        start_timer(lambda: auto_connect_to_plc(handle_plc_option, self.prices_df, self.conversion_rate_dkk_to_eur))
        while True:
            if auto_mode:
                time.sleep(1)
                continue

            print_logo()
            print("\n*** Main Menu ***")
            print("1. See current prices (i)")
            print("2. Connect to PLC (p)")
            print("3. Save to Excel (x)")
            print("4. Quit (q)\n")
            print("INFO: THIS PROGRAM ONLY RUNS FOR AS LONG AS THIS WINDOW IS OPEN. IF YOU CLOSE IT, THE PROGRAM WILL STOP.\n")

            user_choice = input("\nPlease enter your choice: ").lower()
            logging.info("Prompting user choice.")

            stop_timer()

            if user_choice == 'p':
                handle_plc_option(self.prices_df, self.conversion_rate_dkk_to_eur)
                logging.info("User chose to initiate PLC connection.")

            elif user_choice == 'i':
                display_info(self.current_hour_price_DK1_EUR, self.daily_max_eur, self.daily_min_eur, self.price_diff_eur, self.avg_price_eur)
                logging.info("User chose to see daily info.")

            elif user_choice == 'x':
                self.handle_excel_option(self.prices_df, None)
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

if __name__ == "__main__":
    program = PLCProgram()
    program.run()
