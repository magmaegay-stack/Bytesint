import sys
import requests
import json
import random

def check(address):
    url_balance = f"https://eth.blockscout.com/api/v2/addresses/{address}"
    url_txs = f"https://eth.blockscout.com/api/v2/addresses/{address}/transactions?limit=10"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        # Recupero informazioni e saldo
        resp_bal = requests.get(url_balance, headers=headers, timeout=10)
        if resp_bal.status_code != 200:
            return {"taken": False, "ExtraData": {"Address": address, "Error": "Indirizzo non trovato o errore API"}}
        
        bal_data = resp_bal.json()
        # Conversione da Wei a ETH (1 ETH = 10^18 Wei)
        balance_wei = int(bal_data.get("coin_balance", 0) or 0)
        balance_eth = balance_wei / 10**18

        # Recupero transazioni
        resp_txs = requests.get(url_txs, headers=headers, timeout=10)
        transactions = []
        
        if resp_txs.status_code == 200:
            tx_data = resp_txs.json().get("items", [])
            for tx in tx_data:
                value_wei = int(tx.get("value", 0) or 0)
                value_eth = value_wei / 10**18
                
                from_addr = tx.get("from", {}).get("hash")
                to_addr = tx.get("to", {}).get("hash")
                
                transactions.append({
                    "TxID": tx.get("hash"),
                    "Timestamp": tx.get("timestamp"),
                    "From": [from_addr] if from_addr else [],
                    "To": [{"Address": to_addr, "AmountETH": value_eth}] if to_addr else [],
                    "Status": tx.get("status")
                })

        return {
            "taken": True,
            "ExtraData": {
                "Address": address,
                "Chain": "Ethereum",
                "BalanceETH": balance_eth,
                "TotalTransactions": bal_data.get("tx_count", len(transactions)),
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
