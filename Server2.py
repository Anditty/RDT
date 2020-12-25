from rdt import RDTSocket

address = ("127.0.0.1", 9999)
server = RDTSocket()
server.bind(address)
while True:
    conn, address = server.accept()
    print("------------------------")
    while True:
        recv_data = conn.recv(2048)
        print(f"recv ok SEQ:{conn.SEQ} SEQACK:{conn.SEQACK}")
        if recv_data is None:
            break
        conn.send(recv_data)
        print(f"send ok SEQ:{conn.SEQ} SEQACK:{conn.SEQACK}")
