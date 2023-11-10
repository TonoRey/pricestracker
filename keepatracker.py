import datetime
import os.path
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from twilio.rest import Client

# Define los alcances necesarios para leer correos electrónicos de Gmail.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def gmail_authenticate():
    """
    Autentica al usuario en Gmail. Usa 'token.json' para tokens de acceso y
    'credentials.json' para la información del cliente. Genera nuevos tokens si es necesario.
    """
    creds = None
    # Verifica si ya existe un archivo de token y lo carga
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('/Volumes/ReyCasHD1/TonRayNavy/ProyectosPython/Keepa/token.json', SCOPES)
    # Si no hay credenciales válidas, inicia el flujo de autenticación
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('/Volumes/ReyCasHD1/TonRayNavy/ProyectosPython/Keepa/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guarda las credenciales para la próxima ejecución
        with open('/Volumes/ReyCasHD1/TonRayNavy/ProyectosPython/Keepa/token.json', 'w') as token:
            token.write(creds.to_json())
    # Retorna un servicio Gmail autorizado con las credenciales
    return build('gmail', 'v1', credentials=creds)

def search_messages(service, query):
    """
    Busca mensajes en la cuenta de Gmail del usuario usando la consulta proporcionada.
    """
    # Realiza la búsqueda y retorna los mensajes encontrados
    return service.users().messages().list(userId='me', q=query).execute().get('messages', [])

def get_message_subject(service, message_id):
    """
    Obtiene el asunto de un mensaje de Gmail usando su ID.
    """
    # Obtiene los metadatos del mensaje, específicamente el encabezado del asunto
    message = service.users().messages().get(userId='me', id=message_id, format='metadata', metadataHeaders=['Subject']).execute()
    headers = message.get('payload', {}).get('headers', [])
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'Sin Asunto')
    return subject

def send_whatsapp_message(client, body, from_whatsapp_number, to_whatsapp_number):
    """
    Envía un mensaje de WhatsApp usando el cliente de Twilio.
    """
    return client.messages.create(
        body=body,
        from_='whatsapp:' + from_whatsapp_number,
        to='whatsapp:' + to_whatsapp_number
    ).sid

def load_twilio_config():
    """
    Carga la configuración de Twilio desde un archivo JSON.
    """
    with open('/Volumes/ReyCasHD1/TonRayNavy/ProyectosPython/Keepa/twilio_conf.json', 'r') as f:
        return json.load(f)

def main():
    """
    Función principal que ejecuta el flujo de autenticación de Gmail,
    busca mensajes y envía notificaciones de WhatsApp.
    """
    # Autentica y obtiene el servicio de Gmail
    service = gmail_authenticate()
    # Formatea la fecha de hoy para la búsqueda en Gmail
    today = datetime.date.today().strftime("%Y/%m/%d")
    # Define la consulta de búsqueda de mensajes
    query = f'from:pricealert@keepa.com after:{today}'
    # Busca los mensajes en Gmail
    messages = search_messages(service, query)

    if not messages:
        print("No se encontraron mensajes de Keepa.")
        return

    # Carga la configuración de Twilio desde el archivo JSON
    twilio_config = load_twilio_config()
    # Crea un cliente de Twilio con las credenciales cargadas
    client = Client(twilio_config['twilio']['account_sid'], twilio_config['twilio']['auth_token'])
    # Asigna números de WhatsApp de la configuración
    from_whatsapp_number = twilio_config['twilio']['from_whatsapp_number']
    to_whatsapp_number = twilio_config['twilio']['to_whatsapp_number']
    
    # Para cada mensaje encontrado, obtiene el asunto y envía una notificación de WhatsApp
    for msg in messages:
        subject = get_message_subject(service, msg['id'])
        whatsapp_msg_sid = send_whatsapp_message(
            client,
            f"Has recibido una oferta en keepa del producto: {subject}",
            from_whatsapp_number,
            to_whatsapp_number
        )
        print(f"Mensaje de WhatsApp enviado: {whatsapp_msg_sid} para el correo con ID: {msg['id']} y asunto: {subject}")

if __name__ == '__main__':
    main()
