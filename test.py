import mysql.connector

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="dokumen_kerjasama"
)

cursor = mydb.cursor()

# get dokumen data
# cursor.execute("SELECT * FROM dokumen")

# get all data with validated status
# sql = "SELECT \
#   dokumen.id AS id, \
#   dokumen.judul AS judul, \
#   dokumen.jenis AS jenis, \
#   validitas.meterai AS meterai, \
#   validitas.cap AS cap, \
#   validitas.ttd AS ttd \
#   FROM dokumen \
#   LEFT JOIN validitas ON dokumen.id = validitas.dokumen_id"

# cursor.execute(sql)

# get detail data
# sql = "SELECT \
#   dokumen.id AS id, \
#   dokumen.judul AS judul, \
#   dokumen.jenis AS jenis, \
#   validitas.meterai AS meterai, \
#   validitas.cap AS cap, \
#   validitas.ttd AS ttd \
#   FROM dokumen \
#   LEFT JOIN validitas ON dokumen.id = validitas.dokumen_id \
#   WHERE dokumen.id = %s"

# id_doc = (2, )

# cursor.execute(sql, id_doc)

# result = cursor.fetchall()

# for x in result:
#   print(x)


# insert data
in_dokumen = "INSERT INTO dokumen (judul, jenis) VALUES (%s, %s)"
val_dokumen = ("Dokumen Kerja Sama 2", "dalam_negeri")
cursor.execute(in_dokumen, val_dokumen)

mydb.commit()

cursor.execute("SELECT last_insert_id()")
current_id = cursor.fetchall()[0][0]

in_validitas = "INSERT INTO validitas (meterai, cap, ttd, dokumen_id) VALUES (%s, %s, %s, %s)"
val_validitas = (1, 2, 2, current_id)
cursor.execute(in_validitas, val_validitas)

mydb.commit()

