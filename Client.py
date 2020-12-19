from rdt import RDTSocket

client = RDTSocket()
client.SYN = 1
client.connect(("127.0.0.1", 8888))
client.send((1).to_bytes(10, byteorder="big"))
client.send((100).to_bytes(10, byteorder="big"))
client.close()

