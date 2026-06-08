import pymysql

# Connect to MySQL server (without selecting a database)
try:
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',  # XAMPP default is empty
        charset='utf8mb4'
    )
    
    cursor = connection.cursor()
    
    # Create database if it doesn't exist
    cursor.execute("CREATE DATABASE IF NOT EXISTS fitness_db")
    print("✅ Database 'fitness_db' created successfully!")
    
    # Show all databases to verify
    cursor.execute("SHOW DATABASES")
    databases = cursor.fetchall()
    print("\n📋 Available databases:")
    for db in databases:
        print(f"   - {db[0]}")
    
    cursor.close()
    connection.close()
    
except pymysql.Error as e:
    print(f"❌ Error: {e}")
    print("\nMake sure MySQL is running in XAMPP!")