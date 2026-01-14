import os
import socket
import requests
import xml.etree.ElementTree as ET
import subprocess
import time

def find_roku_ip():
    print("--- Step 1: Locating Roku ---")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    
    prefix = ".".join(local_ip.split('.')[:-1])
    for i in range(1, 255):
        ip = f"{prefix}.{i}"
        try:
            r = requests.get(f"http://{ip}:8060/query/device-info", timeout=0.1)
            if "roku" in r.text.lower():
                print(f"Found Roku at: {ip}")
                return ip
        except:
            continue
    return None

def run_test(ip, app_id):
    print("\n--- Running Live Test ---")
    print("Sending PowerOn commands...")
    requests.post(f"http://{ip}:8060/keypress/PowerOn")
    time.sleep(2)
    requests.post(f"http://{ip}:8060/keypress/PowerOn")
    print("Waiting 5 seconds for TV to initialize...")
    time.sleep(5)
    print("Launching app...")
    requests.post(f"http://{ip}:8060/launch/{app_id}")
    print("Test sequence complete. Check your TV!")

def get_schedule_params():
    print("\n--- Step 2: Scheduling ---")
    time_input = input("What time should it run? (Format HH:MM, e.g., 12:25): ").strip()
    
    print("When should this run?")
    print("1. Every day")
    print("2. Weekdays only (Mon-Fri)")
    print("3. Weekends only (Sat-Sun)")
    choice = input("Select 1, 2, or 3: ").strip()
    
    schedule_map = {
        "1": ("DAILY", ""),
        "2": ("WEEKLY", "/d MON,TUE,WED,THU,FRI"),
        "3": ("WEEKLY", "/d SAT,SUN")
    }
    return time_input, schedule_map.get(choice, ("DAILY", ""))

def setup_automation():
    roku_ip = find_roku_ip()
    if not roku_ip:
        roku_ip = input("Could not auto-find Roku. Enter IP manually: ")

    try:
        response = requests.get(f"http://{roku_ip}:8060/query/apps")
        root = ET.fromstring(response.content)
        apps = {app.text.lower(): app.get('id') for app in root.findall('app')}
        
        print("\nAvailable Apps:")
        for name in apps.keys():
            print(f"- {name.capitalize()}")
        
        target_app = input("\nWhich app should I open? ").strip().lower()
        app_id = apps.get(target_app)
    except:
        print("Error connecting to Roku. Check your network.")
        return

    if not app_id:
        print("App not found.")
        return

    # Ask for test before scheduling
    do_test = input("\nWould you like to run a test now? (y/n): ").lower()
    if do_test == 'y':
        run_test(roku_ip, app_id)

    time_val, (freq, days_flag) = get_schedule_params()

    # Create the batch script
    script_path = os.path.join(os.getcwd(), "roku_trigger.bat")
    with open(script_path, "w") as f:
        f.write("@echo off\n")
        f.write(f'curl -d "" "http://{roku_ip}:8060/keypress/PowerOn"\n')
        f.write("timeout /t 3 /nobreak\n") 
        f.write(f'curl -d "" "http://{roku_ip}:8060/keypress/PowerOn"\n')
        f.write("timeout /t 2 /nobreak\n")
        f.write(f'curl -d "" "http://{roku_ip}:8060/launch/{app_id}"\n')

    # Register Task
    task_name = "RokuAutoLaunch"
    cmd = f'schtasks /create /tn "{task_name}" /tr "\"{script_path}\"" /sc {freq} {days_flag} /st {time_val} /f'
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"\n✅ SUCCESS!")
        print(f"Task scheduled for {time_val} ({freq}).")
    except subprocess.CalledProcessError:
        print("\n❌ ERROR: Please run this script as an ADMINISTRATOR (Right-click Terminal > Run as Admin).")

if __name__ == "__main__":
    setup_automation()
