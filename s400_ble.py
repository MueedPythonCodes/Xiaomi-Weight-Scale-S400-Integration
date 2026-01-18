# import sys
# import os
# import asyncio
# import threading
# import webbrowser
# import csv
# import time
# import logging
# from datetime import datetime
# from flask import Flask, render_template, jsonify
# from bleak import BleakScanner

# # --- CONFIGURATION ---
# TARGET_MAC = "2C:19:5C:A9:C3:E8"
# BLE_KEY_HEX = "8d530299501f34a703586c5f5f2a9652"
# CSV_FILE = "weight_history.csv"

# # --- PATH CORRECTION ---
# # This ensures we find the 'lib' folder whether we are in root or a subfolder
# current_dir = os.path.dirname(os.path.abspath(__file__))
# lib_path = os.path.join(current_dir, 'lib')
# if not os.path.exists(lib_path):
#     # Try one level up
#     lib_path = os.path.join(os.path.dirname(current_dir), 'lib')

# sys.path.append(lib_path)

# try:
#     from xiaomi_ble.parser import XiaomiBluetoothDeviceData
#     from bluetooth_sensor_state_data import BluetoothServiceInfo
# except ImportError:
#     print(f"\n❌ ERROR: Could not find 'lib' folder at: {lib_path}")
#     print("Please make sure you are running this script from the project root.\n")
#     XiaomiBluetoothDeviceData = None

# # --- FLASK SERVER ---
# # We use template_folder='.' so it finds index.html in the SAME folder
# app = Flask(__name__, template_folder='.')
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

# state = {
#     "weight": 0.00,
#     "status": "Scanning...",
#     "last_update": "--:--:--"
# }

# # Buffers for stabilization
# weight_buffer = []
# last_saved_weight = 0.0

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/data')
# def data():
#     return jsonify(state)

# def save_csv(weight):
#     try:
#         file_exists = os.path.isfile(CSV_FILE)
#         with open(CSV_FILE, 'a', newline='') as f:
#             writer = csv.writer(f)
#             if not file_exists:
#                 writer.writerow(["Timestamp", "Weight (kg)", "MAC"])
#             writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), weight, TARGET_MAC])
#         print(f"💾 DATA SAVED: {weight} kg")
#     except Exception as e:
#         print(f"❌ CSV ERROR: {e}")

# # --- BLE LOGIC ---
# ble_key = bytes.fromhex(BLE_KEY_HEX)
# parser = XiaomiBluetoothDeviceData(bindkey=ble_key) if XiaomiBluetoothDeviceData else None

# def callback(device, advertisement_data):
#     global state, weight_buffer, last_saved_weight
    
#     if device.address.upper() != TARGET_MAC:
#         return

#     if not parser:
#         return

#     try:
#         service_info = BluetoothServiceInfo(
#             name=device.name,
#             address=device.address,
#             rssi=advertisement_data.rssi,
#             manufacturer_data=advertisement_data.manufacturer_data,
#             service_data=advertisement_data.service_data,
#             service_uuids=advertisement_data.service_uuids,
#             source=device.address
#         )

#         if parser.supported(service_info):
#             update = parser.update(service_info)
#             if update and update.entity_values:
#                 # Find the mass value dynamically
#                 mass = 0.0
#                 for entity in update.entity_values.values():
#                     if 'mass' in entity.name.lower():
#                         mass = entity.native_value
#                         break
                
#                 if mass > 0:
#                     weight = round(float(mass), 2)
                    
#                     # Update Web State
#                     state["weight"] = weight
#                     state["status"] = "Connected"
#                     state["last_update"] = datetime.now().strftime("%H:%M:%S")

#                     # Print to Console (overwriting line)
#                     print(f"\r⚖️  Current Weight: {weight} kg   ", end="")

#                     # Stabilization & Saving Logic
#                     if weight > 5.0:
#                         weight_buffer.append(weight)
#                         if len(weight_buffer) > 5:
#                             weight_buffer.pop(0)
                        
#                         # If last 5 readings are identical
#                         if len(weight_buffer) == 5 and all(w == weight for w in weight_buffer):
#                             if abs(weight - last_saved_weight) > 0.1:
#                                 print() # New line
#                                 save_csv(weight)
#                                 last_saved_weight = weight
#                                 weight_buffer = []

#     except Exception:
#         pass

# async def scan():
#     print("---------------------------------------")
#     print(f"📡 SCANNING FOR: {TARGET_MAC}")
#     print("---------------------------------------")
#     scanner = BleakScanner(detection_callback=callback)
#     while True:
#         try:
#             await scanner.start()
#             await asyncio.sleep(5.0)
#             await scanner.stop()
#         except Exception:
#             await asyncio.sleep(1.0)

