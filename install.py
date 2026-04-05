#!/usr/bin/env python3
"""
Installation script for APK repacking tools: keytool, apktool, and jarsigner.

This script checks for the required tools and installs/downloads them if missing.
- keytool and jarsigner: Come with JDK. If not found, prompts to install JDK.
- apktool: Downloads the JAR file if not present.
"""

import os
import sys
import subprocess
import urllib.request
import shutil


def run_command(cmd, shell=False):
    """Run a command and return True if successful."""
    try:
        subprocess.check_call(cmd, shell=shell)
        return True
    except subprocess.CalledProcessError:
        return False


def check_java():
    """Check if Java is installed."""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if result.returncode == 0:
            print("[+] Java is installed.")
            return True
        else:
            print("[-] Java not found or not working.")
            return False
    except FileNotFoundError:
        print("[-] Java not found in PATH.")
        return False


def check_keytool():
    """Check if keytool is available."""
    try:
        result = subprocess.run(['keytool', '-version'], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if result.returncode == 0:
            print("[+] keytool is available.")
            return True
        else:
            print("[-] keytool not working.")
            return False
    except FileNotFoundError:
        print("[-] keytool not found in PATH.")
        return False


def check_jarsigner():
    """Check if jarsigner is available."""
    try:
        result = subprocess.run(['jarsigner', '-version'], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if result.returncode == 0:
            print("[+] jarsigner is available.")
            return True
        else:
            print("[-] jarsigner not working.")
            return False
    except FileNotFoundError:
        print("[-] jarsigner not found in PATH.")
        return False


def check_apktool():
    """Check if apktool is available (either command or jar)."""
    # Check for apktool command
    try:
        result = subprocess.run('apktool --version < nul', shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and '2.' in result.stdout:
            print("[+] apktool command is available.")
            return True
    except subprocess.TimeoutExpired as e:
        if '2.' in e.stdout:
            print("[+] apktool command is available.")
            return True
    except (FileNotFoundError, OSError):
        pass

    # Check for apktool.jar
    if os.path.isfile('apktool.jar'):
        print("[+] apktool.jar found in current directory.")
        return True

    print("[-] apktool not found.")
    return False


def install_jdk():
    """Prompt to install JDK."""
    print("\n[!] JDK is required for keytool and jarsigner.")
    print("Please install JDK (Java Development Kit) from:")
    print("  - Oracle JDK: https://www.oracle.com/java/technologies/javase-downloads.html")
    print("  - OpenJDK: https://adoptium.net/ (recommended)")
    print("Or use package manager:")
    print("  - Windows: winget install Microsoft.OpenJDK.17")
    print("  - Chocolatey: choco install openjdk")
    print("After installation, run this script again.")
    return False


def download_apktool():
    """Download apktool.jar and apktool.bat."""
    jar_url = "https://github.com/iBotPeaches/Apktool/releases/latest/download/apktool.jar"
    bat_url = "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/windows/apktool.bat"
    jar_filename = "apktool.jar"
    bat_filename = "apktool.bat"
    
    # Download jar
    print(f"[*] Downloading {jar_filename} from {jar_url}...")
    try:
        with urllib.request.urlopen(jar_url) as response, open(jar_filename, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"[+] Downloaded {jar_filename} successfully.")
    except Exception as e:
        print(f"[-] Failed to download {jar_filename}: {e}")
        return False
    
    # Download bat
    print(f"[*] Downloading {bat_filename} from {bat_url}...")
    try:
        with urllib.request.urlopen(bat_url) as response, open(bat_filename, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"[+] Downloaded {bat_filename} successfully.")
    except Exception as e:
        print(f"[-] Failed to download {bat_filename}: {e}")
        return False
    
    # Move to C:\Windows
    dest_dir = r"C:\Windows"
    try:
        shutil.move(jar_filename, os.path.join(dest_dir, jar_filename))
        shutil.move(bat_filename, os.path.join(dest_dir, bat_filename))
        print(f"[+] Moved {jar_filename} and {bat_filename} to {dest_dir}.")
        return True
    except PermissionError:
        print(f"[-] Permission denied moving to {dest_dir}. Please run as administrator or move manually.")
        print(f"Move {jar_filename} and {bat_filename} from current directory to {dest_dir}.")
        return False
    except Exception as e:
        print(f"[-] Failed to move files: {e}")
        return False


def main():
    print("APK Repacking Tools Installer")
    print("=" * 30)

    java_ok = check_java()
    keytool_ok = check_keytool()
    jarsigner_ok = check_jarsigner()
    apktool_ok = check_apktool()

    if not java_ok:
        install_jdk()
        return

    if not keytool_ok or not jarsigner_ok:
        print("[-] keytool or jarsigner not found, but Java is installed. They should be available with JDK.")
        print("Please check your JDK installation.")

    if not apktool_ok:
        if download_apktool():
            print("[+] apktool.jar is now available.")
        else:
            print("[-] Failed to install apktool.")

    print("\n[*] Installation check complete.")
    if java_ok and (keytool_ok or jarsigner_ok) and apktool_ok:
        print("[+] All tools are ready!")
    else:
        print("[-] Some tools may still be missing. Please resolve the issues above.")


if __name__ == '__main__':
    main()