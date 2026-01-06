import logging
import asyncio
import os
import re
import datetime
import random
from telethon import TelegramClient, events, Button, errors
import database

# --- الإعدادات ---
API_ID = 25238205
API_HASH = '4ce319340d9a2e6b43ef64a4b053b68f'
BOT_TOKEN = '7950863117:AAE0oDSbEJa_wRwzJoKPL0yyoHQIWfuzbvk'
SESSIONS_DIR = 'sessions'

if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# إعداد السجلات
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
database.init_db()

# عميل البوت
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# إدارة الحالات
user_states = {}
# يتم استرداد العملاء ديناميكياً لتجنب استهلاك الذاكرة

def get_user_session_path(user_id, phone_suffix):
    return os.path.join(SESSIONS_DIR, f'user_{user_id}_{phone_suffix}')

async def get_user_client(user_id, session_name=None):
    try:
        if not session_name:
            # افتراضياً نأخذ أول حساب مربوط
            accounts = database.get_user_accounts(user_id)
            if not accounts: return None
            session_name = accounts[0]
        
        session_path = os.path.join(SESSIONS_DIR, session_name)
        if not os.path.exists(session_path + ".session"):
            return None
            
        client = TelegramClient(
            session_path, 
            API_ID, 
            API_HASH,
            device_model="Samsung Galaxy S22",
            system_version="Android 12",
            app_version="8.9.3"
        )
        await client.connect()
        
        if await client.is_user_authorized():
            return client
    except Exception as e:
        logger.error(f"Error getting user client: {e}")
    return None

# --- القوائم ---

def main_menu_buttons():
    return [
        [Button.inline("➕ ربط حساب جديد", b"login")],
        [Button.inline("📢 إرسال إعلان مباشر", b"broadcast")],
        [Button.inline("⏰ الرسائل المجدولة", b"scheduled_ads"), Button.inline("❌ إلغاء الجدولة", b"cancel_ads")],
        [Button.inline("🔹 الحسابات المربوطة", b"status"), Button.inline("❄️ تسجيل الخروج", b"logout")],
        [Button.url("🌐 لمراسلة المطور", "https://t.me/nu_24")]
    ]

# --- معالجات الأحداث ---

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    database.add_user(event.sender_id)
    await event.respond(
        "💎 **أهلاً بك في بوت إعلانات تيلي المطور**\n\n"
        "❄️ **بإمكانك الآن ربط عدة حسابات وجدولة إعلاناتك بسهولة**\n\n"
        "🔹 لمراسلة المطور: (@nu_24)\n\n"
        "الرجاء اختيار أحد الخيارات التالية:",
        buttons=main_menu_buttons()
    )

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data

    if data == b"login":
        user_states[user_id] = {'state': 'WAITING_PHONE'}
        await event.edit("🧊 **ربط حساب جديد**\n\nأرسل الآن رقم هاتفك مع مفتاح الدولة (مثال: `+9665xxxxxxxx`):")
    
    elif data == b"broadcast":
        accounts = database.get_user_accounts(user_id)
        if not accounts:
            await event.answer("⚠️ يجب ربط حساب واحد على الأقل أولاً!", alert=True)
            return
        
        user_states[user_id] = {'state': 'WAITING_AD'}
        await event.edit("📝 **إعداد الإعلان المباشر**\n\nأرسل الآن نص الإعلان أو الوسائط التي تريد نشرها:")

    elif data == b"scheduled_ads":
        accounts = database.get_user_accounts(user_id)
        if not accounts:
            await event.answer("⚠️ يجب ربط حساب واحد على الأقل أولاً!", alert=True)
            return
        
        user_states[user_id] = {'state': 'WAITING_SCH_AD'}
        await event.edit("  **إعداد الرسائل المجدولة**\n\nأرسل الآن نص الإعلان الذي تريد جدولته:")

    elif data == b"cancel_ads":
        database.deactivate_all_user_tasks(user_id)
        await event.answer("✅ تم إلغاء جميع الرسائل المجدولة بنجاح", alert=True)
        await event.edit("💠 تم إيقاف جميع عمليات النشر المجدولة الخاصة بك.", buttons=main_menu_buttons())

    elif data == b"status":
        accounts = database.get_user_accounts(user_id)
        if accounts:
            msg = "✅ **الحسابات المربوطة:**\n\n"
            for acc in accounts:
                msg += f"👤 `{acc}`\n"
            await event.edit(msg, buttons=main_menu_buttons())
        else:
            await event.edit("❌ **لا توجد حسابات مربوطة حالياً**", buttons=main_menu_buttons())

    elif data == b"logout":
        accounts = database.get_user_accounts(user_id)
        if not accounts:
            await event.answer("⚠️ لا توجد حسابات لتسجيل الخروج منها.", alert=True)
            return
        
        # حذف أول حساب مربوط كمثال للتصدير، أو يمكن عمل قائمة لاحقاً
        acc_to_del = accounts[0]
        session_path = os.path.join(SESSIONS_DIR, acc_to_del)
        if os.path.exists(session_path + ".session"):
            os.remove(session_path + ".session")
        database.delete_account(user_id, acc_to_del)
        await event.answer("✅ تم حذف الحساب بنجاح", alert=True)
        await event.edit("💠 تم تسجيل الخروج من أحد الحسابات.", buttons=main_menu_buttons())

