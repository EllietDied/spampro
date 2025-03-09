import asyncio
import os, sys, json, datetime
from pystyle import *
from telethon.sync import TelegramClient
from telethon import events

# Diccionario para llevar el control de respuestas automáticas por usuario (una vez al día)
last_auto_reply = {}  # clave: user id, valor: fecha (datetime.date)

def cls():
    os.system("cls")

def pause():
    os.system("pause>null")
    os.remove("null")

# Funciones para manejar la lista de grupos ignorados
def load_ignored_groups():
    filename = "ignored_groups.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_ignored_groups(ignored_groups):
    with open("ignored_groups.json", "w") as f:
        json.dump(ignored_groups, f)

# Manejadores de comandos
async def ignore_group_handler(event):
    if event.is_group:
        group_id = event.chat_id
        group_name = event.chat.title
        ignored = load_ignored_groups()
        if any(g["id"] == group_id for g in ignored):
            await event.reply(f"El grupo '{group_name}' ya está en la lista de ignorados.")
        else:
            ignored.append({"id": group_id, "name": group_name})
            save_ignored_groups(ignored)
            await event.reply(f"Grupo '{group_name}' ha sido agregado a la lista de ignorados.")

async def list_ignored_handler(event):
    ignored = load_ignored_groups()
    if ignored:
        message = "Grupos ignorados:\n"
        for g in ignored:
            message += f"- {g['name']} (ID: {g['id']})\n"
    else:
        message = "No hay grupos ignorados."
    await event.reply(message)

async def unignore_group_handler(event):
    if event.is_group:
        group_id = event.chat_id
        group_name = event.chat.title
        ignored = load_ignored_groups()
        new_ignored = [g for g in ignored if g["id"] != group_id]
        if len(new_ignored) == len(ignored):
            await event.reply(f"El grupo '{group_name}' no estaba en la lista de ignorados.")
        else:
            save_ignored_groups(new_ignored)
            await event.reply(f"Grupo '{group_name}' ha sido removido de la lista de ignorados.")

# Manejador para respuestas automáticas a mensajes en grupo
# Se responde únicamente si:
#  • El mensaje es en grupo y es una respuesta.
#  • El remitente no es un bot.
#  • El mensaje respondido fue enviado por "mí" (el propietario del bot).
#  • Solo se envía una vez al día por cada usuario.
async def auto_reply_handler(event):
    if not event.is_group or not event.is_reply:
        return
    try:
        sender = await event.get_sender()
        # Ignorar si el remitente es un bot
        if sender.bot:
            return

        replied_message = await event.get_reply_message()
        # Verificar que el mensaje respondido sea uno de "mis mensajes"
        me = await event.client.get_me()
        if replied_message.sender_id != me.id:
            return

        # Comprobar si ya se respondió a este usuario hoy
        current_date = datetime.datetime.now().date()
        if sender.id in last_auto_reply and last_auto_reply[sender.id] == current_date:
            return

        # Registrar que se respondió hoy a este usuario
        last_auto_reply[sender.id] = current_date

        saludo = "¡Hola! Te reenvío el mensaje. ¿Estás interesado?"
        # Enviar mensaje privado y reenviar el mensaje respondido
        await event.client.send_message(sender.id, saludo)
        await event.client.forward_messages(sender.id, replied_message)
        Write.Print(f"Respondido automáticamente a {sender.id}", Colors.blue, interval=0)
    except Exception as e:
        Write.Print(f"Error en auto_reply_handler: {str(e)}", Colors.red, interval=0)

# Función de spam modificada para excluir grupos ignorados
async def send_messages_to_groups(client):
    while True:
        ignored = load_ignored_groups()
        ignored_ids = [g["id"] for g in ignored]
        group_ids = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group and dialog.name != 'mis spams' and dialog.id not in ignored_ids:
                group_ids.append(dialog.id)
        async for dialog in client.iter_dialogs():
            if dialog.is_group and dialog.name == 'mis spams':
                async for message in client.iter_messages(dialog, limit=10):
                    if message.text:
                        for group_id in group_ids:
                            try:
                                await client.forward_messages(group_id, messages=[message])
                                Write.Print(f"\nMensaje reenviado a {group_id}", Colors.green, interval=0)
                            except Exception as e:
                                Write.Print(f"\nFallo al reenviar a {group_id}: {str(e)}", Colors.red, interval=0)
        await asyncio.sleep(930)

