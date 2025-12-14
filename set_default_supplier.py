import requests
import json
import os

# Load server config from config/servers.json
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "servers.json"
)
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

# Choose server (change to 'production' if needed)
SERVER_NAME = "staging"
server = config["servers"][SERVER_NAME]
SERVER_URL = server["url"]
API_TOKEN = server["api_key"]

headers = {"Authorization": f"Token {API_TOKEN}", "Content-Type": "application/json"}

# Prompt user for Part ID and Supplier Part ID
part_id = input("Enter the Part ID to update: ").strip()
supplier_part_id = input("Enter the Supplier Part ID to set as default: ").strip()

# PATCH the part to set default_supplier
resp = requests.patch(
    f"{SERVER_URL}/api/part/{part_id}/",
    headers=headers,
    json={"default_supplier": supplier_part_id},
)
if resp.status_code == 200:
    print(
        f"[OK] Set default supplier for part {part_id} to supplier part {supplier_part_id}"
    )
else:
    print(f"[ERROR] Failed for part {part_id}: {resp.text}")
