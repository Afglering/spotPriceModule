# Purpose: Module to export dataframes to Excel
import pandas as pd
import logging


# Export dataframes to Excel
def export_to_excel(prices_df, percentiles_df):
    try:
        with pd.ExcelWriter('SpotPrices.xlsx') as writer:
            prices_df.to_excel(writer, sheet_name='Prices', index=False)
            percentiles_df.to_excel(writer, sheet_name='Percentiles', index=False)
            logging.info("Successfully exported dataframes to Excel.")
    except Exception as e:
        logging.error(f"Error while exporting dataframes to Excel: {e}")
