# MultiUser Adbot Manager with Auto Name/Bio Update
# Requirements: pip install telethon colorama

import os, json, asyncio, re
from telethon import TelegramClient, events, Button, functions
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from colorama import Fore, Style

# ---------------- CONFIG ----------------
BOT_TOKEN = "8423054396:AAHL03-4qf5XnBBmWnBHlJneOAU1-NtGacI"
ADMIN_ID = 8334561878
DEFAULT_INTERVAL = 60
USERDATA_DIR = "userdata"
os.makedirs(USERDATA_DIR, exist_ok=True)

# ---------------- HELPERS ----------------
def userfile(uid): return os.path.join(USERDATA_DIR, f"user_{uid}.json")
def load_userdata(uid): return json.load(open(userfile(uid))) if os.path.exists(userfile(uid)) else {}
def save_userdata(uid, data): json.dump(data, open(userfile(uid),"w"), indent=2)

# ---------------- STATE ----------------
user_context = {}    # current login step
running_tasks = {}   # forward loops
counters = {}        # counters per user
sent_msgs = {}       # status messages per user

# ---------------- MANAGER BOT ----------------
manager = TelegramClient("manager_session", 12345, "dummy").start(bot_token=BOT_TOKEN)
print(f"{Fore.GREEN}[+] Manager bot started. Listening for /start...{Style.RESET_ALL}")

# ---------------- HELPERS ----------------
def main_menu():
    return [
        [Button.inline("🔐 Login Account", b"login"),
         Button.inline("❌ Logout", b"logout")],
        [Button.inline("📤 Forward Message", b"forward_msg"),
         Button.inline("➕ Add Market Link", b"add_market")],
        [Button.inline("📋 List Market Links", b"list_markets"),
         Button.inline("➖ Remove Market Link", b"remove_market")],
        [Button.inline("🧾 Set Interval", b"set_interval")],
        [Button.inline("▶️ Run Bot", b"run_bot"),
         Button.inline("⛔ Stop Bot", b"stop_bot")],
    ]

async def update_name_bio(session_name, api_id, api_hash, old_name="User"):
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    try:
        await client(functions.account.UpdateProfileRequest(
            first_name=f"{old_name} - via @nishuadbot",
            about="This Account Run By @nishuadbot"
        ))
    finally:
        await client.disconnect()

# ---------------- START ----------------
@manager.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    uid = event.sender_id
    ud = load_userdata(uid)
    txt = "🤖 **AdBot Manager**\n\n"
    if ud.get("logged_in"):
        txt += f"✅ Logged in as `{ud.get('phone')}`\n\n"
    else:
        txt += "🔐 Not logged in yet.\n\n"
    txt += "Choose option:"
    await event.respond(txt, buttons=main_menu())

# ---------------- RESET COUNTER ----------------
@manager.on(events.NewMessage(pattern="/reset_counter"))
async def reset_handler(event):
    uid = event.sender_id
    if uid not in counters:
        await event.respond("⚠️ No counters to reset.")
        return
    for m in counters[uid]:
        counters[uid][m] = 0
        if uid in sent_msgs and m in sent_msgs[uid]:
            try:
                await sent_msgs[uid][m].edit(f"📤 {m}\nCount: 0")
            except: pass
    await event.respond("✅ Counters have been reset!")

# ---------------- STATS ----------------
@manager.on(events.NewMessage(pattern="/stats"))
async def stats_handler(event):
    uid = event.sender_id
    if uid not in counters or not counters[uid]:
        await event.respond("⚠️ No active counters yet.")
        return
    txt = "📊 **Forward Stats**\n\n"
    for m, count in counters[uid].items():
        txt += f"➡️ {m} → {count} times\n"
    await event.respond(txt)

