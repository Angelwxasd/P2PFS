import argparse, os, socket, threading, pickle, sys, time, uuid

BUFFER = 65536
SYNC_INTERVAL = 5  # segundos entre reintentos de sincronización
TIMEOUT = 0.5      # timeout en segundos para conexiones


def reliable_send(sock, obj):
    data = pickle.dumps(obj)
    length = len(data).to_bytes(4, 'big')
    sock.sendall(length + data)


def reliable_recv(sock):
    length_data = sock.recv(4)
    if not length_data:
        return None
    length = int.from_bytes(length_data, 'big')
    data = b''
    while len(data) < length:
        packet = sock.recv(min(BUFFER, length - len(data)))
        if not packet:
            raise ConnectionError('Socket closed prematurely')
        data += packet
    return pickle.loads(data)

class Node:
    def __init__(self, node_id, port, peers, root):
        self.id = node_id
        self.port = port
        self.peers = peers
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.log = []
        self.applied = set()

        # Inicia servidor
        self.server_thread = threading.Thread(target=self.server, daemon=True)
        self.server_thread.start()
        time.sleep(0.2)

        # Sincronización inicial y bucle de retentativas
        self.sync_with_peers()
        threading.Thread(target=self._sync_loop, daemon=True).start()

    def server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', self.port))
            s.listen()
            print(f'[Nodo {self.id}] escuchando en {self.port}')
            while True:
                conn, _ = s.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

    def handle_client(self, conn):
        with conn:
            try:
                msg = reliable_recv(conn)
                if not msg:
                    return
                if msg.get('type') == 'ops':
                    self.apply_operations(msg.get('log', []))
                    reliable_send(conn, {'status': 'ok'})
                elif msg.get('type') == 'sync':
                    reliable_send(conn, {'log': self.log})
            except (OSError, ConnectionError) as e:
                print(f'[Nodo {self.id}] Error cliente (red): {e}')
            except Exception as e:
                print(f'[Nodo {self.id}] Error cliente: {e}')

    def broadcast(self, ops):
        for host, port in self.peers:
            try:
                with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
                    reliable_send(sock, {'type': 'ops', 'log': ops})
                    reliable_recv(sock)
            except (OSError, socket.timeout):
                continue

    def sync_with_peers(self):
        """
        Sincroniza con todos los peers disponibles y aplica la versión de log más larga.
        """
        collected_logs = []
        for host, port in self.peers:
            try:
                with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
                    reliable_send(sock, {'type': 'sync'})
                    resp = reliable_recv(sock)
                    peer_log = resp.get('log', [])
                    collected_logs.append(peer_log)
                    print(f'[Nodo {self.id}] recibió log de {host}:{port} ({len(peer_log)} ops)')
            except (OSError, socket.timeout):
                continue

        if not collected_logs:
            print(f'[Nodo {self.id}] sin peers alcanzables al iniciar/sincronizar')
            return

        # Selecciona el log más largo
        longest = max(collected_logs, key=lambda l: len(l))
        self.apply_operations(longest)
        print(f'[Nodo {self.id}] sincronizado con el log más largo ({len(longest)} ops)')

    def _sync_loop(self):
        while True:
            time.sleep(SYNC_INTERVAL)
            self.sync_with_peers()

    # Operaciones públicas
    def op_transfer(self, src_local, dest_path):
        if not os.path.isfile(src_local):
            print('El archivo origen no existe')
            return
        with open(src_local, 'rb') as f:
            content = f.read()
        op = {
            'id': str(uuid.uuid4()),
            'cmd': 'transfer',
            'path': dest_path,
            'content': content
        }
        self.apply_operations([op])
        self.broadcast([op])

    def op_delete(self, path):
        op = {
            'id': str(uuid.uuid4()),
            'cmd': 'delete',
            'path': path
        }
        self.apply_operations([op])
        self.broadcast([op])

    def op_mkdir(self, path):
        op = {
            'id': str(uuid.uuid4()),
            'cmd': 'mkdir',
            'path': path
        }
        self.apply_operations([op])
        self.broadcast([op])

    def apply_operations(self, ops):
        for op in ops:
            if op['id'] in self.applied:
                continue
            abspath = os.path.join(self.root, op['path'].lstrip('/'))
            if op['cmd'] == 'transfer':
                os.makedirs(os.path.dirname(abspath), exist_ok=True)
                with open(abspath, 'wb') as f:
                    f.write(op['content'])
            elif op['cmd'] == 'delete':
                if os.path.isdir(abspath):
                    for r, _, fs in os.walk(abspath, topdown=False):
                        for name in fs:
                            os.remove(os.path.join(r, name))
                    os.rmdir(abspath)
                elif os.path.exists(abspath):
                    os.remove(abspath)
            elif op['cmd'] == 'mkdir':
                os.makedirs(abspath, exist_ok=True)

            self.log.append(op)
            self.applied.add(op['id'])

    def list_dir(self):
        for root, dirs, files in os.walk(self.root):
            lvl = root.replace(self.root, '').count(os.sep)
            ind = '  ' * lvl
            print(f'{ind}{os.path.basename(root) if lvl else root}/')
            sub = '  ' * (lvl + 1)
            for f in files:
                print(f'{sub}{f}')

    def show_peers(self):
        for i, (host, port) in enumerate(self.peers, 1):
            print(f'Peer {i}: {host}:{port}')


def parse():
    p = argparse.ArgumentParser()
    p.add_argument('--id', type=int, required=True)
    p.add_argument('--port', type=int, required=True)
    p.add_argument('--peers', required=True, help='host:port,host:port...')
    p.add_argument('--root', default='fsroot')
    p.add_argument('--op', help='mkdir, delete, transfer, list, peers, wait')
    p.add_argument('--path')
    p.add_argument('--src')
    return p.parse_args()


def main():
    args = parse()
    peers = [(h, int(pt)) for h, pt in (x.split(':') for x in args.peers.split(','))]
    node = Node(args.id, args.port, peers, args.root)
    if args.op == 'mkdir' and args.path:
        node.op_mkdir(args.path)
    elif args.op == 'delete' and args.path:
        node.op_delete(args.path)
    elif args.op == 'transfer' and args.src and args.path:
        node.op_transfer(args.src, args.path)
    elif args.op == 'list':
        node.list_dir()
    elif args.op == 'peers':
        node.show_peers()
    elif args.op == 'wait':
        print(f'[Nodo {node.id}] esperando indefinidamente...')
        while True:
            time.sleep(60)
    else:
        print('Comandos: transfer <src_local> <dest_path>, delete <dest_path>, list, mkdir <path>, peers, exit')
        while True:
            try:
                parts = input('> ').strip().split()
            except EOFError:
                break
            if not parts:
                continue
            cmd, *arg = parts
            if cmd == 'transfer' and len(arg) == 2:
                node.op_transfer(arg[0], arg[1])
            elif cmd == 'delete' and len(arg) == 1:
                node.op_delete(arg[0])
            elif cmd == 'list':
                node.list_dir()
            elif cmd == 'mkdir' and len(arg) == 1:
                node.op_mkdir(arg[0])
            elif cmd == 'peers':
                node.show_peers()
            elif cmd == 'exit':
                sys.exit(0)
            else:
                print('Comando inválido')

if __name__ == '__main__':
    main()
