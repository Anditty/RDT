from rdt import RDTSocket
import time

client = RDTSocket()
client.SYN = 1
client.connect(("127.0.0.1", 8888))
t0 = time.time()
with open("alice.txt", 'rb') as f:
    data = f.read()
client.send(data)
client.send_thread.join()
# while True:
#     print(client.last_SEQACK)
#     data = input("send: ")
#     if data == "exit":
#         break
#     client.send(data.encode())
#     time.sleep(0.1)
# print("emmmmmm")
# print(time.time() - t0)
# client.close()

