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
TARGET_MAC = "AB:AD:45:3B:4C:7A"
BLE_KEY_HEX = "cdcebdcjernjkvnkdfvnf" # Paste you Bindkey here
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
