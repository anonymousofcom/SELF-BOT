import asyncio
from telethon import TelegramClient, events, functions
import random

# 🔐 Your credentials
api_id = 20744090
api_hash = "cf1fcdc320d5986d1c9eb1097afe7381"
OWNER_ID = 6346769377  # Your Telegram user ID

# 🪙 Crypto & Payment details
CRYPTO_ADDRESSES = {
    ".btc": "1DKYFap7MnWJn3SjD4sB4rjUAqsckS9xny",
    ".eth": "0x8d97bd87c9109f0f964b2c230f033209c4b10b67",
    ".ton": "EQD5mxRgCuRNLxKxeOjG6r14iSroLF5FtomPnet-sgP5xNJb",
    ".ltc": "LSjJjh5B9ny1qstGh6eNq7KrgGPMkH5Q19",
    ".sol": "3r31nSc6FFz96Qh2mNuVvyQ6wUi8ygBLrgQpzhEL6gTk",
    ".usdt": "0x8d97bd87c9109f0f964b2c230f033209c4b10b67",
    ".upi": "gareyevzn7@oksbi"
}

# 🧠 Payment confirmation message
REC_MSG = "💸 I received amount, wait I provide you. By the way, thanks for dealing with me 💗"

client = TelegramClient("session", api_id, api_hash)


@client.on(events.NewMessage(outgoing=True, pattern=r"^\.\w+"))
async def command_handler(event):
    if event.sender_id != OWNER_ID:
        return

    cmd = event.raw_text.strip().lower()

    try:
        if cmd in CRYPTO_ADDRESSES:
            await event.reply(f"💰 `{CRYPTO_ADDRESSES[cmd]}`")

        elif cmd == ".rec":
            await event.reply(REC_MSG)

        elif cmd == ".block":
            entity = await client.get_entity(event.chat_id)
            await client(functions.contacts.BlockRequest(id=entity.id))
            await event.reply("⛔ User Blocked.")

        elif cmd == ".unblock":
            entity = await client.get_entity(event.chat_id)
            await client(functions.contacts.UnblockRequest(id=entity.id))
            await event.reply("✅ User Unblocked.")

        elif cmd == ".lock":
            await client.edit_permissions(event.chat_id, send_messages=False)
            await event.reply("🔒 Group Locked.")

        elif cmd == ".clear":
            await client.delete_dialog(event.chat_id)
            await event.respond("🧹 Chat Cleared.")

        elif cmd == ".close":
            await event.reply("☠️ Leaving & deleting group...")
            await asyncio.sleep(2)
            await client.delete_dialog(event.chat_id)

        elif cmd == ".mm":
            me = await client.get_me()
            title = f"MM Group - {random.randint(1000, 9999)}"
            result = await client(functions.messages.CreateChatRequest(
                users=[me],
                title=title
            ))
            group = await client.get_entity(result.chats[0].id)
            link = f"https://t.me/c/{group.id}/1"
            await event.respond(f"✅ MM Group Created:\n📛 {title}\n🔗 [Open Group]({link})")

        elif cmd == ".userinfo":
            reply = await event.get_reply_message()
            user = await client.get_entity(reply.sender_id if reply else event.chat_id)
            msg = f"👤 **User Info:**\n"
            msg += f"• Name: {user.first_name or ''} {user.last_name or ''}\n"
            msg += f"• Username: @{user.username}\n" if user.username else ""
            msg += f"• ID: {user.id}\n"
            await event.reply(msg)

        elif cmd == ".id":
            reply = await event.get_reply_message()
            uid = reply.sender_id if reply else event.chat_id
            await event.reply(f"🆔 ID: `{uid}`")

    except Exception as e:
        await event.reply(f"⚠️ Error: `{e}`")

    await asyncio.sleep(2)
    await event.delete()


async def main():
    print("🔐 Logging in...")
    await client.start()
    print("✅ Bot is running. Type .mm, .btc etc.")
    await client.run_until_disconnected()


client.loop.run_until_complete(main())
