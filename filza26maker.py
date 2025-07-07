import os
import shutil
import subprocess
import requests
from zipfile import ZipFile
from pathlib import Path

# Constants
DEB_URL = "https://tigisoftware.com/cydia/com.tigisoftware.filza_4.0.1-2_iphoneos-arm.deb"
DEB_FILE = "filza.deb"
WORK_DIR = "_GEO_TEMP"
IPA_NAME = "Filza-Jailed-iOS26-GeoSn0w.ipa"

def run_cmd(cmd, check=True):
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")

def download_deb():
    print("[+]Download file Filza.deb ...")
    response = requests.get(DEB_URL, stream=True)
    response.raise_for_status()
    with open(DEB_FILE, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("[+]Download completed successfully.")

def extract_deb():
    print("[*]Extract contents deb ...")
    run_cmd("ar -x filza.deb")
    run_cmd("tar -xzf data.tar.gz")

def prepare_payload():
    print("[*]Preparing a folder Payload ...")
    os.makedirs("Payload", exist_ok=True)
    # Try copying Filza.app from the right place
    found = False
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "Filza.app":
                full_path = os.path.join(root, d)
                shutil.copytree(full_path, os.path.join("Payload", "Filza.app"))
                found = True
                break
        if found:
            break
    if not found:
        raise FileNotFoundError("Folder not found Filza.app")

def build_ipa():
    print("[+] Build a file IPA ...")
    with ZipFile(f"../{IPA_NAME}", "w") as zipf:
        for root, _, files in os.walk("Payload"):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, ".")
                zipf.write(full_path, arcname)
    print(f"[✓]File created: {IPA_NAME}")

def clean_up():
    print("[*]Clean up temporary files ...")
    os.chdir("..")
    shutil.rmtree(WORK_DIR)

def main():
    print("[•] Filza26 Python Builder - GeoSn0w Python version\n")

    os.makedirs(WORK_DIR, exist_ok=True)
    os.chdir(WORK_DIR)

    download_deb()
    extract_deb()
    prepare_payload()
    build_ipa()
    clean_up()

    print("\n[✓] It was built Filza IPA Successfully. You can sign it with AltStore or Sideloadly.")

if __name__ == "__main__":
    main()
