import os
import sqlite3
import hashlib
import uuid

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# ==================================================
# Configuration
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

DATABASE = "fileguard.db"
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ==================================================
# Database
# ==================================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_database():

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


def add_file(user_id, filename, sha256):

    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO files
        (user_id, filename, sha256)
        VALUES (?, ?, ?)
        """,
        (user_id, filename, sha256)
    )

    db.commit()

    file_id = cursor.lastrowid

    db.close()

    return file_id


def get_user_files(user_id):

    db = get_db()

    files = db.execute(
        """
        SELECT *
        FROM files
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    db.close()

    return files


def get_file(file_id, user_id):

    db = get_db()

    file = db.execute(
        """
        SELECT *
        FROM files
        WHERE id = ?
        AND user_id = ?
        """,
        (file_id, user_id)
    ).fetchone()

    db.close()

    return file


def delete_file(file_id, user_id):

    db = get_db()

    db.execute(
        """
        DELETE FROM files
        WHERE id = ?
        AND user_id = ?
        """,
        (file_id, user_id)
    )

    db.commit()
    db.close()


# ==================================================
# SHA-256
# ==================================================

def calculate_sha256(path):

    sha256 = hashlib.sha256()

    with open(path, "rb") as file:

        while True:

            chunk = file.read(8192)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# ==================================================
# Keyboards
# ==================================================

def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📥 Register File",
                callback_data="register"
            )
        ],

        [
            InlineKeyboardButton(
                "🔍 Verify File",
                callback_data="verify"
            )
        ],

        [
            InlineKeyboardButton(
                "📁 My Files",
                callback_data="files"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑 Delete File",
                callback_data="delete"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)


def back_button():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back to Menu",
                callback_data="menu"
            )
        ]
    ])


# ==================================================
# Main Menu
# ==================================================

async def show_menu(update, context):

    context.user_data.clear()

    text = (
        "🔐 *FileGuard*\n\n"
        "File Integrity Monitoring using SHA-256.\n\n"
        "Choose an action:"
    )

    if update.callback_query:

        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    else:

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )


# ==================================================
# Start
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await show_menu(update, context)


# ==================================================
# Register
# ==================================================

async def register(update, context):

    context.user_data.clear()

    context.user_data["mode"] = "register"

    text = (
        "📥 *Register File*\n\n"
        "Send me the file you want to register.\n\n"
        "I will calculate its SHA-256 fingerprint "
        "and save it for future verification."
    )

    await update.callback_query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_button()
    )


# ==================================================
# Files List
# ==================================================

async def show_files(update, context):

    user_id = update.effective_user.id

    files = get_user_files(user_id)

    if not files:

        text = (
            "📁 *My Files*\n\n"
            "You don't have any registered files yet."
        )

        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=back_button()
        )

        return

    keyboard = []

    for file in files:

        filename = file["filename"]

        if len(filename) > 25:
            filename = filename[:22] + "..."

        keyboard.append([
            InlineKeyboardButton(
                f"📄 {filename}",
                callback_data=f"info:{file['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back to Menu",
            callback_data="menu"
        )
    ])

    text = (
        "📁 *My Files*\n\n"
        f"Registered files: {len(files)}\n\n"
        "Select a file to view its SHA-256 fingerprint."
    )

    await update.callback_query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================================================
# Verify List
# ==================================================

