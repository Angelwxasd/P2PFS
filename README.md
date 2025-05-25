# Instrucciones para usar el programa

#### Actualmente realizamos las siguientes operaciones:
1. Crear Directorios 
  mkdir
2. Transferir Archivos
   transfer
3. Eliminar Archivos o Directorios
  delete
4. Listar contenido (Se realiza en automático)
  list
7. Mostrar Peers (Tanto conectados como los que se conocen pero están desconectados)
  peers

### Para correr el archivo se necesita:

1. Python 3.7 (o superior)
  python --version
2. PySide6 (para la interfaz gráfica)
  pip install PySide6
3. Asegurar que el puerto que elijas esté permitido en el firewall local


#### Estructura para correr el programa

Para ejecutar el programa se propone la siguiente sintaxis:
  python gui_main.py --id 1 --port 5000 \
  --peers 127.0.0.1:5001,127.0.0.1:5002 --root fs1

**--id X**: Identificador numérico único para este nodo (debe diferir de los demás).

**--port 5000**: Puerto TCP en el que este nodo escucha conexiones entrantes de peers.

**--peers 127.0.0.1:5001,127.0.0.1:5002**: No incluye al propio nodo. Aquí le dices con quién debe sincronizar y reenviar operaciones.
  Por ejemplo: --peers IPNodo2:5002, IPNodo3:50003, IPNodo4:5004 (esto es suponiendo que yo soy en NODO1, por lo que no agrego mi ip aquí)

**--root fs1**: Carpeta local donde este nodo mantiene su copia del sistema de archivos distribuido. Si no existe, se crea al arrancar.

Entonces aparecerá la siguiente interfaz:
![image](https://github.com/user-attachments/assets/651830a1-7e0f-4904-b50c-1a730ae07b7b)


## TOLERANTE A FALLOS:
Si un nodo se desconecta y se vuelve a conectar, este nodo busca cuál de los peers tiene el log más largo y lo aplica a su log.

Si alguno está offline, la conexión a ese peer falla y se omite, pero el resto de peers vivos reciben la operación.

No hay un nodo maestro ni votaciones que detengan el sistema si faltan nodos (por lo que no es como en raft fundamentalmente).

Tras un fallo de red o un reinicio, las operaciones pendientes hacia peers caídos se ignoran temporalmente, pero el bucle de sync posterior garantiza que nada se pierda: cualquier operación que no llegó a un peer será recuperada cuando éste arranque y pida el log más largo.


