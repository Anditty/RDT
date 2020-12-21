from rdt import RDTSocket
import time

client = RDTSocket()
client.SYN = 1
client.connect(("127.0.0.1", 9999))
with open("alice.txt", 'rb') as f:
    data = f.read()
t0 = time.time()
client.send(data)
print(time.time() - t0)
client.close()

