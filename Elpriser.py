import requests
import pandas as pd
from datetime import datetime as dt
import pickle


# Function to fetch current exchange rate from DKK to EUR from ExchangeRate-API
def fetch_exchange_rate(api_key):
    url = f"https://api.exchangerate-api.com/v4/latest/DKK"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['rates']['EUR']
    else:
        print(f"Failed to fetch exchange rate. Error code: {response.status_code}")
        return None


# Fetch the current exchange rate from DKK to EUR
api_key = "c26cf82c420f4ffee62965e1"
conversion_rate_dkk_to_eur = fetch_exchange_rate(api_key)

# Load the last specified percentiles
try:
    with open('percentiles_cache.pkl', 'rb') as f:
        x_last, y_last = pickle.load(f)
except FileNotFoundError:
    x_last, y_last = None, None

# GET data from ENERGY DATA SERVICE API
response = requests.get('https://api.energidataservice.dk/dataset/Elspotprices?start=StartOfDay&filter=%20%7B' +
                        '%22PriceArea%22%3A%20%22DK1%2CDK2%22%7D')

# Check if response is OK
if response.status_code == 200:
    # Convert response to JSON
    data = response.json()

    # Extract data from JSON
    records = [record for record in data['records'] if record['PriceArea'] in ['DK1', 'DK2']]

    # Create a dataframe from the records
    prices_df = pd.DataFrame(records)
    # Keep only the columns we need
    prices_df = prices_df[['HourDK', 'PriceArea', 'SpotPriceDKK']]

    # Convert SpotPriceDKK to EUR if conversion rate is available
    if conversion_rate_dkk_to_eur:
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
        print(f'The price difference between the daily minimum and maximum is {price_diff_eur} EUR/MWh')

    # Calculate the average price for the day in EUR
    if conversion_rate_dkk_to_eur:
        avg_price_eur = prices_df['SpotPriceEUR'].mean()
        print(f'The average price for the day is {avg_price_eur} EUR/MWh')

    # Get the current hour and display the price.
    # DK1, DK2 and the average of the two prices are displayed.
    current_hour = dt.now().hour
    current_hour_prices = prices_df[prices_df['HourDK'].str.contains(f'T{current_hour:02d}:')]

# Calculate the average price for the current hour in EUR
    if conversion_rate_dkk_to_eur:
        current_hour_price_DK1_EUR = current_hour_prices[current_hour_prices['PriceArea'] == 'DK1']['SpotPriceEUR'].values[0]
        current_hour_price_DK2_EUR = current_hour_prices[current_hour_prices['PriceArea'] == 'DK2']['SpotPriceEUR'].values[0]
        current_hour_price_avg_EUR = (current_hour_price_DK1_EUR + current_hour_price_DK2_EUR) / 2

        print(
            f'The price for the current hour ({current_hour}) is {current_hour_price_DK1_EUR} EUR/MWh for DK1 and '
            f'{current_hour_price_DK2_EUR} EUR/MWh for DK2. '
            f'The average of the two PriceAreas is {current_hour_price_avg_EUR} EUR/MWh')

    # Sort prices from low to high if prompted by user
    sort = input("Sort prices from low to high? (y/n): ")
    if sort == 'y':
        prices_df = prices_df.sort_values(by=['SpotPriceEUR'])

    # Ask user for x and y percentiles
    x = input(f"Enter the xth maximum percentile (e.g., 0.66 for 66%), or press ENTER to use last value ({x_last}): ")
    y = input(f"Enter the yth minimum percentile (e.g., 0.33 for 33%), or press ENTER to use last value ({y_last}): ")

    # Use last values if user presses ENTER
    if not x:
        x = x_last
    if not y:
        y = y_last

    # Create a DataFrame for percentiles
    percentiles_df = pd.DataFrame(columns=['Percentile', 'SpotPriceEUR'])

    # Calculate x and y percentiles
    if x:
        try:
            x = float(x)

            # Handling of invalid input for x
            if 0 <= x <= 1:
                x_max_percentile = prices_df['SpotPriceEUR'].quantile(1 - x)
                print('The ' + str(x * 100) + 'th maximum percentile is ' + str(x_max_percentile) + ' EUR/MWh')

                # Append x_max_percentile to percentiles_df
                df_x = pd.DataFrame([{'Percentile': f'{x * 100}th Max', 'SpotPriceEUR': x_max_percentile}],
                                    columns=percentiles_df.columns)
                percentiles_df = pd.concat([percentiles_df, df_x])

            else:
                print("Error: x should be a number between 0 and 1")
        except ValueError:
            print("Error: Invalid input for x")

    if y:
        try:
            y = float(y)

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
            print("Error: Invalid input for y")

    # Save the specified percentiles to a pickle (pkl) file for caching purposes in case of system failure
    with open('percentiles_cache.pkl', 'wb') as f:
        pickle.dump((x, y), f)

    # Export dataframes to Excel
    with pd.ExcelWriter('Elpriser.xlsx') as writer:
        prices_df.to_excel(writer, sheet_name='Prices', index=False)
        percentiles_df.to_excel(writer, sheet_name='Percentiles', index=False)

    # If response is not OK, print error message
else:
    print('Error: ' + str(response.status_code))
