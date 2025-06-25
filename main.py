import asyncio
from telethon import TelegramClient, events, functions
from telethon.sessions import StringSession
import random

# 🔐 Session login
api_id = 20744090
api_hash = "cf1fcdc320d5986d1c9eb1097afe7381"
session_string = "1BVtsOLsBuw7X_lrWczvJMP7Jlstai2nP6aj0iNbvbID0w4iZUjl-pazFfqFki4dwDbmgHk50fvnE5N-rUGfLspmgZJJNv2_xtUcauHlbH0JP7UrdL4QsFGoS-IaWSQ--viyDx0K97DMl-32O4lnNqFIUcPkdV62E64gfdmgD8olEEZ2cHW1u_QRDSVp-9_vR7B-tju60Lkk6j3VKIQguPoT0q6GVQsGxrwSm1tURUV7ZLq5Q8gZDRyvPHZLS0URW-G1zKhA3JScnM394Ry2YYv2dXSLQsb53ccKrTvWJJ3BtmEBRxlGQ0Vyfj-wwBHy9EpaJx6sV3NPZlZgfWgmcSCL1od0vAd4="

OWNER_ID = 6346769377  # Sirf tu hi chalayega commands

CRYPTO_ADDRESSES = {
    ".btc": "1DKYFap7MnWJn3SjD4sB4rjUAqsckS9xny",
    ".eth": "0x8d97bd87c9109f0f964b2c230f033209c4b10b67",
    ".ton": "EQD5mxRgCuRNLxKxeOjG6r14iSroLF5FtomPnet-sgP5xNJb",
    ".ltc": "LSjJjh5B9ny1qstGh6eNq7KrgGPMkH5Q19",
    ".sol": "3r31nSc6FFz96Qh2mNuVvyQ6wUi8ygBLrgQpzhEL6gTk",
    ".usdt": "0x8d97bd87c9109f0f964b2c230f033209c4b10b67"
}

UPI_ID = "gareyevzn7@oksbi"

client = TelegramClient(StringSession(session_string), api_id, api_hash)


@client.on(events.NewMessage(outgoing=True, pattern=r'^\.\w+'))
async def handler(event):
    if event.sender_id != OWNER_ID:
        return

    cmd = event.raw_text.strip().lower()
    try:
        if cmd in CRYPTO_ADDRESSES:
            await event.reply(f" {CRYPTO_ADDRESSES[cmd]}")
        elif cmd == ".rec":
            await event.reply("📥 I received amount by the way thanks for dealing with me 💗")
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
            group_title = f"MM Group - {random.randint(1000, 9999)}"
            result = await client(functions.messages.CreateChatRequest(
                users=[me],
                title=group_title
            ))
            chat_id = result.chats[0].id
            access_hash = result.chats[0].access_hash
            link = f"https://t.me/c/{chat_id}/1"
            await event.reply(f"✅ MM Group Created:\n📛 {group_title}\n🔗 [Open Group]({link})", link_preview=False)
        elif cmd == ".id":
            reply = await event.get_reply_message()
            target = reply.sender_id if reply else event.chat_id
            await event.reply(f"🆔 ID: {target}")
        elif cmd == ".userinfo":
            reply = await event.get_reply_message()
            user = await client.get_entity(reply.sender_id if reply else event.chat_id)
            msg = f"👤 **User Info:**\n"
            msg += f"• Name: {user.first_name or ''} {user.last_name or ''}\n"
            msg += f"• Username: @{user.username}\n" if user.username else ""
            msg += f"• ID: {user.id}\n"
            msg += f"• Bio: {getattr(user, 'bot_info_description', 'Not available')}"
            await event.reply(msg)

    except Exception as e:
        await event.reply(f"⚠️ Error: {e}")

    await asyncio.sleep(2)
    await event.delete()


async def main():
    print("🔐 Logging in...")
    await client.start()
    print("✅ Selfbot is running. Type .mm or other commands.")
    await client.run_until_disconnected()


client.loop.run_until_complete(main())