# ---------------- CALLBACKS ----------------
@manager.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "login":
        user_context[uid] = {"action": "login", "step": "api_id"}
        await event.edit("🔑 Send your **API ID**:")
        return

    if data == "logout":
        ud = load_userdata(uid)
        sess = ud.get("session_name")
        if sess:
            try: os.remove(f"{sess}.session")
            except: pass
        ud["logged_in"] = False
        save_userdata(uid, ud)
        await event.edit("❌ Logged out.", buttons=main_menu())
        return

    if data == "forward_msg":
        user_context[uid] = {"action": "source", "step": "url"}
        await event.edit("📤 Send source message URL:")
        return

    if data == "add_market":
        user_context[uid] = {"action": "market", "step": "url"}
        await event.edit("➕ Send public group/channel link:")
        return

    if data == "list_markets":
        mk = load_userdata(uid).get("markets", [])
        msg = "📋 **Market Links:**\n" + ("\n".join(mk) if mk else "None yet")
        await event.edit(msg, buttons=main_menu())
        return

    if data == "remove_market":
        mk = load_userdata(uid).get("markets", [])
        if not mk:
            await event.edit("⚠️ No markets added yet.", buttons=main_menu()); return
        btns = [[Button.inline(m, f"del_{i}".encode())] for i, m in enumerate(mk)]
        btns.append([Button.inline("⬅️ Back", b"back")])
        await event.edit("Select a market to remove:", buttons=btns)
        return

    if data.startswith("del_"):
        idx = int(data.split("_")[1])
        ud = load_userdata(uid)
        mk = ud.get("markets", [])
        if idx < len(mk):
            removed = mk.pop(idx)
            ud["markets"] = mk; save_userdata(uid, ud)
            await event.edit(f"✅ Removed: {removed}", buttons=main_menu())
        return

    if data == "back":
        await event.edit("Main Menu:", buttons=main_menu())
        return

    if data == "set_interval":
        user_context[uid] = {"action": "interval", "step": "num"}
        await event.edit("⏱️ Send interval seconds (5-3600):")
        return

    if data == "run_bot":
        ud = load_userdata(uid)
        if not ud.get("logged_in"):
            await event.edit("❌ Please login first.", buttons=main_menu()); return
        if not ud.get("source_message") or not ud.get("markets"):
            await event.edit("❌ Set source + markets first.", buttons=main_menu()); return
        if uid in running_tasks and not running_tasks[uid].done():
            await event.edit("⚠️ Already running.", buttons=main_menu()); return
        running_tasks[uid] = asyncio.create_task(forward_loop(uid))
        await event.edit("▶️ Forwarder started.", buttons=main_menu())
        return

    if data == "stop_bot":
        t = running_tasks.get(uid)
        if t and not t.done(): t.cancel()
        await event.edit("⛔ Forwarder stopped.", buttons=main_menu())
        return

