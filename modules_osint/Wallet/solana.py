import sys
import requests
import json

def check(address):
    rpc_url = "https://api.mainnet-beta.solana.com"
    headers = {"Content-Type": "application/json"}

    try:
        # 1. Richiesta del saldo (in Lamports)
        payload_balance = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [address]
        }
        resp_bal = requests.post(rpc_url, json=payload_balance, headers=headers, timeout=10)
        bal_json = resp_bal.json()
        
        if "error" in bal_json or "result" not in bal_json:
            return {"taken": False, "ExtraData": {"Address": address, "Error": "Indirizzo Solana non valido o errore RPC"}}

        lamports = bal_json["result"].get("value", 0)
        balance_sol = lamports / 1000000000.0  # 1 SOL = 10^9 Lamports

        # 2. Richiesta delle ultime transazioni (firme)
        payload_sigs = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [address, {"limit": 10}]
        }
        resp_sigs = requests.post(rpc_url, json=payload_sigs, headers=headers, timeout=10)
        sigs_json = resp_sigs.json()
        
        transactions = []
        if "result" in sigs_json:
            for sig_info in sigs_json["result"]:
                transactions.append({
                    "TxID": sig_info.get("signature"),
                    "Slot": sig_info.get("slot"),
                    "Timestamp": sig_info.get("blockTime"),
                    "Error": sig_info.get("err"),
                    "Memo": sig_info.get("memo")
                })

        return {
            "taken": True,
            "ExtraData": {
                "Address": address,
                "Chain": "Solana",
                "BalanceSOL": balance_sol,
                "TransactionsCount": len(transactions),
                "TransactionsList": transactions
            }
        }
    except Exception as e:
        return {"taken": False, "error": str(e), "ExtraData": {"Address": address}}

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = check(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
