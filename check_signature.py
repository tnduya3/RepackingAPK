import subprocess
import os
import argparse


def find_tool(name):
    # check PATH
    p = subprocess.run(['where', name], capture_output=True, text=True)
    if p.returncode == 0:
        return p.stdout.strip().split('\n')[0]
    # fallback
    return None


def check_signature(apk_path, keytool_cmd=None):
    if not os.path.exists(apk_path):
        print(f"[-] APK not found: {apk_path}")
        return False

    if keytool_cmd is None:
        keytool_cmd = find_tool('keytool')
        if not keytool_cmd:
            print('[-] keytool not found in PATH.')
            return False

    print(f"[*] Checking signature for: {apk_path}")
    cmd = [keytool_cmd, '-printcert', '-jarfile', apk_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("[+] Certificate details:")
            print(result.stdout)
            return True
        else:
            print("[-] Failed to check signature:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Check APK signature using keytool and jarsigner')
    parser.add_argument('apk', help='Path to the APK file')

    args = parser.parse_args()
    keytool_arg = None
    success = check_signature(args.apk, keytool_arg)


if __name__ == '__main__':
    main()