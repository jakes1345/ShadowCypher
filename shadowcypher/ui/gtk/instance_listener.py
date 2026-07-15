"""P2P connection listener daemon for GTK desktop app."""
import socket
import threading

from shadowcypher.chat import p2p_relay


class InstanceListener:
    """Listens for incoming P2P connections on port 19999."""

    def __init__(self, port=19999):
        self.port = port
        self.server_socket = None
        self.running = False

    def start(self):
        """Start the P2P listener daemon."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))  # nosec B104
        self.server_socket.listen(5)
        self.running = True

        print(f"[*] Instance listener started on port {self.port}")

        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"[+] P2P connection from {client_address}")

                thread = threading.Thread(
                    target=self._handle_p2p_connection,
                    args=(client_socket,),
                    daemon=True
                )
                thread.start()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[-] Accept error: {e}")

    def _handle_p2p_connection(self, client_socket: socket.socket):
        """Handle incoming P2P connection."""
        try:
            data = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break

            if data:
                msg_json = data.decode().strip()
                msg = p2p_relay.P2PMessage.from_json(msg_json)
                print(f"[+] P2P message from {msg.from_instance_id} to {msg.to_instance_id}")
        except Exception as e:
            print(f"[-] P2P handler error: {e}")
        finally:
            client_socket.close()

    def stop(self):
        """Stop the listener."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()


if __name__ == "__main__":
    listener = InstanceListener()
    try:
        listener.start()
    except KeyboardInterrupt:
        listener.stop()
