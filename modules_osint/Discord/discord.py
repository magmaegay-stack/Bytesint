#!/usr/bin/env python3
import sys
import os
import re

# Direct forward to discord_snowflake
current_dir = os.path.dirname(os.path.abspath(__file__))
snowflake_script = os.path.join(current_dir, "discord_snowflake.py")

if __name__ == "__main__":
    target = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    # If target is email, check Mail/discord.py, otherwise Discord snowflake
    if "@" in target:
        mail_script = os.path.join(current_dir, "..", "Mail", "discord.py")
        if os.path.exists(mail_script):
            os.system(f'python3 "{mail_script}" "{target}"')
            sys.exit(0)
    
    # Run snowflake lookup
    os.system(f'python3 "{snowflake_script}" "{target}"')
