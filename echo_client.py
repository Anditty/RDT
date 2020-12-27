from rdt import RDTSocket
import time
from difflib import Differ

client = RDTSocket()
client.connect(('127.0.0.1', 9999))

data_count = 0
echo = b''
count = 1

with open('alice.txt', 'r') as f:
    data = f.read()
    encoded = data.encode()
    assert len(data) == len(encoded)
start = time.perf_counter()
for i in range(count):  # send 'alice.txt' for count times
    data_count += len(data)
    client.send(encoded)

'''
blocking send works but takes more time
'''

while True:
    reply = client.recv(2048)
    echo += reply
    if len(echo) == len(encoded) * count:
        break
while len(client.ack_buffer) > 0:
    pass
print(f"{client.last_SEQ}, {len(client.send_buffer)}")
client.close()

'''
make sure the following is reachable
'''

print(f'transmitted {data_count}bytes in {time.perf_counter() - start}s')
diff = Differ().compare((data*count).splitlines(keepends=True), echo.decode().splitlines(keepends=True))
for line in diff:
    if not line.startswith('  '):  # check if data is correctly echoed
        print(line)
