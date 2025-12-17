#!/usr/bin/env python3
"""
RetroViewer Dependency Installer
Automatically installs all required Python packages for RetroViewer applications.
"""

import subprocess
import sys
import os
import platform


def install_package(package_name):
    """Install a Python package using pip."""
    print(f"Installing {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✓ {package_name} installed successfully\n")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package_name}\n")
        return False


def check_package(package_name):
    """Check if a package is already installed."""
    try:
        __import__(package_name.replace("-", "_"))
        return True
    except ImportError:
        return False


def check_tkinter():
    """Check if tkinter is installed."""
    try:
        import tkinter
        return True
    except ImportError:
        return False


def install_tkinter_linux():
    """Install tkinter on Linux using system package manager."""
    os_system = platform.system()
    if os_system != "Linux":
        return False
    
    print("Attempting to install tkinter for Linux...")
    print("This requires sudo privileges and may prompt for your password.")
    print()
    
    # Try to detect Linux distribution
    try:
        # Check for Debian/Ubuntu
        if os.path.exists("/etc/debian_version"):
            print("Detected Debian/Ubuntu system")
            cmd = ["sudo", "apt-get", "update"]
            print(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            
            cmd = ["sudo", "apt-get", "install", "-y", "python3-tk"]
            print(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            return True
        
        # Check for Red Hat/Fedora/CentOS
        elif os.path.exists("/etc/redhat-release"):
            print("Detected Red Hat/Fedora/CentOS system")
            # Try dnf first (newer), fall back to yum
            try:
                cmd = ["sudo", "dnf", "install", "-y", "python3-tkinter"]
                print(f"Running: {' '.join(cmd)}")
                subprocess.check_call(cmd)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                cmd = ["sudo", "yum", "install", "-y", "python3-tkinter"]
                print(f"Running: {' '.join(cmd)}")
                subprocess.check_call(cmd)
                return True
        
        # Check for Arch Linux
        elif os.path.exists("/etc/arch-release"):
            print("Detected Arch Linux system")
            cmd = ["sudo", "pacman", "-S", "--noconfirm", "tk"]
            print(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            return True
        
        else:
            print("Could not detect Linux distribution.")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Failed to install tkinter: {e}")
        return False
    except Exception as e:
        print(f"Error during tkinter installation: {e}")
        return False


def main():
    print("=" * 60)
    print("RetroViewer Dependency Installer")
    print("=" * 60)
    print()
    
    # List of required packages
    packages = [
        ("python-vlc", "vlc"),           # VLC Python bindings (import as 'vlc')
        ("mutagen", "mutagen")           # MP4 metadata library
    ]
    
    # Check Python version and OS
    os_system = platform.system()
    print(f"Operating System: {os_system}")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print()
    
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required!")
        print("Please upgrade your Python installation.")
        sys.exit(1)
    
    # Check and install packages
    print("Checking dependencies...")
    print()
    
    installed = []
    failed = []
    already_installed = []
    
    for pip_name, import_name in packages:
        if check_package(import_name):
            print(f"✓ {pip_name} is already installed")
            already_installed.append(pip_name)
        else:
            print(f"✗ {pip_name} not found")
            if install_package(pip_name):
                installed.append(pip_name)
            else:
                failed.append(pip_name)
    
    # Check tkinter
    print()
    print("Checking tkinter (GUI framework)...")
    tkinter_status = "✓ Installed"
    
    if not check_tkinter():
        print("✗ tkinter not found")
        
        if os_system == "Linux":
            print()
            response = input("Would you like to install tkinter now? (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                if install_tkinter_linux():
                    if check_tkinter():
                        print("✓ tkinter installed successfully!")
                        tkinter_status = "✓ Newly installed"
                    else:
                        print("✗ tkinter installation completed but import still fails.")
                        print("You may need to restart your terminal or Python environment.")
                        tkinter_status = "✗ Installation issue"
                else:
                    tkinter_status = "✗ Failed to install"
            else:
                tkinter_status = "✗ Not installed (skipped)"
        elif os_system == "Windows":
            print("On Windows, tkinter should be included with Python.")
            print("If missing, reinstall Python and ensure 'tcl/tk and IDLE' is selected.")
            tkinter_status = "✗ Not found (reinstall Python)"
        elif os_system == "Darwin":  # macOS
            print("On macOS, tkinter should be included with Python.")
            print("If missing, reinstall Python from python.org or use Homebrew:")
            print("  brew install python-tk@3.x")
            tkinter_status = "✗ Not found (reinstall Python)"
        else:
            print(f"Unsupported OS for automatic tkinter installation: {os_system}")
            tkinter_status = "✗ Manual installation required"
    else:
        print("✓ tkinter is installed")
    
    print()
    print("=" * 60)
    print("Installation Summary")
    print("=" * 60)
    
    if already_installed:
        print(f"\nAlready installed ({len(already_installed)}):")
        for pkg in already_installed:
            print(f"  ✓ {pkg}")
    
    if installed:
        print(f"\nNewly installed ({len(installed)}):")
        for pkg in installed:
            print(f"  ✓ {pkg}")
    
    if failed:
        print(f"\nFailed to install ({len(failed)}):")
        for pkg in failed:
            print(f"  ✗ {pkg}")
        print("\nPlease install these packages manually:")
        print(f"  pip install {' '.join(failed)}")
    
    print(f"\ntkinter: {tkinter_status}")
    
    print()
    
    all_ok = not failed and "✓" in tkinter_status
    
    if all_ok:
        print("✓ All dependencies are installed!")
        print()
        print("You can now run:")
        print("  - Manager.py (Unified management interface)")
        print("  - MediaPlayer.py (Commercial player)")
        print("  - FeaturePlayer.py (Movies with commercial breaks)")
        print("  - Manager.py (Includes Video Scanner to scan and sync video files)")
    else:
        print("✗ Some dependencies are missing or failed to install.")
        print("Please resolve the errors above before running RetroViewer.")
        
        if "✗" in tkinter_status:
            print()
            print("tkinter installation notes:")
            if os_system == "Linux":
                print("  - Ubuntu/Debian: sudo apt-get install python3-tk")
                print("  - Fedora/RHEL: sudo dnf install python3-tkinter")
                print("  - Arch Linux: sudo pacman -S tk")
            elif os_system == "Windows":
                print("  - Reinstall Python and select 'tcl/tk and IDLE' option")
            elif os_system == "Darwin":
                print("  - Reinstall Python from python.org")
                print("  - Or use Homebrew: brew install python-tk")
    
    print()
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
