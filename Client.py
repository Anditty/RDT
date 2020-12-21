from rdt import RDTSocket

client = RDTSocket()
client.SYN = 1
client.connect(("127.0.0.1", 8888))
with open("alice.txt", 'rb') as f:
    data = f.read()
client.send(data)
client.close()

