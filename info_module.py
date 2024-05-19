# info_module.py

from datetime import datetime

def display_info(current_hour_price_DK1_EUR, daily_max_eur, daily_min_eur, price_diff_eur, avg_price_eur):
    print("\n*** CURRENT HOUR PRICE POINT ***")
    if current_hour_price_DK1_EUR is not None:
        print(f'The price for the current hour ({datetime.now().hour}) is {current_hour_price_DK1_EUR:.2f} EUR/MWh for DK1\n')
    else:
        print("Current hour price for DK1 is not available.")

    print("*** DAILY MAX PRICE ***")
    print(f'The daily max price point is {daily_max_eur:.2f} EUR/MWh\n')

    print("*** DAILY MIN PRICE ***")
    print(f'The daily minimum price point is {daily_min_eur:.2f} EUR/MWh\n')

    print("*** SPOT PRICE DIFFERENCE ***")
    print(f'The price difference between the daily minimum and maximum is {price_diff_eur:.2f} EUR/MWh\n')

    print("*** DAILY PRICE AVERAGE ***")
    print(f'The average price for the day is {avg_price_eur:.2f} EUR/MWh\n')
