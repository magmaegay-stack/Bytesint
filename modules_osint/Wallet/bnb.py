import json
import os
import sys
import requests
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

_BSC_RPC = "https://bsc-dataseed.binance.org/"
_WEI_PER_BNB = 10 ** 18


def _eth_rpc(method, params):
    resp = requests.post(
        _BSC_RPC,
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
        timeout=15,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


def check(address):
    try:
        # Balance
        bal_resp = _eth_rpc("eth_getBalance", [address, "latest"])
        if "error" in bal_resp:
            return {
                "taken": False,
                "ExtraData": {"Address": address, "Chain": "BNB Smart Chain", "Error": bal_resp["error"]},
            }

        balance_wei = int(bal_resp["result"], 16)
        balance_bnb = balance_wei / _WEI_PER_BNB

        # Outgoing transaction count (nonce)
        nonce_resp = _eth_rpc("eth_getTransactionCount", [address, "latest"])
        nonce = int(nonce_resp["result"], 16) if "result" in nonce_resp else None

        # Check if contract or EOA
        code_resp = _eth_rpc("eth_getCode", [address, "latest"])
        is_contract = False
        if "result" in code_resp:
            is_contract = code_resp["result"] not in ("0x", "0x0", "")

        taken = balance_bnb > 0 or (nonce is not None and nonce > 0)

        return {
            "taken": taken,
            "ExtraData": {
                "Address": address,
                "Chain": "BNB Smart Chain",
                "BalanceBNB": balance_bnb,
                "OutgoingTransactions": nonce,
                "IsContract": is_contract,
                "Note": "Transaction history requires BscScan API key",
                "TransactionsList": [],
            },
        }
    except Exception as e:
        return {
            "taken": False,
            "error": str(e),
            "ExtraData": {"Address": address, "Chain": "BNB Smart Chain"},
        }


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    result = check(_sys.argv[1].strip())
    print(json.dumps(result, indent=4, ensure_ascii=False))
