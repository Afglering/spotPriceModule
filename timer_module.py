#timer_module.py

import threading
import logging

timer_thread = None

def start_timer(auto_connect_callback):
    global timer_thread
    timer_thread = threading.Timer(30.0, auto_connect_callback)
    timer_thread.start()

def stop_timer():
    global timer_thread
    if timer_thread:
        timer_thread.cancel()

def auto_connect_to_plc(handle_plc_option, prices_df, conversion_rate_dkk_to_eur):
    print("No user interaction detected. Attempting to connect to PLC with cached values...")
    try:
        handle_plc_option(prices_df, conversion_rate_dkk_to_eur, auto=True)
    except Exception as e:
        logging.error(f"Automatic PLC connection failed: {e}")
        print(f"Automatic PLC connection failed: {e}")
