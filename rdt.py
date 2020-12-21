from USocket import UnreliableSocket
import threading
import time
import random
import sys


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

        self.acknumber = -1
        self.start_state = 0  # 0,1,2 分别表示握手的三个阶段
        self.father: RDTSocket = None  # 对于server端生成的conn，记录是谁创建了它
        self.window_size = 10
        self.cwnd = 10  # congestion control window size
        self.rwnd = 1000  # GBN window size
        self.pkt_length = 1460  # 每一个packet的长度
        self.ssthresh = sys.maxsize  # 发生丢包等错误时回退的值，默认为int最大值
        self.duplicate = 0  # duplicate packet number
        # head
        # flags
        self.SYN = 0  # 1 0
        self.FIN = 0  # 1 1
        self.ACK = 0  # 1 2
        # others
        self.SEQ = 0  # 4 3
        self.SEQACK = 0  # 4 7
        self.LEN = 0  # 4 11
        self.CHECKSUM = 0  # 2 15
        self.PAYLOAD = 0  # 4 17

        self.STOP = 0  # 21

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
        return data[22:]

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
                    self.start_state -= 1
                    continue
                data_stage_3, addr = data_stage_3
                if RDTSocket.get_SYN(data_stage_3) == 1:  # 如果收到SYN, 说明对方可能没有收到SYN,ACK。
                    self.start_state -= 1
                    continue

                if RDTSocket.get_ACK(data_stage_3) == 1:  # 判断ACK是否为1
                    self.start_state += 1
                    conn.set_send_to(addr)
                    conn.set_recv_from(addr)
                    self.set_send_to(addr)
                    self.set_recv_from(addr)
                    conn.father = self
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

        self.bind(("127.0.0.1", random.randint(1, 1000) + 61000))

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
                continue

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        data = None
        fin_data = None
        assert self._recv_from, "Connection not established yet. Use recvfrom instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        while data is None:
            if self.father is not None:
                data, address = self.father.recvfrom_check(bufsize)
            else:
                data, address = self.recvfrom_check(bufsize)

        # 如果接受的数据STOP为1，表示对方已经发送结束；如果FIN为1，表示是对方需要进行close
        while RDTSocket.get_STOP(data) != 1 and RDTSocket.get_FIN(data) != 1:
            if RDTSocket.get_SEQ(data) == self.SEQACK:
                self.SEQACK = RDTSocket.get_SEQ(data) + 1

                # 将收到的数据去掉报文头，并进行拼接
                if fin_data is None:
                    fin_data = RDTSocket.remove_head(data)
                else:
                    fin_data += RDTSocket.remove_head(data)

            pkt_data = self.generatePkt(None)

            if self.father is not None:
                self.father.sendto(pkt_data, self._send_to)
            else:
                self.sendto(pkt_data, self._send_to)

            if self.father is not None:  # 接受数据
                tmp_data = self.father.recvfrom_check(bufsize)
            else:
                tmp_data = self.recvfrom_check(bufsize)

            if tmp_data is not None:
                data = tmp_data[0]

        if RDTSocket.get_FIN(data) == 1:
            close_state = 0
            while close_state < 3:
                print(f"server close state {close_state}")
                if close_state == 0:  # 发送ACK，表示已经收到了FIN
                    self.clear_flags()
                    self.ACK = 1
                    data_stage_1 = self.generatePkt(None)
                    if self.father is not None:
                        self.father.sendto(data_stage_1, self._send_to)
                    else:
                        self.sendto(data_stage_1, self._send_to)
                    close_state += 1
                    continue

                if close_state == 1:  # 发送FIN，表示自己要关闭连接
                    self.clear_flags()
                    self.ACK = 1
                    self.FIN = 1
                    data_stage_2 = self.generatePkt(None)
                    if self.father is not None:
                        self.father.sendto(data_stage_2, self._send_to)
                    else:
                        self.sendto(data_stage_2, self._send_to)
                    close_state += 1
                    continue

                if close_state == 2:  # 等待对方发送ack
                    if self.father is not None:
                        data_stage_3 = self.father.recvfrom_check(bufsize)
                    else:
                        data_stage_3 = self.recvfrom_check(bufsize)
                    if data_stage_3 is None:
                        continue
                    data_stage_3 = data_stage_3[0]

                    if RDTSocket.get_FIN(data_stage_3) == 1:  # 对方没有收到ACK/ACK+FIN
                        close_state = 0
                        continue

                    if RDTSocket.get_ACK(data_stage_3) == 1:
                        self._send_to = None
                        self._recv_from = None
                        close_state += 1
                        continue

                    self._send_to = None
                    self._recv_from = None
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return fin_data

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to, "Connection not established yet. Use sendto instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        pkt_list = []
        pkt_l = 0
        pkt_point = 0  # 表示本次发送中，要发第几个包
        base_point = self.SEQ  # 表示本次发送之前已经发了多少个包
        last_SEQ = self.SEQ  # 记录最后发送的seq
        last_SEQACK = self.SEQ  # 记录最新收到的ack
        while pkt_l < len(bytes):
            pkt_list.append(bytes[pkt_l:pkt_l + min(self.pkt_length, len(bytes) - pkt_l)])
            pkt_l = pkt_l + self.pkt_length

        while last_SEQACK < len(pkt_list) + base_point:
            self.window_size = min(self.cwnd, self.rwnd)
            if last_SEQ - last_SEQACK < self.window_size and pkt_point < len(pkt_list):
                # 只要window_size没有满，就进行发送
                self.SEQ = base_point + pkt_point
                last_SEQ = self.SEQ
                pkt_point += 1

                pkt_data = self.generatePkt(pkt_list[pkt_point])
                if self.father is not None:
                    self.father.sendto(pkt_data, self._send_to)
                else:
                    self.sendto(pkt_data, self._send_to)
            else:
                try:
                    # 当window已满，进行接收
                    self.settimeout(1.5)
                    if self.father is not None:
                        ack_data = self.father.recvfrom_check(2048)
                    else:
                        ack_data = self.recvfrom_check(2048)
                    if ack_data is None:
                        continue
                    ack_data = ack_data[0]
                    # 如果连续多次收到重复的ack，缩小cwnd
                    if RDTSocket.get_SEQACK(ack_data) == self.acknumber:
                        self.duplicate += 1
                        if self.duplicate == 3:
                            self.duplicate = 0
                            self.cwnd /= 2
                            self.ssthresh /= 2

                    else:
                        # 正常接收
                        self.duplicate = 0
                        self.acknumber = RDTSocket.get_SEQACK(ack_data)
                        last_SEQACK = max(last_SEQACK, self.acknumber)
                        self.congest_control()
                except Exception:  # 发生超时
                    last_SEQ = max(last_SEQACK - 1, base_point)
                    pkt_point = last_SEQ - base_point

                    self.ssthresh = self.cwnd / 2
                    self.cwnd = 1  # 快回退

        # 当所有消息发送完时，发送一条STOP为1的packet
        self.clear_flags()
        self.STOP = 1
        self.SEQ += 1
        if self.father is not None:
            self.father.sendto(self.generatePkt(None), self._send_to)
        else:
            self.sendto(self.generatePkt(None), self._send_to)
        self.STOP = 0
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
        close_state = 0
        while close_state < 4:
            print(f"close state {close_state}")
            try:
                self.settimeout(1.5)
                if close_state == 0:  # 发送FIN信息
                    self.clear_flags()
                    self.FIN = 1
                    data_stage_1 = self.generatePkt(None)
                    self.sendto(data_stage_1, self._send_to)
                    close_state += 1
                    continue

                if close_state == 1:  # 等待接收ack
                    data_stage_2 = self.recvfrom_check(2048)
                    if data_stage_2 is None:
                        continue
                    data_stage_2 = data_stage_2[0]
                    if RDTSocket.get_ACK(data_stage_2) == 1:
                        close_state += 1
                    continue

                if close_state == 2:  # 等待接收对方的FIN信息
                    data_stage_3 = self.recvfrom_check(2048)
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
            except Exception:
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
        return pkt_data

    def recvfrom_check(self, buffer_size):  # 接收消息并进行校验，如果校验成功，返回原数据，如果失败则返回None。
        data = self.recvfrom(buffer_size)
        if data is None:
            return data
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
