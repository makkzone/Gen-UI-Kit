import socket
import time
def check_port(port,host="localhost",timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        result = sock.connect_ex((host,port))
        sock.close()
        if result == 0:
            return True
        time.sleep(1)
    return False

def monitor_port(port, host="localhost"):
    if check_port(port,host):
        return True
    else:
        return False