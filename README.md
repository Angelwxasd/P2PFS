# Instrucciones para usar el programa

#### Actualmente realizamos las siguientes operaciones:
1. Crear Directorios 
  mkdir
2. Escribir Archivos
  write
3. Transferir Archivos Binarios (Mejorar, editar para que permita transferir archivos pero de un nodo en específico)
   transfer
4. Eliminar Archivos o Directorios
  delete
5. Listar contenido
  list
6. Mostrar historial de operaciones
  log
7. Mostrar Peers
  peers
8. Esperar indefinidamente (Cómo funciona este comando?)

Cada operación se registra como un diccionario con id, cmd, y campos adicionales según el tipo.


Para ejecutar el programa se propone la siguiente sintaxis:
  python gui_main.py --id 1 --port 5000 \
  --peers 127.0.0.1:5001,127.0.0.1:5002 --root fs1
