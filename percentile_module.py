# percentile_module.py

import logging
from data_processing_module import calculate_percentiles, load_cached_percentiles, save_percentiles_to_cache

def get_percentiles_from_user(prices_df):
    global x_max_percentile, y_min_percentile  # Declare global variables

    # Load the last cached percentiles
    x_last, y_last = load_cached_percentiles()

    x_input = input(f"Enter the xth maximum percentile (MIN: 0.01, MAX: 0.99), or press ENTER to use last value ({x_last}): ")
    y_input = input(f"Enter the yth minimum percentile (MIN: 0.01, MAX: 0.99), or press ENTER to use last value ({y_last}):\n")

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

    return calc_x_max, calc_y_min
