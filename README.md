# Spot Prices - Electricity Price Monitoring & PLC Integration

A Python application for monitoring Danish electricity spot prices, calculating price statistics, and optionally writing data to a PLC (Programmable Logic Controller) via Modbus TCP.

## Overview

This program fetches real-time electricity spot prices from the Danish energy market (DK1 price area), converts them from DKK to EUR, calculates various statistics and percentiles, and can communicate with industrial automation equipment (PLC) to automate processes based on electricity prices.

## Features

- **Real-time Price Monitoring**: Fetches current electricity spot prices from Energi Data Service
- **Currency Conversion**: Automatically converts DKK prices to EUR using current exchange rates
- **Statistical Analysis**: 
  - Current hour electricity price
  - Daily minimum and maximum prices
  - Daily average price
  - Configurable percentile calculations
- **PLC Integration**: Writes price data to PLC registers via Modbus TCP
- **Excel Export**: Saves prices and statistics to Excel format
- **MAC Address Authorization**: Restricts program access to authorized devices
- **Caching**: Remembers your last used percentile settings

## Requirements

### Python Dependencies

```
pandas
requests
pymodbus
openpyxl
```

### Hardware Requirements (Optional)

- Moxa MGate 5103 (or compatible Modbus TCP gateway) at `192.168.127.254`
- PLC with Modbus TCP support

## Installation

1. Clone or download this repository

2. Install required Python packages:
```bash
pip install pandas requests pymodbus openpyxl
```

3. Configure the application by editing `config.json`:
```json
{
  "API_KEY": "your_api_key_here",
  "AUTHORIZED_IDS": [
    "your:mac:address:here"
  ],
  "EXCHANGE_RATE_API_URL": "https://api.exchangerate-api.com/v4/latest/DKK",
  "ELECTRICITY_PRICES_API_URL": "https://api.energidataservice.dk/...",
  "SCALING_FACTOR": 100,
  "UNIT_ID": 1
}
```

## Configuration

### config.json Parameters

- **API_KEY**: Your API key for the exchange rate service
- **AUTHORIZED_IDS**: List of authorized MAC addresses that can run the program
- **MAX_RETRIES**: Number of retry attempts for API calls (default: 3)
- **TIMEOUT**: Request timeout in seconds (default: 10)
- **EXCHANGE_RATE_API_URL**: API endpoint for DKK to EUR conversion
- **ELECTRICITY_PRICES_API_URL**: API endpoint for Danish electricity prices
- **SCALING_FACTOR**: Multiplier for PLC register values (default: 100)
- **UNIT_ID**: Modbus unit identifier (default: 1)

### Getting Your MAC Address

The program uses MAC address authentication. To find your MAC address:

**Windows:**
```cmd
ipconfig /all
```
Look for "Physical Address"

**Linux/Mac:**
```bash
ifconfig
```
Look for "ether" or "HWaddr"

Add your MAC address to the `AUTHORIZED_IDS` list in `config.json` in the format: `"XX:XX:XX:XX:XX:XX"`

## Usage

### Starting the Program

```bash
python main.py
```

### Main Menu Options

1. **See current prices (i)**: Display current hour price, daily price difference, and daily average
2. **Connect to PLC (p)**: Connect to PLC and write price data to Modbus registers
3. **Save to Excel (x)**: Export prices and percentiles to an Excel file
4. **Quit (q)**: Exit the program

### Working with Percentiles

When connecting to PLC or exporting to Excel, you'll be prompted to enter percentiles:

- **Maximum percentile (x)**: Upper threshold (e.g., 0.66 for top 66%)
- **Minimum percentile (y)**: Lower threshold (e.g., 0.33 for bottom 33%)

These values are cached and can be reused by pressing ENTER when prompted.

### PLC Integration Workflow

1. Select option `p` (Connect to PLC)
2. Enter desired percentiles
3. Confirm connection to PLC
4. Review the data preview showing what will be written to each register
5. Confirm write operation

**PLC Register Mapping:**
- Register 0: Price difference (max - min)
- Register 1: Daily average price
- Register 2: Current hour price (DK1)
- Register 3: Minimum percentile value
- Register 4: Maximum percentile value

All values are scaled by the `SCALING_FACTOR` (default: 100) before writing.

### Excel Export

1. Select option `x` (Save to Excel)
2. Enter desired percentiles
3. Choose whether to sort prices from low to high
4. Data is exported to `SpotPrices.xlsx` with two sheets:
   - **Prices**: Hourly spot prices for the current day
   - **Percentiles**: Calculated percentile values

## Data Sources

- **Electricity Prices**: [Energi Data Service](https://api.energidataservice.dk/) - Danish Energy Agency
- **Exchange Rates**: [Exchange Rate API](https://www.exchangerate-api.com/)

## Logging

All operations are logged to `app.log` including:
- API requests and responses
- PLC connection status
- Data processing operations
- Errors and warnings

## File Structure

```
.
├── main.py                      # Main program entry point
├── api_module.py                # API communication functions
├── config_module.py             # Configuration management
├── data_processing_module.py    # Data processing and statistics
├── excel_module.py              # Excel export functionality
├── logging_module.py            # Logging setup
├── plc_module.py                # PLC/Modbus communication
├── config.json                  # Configuration file
├── app.log                      # Log file (generated)
├── percentiles_cache.pkl        # Cached percentile values (generated)
└── SpotPrices.xlsx              # Excel export (generated)
```

## Error Handling

The program includes robust error handling for:
- API connection failures with automatic retry logic
- Rate limiting (429 errors) with exponential backoff
- Invalid JSON responses
- PLC connection issues
- File permission errors
- Unauthorized access attempts

## Security

- MAC address-based access control
- All access attempts are logged
- Unauthorized access attempts are blocked and logged

## Troubleshooting

### "Unauthorized access" message
- Check that your MAC address is in the `AUTHORIZED_IDS` list in `config.json`
- MAC address format must be `"XX:XX:XX:XX:XX:XX"`

### API fetch failures
- Verify your API key is correct
- Check internet connectivity
- Review `app.log` for detailed error messages

### PLC connection issues
- Verify PLC/Moxa gateway is reachable at `192.168.127.254`
- Check network connectivity
- Ensure Modbus TCP port 502 is accessible
- Verify `UNIT_ID` matches your PLC configuration

### Excel export fails
- Ensure you have write permissions in the program directory
- Check that Excel file is not open in another application

## Use Cases

- **Energy Cost Optimization**: Automatically control high-power equipment based on electricity prices
- **Industrial Automation**: Integrate electricity pricing into production scheduling
- **Data Analysis**: Track and analyze electricity price patterns
- **Smart Grid Applications**: Respond to dynamic pricing signals

## License

This program is the intellectual property of Alexander Flor Glering. All Rights Reserved.

## Author

Alexander Flor Glering

## Version History

See `app.log` for operational history and changes.