# if __name__ == "__main__":
#     # 1. Start Web Server
#     threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

#     # 2. Open Browser
#     print("🖥️  Opening Dashboard...")
#     time.sleep(1.5)
#     webbrowser.open("http://127.0.0.1:5000")

#     # 3. Start Scanning
#     try:
#         asyncio.run(scan())
#     except KeyboardInterrupt:
#         print("\nStopped.")





import sys
import os
import asyncio
import threading
import webbrowser
import csv
import time
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify
from bleak import BleakScanner

# --- CONFIGURATION ---
TARGET_MAC = "2C:19:5C:A9:C3:E8"
BLE_KEY_HEX = "8d530299501f34a703586c5f5f2a9652"
CSV_FILE = "weight_history.csv"

# --- FLASK SETUP ---
app = Flask(__name__, template_folder='.')
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Global State
state = {"weight": 0.0, "status": "Scanning...", "last_update": "--:--:--"}
buffer = []
last_saved_weight = 0.0

# --- LIBRARY CHECK ---
try:
    from xiaomi_ble.parser import XiaomiBluetoothDeviceData
    from bluetooth_sensor_state_data import BluetoothServiceInfo
except ImportError:
    print("\n❌ CRITICAL: Libraries missing.")
    print("Run: pip install flask bleak cryptography xiaomi-ble bluetooth-sensor-state-data\n")
    sys.exit(1)

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('monitor.html')

@app.route('/data')
def get_data():
    return jsonify(state)

# --- CSV FUNCTION (OVERWRITE MODE) ---
def update_csv(weight):
    try:
        # 'w' mode overwrites the file every time
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            # Row 1: Headers
            writer.writerow(["Timestamp", "Weight (kg)", "MAC"])
            # Row 2: Newest Data
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), weight, TARGET_MAC])
        print(f"💾 CSV Updated: {weight} kg (Row 2 overwritten)")
    except Exception as e:
        print(f"❌ CSV Error: {e}")

# --- BLE LOGIC ---
ble_key = bytes.fromhex(BLE_KEY_HEX)
parser = XiaomiBluetoothDeviceData(bindkey=ble_key)

def callback(device, advertisement_data):
    global state, buffer, last_saved_weight
    
    if device.address.upper() != TARGET_MAC:
        return

    try:
        service_info = BluetoothServiceInfo(
            name=device.name,
            address=device.address,
            rssi=advertisement_data.rssi,
            manufacturer_data=advertisement_data.manufacturer_data,
            service_data=advertisement_data.service_data,
            service_uuids=advertisement_data.service_uuids,
            source=device.address
        )
        
        if parser.supported(service_info):
            update = parser.update(service_info)
            if update and update.entity_values:
                # Extract Weight/Mass
                mass = 0.0
                for v in update.entity_values.values():
                    if 'mass' in v.name.lower():
                        mass = v.native_value
                        break
                
                if mass >= 0:
                    current_weight = round(float(mass), 2)
                    state["weight"] = current_weight
                    state["status"] = "Connected"
                    state["last_update"] = datetime.now().strftime("%H:%M:%S")

                    # Console Feedback
                    print(f"\r⚖️  Live: {current_weight} kg   ", end="")

                    # RESET LOGIC: If weight goes to 0, allow saving next time
                    if current_weight < 1.0:
                        last_saved_weight = 0.0
                        buffer = []

                    # STABILIZATION & SAVE LOGIC
                    if current_weight > 5.0:
                        buffer.append(current_weight)
                        if len(buffer) > 5: buffer.pop(0)
                        
                        # If we have 5 identical readings
                        if len(buffer) == 5 and all(w == current_weight for w in buffer):
                            # And it's different from what we last saved
                            if abs(current_weight - last_saved_weight) > 0.1:
                                print() # New line
                                update_csv(current_weight)
                                last_saved_weight = current_weight
                                buffer = [] # Clear buffer after save
    except Exception:
        pass

async def scan():
    print(f"📡 Scanning for S400 ({TARGET_MAC})...")
    scanner = BleakScanner(detection_callback=callback)
    while True:
        try:
            await scanner.start()
            await asyncio.sleep(5)
            await scanner.stop()
        except:
            await asyncio.sleep(1)

if __name__ == "__main__":
    # 1. Start Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()
    
    # 2. Open Browser (Once)
    print("🖥️  Opening Dashboard...")
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")
    
    # 3. Start Scanning Loop
    try:
        asyncio.run(scan())
    except KeyboardInterrupt:
        print("\nStopped.")