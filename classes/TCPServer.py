import socketserver


class TCPServer(socketserver.TCPServer):
    def __init__(self,
                 server,
                 server_address,
                 RequestHandlerClass,
                 bind_and_activate=True,
                 ):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)

        self.server = server
