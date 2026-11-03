import os
import sys
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")

monitor_ico = os.path.join(SCRIPT_DIR, "SmartWardMonitor.ico")
dispatcher_ico = os.path.join(SCRIPT_DIR, "EmergencyDispatcher.ico")
launcher_ico = os.path.join(SCRIPT_DIR, "SmartWardLauncher.ico")

def build_app(script_name, exe_name, icon_path, extra_args=None):
    print(f"\n=======================================================")
    print(f"Building {exe_name} with icon {icon_path}...")
    print(f"=======================================================")
    
    script_path = os.path.join(SCRIPT_DIR, script_name)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", exe_name,
        "--icon", icon_path,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", SCRIPT_DIR,
        "--collect-all", "customtkinter",
    ]
    
    if extra_args:
        cmd.extend(extra_args)
        
    cmd.append(script_path)
    
    subprocess.run(cmd, check=True)
    print(f"Successfully generated {exe_name} with embedded icon!")

if __name__ == "__main__":
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    
    # 1. Build SmartWardMonitor with icon
    build_app(
        script_name="smart_ward_monitor.py",
        exe_name="SmartWardMonitor",
        icon_path=monitor_ico,
        extra_args=[
            "--hidden-import", "pyttsx3.drivers",
            "--hidden-import", "pyttsx3.drivers.sapi5",
            "--collect-all", "pyttsx3",
            "--collect-all", "requests",
            "--collect-all", "serial"
        ]
    )
    
    # 2. Build EmergencyLocationDispatcher with icon
    build_app(
        script_name="emergency_location_dispatcher.py",
        exe_name="EmergencyLocationDispatcher",
        icon_path=dispatcher_ico,
        extra_args=[
            "--hidden-import", "pyttsx3.drivers",
            "--hidden-import", "pyttsx3.drivers.sapi5",
            "--collect-all", "pyttsx3",
            "--collect-all", "requests",
            "--collect-all", "serial"
        ]
    )

    # 3. Build SmartWardLauncher with icon
    build_app(
        script_name="smart_ward_launcher.py",
        exe_name="SmartWardLauncher",
        icon_path=launcher_ico,
        extra_args=[
            "--collect-all", "customtkinter",
            "--collect-all", "serial"
        ]
    )
    
    # Copy to workspace root & user Desktop
    desktop_dir = os.path.expanduser(r"~\Desktop")
    destinations = [r"D:\Sandbox", desktop_dir]

    for d in destinations:
        if os.path.exists(d):
            try:
                shutil.copy2(os.path.join(DIST_DIR, "SmartWardMonitor.exe"), os.path.join(d, "SmartWardMonitor.exe"))
                shutil.copy2(os.path.join(DIST_DIR, "EmergencyLocationDispatcher.exe"), os.path.join(d, "EmergencyLocationDispatcher.exe"))
                shutil.copy2(os.path.join(DIST_DIR, "SmartWardLauncher.exe"), os.path.join(d, "SmartWardLauncher.exe"))
                print(f"Copied executables to: {d}")
            except Exception as e:
                print(f"Notice copying to {d}: {e}")
    
    print("\nExecutables updated with embedded icons in dist, workspace root, and Desktop!")
