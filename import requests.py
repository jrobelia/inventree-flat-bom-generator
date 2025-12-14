import requests

# CONFIGURE THESE
API_TOKEN = "inv-393961f1e699166b9656a4aa86776f925b6931b0-20250722"
SERVER_URL = "https://staging.inventree.openaeros.com"
SUPPLIER_ID = 36

headers = {"Authorization": f"Token {API_TOKEN}", "Content-Type": "application/json"}

# 1. Get all supplier parts for supplier 36

resp = requests.get(
    f"{SERVER_URL}/api/company/part/?supplier={SUPPLIER_ID}", headers=headers
)
resp.raise_for_status()
supplier_parts = resp.json()

# 2. For each supplier part, set the part's default_supplier to 36
for sp in supplier_parts:
    if sp.get("supplier") == SUPPLIER_ID:
        part_id = sp["part"]
        # PATCH the part to set default_supplier
        patch = requests.patch(
            f"{SERVER_URL}/api/part/{part_id}/",
            headers=headers,
            json={"default_supplier": sp["pk"]},
        )
        if patch.status_code == 200:
            print(
                f"Set default supplier for part {part_id} to supplier part {sp['pk']}"
            )
        else:
            print(f"Failed for part {part_id}: {patch.text}")
