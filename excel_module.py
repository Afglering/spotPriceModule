# excel_module.py

import pandas as pd
import logging


def export_to_excel(prices_df, percentiles_df):
    try:
        with pd.ExcelWriter('SpotPrices.xlsx') as writer:
            prices_df.to_excel(writer, sheet_name='Prices', index=False)
            percentiles_df.to_excel(writer, sheet_name='Percentiles', index=False)
    except Exception as e:
        logging.error(f"Error while exporting dataframes to Excel: {e}")
