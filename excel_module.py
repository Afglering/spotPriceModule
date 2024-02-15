# Purpose: Module to export dataframes to Excel
import logging
import pandas as pd

# Export dataframes to Excel
def export_to_excel(prices_df, percentiles_df):
    try:
        with pd.ExcelWriter('SpotPrices.xlsx') as writer:
            # Always export prices_df
            prices_df.to_excel(writer, sheet_name='Prices', index=False)

            # Export percentiles_df only if it's not None
            if percentiles_df is not None:
                percentiles_df.to_excel(writer, sheet_name='Percentiles', index=False)
            
            logging.info("Successfully exported dataframes to Excel.")
    except Exception as e:
        logging.error(f"Error while exporting dataframes to Excel: {e}")