@bot.on(events.NewMessage)
async def message_handler(event):
    if not event.is_private: return
    user_id = event.sender_id
    text = event.raw_text
    state_data = user_states.get(user_id, {})
    state = state_data.get('state')

    if not state: return

    if state == 'WAITING_PHONE':
        phone = re.sub(r'\s+', '', text)
        state_data['phone'] = phone
        session_name = f"user_{user_id}_{phone[-4:]}"
        client = TelegramClient(os.path.join(SESSIONS_DIR, session_name), API_ID, API_HASH)
        await client.connect()
        try:
            send_code = await client.send_code_request(phone)
            state_data.update({
                'client': client,
                'phone_code_hash': send_code.phone_code_hash,
                'session_name': session_name,
                'state': 'WAITING_CODE'
            })
            await event.respond("📩 **وصلك كود التفعيل**\n\nيرجى إرسال الكود هكذا: `1-2-3-4-5`")
        except Exception as e:
            await event.respond(f"❌ خطأ: {e}")
            await client.disconnect()

    elif state == 'WAITING_CODE':
        code = ''.join(filter(str.isdigit, text))
        client = state_data['client']
        phone = state_data['phone']
        phone_code_hash = state_data['phone_code_hash']
        
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            database.add_account(user_id, state_data['session_name'], phone)
            user_states.pop(user_id)
            await event.respond("✅ **تم الربط بنجاح!**", buttons=main_menu_buttons())
        except errors.SessionPasswordNeededError:
            state_data['state'] = 'WAITING_PASSWORD'
            await event.respond("🔐 الحساب محمي بكلمة سر. يرجى إرسالها:")
        except Exception as e:
            await event.respond(f"❌ خطأ في الكود: {e}")

    elif state == 'WAITING_PASSWORD':
        password = text
        client = state_data['client']
        try:
            await client.sign_in(password=password)
            database.add_account(user_id, state_data['session_name'], state_data['phone'])
            user_states.pop(user_id)
            await event.respond("✅ **تم الربط بنجاح!**", buttons=main_menu_buttons())
        except Exception as e:
            await event.respond(f"❌ كلمة سر خاطئة: {e}")

    elif state == 'WAITING_AD':
        ad_msg = event.message
        user_states.pop(user_id)
        accounts = database.get_user_accounts(user_id)
        
        for session in accounts:
            asyncio.create_task(run_broadcast(user_id, session, ad_msg))
        
        await event.respond("🚀 **بدأت الآن عملية النشر من جميع حساباتك...**", buttons=main_menu_buttons())

    elif state == 'WAITING_SCH_AD':
        state_data['ad_text'] = text
        state_data['state'] = 'WAITING_SCH_DAYS'
        await event.respond("📅 **مدة النشر**\n\nكم عدد الأيام التي تريد استمرار النشر فيها؟ (مثال: `7`)")

    elif state == 'WAITING_SCH_DAYS':
        if not text.isdigit():
            await event.respond("❌ يرجى إرسال عدد صحيح.")
            return
        state_data['days'] = int(text)
        state_data['state'] = 'WAITING_SCH_INTERVAL'
        await event.respond("⏱ **الفواصل الزمنية**\n\nأرسل النطاق الزمني بالدقائق (مثال: `10-60`) أي بين 10 و 60 دقيقة:")

    elif state == 'WAITING_SCH_INTERVAL':
        match = re.match(r'(\d+)-(\d+)', text)
        if not match:
            await event.respond("❌ التنسيق غير صحيح. مثال: `10-60`")
            return
        database.add_scheduled_task(
            user_id, 
            state_data['ad_text'], 
            None, 
            state_data['days'], 
            int(match.group(1)), 
            int(match.group(2))
        )
        user_states.pop(user_id)
        await event.respond("✅ **تمت جدولة الإعلان بنجاح!** سوف يبدأ النشر تلقائياً.", buttons=main_menu_buttons())


async def run_broadcast(user_id, session_name, ad_msg):
    client = await get_user_client(user_id, session_name)
    if not client: return
    
    sent = 0
    try:
        async for dialog in client.iter_dialogs():
            if dialog.is_group or (dialog.is_channel and not getattr(dialog.entity, 'broadcast', False)):
                try:
                    await client.send_message(dialog.id, ad_msg)
                    sent += 1
                    await asyncio.sleep(random.randint(5, 10))
                except Exception as e:
                    if "flood" in str(e).lower():
                        await asyncio.sleep(300) # انتظار 5 دقائق عند التقييد
        
        await bot.send_message(user_id, f"📊 **انتهى النشر للحساب:** `{session_name}`\n✅ تــم الإرسال إلى: `{sent}` مجموعة")
    except Exception as e:
        logger.error(f"Broadcast error for {session_name}: {e}")
    finally:
        await client.disconnect()

async def scheduler_loop():
    while True:
        try:
            tasks = database.get_active_tasks()
            for task in tasks:
                t_id, u_id, _, ad_text, _, _, min_int, max_int, start_t, end_t, last_run, _ = task
                
                # التحقق إذا انتهت المدة
                if datetime.datetime.now() > datetime.datetime.fromisoformat(end_t):
                    database.deactivate_task(t_id)
                    await bot.send_message(u_id, "🔔 **تنبيه:** انتهت مدة النشر المجدول للإعلان الخاص بك.")
                    continue

                # التحقق إذا حان موعد النشر القادم
                should_run = False
                if not last_run:
                    should_run = True
                else:
                    last_run_dt = datetime.datetime.fromisoformat(last_run)
                    next_run = last_run_dt + datetime.timedelta(minutes=random.randint(min_int, max_int))
                    if datetime.datetime.now() > next_run:
                        should_run = True
                
                if should_run:
                    accounts = database.get_user_accounts(u_id)
                    if accounts:
                        # النشر من حساب عشوائي أو من الأول
                        asyncio.create_task(run_broadcast(u_id, accounts[0], ad_text))
                        database.update_task_last_run(t_id)
        
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        await asyncio.sleep(60) # التحقق كل دقيقة

async def main():
    print("🚀 البوت يعمل الآن...")
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        bot.loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass

