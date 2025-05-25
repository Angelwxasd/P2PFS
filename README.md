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

#### Estructura para correr el programa

Para ejecutar el programa se propone la siguiente sintaxis:
  python gui_main.py --id 1 --port 5000 \
  --peers 127.0.0.1:5001,127.0.0.1:5002 --root fs1

**--id X**: Identificador numérico único para este nodo (debe diferir de los demás).

**--port 5000**: Puerto TCP en el que este nodo escucha conexiones entrantes de peers.

**--peers 127.0.0.1:5001,127.0.0.1:5002**: No incluye al propio nodo. Aquí le dices con quién debe sincronizar y reenviar operaciones.

**--root fs1**: Carpeta local donde este nodo mantiene su copia del sistema de archivos distribuido. Si no existe, se crea al arrancar.

Entonces aparecerá la siguiente interfaz:
![image](https://github.com/user-attachments/assets/651830a1-7e0f-4904-b50c-1a730ae07b7b)


## TOLERANTE A FALLOS:
Si un nodo se desconecta y se vuelve a conectar, este nodo busca cuál de los peers tiene el log más largo y lo aplica a su log.


  
