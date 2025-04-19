import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="QscWdzEax753861942",
        database="bot_database"
    )
    print("✅ Успешное подключение к базе данных!")
    conn.close()
except mysql.connector.Error as err:
    print("❌ Ошибка подключения:", err)
