#!/usr/bin/env python3
"""
Enhanced RF Radar Setup Script
Automatically installs dependencies and tests the application
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(cmd, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} detected. Python 3.8+ required.")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    # Core dependencies
    deps = [
        "pydantic>=2.6",
        "bleak>=0.22",
        "requests>=2.31"
    ]
    
    for dep in deps:
        print(f"Installing {dep}...")
        success, stdout, stderr = run_command(f"{sys.executable} -m pip install {dep}")
        if not success:
            print(f"❌ Failed to install {dep}: {stderr}")
            return False
        print(f"✅ {dep} installed successfully")
    
    return True

def check_system_requirements():
    """Check system-specific requirements"""
    system = platform.system()
    print(f"\n🖥️  System: {system}")
    
    if system == "Windows":
        # Check if netsh is available
        success, _, _ = run_command("netsh wlan show profiles", check=False)
        if success:
            print("✅ WiFi scanning available (netsh)")
        else:
            print("⚠️  WiFi scanning may not work (netsh not available)")
    
    # Check Bluetooth availability
    try:
        import bleak
        print("✅ BLE scanning available (bleak)")
    except ImportError:
        print("⚠️  BLE scanning not available (bleak not installed)")
    
    return True

def test_application():
    """Test the enhanced radar application"""
    print("\n🧪 Testing application...")
    
    # Check if the main file exists
    app_path = Path("apps/desktop_py/enhanced_radar.py")
    if not app_path.exists():
        print(f"❌ Application file not found: {app_path}")
        return False
    
    print(f"✅ Application file found: {app_path}")
    
    # Try to import the main modules
    try:
        sys.path.insert(0, str(Path.cwd()))
        from libs.core.schema import Observation, GeoPoint, WifiInfo, BleInfo
        print("✅ Core schemas imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core schemas: {e}")
        return False
    
    return True

def create_desktop_shortcut():
    """Create a desktop shortcut (Windows only)"""
    if platform.system() != "Windows":
        return
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Enhanced RF Radar.lnk")
        target = os.path.join(os.getcwd(), "apps", "desktop_py", "enhanced_radar.py")
        wDir = os.getcwd()
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{target}"'
        shortcut.WorkingDirectory = wDir
        shortcut.IconLocation = sys.executable
        shortcut.save()
        
        print(f"✅ Desktop shortcut created: {path}")
    except ImportError:
        print("⚠️  Desktop shortcut creation requires pywin32 and winshell")
    except Exception as e:
        print(f"⚠️  Could not create desktop shortcut: {e}")

def main():
    """Main setup function"""
    print("🎯 Enhanced RF Radar Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Dependency installation failed")
        sys.exit(1)
    
    # Check system requirements
    check_system_requirements()
    
    # Test application
    if not test_application():
        print("\n❌ Application test failed")
        sys.exit(1)
    
    # Create desktop shortcut
    create_desktop_shortcut()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nTo run the Enhanced RF Radar:")
    print("  python apps/desktop_py/enhanced_radar.py")
    print("\nFor more information, see ENHANCED_README.md")

if __name__ == "__main__":
    main()
