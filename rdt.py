from USocket import UnreliableSocket
import threading
import time
import sys


class StoppableThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.__running = threading.Event()
        self.__running.set()

        self.isRunning = True
        self.job = None
        self.job_args = None

    def set_job(self, job, job_args=None):
        self.job = job
        self.job_args = job_args

    def run(self):
        if self.__running.isSet():
            if self.job is None:
                print("job is None")
            else:
                if self.job_args is None:
                    self.job()
                else:
                    self.job(self.job_args)

    def stop(self):
        self.__running.clear()
        self.isRunning = False


class RDTSocket(UnreliableSocket):
    """
    The functions with which you are to build your RDT.
    -   recvfrom(bufsize)->bytes, addr
    -   sendto(bytes, address)
    -   bind(address)

    You can set the mode of the socket.
    -   settimeout(timeout)
    -   setblocking(flag)
    By default, a socket is created in the blocking mode.
    https://docs.python.org/3/library/socket.html#socket-timeouts

    """

    # packet head defined
    def __init__(self, rate=None, debug=True):
        super().__init__(rate=rate)
        self._rate = rate
        self._send_to = None
        self._recv_from = None
        self.debug = debug

        self.ack_number = -1
        self.start_state = 0  # 0,1,2 分别表示握手的三个阶段
        self.father: RDTSocket = None  # 对于server端生成的conn，记录是谁创建了它
        self.window_size = 10
        self.cwnd = 1  # congestion control window size
        self.rwnd = 12  # GBN window size
        self.pkt_length = 1500  # 每一个packet的长度
        self.ssthresh = sys.maxsize  # 发生丢包等错误时回退的值，默认为int最大值
        self.duplicate = 0  # duplicate packet number
        # head
        # flags
        self.SYN = 0  # 1 0
        self.FIN = 0  # 1 1
        self.ACK = 0  # 1 2
        # others
        self.SEQ = 0  # 4 3
        self.SEQACK = 1  # 4 7
        self.LEN = 0  # 4 11
        self.CHECKSUM = 0  # 2 15
        self.PAYLOAD = 0  # 4 17

        self.STOP = 0  # 21

        # 用来测速度的
        self.accumulate_bytes = 0

        # 用来存储待发数据
        self.send_buffer = []
        self.ack_buffer = []

        # 开一个线程专门用来发送数据
        self.send_thread = StoppableThread()
        self.send_thread.set_job(self.send_rdt)
        self.send_thread.setDaemon(True)

        # 用来存储接收到的数据
        self.recv_buffer = []

        # 开一个线程专门用来接收数据
        self.recv_thread = StoppableThread()
        self.recv_thread.set_job(self.recv_rdt)
        self.recv_thread.setDaemon(True)

        # 收发之间的共享数据
        self.last_SEQ = 0
        self.last_SEQACK = 1

    def combine_head(self):
        return self.SYN.to_bytes(1, byteorder="big") + \
               self.FIN.to_bytes(1, byteorder="big") + \
               self.ACK.to_bytes(1, byteorder="big") + \
               self.STOP.to_bytes(1, byteorder="big") + \
               self.SEQ.to_bytes(4, byteorder="big") + \
               self.SEQACK.to_bytes(4, byteorder="big") + \
               self.LEN.to_bytes(4, byteorder="big") + \
               self.CHECKSUM.to_bytes(2, byteorder="big") + \
               self.PAYLOAD.to_bytes(4, byteorder="big")

    def clear_flags(self):
        self.SYN = 0
        self.FIN = 0
        self.ACK = 0
        self.STOP = 0

    @staticmethod
    def get_SYN(data: bytes):
        return data[0]

    @staticmethod
    def get_FIN(data: bytes):
        return data[1]

    @staticmethod
    def get_ACK(data: bytes):
        return data[2]

    @staticmethod
    def get_STOP(data: bytes):
        return data[3]

    @staticmethod
    def get_SEQACK(data: bytes):
        return int.from_bytes(data[8:12], byteorder="big")

    @staticmethod
    def get_SEQ(data: bytes):
        return int.from_bytes(data[4:8], byteorder="big")

    @staticmethod
    def remove_head(data: bytes):
        if len(data) == 22:
            return None
        else:
            return data[22:]

    def sendto_rdt(self, data, address):
        if self.father is None:
            self.sendto(data, address)
        else:
            self.father.sendto(data, address)

    def recvfrom_rdt(self, bufsize):
        if self.father is None:
            return self.recvfrom_check(bufsize)
        else:
            return self.father.recvfrom_check(bufsize)

    def settimeout_rdt(self, value):
        if self.father is None:
            self.settimeout(value)
        else:
            self.father.settimeout(value)

    def accept(self) -> ('RDTSocket', (str, int)):
        """
        Accept a connection. The socket must be bound to an address and listening for
        connections. The return value is a pair (conn, address) where conn is a new
        socket object usable to send and receive data on the connection, and address
        is the address bound to the socket on the other end of the connection.

        This function should be blocking.
        """
        conn, addr = RDTSocket(self._rate), None

        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        def show_stage():
            if self.start_state == 0:
                print("Listen")

            if self.start_state == 1:
                print("SYN-ACK-Send")

            if self.start_state == 2:
                print("Established")

        self.start_state = 0

        while self.start_state < 3:
            show_stage()
            if self.start_state == 0:  # Listen state
                data_stage_1 = self.recvfrom_check(2048)
                if data_stage_1 is None:
                    continue
                data_stage_1, addr = data_stage_1
                if RDTSocket.get_SYN(data_stage_1) == 1:  # 判断SYN是否为1
                    self.start_state += 1
                    continue

            if self.start_state == 1:  # Send SYN and ACK
                self.clear_flags()
                self.SYN = 1
                self.ACK = 1

                data_stage_2 = self.generatePkt(None)
                self.sendto(data_stage_2, addr)
                self.start_state += 1
                continue

            if self.start_state == 2:  # wait to receive ACK
                data_stage_3 = self.recvfrom_check(2048)
                if data_stage_3 is None:
                    continue

                data_stage_3, addr = data_stage_3
                if RDTSocket.get_SYN(data_stage_3) == 1:  # 如果收到SYN, 说明对方可能没有收到SYN,ACK。
                    self.start_state -= 1
                    continue

                if RDTSocket.get_ACK(data_stage_3) == 1 or RDTSocket.get_SEQ(
                        data_stage_3) > 0:  # 判断ACK是否为1，如果SYN+ACK丢失，在收到数据包时,通过pkt的SEQACK,进入ESTABLISHED。
                    self.start_state += 1

                    conn.set_send_to(addr)
                    conn.set_recv_from(addr)

                    self.set_send_to(addr)
                    self.set_recv_from(addr)

                    conn.father = self
                    conn.SEQ = self.SEQ
                    conn.SEQACK = self.SEQACK

                    conn.send_thread.start()
                    conn.recv_thread.start()

                    self.clear_flags()
                    continue

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return conn, addr

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """

        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        def show_stage():
            if self.start_state == 0:
                print("SYN-Send")

            if self.start_state == 1:
                print("Wait")

            if self.start_state == 2:
                print("Established")

        while self.start_state < 3:
            show_stage()

            if self.start_state == 0:  # 发送SYN，请求建立连接
                self.clear_flags()
                self.SYN = 1

                data_stage_1 = self.generatePkt(None)
                self.sendto(data_stage_1, address)
                self.start_state += 1
                continue

            try:
                if self.start_state == 1:  # 等待接收SYN和ACK
                    self.settimeout(1.5)
                    data_stage_2 = self.recvfrom_check(2048)
                    self.settimeout(None)

                    if data_stage_2 is None:
                        self.start_state -= 1
                        continue
                    data_stage_2 = data_stage_2[0]

                    if RDTSocket.get_SYN(data_stage_2) == 1 and RDTSocket.get_ACK(data_stage_2) == 1:
                        self.start_state += 1
                    else:
                        self.start_state -= 1
                    continue
            except Exception:
                self.start_state -= 1  # 超时， 重新发送SYN
                continue

            if self.start_state == 2:  # 发送ACK， 开始建立连接
                self.clear_flags()
                self.ACK = 1

                data_stage_3 = self.generatePkt(None)
                self.sendto(data_stage_3, address)
                self.start_state += 1

                self.set_send_to(address)
                self.set_recv_from(address)
                self.send_thread.start()
                self.recv_thread.start()

                continue

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def recv_rdt(self):
        while self.recv_thread.isRunning:
            data = None
            while self.recv_thread.isRunning:
                while data is None and self.recv_thread.isRunning:
                    try:
                        self.settimeout_rdt(1)
                        data = self.recvfrom_rdt(bufsize=15000)
                    except:
                        self.settimeout(None)
                        continue

                if self.recv_thread.isRunning is False:
                    break

                if data is not None:
                    data = data[0]

                if RDTSocket.get_FIN(data) == 1:
                    break

                if RDTSocket.remove_head(data) is not None:
                    # 如果收到的是数据包
                    if RDTSocket.get_SEQ(data) == self.SEQACK:
                        self.SEQACK += 1
                        # 收到正确的数据包，放入recv_buffer
                        self.recv_buffer.append(data)

                    # 发送SEQACK回复，并放入send_buffer
                    pkt_data = self.generatePkt(None)
                    self.ack_buffer.append(pkt_data)
                else:
                    # 如果收到的是ACK包
                    if RDTSocket.get_SEQACK(data) == self.ack_number:
                        self.duplicate += 1
                        if self.duplicate == 3:
                            self.duplicate = 0
                            self.cwnd /= 2
                            self.ssthresh /= 2
                    else:
                        # 正常接收
                        self.duplicate = 0
                        self.ack_number = RDTSocket.get_SEQACK(data)
                        self.last_SEQACK = max(self.last_SEQACK, self.ack_number)
                        self.congest_control()

                data = None

            if self.recv_thread.isRunning and RDTSocket.get_FIN(data) == 1:
                self.send_thread.stop()
                close_state = 0
                close_count = 0
                while close_state < 3:
                    print(f"server close state {close_state}")
                    if close_state == 0:  # 发送ACK，表示已经收到了FIN
                        self.clear_flags()
                        self.ACK = 1
                        data_stage_1 = self.generatePkt(None)
                        self.sendto_rdt(data_stage_1, self._send_to)
                        close_state += 1
                        continue

                    if close_state == 1:  # 发送FIN，表示自己要关闭连接
                        self.clear_flags()
                        self.ACK = 1
                        self.FIN = 1
                        data_stage_2 = self.generatePkt(None)
                        self.sendto_rdt(data_stage_2, self._send_to)
                        close_state += 1
                        continue

                    if close_state == 2:  # 等待对方发送ack
                        try:
                            self.settimeout(5)
                            data_stage_3 = self.recvfrom_rdt(2048)
                            self.settimeout(None)

                            if data_stage_3 is None:
                                continue
                            data_stage_3 = data_stage_3[0]

                            if RDTSocket.get_FIN(data_stage_3) == 1:  # 对方没有收到ACK/ACK+FIN
                                close_state = 0
                                continue

                            if RDTSocket.get_ACK(data_stage_3) == 1:
                                self.recv_buffer.append(b'')
                                self._send_to = None
                                self._recv_from = None
                                self.recv_thread.stop()
                                close_state += 1
                                continue

                        except Exception:  # 如果第四次挥手的包丢失，等待一段时间后自动断开连接
                            print("close count: {}".format(close_count))
                            close_count += 1
                            if close_count == 1:
                                self.recv_buffer.append(b'')
                                self._send_to = None
                                self._recv_from = None
                                self.recv_thread.stop()
                                close_state += 1
                            continue

        self.settimeout_rdt(None)

    def send_rdt(self):
        while self.send_thread.isRunning:
            pkt_point = 0
            base_point = 0

            time_count = 0

            while self.send_thread.isRunning:
                time_count += 1

                if len(self.send_buffer) > 0 and self.last_SEQ + 1 - self.last_SEQACK < self.window_size \
                        and pkt_point < len(self.send_buffer):
                    self.window_size = max(min(self.cwnd, self.rwnd), 1)
                    # 只要window_size没有满，就进行发送
                    self.SEQ = base_point + (pkt_point + 1)
                    self.last_SEQ = self.SEQ

                    pkt_data = self.generatePkt(self.send_buffer[pkt_point])
                    pkt_point += 1

                    self.sendto_rdt(pkt_data, self._send_to)
                    time_count = 0

                elif len(self.ack_buffer) > 0:
                    self.sendto_rdt(self.ack_buffer[0], self._send_to)
                    self.ack_buffer.remove(self.ack_buffer[0])
                else:
                    time.sleep(0.001)

                if time_count >= 300:
                    if self.last_SEQACK <= len(self.send_buffer):
                        self.last_SEQ = max(self.last_SEQACK - 1, base_point)
                        pkt_point = self.last_SEQ - (base_point + 1)

                        self.ssthresh = self.cwnd / 2
                        self.cwnd = 1  # 快回退

                        time_count = 0
                    else:
                        time_count = 0
        self.settimeout_rdt(None)

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        assert self._recv_from, "Connection not established yet. Use recvfrom instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        while True:
            if len(self.recv_buffer) > 0:
                recv_data: bytes = self.recv_buffer[0]

                assert len(recv_data) <= bufsize, "bufsize is too small."

                # 数据读取成功，将其移出recv_buffer
                self.recv_buffer.remove(self.recv_buffer[0])
                recv_data = RDTSocket.remove_head(recv_data)
                break
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return recv_data

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to, "Connection not established yet. Use sendto instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        pkt_length = 0  # 以bytes为单位

        # 将data进行拆分
        while pkt_length < len(bytes):
            self.send_buffer.append(bytes[pkt_length:pkt_length + min(self.pkt_length, len(bytes) - pkt_length)])
            pkt_length = pkt_length + self.pkt_length
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def congest_control(self):
        """
        这个方法应当在每次成功接受到ack时被调用，用于拥塞控制
        """
        if self.cwnd < self.ssthresh:
            self.cwnd += 1  # slow start
        else:
            self.cwnd += (1 / self.cwnd)  # linear add
        # 3 times duplicate or timeout

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither futher sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        if self.father is not None:
            super().close()
            return

        while self.last_SEQ < len(self.send_buffer) or len(self.ack_buffer) > 0:
            pass

        self.send_thread.stop()
        self.recv_thread.stop()

        while self.send_thread.is_alive() or self.recv_thread.is_alive():
            pass

        close_state = 0
        while close_state < 4:
            print(f"close state {close_state}")
            try:
                if close_state == 0:  # 发送FIN信息
                    self.clear_flags()
                    self.FIN = 1
                    data_stage_1 = self.generatePkt(None)
                    self.sendto(data_stage_1, self._send_to)
                    close_state += 1
                    continue

                if close_state == 1:  # 等待接收ack
                    self.settimeout(1.5)
                    data_stage_2 = self.recvfrom_check(2048)

                    self.settimeout(None)
                    if data_stage_2 is None:
                        continue
                    data_stage_2 = data_stage_2[0]
                    if RDTSocket.get_ACK(data_stage_2) == 1:
                        close_state += 1
                    continue

                if close_state == 2:  # 等待接收对方的FIN信息
                    self.settimeout(1.5)
                    data_stage_3 = self.recvfrom_check(2048)
                    self.settimeout(None)

                    if data_stage_3 is None:
                        continue
                    data_stage_3 = data_stage_3[0]
                    if RDTSocket.get_FIN(data_stage_3) == 1 and RDTSocket.get_ACK(data_stage_3) == 1:
                        close_state += 1
                    continue

                if close_state == 3:  # 发送ack信息并断开连接
                    self.clear_flags()
                    self.ACK = 1
                    data_stage_4 = self.generatePkt(None)
                    self.sendto(data_stage_4, self._send_to)
                    self._send_to = None
                    self._recv_from = None
                    close_state += 1
                    continue
            except Exception as e:
                print(e)
                close_state = 0
                continue
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()

    def set_send_to(self, send_to):
        self._send_to = send_to

    def set_recv_from(self, recv_from):
        self._recv_from = recv_from

    def prepareForreceive(self, seq, ack, len, mod):  # len is the previous packet len
        if mod == 0:
            self.SEQ = seq + len
            self.ACK = ack
        else:
            self.SEQ = ack
            self.ACK = seq + len

    def generatePkt(self, data):
        self.CHECKSUM = 0
        if data is None:
            pkt_data = self.combine_head()
        else:
            pkt_data = self.combine_head() + data
        checksum = self.generateChecksum(pkt_data)
        self.CHECKSUM = checksum
        if data is None:
            pkt_data = self.combine_head()
        else:
            pkt_data = self.combine_head() + data
        self.clear_flags()
        return pkt_data

    def recvfrom_check(self, buffer_size):  # 接收消息并进行校验，如果校验成功，返回原数据，如果失败则返回None。
        data = self.recvfrom(buffer_size)
        if data is None:
            return None
        is_correct = self.check(data[0])
        if is_correct:
            return data
        else:
            return None

    def check(self, data):
        head = data[0:22]
        checksum = data[16:18]
        pkt_data = head[0:16] + (0).to_bytes(2, byteorder="big") + data[18:]
        return self.checkCheckSum(pkt_data, checksum)

    @staticmethod
    def generateChecksum(message):  # require meassage in bytes
        length = len(message)
        inves_checksum = 0

        for index in range(2, length):
            inves_checksum = inves_checksum + int.from_bytes(message[index:index + 2], byteorder="big")
            cout = inves_checksum >> 16
            inves_checksum = inves_checksum - (cout << 16) + cout

        checkcum = 0xFFFF ^ int(hex(inves_checksum), 16)
        return (int)(checkcum)

    @staticmethod
    def checkCheckSum(message, checksum):
        # assume checksum is the k position
        # 8-bit
        k = 2
        checksum = int.from_bytes(checksum, byteorder="big")
        inves_checksum = 0
        length = len(message)
        for index in range(2, length):
            inves_checksum = inves_checksum + int.from_bytes(message[index:index + 2], byteorder="big")
            cout = inves_checksum >> 16
            inves_checksum = inves_checksum - (cout << 16) + cout

        if checksum ^ int(hex(inves_checksum), 16) == int(0xFFFF):
            return True
        else:
            return False


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""
