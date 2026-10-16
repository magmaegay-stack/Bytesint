#!/usr/bin/env python3
import sys
import os
import json
import re

DIR = os.path.dirname(os.path.abspath(__file__))

def detect_chain(address: str) -> str:
    addr = address.strip()
    if addr.startswith("0x") and len(addr) == 42:
        return "ethereum"
    if addr.startswith("bc1") or ((addr.startswith("1") or addr.startswith("3")) and 26 <= len(addr) <= 35):
        return "bitcoin"
    if addr.startswith("ltc1") or ((addr.startswith("L") or addr.startswith("M")) and 26 <= len(addr) <= 35):
        return "litecoin"
    if addr.startswith("D") and 30 <= len(addr) <= 36:
        return "dogecoin"
    if addr.startswith("T") and len(addr) == 34:
        return "tron"
    if addr.startswith("r") and 25 <= len(addr) <= 35:
        return "xrp"
    if re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", addr):
        return "solana"
    return "ethereum"

def resolve_wallet(address: str, chain_override: str = None) -> dict:
    addr = address.strip()
    chain = (chain_override or detect_chain(addr)).lower()
    
    script_map = {
        "bitcoin": "bitcoin.py",
        "btc": "bitcoin.py",
        "ethereum": "ethereum.py",
        "eth": "ethereum.py",
        "solana": "solana.py",
        "sol": "solana.py",
        "litecoin": "litecoin.py",
        "ltc": "litecoin.py",
        "dogecoin": "dogecoin.py",
        "doge": "dogecoin.py",
        "tron": "tron.py",
        "trx": "tron.py",
        "xrp": "xrp.py",
        "bnb": "bnb.py",
        "bsc": "bnb.py",
    }
    
    script_name = script_map.get(chain, "ethereum.py")
    script_path = os.path.join(DIR, script_name)
    
    if not os.path.exists(script_path):
        return {"target": addr, "service": "wallet", "result": "error", "msg": f"Script not found: {script_name}"}
        
    try:
        import subprocess
        out = subprocess.check_output([sys.executable, script_path, addr], text=True, timeout=12)
        data = json.loads(out)
        
        extra = data.get("ExtraData", {})
        is_taken = data.get("taken", False)
        
        # Normalize balance key across scripts
        balance = None
        for k in ["BalanceETH", "BalanceBTC", "BalanceSOL", "BalanceLTC", "BalanceDOGE", "BalanceTRX", "BalanceXRP", "BalanceBNB", "Balance"]:
            if k in extra:
                balance = f"{extra[k]} {k.replace('Balance', '') or chain.upper()}"
                break
                
        tx_count = extra.get("TotalTransactions", len(extra.get("TransactionsList", [])))
        tx_list = extra.get("TransactionsList", [])
        
        ret_data = {
            "address": addr,
            "chain": extra.get("Chain", chain.capitalize()),
            "balance": balance or "0.00",
            "total_transactions": tx_count,
            "transactions": tx_list[:10] if isinstance(tx_list, list) else [],
            "status": "active_ledger" if is_taken else "clean_unfunded",
            "explorer_url": get_explorer_url(chain, addr),
        }
        
        return {
            "target": addr,
            "service": "wallet",
            "result": "found" if is_taken else "not_found",
            "return": ret_data,
            "raw": data
        }
    except Exception as e:
        return {"target": addr, "service": "wallet", "result": "error", "msg": str(e)}

def get_explorer_url(chain: str, addr: str) -> str:
    c = chain.lower()
    if "eth" in c:
        return f"https://etherscan.io/address/{addr}"
    if "btc" in c or "bit" in c:
        return f"https://www.blockchain.com/explorer/addresses/btc/{addr}"
    if "sol" in c:
        return f"https://solscan.io/account/{addr}"
    if "ltc" in c or "lite" in c:
        return f"https://blockchair.com/litecoin/address/{addr}"
    if "doge" in c:
        return f"https://dogechain.info/address/{addr}"
    if "tron" in c or "trx" in c:
        return f"https://tronscan.org/#/address/{addr}"
    if "xrp" in c:
        return f"https://xrpscan.com/account/{addr}"
    if "bnb" in c or "bsc" in c:
        return f"https://bscscan.com/address/{addr}"
    return f"https://etherscan.io/address/{addr}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('{"error": "missing address argument"}')
        sys.exit(1)
    addr_arg = sys.argv[1].strip()
    chain_arg = sys.argv[2].strip() if len(sys.argv) > 2 else None
    res = resolve_wallet(addr_arg, chain_arg)
    print(json.dumps(res, indent=4, ensure_ascii=False))
