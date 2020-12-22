from rdt import RDTSocket

address = ("127.0.0.1", 9999)
server = RDTSocket()
server.bind(address)
while True:
    conn, address = server.accept()
    print("------------------------")
    while True:
        try:
            print(conn.recv(2048).decode())
        except Exception as e:
            print(e)
            break
