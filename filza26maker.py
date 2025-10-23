#!/usr/bin/env python3
"""
Filza26Maker - Pure Python Edition for Windows
Based on the original Filza26Maker by GeoSn0w
Automatically installs required Python packages if missing.

What it does:
 - Downloads a Filza .deb
 - Parses the .deb (AR archive) to extract data.tar.* (handles gz, xz, bz2, zst, tar)
 - Extracts package contents
 - Locates Filza.app, builds Payload/ and creates Filza-Jailed-iOS26-GeoSn0w.ipa
 - Cleans up temporary files

Requires:
 - Python 3.8+
"""
import os
import io
import sys
import shutil
import tarfile
import subprocess
from zipfile import ZipFile

# ---------- Auto-install Dependencies ----------
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError:
        print(f"[!] Failed to install {package}. Please install manually.")
        sys.exit(1)

# Check mandatory packages
try:
    import requests
except ImportError:
    print("[•] Installing missing dependency: requests")
    install_package("requests")
    import requests

# Optional package (zstandard)
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

# ---------- Configuration ----------
DEB_URL = "https://tigisoftware.com/cydia/com.tigisoftware.filza_4.0.1-2_iphoneos-arm.deb"
DEB_FILE = "filza.deb"
WORK_DIR = "_PY_TEMP"
IPA_NAME = "Filza-Jailed-iOS26-GeoSn0w.ipa"
# -----------------------------------

MAGICS = {
    b"\x1f\x8b": "gz",        # gzip
    b"\xfd7zXZ": "xz",        # xz
    b"BZh": "bz2",            # bzip2
    b"\x28\xb5\x2f\xfd": "zst" # zstd
}

def download_deb(url=DEB_URL, out_path=DEB_FILE):
    if os.path.exists(out_path):
        print(f"[!] {out_path} already exists, skipping download.")
        return out_path
    print("[+] Downloading Filza .deb ...")
    r = requests.get(url, stream=True)
    try:
        r.raise_for_status()
    except Exception as e:
        print(f"[!] Download failed: {e}")
        raise
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
    print("[✓] Download completed.")
    return out_path

def parse_ar_and_get_data_bytes(deb_path):
    with open(deb_path, "rb") as f:
        data = f.read()
    if not data.startswith(b"!<arch>\n"):
        raise RuntimeError("Not a valid ar archive (missing !<arch> header).")
    offset = 8
    length = len(data)
    while offset + 60 <= length:
        header = data[offset:offset+60]
        name = header[0:16].decode('utf-8', errors='ignore').strip()
        size_field = header[48:58].decode('utf-8', errors='ignore').strip()
        try:
            size = int(size_field)
        except ValueError:
            raise RuntimeError("Could not parse ar header size.")
        offset += 60
        file_data = data[offset:offset+size]
        clean_name = name.rstrip('/')
        if clean_name.startswith("data.tar"):
            return clean_name, file_data
        offset += size
        if size % 2 == 1:
            offset += 1
    raise RuntimeError("data.tar* member not found in .deb")

def detect_compression_from_bytes(bts):
    for magic, ident in MAGICS.items():
        if bts.startswith(magic):
            return ident
    if len(bts) > 262 and bts[257:262] == b"ustar":
        return "tar"
    return None

def decompress_if_needed(name, data_bytes):
    global zstd, ZSTD_AVAILABLE  # <-- fix global usage
    comp = detect_compression_from_bytes(data_bytes)
    if comp is None:
        return data_bytes, "tar"
    if comp == "gz" or name.endswith(".gz"):
        return data_bytes, "gz"
    if comp == "xz" or name.endswith(".xz"):
        return data_bytes, "xz"
    if comp == "bz2" or name.endswith(".bz2"):
        return data_bytes, "bz2"
    if comp == "zst" or name.endswith(".zst"):
        if not ZSTD_AVAILABLE:
            print("[•] Installing missing dependency: zstandard for .zst extraction")
            install_package("zstandard")
            import zstandard as zstd
            ZSTD_AVAILABLE = True
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(data_bytes)
        return decompressed, "tar"
    return data_bytes, "tar"

def extract_tar_bytes_to_dir(tar_bytes, work_dir):
    bio = io.BytesIO(tar_bytes)
    try:
        with tarfile.open(fileobj=bio, mode='r:*') as tar:
            tar.extractall(work_dir)
    except tarfile.ReadError as e:
        raise RuntimeError(f"tarfile extraction failed: {e}")

def find_app_and_prepare_payload(work_dir):
    payload_dir = os.path.join(work_dir, "Payload")
    os.makedirs(payload_dir, exist_ok=True)
    filza_app_path = None
    for root, dirs, files in os.walk(work_dir):
        for d in dirs:
            if d == "Filza.app":
                filza_app_path = os.path.join(root, d)
                break
        if filza_app_path:
            break
    if not filza_app_path:
        raise RuntimeError("Filza.app not found in extracted data.")
    dest = os.path.join(payload_dir, "Filza.app")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.move(filza_app_path, dest)
    return payload_dir

def build_ipa_from_payload(payload_dir, output_ipa):
    base_name = os.path.splitext(output_ipa)[0]
    tmp_zip = base_name + ".zip"
    with ZipFile(tmp_zip, "w") as zf:
        for root, dirs, files in os.walk(payload_dir):
            for file in files:
                full = os.path.join(root, file)
                arcname = os.path.relpath(full, os.path.dirname(payload_dir))
                zf.write(full, arcname)
    if os.path.exists(output_ipa):
        os.remove(output_ipa)
    os.replace(tmp_zip, output_ipa)

def clean_workdir(work_dir):
    shutil.rmtree(work_dir, ignore_errors=True)

def main():
    print("[•] Filza26Maker - Pure Python Edition\n")
    try:
        download_deb()
    except Exception as e:
        print(f"[!] Error downloading .deb: {e}")
        print("Update DEB_URL if needed.")
        sys.exit(1)

    if os.path.exists(WORK_DIR):
        clean_workdir(WORK_DIR)
    os.makedirs(WORK_DIR, exist_ok=True)

    try:
        member_name, member_bytes = parse_ar_and_get_data_bytes(DEB_FILE)
        print(f"[*] Found internal archive: {member_name}")
        tar_bytes, detected = decompress_if_needed(member_name, member_bytes)
        print(f"[*] Detected compression: {detected}")
        extract_tar_bytes_to_dir(tar_bytes, WORK_DIR)
        print("[✓] Extraction of data.tar* completed.")
        payload = find_app_and_prepare_payload(WORK_DIR)
        print("[✓] Payload prepared.")
        build_ipa_from_payload(payload, IPA_NAME)
        print(f"[✓] IPA built: {IPA_NAME}")
    except Exception as exc:
        print(f"[!] Error: {exc}")
        clean_workdir(WORK_DIR)
        sys.exit(1)

    clean_workdir(WORK_DIR)
    print("[✓] Done. You can now install the IPA with AltStore/Sideloadly/TrollStore.")

if __name__ == "__main__":
    main()