async def show_verify_files(update, context):

    user_id = update.effective_user.id

    files = get_user_files(user_id)

    if not files:

        await update.callback_query.edit_message_text(
            "🔍 *Verify File*\n\n"
            "❌ You don't have any registered files.\n\n"
            "Register a file first.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )

        return

    keyboard = []

    for file in files:

        filename = file["filename"]

        if len(filename) > 25:
            filename = filename[:22] + "..."

        keyboard.append([
            InlineKeyboardButton(
                f"🔍 {filename}",
                callback_data=f"verify_select:{file['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back to Menu",
            callback_data="menu"
        )
    ])

    await update.callback_query.edit_message_text(
        "🔍 *Verify File*\n\n"
        "Select the original file:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================================================
# Delete List
# ==================================================

async def show_delete_files(update, context):

    user_id = update.effective_user.id

    files = get_user_files(user_id)

    if not files:

        await update.callback_query.edit_message_text(
            "🗑 *Delete File*\n\n"
            "You don't have any registered files.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )

        return

    keyboard = []

    for file in files:

        filename = file["filename"]

        if len(filename) > 25:
            filename = filename[:22] + "..."

        keyboard.append([
            InlineKeyboardButton(
                f"🗑 {filename}",
                callback_data=f"delete_select:{file['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back to Menu",
            callback_data="menu"
        )
    ])

    await update.callback_query.edit_message_text(
        "🗑 *Delete File*\n\n"
        "Select the file you want to delete:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================================================
# Button Handler
# ==================================================

async def button_handler(update, context):

    query = update.callback_query

    await query.answer()

    data = query.data

    user_id = query.from_user.id


    # ----------------------------
    # Back to Menu
    # ----------------------------

    if data == "menu":

        await show_menu(update, context)

        return


    # ----------------------------
    # Register
    # ----------------------------

    if data == "register":

        await register(update, context)

        return


    # ----------------------------
    # Verify
    # ----------------------------

    if data == "verify":

        context.user_data.clear()

        await show_verify_files(update, context)

        return


    # ----------------------------
    # Files
    # ----------------------------

    if data == "files":

        await show_files(update, context)

        return


    # ----------------------------
    # Delete
    # ----------------------------

    if data == "delete":

        await show_delete_files(update, context)

        return


    # ----------------------------
    # File Information
    # ----------------------------

    if data.startswith("info:"):

        file_id = int(data.split(":")[1])

        file = get_file(file_id, user_id)

        if not file:

            await query.edit_message_text(
                "❌ File not found.",
                reply_markup=back_button()
            )

            return

        text = (
            "📄 *File Information*\n\n"
            f"Filename:\n`{file['filename']}`\n\n"
            "🔐 SHA-256:\n"
            f"`{file['sha256']}`\n\n"
            f"📅 Registered:\n{file['created_at']}"
        )

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=back_button()
        )

        return


    # ----------------------------
    # Select file for verification
    # ----------------------------

    if data.startswith("verify_select:"):

        file_id = int(data.split(":")[1])

        file = get_file(file_id, user_id)

        if not file:

            await query.edit_message_text(
                "❌ File not found.",
                reply_markup=back_button()
            )

            return

        context.user_data.clear()

        context.user_data["mode"] = "verify"

        context.user_data["selected_file_id"] = file_id

        text = (
            "🔍 *Verification Ready*\n\n"
            f"Original file:\n`{file['filename']}`\n\n"
            "Now send me the file you want to verify.\n\n"
            "I will compare its SHA-256 fingerprint "
            "with the original."
        )

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=back_button()
        )

        return


    # ----------------------------
    # Delete confirmation
    # ----------------------------

    if data.startswith("delete_select:"):

        file_id = int(data.split(":")[1])

        file = get_file(file_id, user_id)

        if not file:

            await query.edit_message_text(
                "❌ File not found.",
                reply_markup=back_button()
            )

            return

        keyboard = [

            [
                InlineKeyboardButton(
                    "✅ Yes, Delete",
                    callback_data=f"delete_confirm:{file_id}"
                )
            ],

            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="delete"
                )
            ]

        ]

        await query.edit_message_text(
            f"⚠️ *Delete File?*\n\n"
            f"`{file['filename']}`\n\n"
            "This will permanently delete its saved "
            "SHA-256 fingerprint.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return


    # ----------------------------
    # Delete confirmed
    # ----------------------------

    if data.startswith("delete_confirm:"):

        file_id = int(data.split(":")[1])

        file = get_file(file_id, user_id)

        if not file:

            await query.edit_message_text(
                "❌ File not found.",
                reply_markup=back_button()
            )

            return

        delete_file(file_id, user_id)

        await query.edit_message_text(
            "✅ *File Deleted*\n\n"
            f"`{file['filename']}` has been removed successfully.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )

        return


# ==================================================
# File Handler
# ==================================================

async def handle_file(update: Update, context):

    mode = context.user_data.get("mode")

    if mode not in ["register", "verify"]:

        await update.message.reply_text(
            "Please choose an action from the menu first.",
            reply_markup=main_menu()
        )

        return

    document = update.message.document

    filename = document.file_name or "unknown_file"

    safe_filename = os.path.basename(filename)

    unique_filename = (
        str(uuid.uuid4()) + "_" + safe_filename
    )

    file_path = os.path.join(
        DOWNLOAD_DIR,
        unique_filename
    )

    try:

        telegram_file = await document.get_file()

        await telegram_file.download_to_drive(
            file_path
        )

        current_hash = calculate_sha256(
            file_path
        )

        user_id = update.effective_user.id


        # ==========================================
        # REGISTER
        # ==========================================

        if mode == "register":

            file_id = add_file(
                user_id,
                safe_filename,
                current_hash
            )

            text = (
                "✅ *File Registered Successfully!*\n\n"
                f"📄 Filename:\n`{safe_filename}`\n\n"
                f"🆔 File ID: `{file_id}`\n\n"
                "🔐 SHA-256:\n"
                f"`{current_hash}`"
            )

            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=main_menu()
            )


        # ==========================================
        # VERIFY
        # ==========================================

        elif mode == "verify":

            selected_file_id = (
                context.user_data.get(
                    "selected_file_id"
                )
            )

            if not selected_file_id:

                await update.message.reply_text(
                    "❌ No original file selected.",
                    reply_markup=main_menu()
                )

                return

            original = get_file(
                selected_file_id,
                user_id
            )

            if not original:

                await update.message.reply_text(
                    "❌ Original file not found.",
                    reply_markup=main_menu()
                )

                return

            original_hash = original["sha256"]


            # --------------------------------------
            # MATCH
            # --------------------------------------

            if current_hash == original_hash:

                text = (
                    "🟢 *INTEGRITY CHECK PASSED*\n\n"
                    f"📄 File:\n`{safe_filename}`\n\n"
                    "The file matches the original "
                    "fingerprint.\n\n"
                    "🔐 SHA-256:\n"
                    f"`{current_hash}`"
                )

            # --------------------------------------
            # DIFFERENT
            # --------------------------------------

            else:

                text = (
                    "🔴 *INTEGRITY CHECK FAILED*\n\n"
                    f"📄 File:\n`{safe_filename}`\n\n"
                    "⚠️ The file does NOT match the "
                    "original fingerprint.\n\n"
                    "🔐 Original SHA-256:\n"
                    f"`{original_hash}`\n\n"
                    "🔐 Current SHA-256:\n"
                    f"`{current_hash}`"
                )

            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=main_menu()
            )


    except Exception as error:

        print("ERROR:", error)

        await update.message.reply_text(
            "❌ An error occurred while processing the file.",
            reply_markup=main_menu()
        )


    finally:

        if os.path.exists(file_path):

            os.remove(file_path)

        context.user_data.clear()


# ==================================================
# Main
# ==================================================

def main():

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN is not set!"
        )

        print(
            "Run: export BOT_TOKEN='YOUR_TOKEN'"
        )

        return


    init_database()


    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )


    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_file
        )
    )


    print(
        "🔐 FileGuard is running..."
    )


    app.run_polling()


# ==================================================
# Run
# ==================================================

if __name__ == "__main__":

    main()
