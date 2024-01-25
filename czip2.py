#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import socket
from struct import pack, unpack
import threading
from queue import Queue

class IPInfo(object):
    def __init__(self, dbname="qqwry.dat"):
        self.dbname = dbname
        f = open(dbname, 'rb')
        self.img = f.read()
        f.close()
        (self.firstIndex, self.lastIndex) = unpack('<II', self.img[:8])
        self.indexCount = (self.lastIndex - self.firstIndex) // 7 + 1

    def getString(self, offset=0):
        o = self.img.find(b'\0', offset)
        return self.img[offset:o].decode('gbk', errors='ignore')

    def getLong3(self, offset=0):
        s = self.img[offset: offset + 3] + b'\0'
        return unpack('<I', s)[0]

    def gbk2utf8(self, string):
        return string.encode('utf-8')

    def utf82gbk(self, string):
        return string.decode('utf-8').encode('gbk')

    def find(self, ip):
        low = 0
        high = self.indexCount
        while (low < high - 1):
            mid = low + (high - low) // 2
            o = self.firstIndex + mid * 7
            start_ip = unpack('<I', self.img[o: o+4])[0]
            if ip < start_ip:
                high = mid
            else:
                low = mid

        return low

    def getAddr(self, offset):
        img = self.img
        byte = img[offset]
        if byte == 1:
            offset = self.getLong3(offset + 1)
            byte = img[offset]

        if byte == 2:
            zone = self.getString(self.getLong3(offset + 1))
            offset += 4
        else:
            zone = self.getString(offset)
            offset += len(zone) + 1

        byte = img[offset]
        if byte == 2:
            area = self.getString(self.getLong3(offset + 1))
        else:
            area = self.getString(offset)

        return (zone, area)

    def getIPAddr(self, ip):
        ip = unpack('!I', socket.inet_aton(ip))[0]
        i = self.find(ip)
        offset = self.firstIndex + i * 7
        offset = self.getLong3(offset + 4)
        return self.getAddr(offset + 4)

def worker(ip_queue, result_queue):
    i = IPInfo()
    while True:
        ip = ip_queue.get()
        if ip is None:
            break

        try:
            location = i.getIPAddr(ip)
            result_queue.put((ip, location))
        except OSError as e:
            print(f"处理IP {ip} 时发生错误：{e}")

        ip_queue.task_done()

def main():
    ipin_filename = 'ipin.txt'
    ipout_filename = 'ipout.txt'

    # Read IPs from ipin.txt
    with open(ipin_filename, 'r') as ipin_file:
        ip_list = [line.strip() for line in ipin_file]

    # Create queues for IPs and results
    ip_queue = Queue()
    result_queue = Queue()

    # Start worker threads
    num_threads = 5  # Adjust the number of threads as needed
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker, args=(ip_queue, result_queue))
        thread.start()
        threads.append(thread)

    # Add IPs to the queue
    for ip in ip_list:
        ip_queue.put(ip)

    # Add sentinel values to signal the threads to exit
    for _ in range(num_threads):
        ip_queue.put(None)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # Collect results and write to ipout.txt
    with open(ipout_filename, 'w') as ipout_file:
        while not result_queue.empty():
            ip, location = result_queue.get()
            ipout_file.write(f'{ip}-{location[0]}/{location[1]}\n')

if __name__ == '__main__':
    main()
