import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="QscWdzEax753861942",
        database="bot_database"
    )
