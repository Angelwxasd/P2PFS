#!/usr/bin/env python3
import sys, os, argparse, signal, pathlib, posixpath
from PySide6.QtWidgets import (QApplication, QMessageBox, QFileDialog,
                               QPushButton, QLineEdit, QListWidget)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer
from distribuidoFS import Node


# ---------- Helpers ----------
def parse_peers(text):
    if not text:
        return []
    return [(h, int(p)) for h, p in (item.split(':') for item in text.split(','))]

def graceful_exit(sig, frame):
    print("\nCerrando aplicación…")
    sys.exit(0)


# ---------- GUI ----------
class GuiApp:
    def __init__(self, cli):
        # 1. Carga UI
        ui_path = os.path.join(os.path.dirname(__file__), "menu.ui")
        loader = QUiLoader()
        f = QFile(ui_path)
        if not f.exists():
            raise FileNotFoundError(f"No se encontró {ui_path}")
        f.open(QFile.ReadOnly)
        self.window = loader.load(f)
        f.close()

        # 2. Arranca nodo
        self.node = Node(cli.id, cli.port, parse_peers(cli.peers), cli.root)
        print(f"[Nodo {cli.id}] escuchando en 0.0.0.0:{cli.port} | Peers: {cli.peers or '—'}")

        # 3. Widgets ↔︎ lógica
        self._wire_widgets()

        # 4. Primer refresco + timer
        self._last_snapshot = set()
        self.refresh_file_list()
        self.auto_timer = QTimer(self.window)
        self.auto_timer.setInterval(3000)             # 3 s
        self.auto_timer.timeout.connect(self.refresh_file_list)
        self.auto_timer.start()

    # -------------------------------
    def _wire_widgets(self):
        # Listas
        self.fileList: QListWidget      = self.window.findChild(QListWidget, "fileList")
        self.registrosList: QListWidget = self.window.findChild(QListWidget, "RegistrosList")

        # Transferir archivo
        btn_transfer = self.window.findChild(QPushButton, "btnTransfer")
        self.txt_dest: QLineEdit = self.window.findChild(QLineEdit, "lineEdit_2")
        if btn_transfer:
            btn_transfer.clicked.connect(self._slot_transfer)

        # Crear directorio
        btn_mkdir = self.window.findChild(QPushButton, "btnMkdir")
        self.txt_mkdir: QLineEdit = self.window.findChild(QLineEdit, "lineaEdit1")
        if btn_mkdir:
            btn_mkdir.clicked.connect(self._slot_mkdir)

        # Eliminar archivo/directorio
        btn_delete = self.window.findChild(QPushButton, "btnDelete")
        if btn_delete:
            btn_delete.clicked.connect(self._slot_delete)

        # Peers conectados
        btn_peers = self.window.findChild(QPushButton, "PeersBtn")
        if btn_peers:
            btn_peers.clicked.connect(self._slot_show_peers)

    # -------------------------------
    # SUBIR ARCHIVO
    def _slot_transfer(self):
        src_path, _ = QFileDialog.getOpenFileName(self.window, "Selecciona archivo")
        if not src_path:
            return

        dest_dir = self.txt_dest.text().strip() if self.txt_dest else ""
        if not dest_dir:
            dest_dir = "/"
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir

        dest_path = posixpath.join(dest_dir, pathlib.Path(src_path).name)

        try:
            self.node.op_mkdir(dest_dir)
            self.node.op_transfer(src_path, dest_path)
            QMessageBox.information(self.window, "Éxito", 
                                     f"Archivo '{src_path}' replicado en {dest_path}")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self.window, "Error", str(e))

    # -------------------------------
    # CREAR DIRECTORIO
    def _slot_mkdir(self):
        path = self.txt_mkdir.text().strip() if self.txt_mkdir else ""
        if not path:
            QMessageBox.warning(self.window, "Ruta vacía", 
                                "Ingresa el nombre/directorio (ej. /docs).")
            return
        if not path.startswith("/"):
            path = "/" + path
        try:
            self.node.op_mkdir(path)
            QMessageBox.information(self.window, "Éxito", f"Directorio creado: {path}")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self.window, "Error", str(e))

    # -------------------------------
    # ELIMINAR ARCHIVO/DIRECTORIO
    def _slot_delete(self):
        if not self.fileList or not self.fileList.currentItem():
            QMessageBox.warning(self.window, "Sin selección", 
                                "Selecciona un archivo o directorio en la lista.")
            return

        item_text = self.fileList.currentItem().text()
        path = "/" + item_text.lstrip("./").lstrip("/")

        confirm = QMessageBox.question(
            self.window, "Confirmar eliminación",
            f"¿Seguro que deseas borrar '{path}' en todos los nodos?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.node.op_delete(path)
            QMessageBox.information(self.window, "Eliminado", f"'{path}' borrado.")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self.window, "Error", str(e))

    # -------------------------------
    # MOSTRAR PEERS
    def _slot_show_peers(self):
        if not getattr(self, "registrosList", None):
            return
        self.registrosList.clear()
        peers = getattr(self.node, "peers", [])
        if not peers:
            self.registrosList.addItem("Sin peers conectados.")
            return
        for host, port in peers:
            self.registrosList.addItem(f"{host}:{port}")

    # -------------------------------
    # REFRESCAR LISTA DE ARCHIVOS
    def refresh_file_list(self):
        if not getattr(self, "fileList", None):
            return

        curr = set()
        for root, dirs, files in os.walk(self.node.root):
            rel_root = os.path.relpath(root, self.node.root)
            prefix = "" if rel_root == "." else rel_root + "/"
            curr |= {prefix + d + "/" for d in dirs}
            curr |= {prefix + f for f in files}

        if curr == self._last_snapshot:
            return
        self._last_snapshot = curr

        self.fileList.blockSignals(True)
        self.fileList.clear()
        for item in sorted(curr):
            self.fileList.addItem(item.lstrip("./"))
        self.fileList.blockSignals(False)

    # -------------------------------
    def run(self):
        self.window.show()


# ---------- MAIN ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser("GUI + CLI para sistema de archivos distribuido")
    ap.add_argument("--id",   type=int, required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--peers", default="")
    ap.add_argument("--root",  default="fsroot")
    args = ap.parse_args()

    app = QApplication(sys.argv)
    gui = GuiApp(args)
    gui.run()

    signal.signal(signal.SIGINT, graceful_exit)
    sys.exit(app.exec())
