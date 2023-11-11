# Purpose: This module contains functions for communicating with the PLC over Modbus TCP.
import logging

from pymodbus.client import ModbusTcpClient as ModbusClient
from pymodbus.exceptions import ConnectionException, ModbusIOException

# IP address for the Moxa MGate 5103 device
MOXA_IP_ADDRESS = '192.168.127.254'


# Setup plc modbus tcp client
def setup_plc_client(IP_ADDRESS, PORT=502):
    try:
        client = ModbusClient(host=IP_ADDRESS, port=PORT)
        if client.connect():
            logging.info("PLC TCP client setup successful.")
            print("PLC TCP client setup successful.")
            return client
        else:
            logging.error("Failed to connect to PLC TCP client.")
            return None
    except Exception as e:
        logging.error(f"Error setting up PLC TCP client: {e}")
        return None


# Write data to plc over Modbus TCP with enhanced diagnostics
def write_data_to_plc(client, register_address, value, scaling_factor, unit_id=1):
    try:
        # Ensure the socket is open before attempting to write
        if not client.is_socket_open():
            client.connect()

        logging.info("Connected to the PLC over TCP/IP.")

        # Scale the value to an integer before writing to the register
        scaled_value = int(value * scaling_factor)

        # Write the scaled value to the specified register address
        response = client.write_register(register_address, scaled_value, unit=unit_id)

        # Check if the response indicates an error
        if response.isError():
            logging.error(f"Failed to write value {scaled_value} to register address {register_address}. Error: {response}")
            return False
        else:
            logging.info(f"Successfully wrote value {scaled_value} to register address {register_address}.")
            return True
    except ModbusIOException as e:
        logging.error(f"Modbus IO Error while writing to PLC: {e}")
        return False
    except ConnectionException as e:
        logging.error(f"Connection Error while writing to PLC: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while writing to PLC: {e}")
        return False
    finally:
        # It's usually a good idea to close the client, but you may wish to manage the connection elsewhere
        client.close()
