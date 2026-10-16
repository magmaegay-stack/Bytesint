import sys
import requests
import json
import random

def check(address):
    url = f"https://apilist.tronscanapi.com/api/account?address={address}"
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
    ]

    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return {"taken": False, "ExtraData": {"Address": address, "Error": f"Errore API o indirizzo inesistente (HTTP {response.status_code})"}}
        
        data = response.json()
        
        if not data or "address" not in data:
            return {"taken": False, "ExtraData": {"Address": address, "Error": "Dati account Tron non trovati."}}

        # 1 TRX = 10^6 Sun
        balance_sun = data.get("balance", 0)
        balance_trx = balance_sun / 1000000.0
        
        # Estrazione transazioni recenti (se presenti nella risposta dell'account)
        # TronScan fornisce solitamente un riepilogo o transazioni correlate
        transfers_url = f"https://apilist.tronscanapi.com/api/transfer?address={address}&limit=10"
        resp_txs = requests.get(transfers_url, headers=headers, timeout=10)
        
        transactions = []
        if resp_txs.status_code == 200:
            tx_data = resp_txs.json().get("data", [])
            for tx in tx_data:
                tx_hash = tx.get("txHash")
                amount = float(tx.get("amount", 0)) / 1000000.0
                from_addr = tx.get("transferFromAddress")
                to_addr = tx.get("transferToAddress")
                
                transactions.append({
                    "TxID": tx_hash,
                    "Timestamp": tx.get("block_ts"),
                    "From": [from_addr] if from_addr else [],
                    "To": [{"Address": to_addr, "AmountTRX": amount}] if to_addr else [],
                    "TokenName": tx.get("tokenName", "TRX")
                })

        return {
            "taken": True,
            "ExtraData": {
                "Address": address,
                "Chain": "Tron",
                "BalanceTRX": balance_trx,
                "TotalTransactions": data.get("totalTransactionCount", len(transactions)),
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
