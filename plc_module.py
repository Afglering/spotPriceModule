# Purpose: This module contains functions for communicating with the PLC.
import logging

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException


# Setup plc modbus rtu client
def setup_plc_client(SERIAL_PORT, BAUD_RATE, PARITY, STOP_BITS, BYTE_SIZE):
    try:
        client = ModbusSerialClient(method='rtu', port=SERIAL_PORT, baudrate=BAUD_RATE, parity=PARITY,
                                    stopbits=STOP_BITS, bytesize=BYTE_SIZE)
        if client:
            logging.info("PLC client setup successful.")
        return client
    except Exception as e:
        logging.error(f"Error setting up PLC client: {e}")
        return None


# Write data to plc
def write_data_to_plc(client, register_address, value, scaling_factor, slave_id=1):  # Default slave_id is 1
    try:
        # Try to establish a connection
        if client.connect():
            logging.info("Connected to the PLC.")

            # Proceed to write data
            scaled_value = int(value * scaling_factor)
            response = client.write_register(register_address, scaled_value, unit=slave_id)

            if response.isError():
                logging.error(
                    f"Failed to write value {value} to register address {register_address}. Error: {response}")
            else:
                logging.info(f"Successfully wrote value {value} to register address {register_address}.")

            # Close the connection
            client.close()
        else:
            logging.error("Failed to connect to the PLC.")
    except ModbusException as e:
        logging.error(f"Modbus Error while writing to PLC: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while writing to PLC: {e}")
