import socket


running_at_enbw = False


host_name = socket.gethostname()
if "ENBW-" in host_name:
    running_at_enbw = True



