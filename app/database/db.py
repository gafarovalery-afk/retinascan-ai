import mysql.connector

db = mysql.connector.connect(

    host="localhost",

    user="root",

    password="",

    port=3307,

    database="retinascan_db"

)

cursor = db.cursor()