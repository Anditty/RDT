from rdt import RDTSocket
import time

client = RDTSocket()
client.SYN = 1
client.connect(("127.0.0.1", 9999))
with open("alice.txt", 'rb') as f:
    data = f.read()
t0 = time.time()

client.send(data)
print(f"send ok SEQ:{client.SEQ} SEQACK:{client.SEQACK}")
if len(client.recv(2048)) == len(data):
    print(f"recv ok SEQ:{client.SEQ} SEQACK:{client.SEQACK}")
else:
    print(f"recv failed SEQ:{client.SEQ} SEQACK:{client.SEQACK}")

client.send(data)
print(f"send ok SEQ:{client.SEQ} SEQACK:{client.SEQACK}")
if len(client.recv(2048)) == len(data):
    print(f"recv ok SEQ:{client.SEQ} SEQACK:{client.SEQACK}")
else:
    print(f"recv failed SEQ:{client.SEQ} SEQACK:{client.SEQACK}")

print(time.time() - t0)
client.close()

