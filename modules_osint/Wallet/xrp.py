import json
import os
import sys
import requests
from datetime import datetime, timezone

if os.name == "nt":
    os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

_XRPL_RPC = "https://xrplcluster.com/"
_DROPS_PER_XRP = 1_000_000


def _rpc(method, params):
    resp = requests.post(
        _XRPL_RPC,
        json={"method": method, "params": [params]},
        timeout=15,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json().get("result", {})


def check(address):
    try:
        # Account info + balance
        info = _rpc("account_info", {"account": address, "ledger_index": "validated"})

        if info.get("error"):
            err = info.get("error")
            if err in ("actNotFound", "account_not_found"):
                return {
                    "taken": False,
                    "ExtraData": {"Address": address, "Chain": "XRP Ledger", "Error": "address_not_found"},
                }
            return {
                "taken": False,
                "ExtraData": {"Address": address, "Chain": "XRP Ledger", "Error": err},
            }

        acc = info.get("account_data", {})
        balance_xrp = int(acc.get("Balance", 0)) / _DROPS_PER_XRP

        # Recent transactions
        tx_result = _rpc(
            "account_tx",
            {"account": address, "limit": 10, "ledger_index_min": -1, "ledger_index_max": -1},
        )
        transactions = []
        for tx_obj in tx_result.get("transactions") or []:
            tx = tx_obj.get("tx") or {}
            meta = tx_obj.get("meta") or {}
            delivered = meta.get("delivered_amount")
            amount_xrp = None
            if isinstance(delivered, str):
                try:
                    amount_xrp = int(delivered) / _DROPS_PER_XRP
                except ValueError:
                    pass
            date_offset = tx.get("date")
            ts = None
            if date_offset:
                # XRP epoch starts 2000-01-01T00:00:00Z = 946684800 Unix
                ts = datetime.utcfromtimestamp(946684800 + date_offset).strftime("%Y-%m-%dT%H:%M:%SZ")
            transactions.append({
                "TxID": tx.get("hash"),
                "Timestamp": ts,
                "Type": tx.get("TransactionType"),
                "From": tx.get("Account"),
                "To": tx.get("Destination"),
                "AmountXRP": amount_xrp,
                "Fee": int(tx.get("Fee", 0)) / _DROPS_PER_XRP if tx.get("Fee") else None,
                "Confirmations": tx_obj.get("validated"),
            })

        return {
            "taken": True,
            "ExtraData": {
                "Address": address,
                "Chain": "XRP Ledger",
                "BalanceXRP": balance_xrp,
                "OwnerCount": acc.get("OwnerCount"),
                "Sequence": acc.get("Sequence"),
                "Flags": acc.get("Flags"),
                "TotalTransactions": tx_result.get("total") or len(transactions),
                "TransactionsList": transactions,
            },
        }
    except Exception as e:
        return {
            "taken": False,
            "error": str(e),
            "ExtraData": {"Address": address, "Chain": "XRP Ledger"},
        }


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    result = check(_sys.argv[1].strip())
    print(json.dumps(result, indent=4, ensure_ascii=False))
