import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

print("🔧 Fixing User Database...")
print("=" * 50)

# Load existing users
if os.path.exists('users.json'):
    with open('users.json', 'r') as f:
        users = json.load(f)
    
    changed = False
    
    for email, data in users.items():
        # Fix plain text passwords
        if 'password' in data and 'password_hash' not in data:
            print(f"📧 Fixing user: {email}")
            password_hash = generate_password_hash(data['password'])
            data['password_hash'] = password_hash
            del data['password']
            changed = True
            print(f"   ✅ Migrated to hashed password")
    
    # Save fixed users
    if changed:
        with open('users.json', 'w') as f:
            json.dump(users, f, indent=4)
        print("\n✅ User database fixed!")
    else:
        print("\n✅ No users needed fixing")
    
    # Show all users
    print("\n📋 Registered users:")
    for email, data in users.items():
        print(f"   - {email} ({data.get('name')})")
        
else:
    print("❌ users.json not found. Create a new user via signup first.")

print("\n" + "=" * 50)
print("Now try logging in again!")