async def keep_spamming(client):
    while True:
        try:
            if not client.is_connected():
                Write.Print(f"Conectando {client.session_name}...", Colors.yellow, interval=0)
                await client.connect()
            await send_messages_to_groups(client)
        except Exception as e:
            Write.Print(f"\nError en {client.session_name}: {str(e)}", Colors.red, interval=0)
            Write.Print(f"Reintentando conexión en 10 segundos...", Colors.yellow, interval=0)
            try:
                await client.disconnect()
            except Exception as disconn_e:
                Write.Print(f"Error al desconectar: {str(disconn_e)}", Colors.red, interval=0)
            await asyncio.sleep(10)

async def main():
    cls()
    accounts = []
    accounts_file = "accounts.json"
    if os.path.exists(accounts_file):
        with open(accounts_file, "r") as f:
            try:
                accounts = json.load(f)
            except json.JSONDecodeError:
                accounts = []
    else:
        accounts = []
    
    if accounts:
        Write.Print("Cuentas vinculadas previamente:", Colors.dark_green, interval=0)
        for acc in accounts:
            Write.Print(f" - {acc['session']}", Colors.dark_green, interval=0)
        # Se espera 60 segundos para detectar si se quiere vincular una cuenta nueva
        try:
            respuesta = await asyncio.wait_for(
                asyncio.to_thread(Write.Input, "\n¿Desea vincular otra cuenta? (s/n): ", Colors.dark_green, interval=0),
                timeout=60
            )
        except asyncio.TimeoutError:
            respuesta = "n"
    else:
        Write.Print("No se han vinculado cuentas. Por favor, ingrese una nueva cuenta.", Colors.dark_green, interval=0)
        respuesta = "s"
    
    if respuesta.lower() == 's':
        session_name = Write.Input("Ingrese nombre de sesión (ej: account1): ", Colors.dark_green, interval=0)
        api_id = Write.Input("Ingrese su API ID: ", Colors.dark_green, interval=0)
        api_hash = Write.Input("Ingrese su API Hash: ", Colors.dark_green, interval=0)
        new_account = {"session": session_name, "api_id": api_id, "api_hash": api_hash}
        accounts.append(new_account)
        with open(accounts_file, "w") as f:
            json.dump(accounts, f)
    
    # Crear e iniciar clientes para cada cuenta vinculada
    clients = []
    for acc in accounts:
        try:
            client = TelegramClient(acc["session"], int(acc["api_id"]), acc["api_hash"])
            await client.start()
            # Registrar manejadores de comandos para ignorar, listar y quitar ignoración de grupos
            client.add_event_handler(ignore_group_handler, events.NewMessage(pattern='/ignorargrupo'))
            client.add_event_handler(list_ignored_handler, events.NewMessage(pattern='/verignorados'))
            client.add_event_handler(unignore_group_handler, events.NewMessage(pattern='/quitarignorargrupo'))
            # Registrar manejador para respuestas automáticas a mensajes en grupo
            client.add_event_handler(auto_reply_handler, events.NewMessage(func=lambda e: e.is_reply and e.is_group))
            
            Write.Print(f"Cuenta {acc['session']} iniciada.", Colors.green, interval=0)
            clients.append(client)
        except Exception as e:
            Write.Print(f"Error iniciando {acc['session']}: {str(e)}", Colors.red, interval=0)
    
    if not clients:
        Write.Print("No hay cuentas disponibles para spam. Saliendo...", Colors.red, interval=0)
        sys.exit()
    
    # Ejecutar la función de spam con reconexión automática para cada cliente en paralelo
    tasks = [asyncio.create_task(keep_spamming(client)) for client in clients]
    await asyncio.gather(*tasks)
    
    for client in clients:
        await client.disconnect()

asyncio.run(main())
