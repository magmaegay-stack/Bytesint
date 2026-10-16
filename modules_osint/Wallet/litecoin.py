import sys
import requests
import json
import random

def check(address):
    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/full?limit=10"
    
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
        
        if response.status_code == 429:
            return {
                "taken": False, 
                "ExtraData": {
                    "Address": address, 
                    "Error": "Rate limit superato su BlockCypher (HTTP 429)."
                }
            }
            
        if response.status_code != 200:
            return {
                "taken": False, 
                "ExtraData": {
                    "Address": address, 
                    "Error": f"Indirizzo non trovato o errore API (HTTP {response.status_code})"
                }
            }
        
        data = response.json()
        
        balance_ltc = data.get("balance", 0) / 100000000.0
        total_received_ltc = data.get("total_received", 0) / 100000000.0
        total_sent_ltc = data.get("total_sent", 0) / 100000000.0
        
        txs = data.get("txs", [])
        transactions = []
        
        for tx in txs:
            tx_id = tx.get("hash")
            received_time = tx.get("received")
            
            inputs_list = []
            for inp in tx.get("inputs") or []:
                prev_addresses = inp.get("addresses") or []
                inputs_list.extend(prev_addresses)

            outputs_list = []
            for out in tx.get("outputs") or []:
                out_addresses = out.get("addresses") or []
                out_value = out.get("value", 0) / 100000000.0
                for addr in out_addresses:
                    outputs_list.append({
                        "Address": addr,
                        "AmountLTC": out_value
                    })

            transactions.append({
                "TxID": tx_id,
                "Timestamp": received_time,
                "From": list(set(inputs_list)),
                "To": outputs_list,
                "FeesLTC": tx.get("fees", 0) / 100000000.0,
                "Confirmations": tx.get("confirmations", 0)
            })

        return {
            "taken": True,
            "ExtraData": {
                "Address": address,
                "Chain": "Litecoin",
                "BalanceLTC": balance_ltc,
                "TotalReceivedLTC": total_received_ltc,
                "TotalSpentLTC": total_sent_ltc,
                "TotalTransactions": data.get("n_tx", 0),
                "TransactionsList": transactions
            }
        }

    except Exception as e:
        return {
            "taken": False, 
            "error": str(e), 
            "ExtraData": {"Address": address}
        }

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print('{"error": "missing argument"}')
        _sys.exit(1)
    _res = check(_sys.argv[1].strip())
    print(json.dumps(_res, indent=4, ensure_ascii=False))
