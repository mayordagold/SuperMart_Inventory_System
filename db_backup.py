import os
import shutil
import sys
from datetime import datetime

DB_FILE = "SuperMart.db"
BACKUP_DIR = "backups"

os.makedirs(BACKUP_DIR, exist_ok=True)

def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"SuperMart_{timestamp}.db")
    shutil.copy2(DB_FILE, backup_file)
    print(f"Backup created: {backup_file}")

def restore(backup_file):
    if not os.path.exists(backup_file):
        print(f"Backup file not found: {backup_file}")
        return
    shutil.copy2(backup_file, DB_FILE)
    print(f"Database restored from: {backup_file}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage:")
        print("  python db_backup.py backup        # Create a backup")
        print("  python db_backup.py restore <backup_file>  # Restore from backup")
    elif sys.argv[1] == "backup":
        backup()
    elif sys.argv[1] == "restore" and len(sys.argv) == 3:
        restore(sys.argv[2])
    else:
        print("Invalid command.")