# ---------------- TEXT HANDLER ----------------
@manager.on(events.NewMessage)
async def text_handler(event):
    uid = event.sender_id
    ctx = user_context.get(uid)
    text = (event.text or "").strip()
    ud = load_userdata(uid)
    if not ctx: return

    # ---------------- LOGIN FLOW ----------------
    if ctx["action"] == "login":
        if ctx["step"] == "api_id":
            if text.isdigit():
                ctx["api_id"] = int(text)
                ctx["step"] = "api_hash"
                await event.respond("🔑 Send your **API Hash**:")
            else:
                await event.respond("❌ Invalid API ID. Must be a number.\n🔁 Try again. Send API ID:")
            return

        if ctx["step"] == "api_hash":
            ctx["api_hash"] = text
            try:
                test_client = TelegramClient("test", ctx["api_id"], ctx["api_hash"])
                await test_client.connect()
                await test_client.disconnect()
                ctx["step"] = "phone"
                await event.respond("📱 Send your **phone number** (+countrycode):")
            except Exception:
                user_context[uid] = {"action": "login", "step": "api_id"}
                await event.respond("❌ Invalid API ID/Hash.\n🔁 Please re-enter your **API ID**:")
            return

        if ctx["step"] == "phone":
            ctx["phone"] = text
            client = TelegramClient(f"session_{uid}", ctx["api_id"], ctx["api_hash"])
            await client.connect()
            try:
                sent = await client.send_code_request(text)
                ctx["phone_code_hash"] = sent.phone_code_hash
                ctx["step"] = "otp"
                await client.disconnect()
                await event.respond("✳️ Enter the OTP you received:")
            except PhoneNumberInvalidError:
                await event.respond("❌ Invalid number.")
            return

        if ctx["step"] == "otp":
            phone = ctx["phone"]; otp = text; code_hash = ctx["phone_code_hash"]
            session_name = f"session_{uid}"
            client = TelegramClient(session_name, ctx["api_id"], ctx["api_hash"])
            try:
                await client.connect()
                await client.sign_in(phone=phone, code=otp, phone_code_hash=code_hash)
                await client.disconnect()
                ud["logged_in"] = True
                ud["phone"] = phone
                ud["session_name"] = session_name
                ud["api_id"] = ctx["api_id"]
                ud["api_hash"] = ctx["api_hash"]
                save_userdata(uid, ud)
                user_context.pop(uid, None)
                
                old_name = ud.get("old_name", "User")
                await update_name_bio(session_name, ctx["api_id"], ctx["api_hash"], old_name)
                
                await event.respond("✅ Login successful! Name & bio updated.", buttons=main_menu())
            except SessionPasswordNeededError:
                ctx["step"] = "2fa"
                await event.respond("🔒 Send your 2FA password:")
            except PhoneCodeInvalidError:
                await event.respond("❌ Invalid OTP. Try again.")
            return

        if ctx["step"] == "2fa":
            pw = text; phone = ctx["phone"]; session_name = f"session_{uid}"
            client = TelegramClient(session_name, ctx["api_id"], ctx["api_hash"])
            try:
                await client.connect()
                await client.sign_in(password=pw)
                await client.disconnect()
                ud["logged_in"] = True
                ud["phone"] = phone
                ud["session_name"] = session_name
                ud["api_id"] = ctx["api_id"]
                ud["api_hash"] = ctx["api_hash"]
                save_userdata(uid, ud)
                user_context.pop(uid, None)

                old_name = ud.get("old_name", "User")
                await update_name_bio(session_name, ctx["api_id"], ctx["api_hash"], old_name)

                await event.respond("✅ Login successful with 2FA! Name & bio updated.", buttons=main_menu())
            except Exception as e:
                await event.respond(f"❌ 2FA failed: {e}")
            return

    # ---------------- SOURCE / MARKET / INTERVAL ----------------
    if ctx["action"] == "source" and ctx["step"] == "url":
        ud["source_message"] = text; save_userdata(uid, ud)
        user_context.pop(uid, None)
        await event.respond(f"✅ Source saved: {text}", buttons=main_menu())
    if ctx["action"] == "market" and ctx["step"] == "url":
        mk = ud.get("markets", []); mk.append(text)
        ud["markets"] = mk; save_userdata(uid, ud)
        user_context.pop(uid, None)
        await event.respond(f"✅ Market added: {text}", buttons=main_menu())
    if ctx["action"] == "interval" and ctx["step"] == "num":
        if text.isdigit() and 5 <= int(text) <= 3600:
            ud["interval"] = int(text); save_userdata(uid, ud)
            user_context.pop(uid, None)
            await event.respond(f"✅ Interval set to {text}s", buttons=main_menu())
        else:
            await event.respond("❌ Invalid number. Use 5–3600.")

# ---------------- FORWARDING ----------------
async def forward_loop(uid):
    ud = load_userdata(uid)
    client = TelegramClient(ud["session_name"], ud["api_id"], ud["api_hash"])
    await client.connect()

    src = ud["source_message"]; mk = ud["markets"]
    interval = ud.get("interval", DEFAULT_INTERVAL)

    parts = src.split("/")
    src_peer = parts[3]; msg_id = int(parts[-1])

    counters[uid] = {m: 0 for m in mk}
    sent_msgs[uid] = {}

    while True:
        for m in mk:
            try:
                target = m.replace("https://t.me/", "").replace("@", "")
                thread_id = None
                if "/" in target:
                    if re.search(r"\d+$", target):
                        base, tid = target.split("/")
                        target = base; thread_id = int(tid)

                await client(functions.messages.ForwardMessagesRequest(
                    from_peer=src_peer,
                    id=[msg_id],
                    to_peer=target,
                    top_msg_id=thread_id
                ))

                counters[uid][m] += 1
                if m not in sent_msgs[uid]:
                    sent_msgs[uid][m] = await manager.send_message(uid, f"📤 {m}\nCount: {counters[uid][m]}")
                else:
                    await sent_msgs[uid][m].edit(f"📤 {m}\nCount: {counters[uid][m]}")
            except Exception as e:
                if m not in sent_msgs[uid]:
                    sent_msgs[uid] = sent_msgs.get(uid, {})
                    sent_msgs[uid][m] = await manager.send_message(uid, f"❌ {m}\nError: {e}")
                else:
                    await sent_msgs[uid][m].edit(f"❌ {m}\nError: {e}")
            await asyncio.sleep(1)
        await asyncio.sleep(interval)

# ---------------- RUN ----------------
print(f"{Fore.CYAN}Adbot Manager is running. Use your bot to /start.{Style.RESET_ALL}")
manager.run_until_disconnected()
