# 🔐 FileGuard

FileGuard is a Telegram bot designed to demonstrate file integrity verification using SHA-256 hashing.

The project was created as a practical application of cybersecurity and Python programming concepts that I learned through online courses.

## 🚀 Features

- 📥 Register files
- 🔐 Generate SHA-256 fingerprints
- 🔍 Verify file integrity
- 📊 Compare original and current file hashes
- 📁 Store registered files
- 🗑️ Delete registered files
- 🔙 Simple Telegram interface
- 💾 SQLite database for storing file information

## 🧠 How It Works

FileGuard uses SHA-256 hashing to create a unique fingerprint for a file.

When a file is registered:

1. The bot receives the file.
2. It calculates its SHA-256 hash.
3. The hash is stored in the database.

When the file is verified:

1. The user sends the file again.
2. The bot calculates its current SHA-256 hash.
3. The current hash is compared with the original hash.
4. If they match, the file has not changed.
5. If they are different, the bot reports that the file has changed.

## 🛠️ Technologies

- Python
- Telegram Bot API
- python-telegram-bot
- SHA-256
- hashlib
- SQLite
- Termux

## 📂 Project Structure

```text
FileGuard/
│
├── mahmoodbot2.py
├── fileguard.db
├── downloads/
└── README.md
