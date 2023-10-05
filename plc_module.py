# Purpose: This module contains functions for communicating with the PLC.
from pymodbus.client import ModbusSerialClient
import logging


# Setup plc modbus rtu client
def setup_plc_client(SERIAL_PORT, BAUD_RATE, PARITY, STOP_BITS, BYTE_SIZE):
    client = ModbusSerialClient(method='rtu', port=SERIAL_PORT, baudrate=BAUD_RATE, parity=PARITY, stopbits=STOP_BITS,
                                bytesize=BYTE_SIZE)
    return client


# Write data to plc
def write_data_to_plc(client, register_address, value, scaling_factor, slave_id=1):  # Default slave_id is 1
    try:
        scaled_value = int(value * scaling_factor)
        response = client.write_register(register_address, scaled_value, unit=slave_id)
        if not response.isError():
            logging.info(f"Successfully wrote value {value} to register address {register_address}.")
        else:
            logging.error(
                f"Failed to write value {value} to register address {register_address}. Error: {response}")
    except Exception as e:
        logging.error(f"Error writing to PLC: {e}")
