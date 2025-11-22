import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import sqlite3
import datetime

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bot tokenini o'rnating
BOT_TOKEN = "7846797998:AAEO1vuFnkHKM1rpk6EETlvc87Qx_JoH47U"

# Ma'lumotlar bazasini yaratish
def init_db():
    conn = sqlite3.connect('tanishuv_bot.db')
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            age INTEGER,
            city TEXT,
            interests TEXT,
            bio TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tanishuv so'rovlari jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1_id) REFERENCES users (user_id),
            FOREIGN KEY (user2_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Foydalanuvchini ro'yxatdan o'tkazish
def register_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect('tanishuv_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    
    conn.commit()
    conn.close()

# Foydalanuvchi ma'lumotlarini yangilash
def update_user_profile(user_id, age=None, city=None, interests=None, bio=None):
    conn = sqlite3.connect('tanishuv_bot.db')
    cursor = conn.cursor()
    
    update_fields = []
    values = []
    
    if age is not None:
        update_fields.append("age = ?")
        values.append(age)
    if city is not None:
        update_fields.append("city = ?")
        values.append(city)
    if interests is not None:
        update_fields.append("interests = ?")
        values.append(interests)
    if bio is not None:
        update_fields.append("bio = ?")
        values.append(bio)
    
    if update_fields:
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
        values.append(user_id)
        cursor.execute(query, values)
    
    conn.commit()
    conn.close()

# Foydalanuvchi ma'lumotlarini olish
def get_user_profile(user_id):
    conn = sqlite3.connect('tanishuv_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user

# Boshqa foydalanuvchilarni topish
def find_users(user_id, limit=10):
    conn = sqlite3.connect('tanishuv_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM users 
        WHERE user_id != ? 
        AND user_id NOT IN (
            SELECT user2_id FROM connections WHERE user1_id = ?
        )
        LIMIT ?
    ''', (user_id, user_id, limit))
    
    users = cursor.fetchall()
    conn.close()
    return users

# Tanishuv so'rovini yuborish
def send_connection_request(user1_id, user2_id):
    conn = sqlite3.connect('tanishuv_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO connections (user1_id, user2_id, status)
        VALUES (?, ?, 'pending')
    ''', (user1_id, user2_id))
    
    conn.commit()
    conn.close()

# Botni ishga tushirish
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""
    Salom {user.first_name}! 👋

    "Men tanishuvlar" botiga xush kelibsiz!
    Bu yerda yangi odamlar bilan tanishishingiz mumkin.

    Quyidagi buyruqlardan foydalaning:
    /profile - Profilingizni ko'rish va sozlash
    /find - Yangi odamlar bilan tanishish
    /help - Yordam olish
    """
    
    await update.message.reply_text(welcome_text)

# Profilni ko'rish va sozlash
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_profile = get_user_profile(user_id)
    
    if user_profile:
        profile_text = f"""
        📋 Sizning profilingiz:

        👤 Ism: {user_profile[2]} {user_profile[3] or ''}
        🆔 Username: @{user_profile[1] or 'Mavjud emas'}
        🎂 Yosh: {user_profile[4] or 'Belgilanmagan'}
        🏙️ Shahar: {user_profile[5] or 'Belgilanmagan'}
        ❗ Qiziqishlar: {user_profile[6] or 'Belgilanmagan'}
        📝 Bio: {user_profile[7] or 'Belgilanmagan'}
        """
        
        keyboard = [
            [InlineKeyboardButton("✏️ Yoshni o'zgartirish", callback_data="edit_age")],
            [InlineKeyboardButton("🏙️ Shaharni o'zgartirish", callback_data="edit_city")],
            [InlineKeyboardButton("❗ Qiziqishlarni o'zgartirish", callback_data="edit_interests")],
            [InlineKeyboardButton("📝 Bio o'zgartirish", callback_data="edit_bio")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(profile_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text("Profil topilmadi. /start ni bosing.")

# Yangi odamlar bilan tanishish
async def find_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = find_users(user_id)
    
    if not users:
        await update.message.reply_text("Hozircha tanishish uchun odamlar topilmadi. Keyinroq urinib ko'ring.")
        return
    
    for user in users:
        profile_text = f"""
        👤 {user[2]} {user[3] or ''}
        🎂 Yosh: {user[4] or 'Noma\'lum'}
        🏙️ Shahar: {user[5] or 'Noma\'lum'}
        ❗ Qiziqishlar: {user[6] or 'Noma\'lum'}
        📝 Bio: {user[7] or 'Noma\'lum'}
        """
        
        keyboard = [[InlineKeyboardButton("👋 Tanishish so'rovini yuborish", callback_data=f"connect_{user[0]}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(profile_text, reply_markup=reply_markup)

# Callback query handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("edit_"):
        field = data.split("_")[1]
        context.user_data['editing_field'] = field
        
        field_names = {
            'age': "yosh",
            'city': "shahar", 
            'interests': "qiziqishlar",
            'bio': "bio"
        }
        
        await query.edit_message_text(f"Iltimos, yangi {field_names[field]}ni yuboring:")
    
    elif data.startswith("connect_"):
        target_user_id = int(data.split("_")[1])
        send_connection_request(user_id, target_user_id)
        await query.edit_message_text("✅ Tanishish so'rovingiz yuborildi!")

# Xabarlarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'editing_field' in context.user_data:
        field = context.user_data['editing_field']
        value = update.message.text
        
        if field == 'age':
            if not value.isdigit():
                await update.message.reply_text("Iltimos, yoshni raqamda kiriting:")
                return
            value = int(value)
        
        update_user_profile(user_id, **{field: value})
        del context.user_data['editing_field']
        await update.message.reply_text("✅ Profilingiz muvaffaqiyatli yangilandi! /profile buyrug'i orqali ko'ring.")

# Yordam
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    🤖 Men tanishuvlar Boti - Yordam

    Quyidagi buyruqlar mavjud:
    
    /start - Botni ishga tushirish
    /profile - Profilingizni ko'rish va sozlash
    /find - Yangi odamlar bilan tanishish
    /help - Yordam
    
    📝 Profilingizni to'liq to'ldirish orqali o'zingizga mos odamlarni topishingiz osonroq bo'ladi.
    
    👥 Bot orqali yangi do'stlar toping va yangi tanishuvlar orttiring!
    """
    
    await update.message.reply_text(help_text)

# Asosiy funksiya
def main():
    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    
    # Bot ilovasini yaratish
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("find", find_people))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Botni ishga tushirish
    application.run_polling()

if __name__ == '__main__':
    main()
