# 🚀 Professional Combined Save Restricted Content Bot

"""
Save Restricted Content Bot - Professional Edition
A powerful Telegram bot for downloading and saving restricted content

Author: Based on @VJ_Bots
Enhanced with professional error handling and code structure
"""

import os
import sys
import asyncio
import traceback
import logging
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

import motor.motor_asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from pyrogram.errors import (
    FloodWait, 
    UserIsBlocked, 
    InputUserDeactivated,
    UserAlreadyParticipant, 
    InviteHashExpired, 
    UsernameNotOccupied,
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    PeerIdInvalid,
    UserNotParticipant
)

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

@dataclass
class Config:
    """Configuration class for bot settings"""
    
    # Required configurations
    API_ID: int = int(os.environ.get("API_ID", "0"))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    DB_URI: str = os.environ.get("DB_URI", "")
    DB_NAME: str = os.environ.get("DB_NAME", "TechVJBot")
    
    # Optional configurations
    STRING_SESSION: Optional[str] = os.environ.get("STRING_SESSION", None)
    CHANNEL_ID: Optional[str] = os.environ.get("CHANNEL_ID", None)
    ADMINS: list = [int(x) for x in os.environ.get("ADMINS", "").split() if x.isdigit()]
    
    # Feature flags
    LOGIN_SYSTEM: bool = os.environ.get("LOGIN_SYSTEM", "True").lower() == "true"
    ERROR_MESSAGE: bool = os.environ.get("ERROR_MESSAGE", "True").lower() == "true"
    
    # Performance settings
    WAITING_TIME: int = int(os.environ.get("WAITING_TIME", "2"))
    MAX_WORKERS: int = int(os.environ.get("MAX_WORKERS", "150"))
    SLEEP_THRESHOLD: int = int(os.environ.get("SLEEP_THRESHOLD", "5"))
    
    # Session settings
    SESSION_STRING_SIZE: int = 351
    
    def validate(self) -> bool:
        """Validate required configurations"""
        if not self.API_ID or self.API_ID == 0:
            logging.error("API_ID is required")
            return False
        if not self.API_HASH:
            logging.error("API_HASH is required")
            return False
        if not self.BOT_TOKEN:
            logging.error("BOT_TOKEN is required")
            return False
        if not self.DB_URI:
            logging.error("DB_URI is required")
            return False
        return True

config = Config()

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

HELP_TEXT = """**🌟 Help Menu** 

**__FOR PRIVATE CHATS__**

__First send invite link of the chat (unnecessary if the account of string session already member of the chat)
then send post/s link__

**__FOR BOT CHATS__**

__Send link with '/b/', bot's username and message id, you might want to install some unofficial client to get the id like below__

```
https://t.me/b/botusername/4321
```

**__MULTI POSTS__**

__Send public/private posts link as explained above with format "from - to" to send multiple messages like below__

```
https://t.me/xxxx/1001-1010

https://t.me/c/xxxx/101 - 120
```

__Note that space in between doesn't matter__"""

START_TEXT = """<b>👋 Hi {}, 

I am Save Restricted Content Bot. I can send you restricted content by its post link.

For downloading restricted content /login first.

Know how to use bot by - /help</b>"""

# ============================================================================
# DATABASE CLASS
# ============================================================================

class Database:
    """Professional database handler with error handling"""
    
    def __init__(self, uri: str, database_name: str):
        """Initialize database connection"""
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self.db = self._client[database_name]
            self.col = self.db.users
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    @staticmethod
    def new_user(user_id: int, name: str) -> Dict[str, Any]:
        """Create new user document"""
        return {
            'id': user_id,
            'name': name,
            'session': None,
            'api_id': None,
            'api_hash': None,
            'created_at': datetime.now(),
            'last_active': datetime.now()
        }
    
    async def add_user(self, user_id: int, name: str) -> bool:
        """Add new user to database"""
        try:
            user = self.new_user(user_id, name)
            await self.col.insert_one(user)
            logger.info(f"New user added: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False
    
    async def is_user_exist(self, user_id: int) -> bool:
        """Check if user exists"""
        try:
            user = await self.col.find_one({'id': int(user_id)})
            return bool(user)
        except Exception as e:
            logger.error(f"Error checking user existence {user_id}: {e}")
            return False
    
    async def total_users_count(self) -> int:
        """Get total users count"""
        try:
            count = await self.col.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0
    
    async def get_all_users(self):
        """Get all users cursor"""
        try:
            return self.col.find({})
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def delete_user(self, user_id: int) -> bool:
        """Delete user from database"""
        try:
            await self.col.delete_many({'id': int(user_id)})
            logger.info(f"User deleted: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    async def update_last_active(self, user_id: int) -> bool:
        """Update user's last active time"""
        try:
            await self.col.update_one(
                {'id': int(user_id)}, 
                {'$set': {'last_active': datetime.now()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating last active {user_id}: {e}")
            return False
    
    async def set_session(self, user_id: int, session: Optional[str]) -> bool:
        """Set user session"""
        try:
            await self.col.update_one(
                {'id': int(user_id)}, 
                {'$set': {'session': session}}
            )
            return True
        except Exception as e:
            logger.error(f"Error setting session {user_id}: {e}")
            return False
    
    async def get_session(self, user_id: int) -> Optional[str]:
        """Get user session"""
        try:
            user = await self.col.find_one({'id': int(user_id)})
            return user.get('session') if user else None
        except Exception as e:
            logger.error(f"Error getting session {user_id}: {e}")
            return None
    
    async def set_api_id(self, user_id: int, api_id: int) -> bool:
        """Set user API ID"""
        try:
            await self.col.update_one(
                {'id': int(user_id)}, 
                {'$set': {'api_id': api_id}}
            )
            return True
        except Exception as e:
            logger.error(f"Error setting API ID {user_id}: {e}")
            return False
    
    async def get_api_id(self, user_id: int) -> Optional[int]:
        """Get user API ID"""
        try:
            user = await self.col.find_one({'id': int(user_id)})
            return user.get('api_id') if user else None
        except Exception as e:
            logger.error(f"Error getting API ID {user_id}: {e}")
            return None
    
    async def set_api_hash(self, user_id: int, api_hash: str) -> bool:
        """Set user API Hash"""
        try:
            await self.col.update_one(
                {'id': int(user_id)}, 
                {'$set': {'api_hash': api_hash}}
            )
            return True
        except Exception as e:
            logger.error(f"Error setting API Hash {user_id}: {e}")
            return False
    
    async def get_api_hash(self, user_id: int) -> Optional[str]:
        """Get user API Hash"""
        try:
            user = await self.col.find_one({'id': int(user_id)})
            return user.get('api_hash') if user else None
        except Exception as e:
            logger.error(f"Error getting API Hash {user_id}: {e}")
            return None

# Initialize database
db = Database(config.DB_URI, config.DB_NAME)

# ============================================================================
# BATCH PROCESSING CLASS
# ============================================================================

class BatchManager:
    """Manage batch processing state"""
    
    def __init__(self):
        self._batch_states: Dict[int, bool] = {}
    
    def is_processing(self, user_id: int) -> bool:
        """Check if user has active batch"""
        return self._batch_states.get(user_id, False) == False
    
    def start_batch(self, user_id: int):
        """Start batch processing for user"""
        self._batch_states[user_id] = False
    
    def stop_batch(self, user_id: int):
        """Stop batch processing for user"""
        self._batch_states[user_id] = True
    
    def cancel_batch(self, user_id: int):
        """Cancel batch processing for user"""
        self._batch_states[user_id] = True
    
    def is_cancelled(self, user_id: int) -> bool:
        """Check if batch is cancelled"""
        return self._batch_states.get(user_id, True) == True

batch_manager = BatchManager()

# ============================================================================
# PROGRESS TRACKING
# ============================================================================

class ProgressTracker:
    """Handle download/upload progress tracking"""
    
    @staticmethod
    def write_progress(message_id: int, progress_type: str, current: int, total: int):
        """Write progress to file"""
        try:
            percentage = (current * 100 / total) if total > 0 else 0
            filename = f'{message_id}{progress_type}status.txt'
            with open(filename, "w") as f:
                f.write(f"{percentage:.1f}%")
        except Exception as e:
            logger.error(f"Error writing progress: {e}")
    
    @staticmethod
    async def monitor_download_progress(
        client: Client, 
        status_file: str, 
        message: Message, 
        chat_id: int
    ):
        """Monitor download progress"""
        # Wait for status file to be created
        while not os.path.exists(status_file):
            await asyncio.sleep(3)
        
        # Monitor progress
        while os.path.exists(status_file):
            try:
                with open(status_file, "r") as f:
                    progress_text = f.read()
                
                await client.edit_message_text(
                    chat_id, 
                    message.id, 
                    f"**Downloaded:** **{progress_text}**"
                )
                await asyncio.sleep(10)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Error monitoring download: {e}")
                await asyncio.sleep(5)
    
    @staticmethod
    async def monitor_upload_progress(
        client: Client, 
        status_file: str, 
        message: Message, 
        chat_id: int
    ):
        """Monitor upload progress"""
        # Wait for status file to be created
        while not os.path.exists(status_file):
            await asyncio.sleep(3)
        
        # Monitor progress
        while os.path.exists(status_file):
            try:
                with open(status_file, "r") as f:
                    progress_text = f.read()
                
                await client.edit_message_text(
                    chat_id, 
                    message.id, 
                    f"**Uploaded:** **{progress_text}**"
                )
                await asyncio.sleep(10)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Error monitoring upload: {e}")
                await asyncio.sleep(5)

progress_tracker = ProgressTracker()

# ============================================================================
# MESSAGE HANDLER CLASS
# ============================================================================

class MessageHandler:
    """Handle different types of messages"""
    
    @staticmethod
    def get_message_type(msg: Message) -> Optional[str]:
        """Determine message type"""
        type_checks = [
            ('document', 'Document'),
            ('video', 'Video'),
            ('animation', 'Animation'),
            ('sticker', 'Sticker'),
            ('voice', 'Voice'),
            ('audio', 'Audio'),
            ('photo', 'Photo'),
            ('text', 'Text')
        ]
        
        for attr, msg_type in type_checks:
            try:
                if getattr(msg, attr):
                    return msg_type
            except AttributeError:
                continue
        
        return None
    
    @staticmethod
    async def send_message_by_type(
        client: Client,
        chat_id: int,
        file_path: str,
        msg_type: str,
        msg: Message,
        message: Message,
        acc: Client
    ):
        """Send message based on type"""
        caption = msg.caption if hasattr(msg, 'caption') else None
        reply_to = message.id
        
        try:
            if msg_type == "Text":
                await client.send_message(
                    chat_id, 
                    msg.text, 
                    entities=msg.entities,
                    reply_to_message_id=reply_to,
                    parse_mode=enums.ParseMode.HTML
                )
            
            elif msg_type == "Document":
                thumb = await MessageHandler._get_thumb(acc, msg.document)
                await client.send_document(
                    chat_id, 
                    file_path,
                    thumb=thumb,
                    caption=caption,
                    reply_to_message_id=reply_to,
                    parse_mode=enums.ParseMode.HTML,
                    progress=lambda c, t: progress_tracker.write_progress(message.id, "up", c, t)
                )
                MessageHandler._cleanup_file(thumb)
            
            elif msg_type == "Video":
                thumb = await MessageHandler._get_thumb(acc, msg.video)
                await client.send_video(
                    chat_id, 
                    file_path,
                    duration=msg.video.duration,
                    width=msg.video.width,
                    height=msg.video.height,
                    thumb=thumb,
                    caption=caption,
                    reply_to_message_id=reply_to,
                    parse_mode=enums.ParseMode.HTML,
                    progress=lambda c, t: progress_tracker.write_progress(message.id, "up", c, t)
                )
                MessageHandler._cleanup_file(thumb)
            
            elif msg_type == "Audio":
                thumb = await MessageHandler._get_thumb(acc, msg.audio)
                await client.send_audio(
                    chat_id, 
                    file_path,
                    thumb=thumb,
                    caption=caption,
                    reply_to_message_id=reply_to,
                    parse_mode=enums.ParseMode.HTML,
                    progress=lambda c, t: progress_tracker.write_progress(message.id, "up", c, t)
                )
                MessageHandler._cleanup_file(thumb)
            
            elif msg_type == "Photo":
                await client.send_photo(
                    chat_id, 
                    file_path,
                    caption=caption,
                    reply_to_message_id=reply_to,
                    parse_mode=enums.ParseMode.HTML
                )
            
            elif msg_type == "Animation":
                await client.send_animation(
                    chat_id, 
                    file_path,
                    reply_to_message_id=reply_to,
                    parse_mode=enums.ParseMode.HTML
                )
            
            elif msg_type == "Sticker":
                await client.send_sticker(
                    chat_id, 
                    file_path,
                    reply_to_message_id=reply_to
                )
            
            elif msg_type == "Voice":
                await client.send_voice(
                    chat_id, 
                    file_path,
                    caption=caption,
                    reply_to_message_id=reply_to,
                    parse_mode=enums.ParseMode.HTML,
                    progress=lambda c, t: progress_tracker.write_progress(message.id, "up", c, t)
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending {msg_type}: {e}")
            raise
    
    @staticmethod
    async def _get_thumb(acc: Client, media) -> Optional[str]:
        """Get thumbnail for media"""
        try:
            if hasattr(media, 'thumbs') and media.thumbs:
                return await acc.download_media(media.thumbs[0].file_id)
        except Exception as e:
            logger.error(f"Error getting thumbnail: {e}")
        return None
    
    @staticmethod
    def _cleanup_file(file_path: Optional[str]):
        """Clean up temporary file"""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing file {file_path}: {e}")

message_handler = MessageHandler()

# ============================================================================
# CONTENT DOWNLOADER CLASS
# ============================================================================

class ContentDownloader:
    """Handle content downloading and forwarding"""
    
    @staticmethod
    async def handle_private_message(
        client: Client,
        acc: Client,
        message: Message,
        chat_id: int,
        msg_id: int
    ):
        """Handle private channel message"""
        try:
            # Get the message
            msg: Message = await acc.get_messages(chat_id, msg_id)
            
            if msg.empty:
                logger.warning(f"Empty message: {chat_id}/{msg_id}")
                return
            
            # Determine message type
            msg_type = message_handler.get_message_type(msg)
            if not msg_type:
                logger.warning(f"Unknown message type: {chat_id}/{msg_id}")
                return
            
            # Determine target chat
            target_chat = int(config.CHANNEL_ID) if config.CHANNEL_ID else message.chat.id
            
            # Check if batch is cancelled
            if batch_manager.is_cancelled(message.from_user.id):
                return
            
            # Handle text messages directly
            if msg_type == "Text":
                try:
                    await client.send_message(
                        target_chat,
                        msg.text,
                        entities=msg.entities,
                        reply_to_message_id=message.id,
                        parse_mode=enums.ParseMode.HTML
                    )
                    return
                except Exception as e:
                    if config.ERROR_MESSAGE:
                        await client.send_message(
                            message.chat.id,
                            f"Error: {e}",
                            reply_to_message_id=message.id
                        )
                    return
            
            # Download media
            status_msg = await client.send_message(
                message.chat.id,
                '**Downloading...**',
                reply_to_message_id=message.id
            )
            
            download_status_file = f'{message.id}downstatus.txt'
            asyncio.create_task(
                progress_tracker.monitor_download_progress(
                    client, 
                    download_status_file, 
                    status_msg, 
                    target_chat
                )
            )
            
            try:
                file_path = await acc.download_media(
                    msg,
                    progress=lambda c, t: progress_tracker.write_progress(message.id, "down", c, t)
                )
                
                if os.path.exists(download_status_file):
                    os.remove(download_status_file)
                    
            except Exception as e:
                logger.error(f"Download error: {e}")
                if config.ERROR_MESSAGE:
                    await client.send_message(
                        message.chat.id,
                        f"Download Error: {e}",
                        reply_to_message_id=message.id
                    )
                await status_msg.delete()
                return
            
            # Check if batch is cancelled
            if batch_manager.is_cancelled(message.from_user.id):
                message_handler._cleanup_file(file_path)
                return
            
            # Upload media
            upload_status_file = f'{message.id}upstatus.txt'
            asyncio.create_task(
                progress_tracker.monitor_upload_progress(
                    client, 
                    upload_status_file, 
                    status_msg, 
                    target_chat
                )
            )
            
            try:
                await message_handler.send_message_by_type(
                    client,
                    target_chat,
                    file_path,
                    msg_type,
                    msg,
                    message,
                    acc
                )
            except Exception as e:
                logger.error(f"Upload error: {e}")
                if config.ERROR_MESSAGE:
                    await client.send_message(
                        message.chat.id,
                        f"Upload Error: {e}",
                        reply_to_message_id=message.id
                    )
            
            # Cleanup
            for file in [upload_status_file, file_path]:
                message_handler._cleanup_file(file)
            
            await client.delete_messages(message.chat.id, [status_msg.id])
            
        except Exception as e:
            logger.error(f"Error handling private message: {e}")
            if config.ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id,
                    f"Error: {e}",
                    reply_to_message_id=message.id
                )

content_downloader = ContentDownloader()

# ============================================================================
# USER CLIENT MANAGER
# ============================================================================

TechVJUser: Optional[Client] = None

def initialize_user_client():
    """Initialize user client if string session is provided"""
    global TechVJUser
    
    if config.STRING_SESSION and not config.LOGIN_SYSTEM:
        try:
            TechVJUser = Client(
                "TechVJ",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=config.STRING_SESSION
            )
            TechVJUser.start()
            logger.info("User client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize user client: {e}")
            TechVJUser = None

# ============================================================================
# BOT CLASS
# ============================================================================

class SaveRestrictedBot(Client):
    """Main bot class"""
    
    def __init__(self):
        super().__init__(
            "SaveRestrictedBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=config.MAX_WORKERS,
            sleep_threshold=config.SLEEP_THRESHOLD
        )
    
    async def start(self):
        """Start the bot"""
        await super().start()
        me = await self.get_me()
        logger.info(f"Bot started as @{me.username}")
        logger.info("Powered By @VJ_Bots")
    
    async def stop(self, *args):
        """Stop the bot"""
        await super().stop()
        logger.info("Bot stopped")

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

def create_bot_instance():
    """Create and configure bot instance"""
    bot = SaveRestrictedBot()
    
    # ========================================================================
    # START COMMAND
    # ========================================================================
    
    @bot.on_message(filters.command(["start"]))
    async def cmd_start(client: Client, message: Message):
        """Handle /start command"""
        try:
            # Add user to database
            if not await db.is_user_exist(message.from_user.id):
                await db.add_user(message.from_user.id, message.from_user.first_name)
            else:
                await db.update_last_active(message.from_user.id)
            
            # Create buttons
            buttons = [
                [InlineKeyboardButton("❣️ Developer", url="https://t.me/kingvj01")],
                [
                    InlineKeyboardButton('🔍 Support Group', url='https://t.me/vj_bot_disscussion'),
                    InlineKeyboardButton('🤖 Update Channel', url='https://t.me/vj_botz')
                ]
            ]
            
            await client.send_message(
                chat_id=message.chat.id,
                text=START_TEXT.format(message.from_user.mention),
                reply_markup=InlineKeyboardMarkup(buttons),
                reply_to_message_id=message.id
            )
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.reply("An error occurred. Please try again later.")
    
    # ========================================================================
    # HELP COMMAND
    # ========================================================================
    
    @bot.on_message(filters.command(["help"]))
    async def cmd_help(client: Client, message: Message):
        """Handle /help command"""
        try:
            await client.send_message(
                chat_id=message.chat.id,
                text=HELP_TEXT,
                reply_to_message_id=message.id
            )
        except Exception as e:
            logger.error(f"Error in help command: {e}")
    
    # ========================================================================
    # CANCEL COMMAND
    # ========================================================================
    
    @bot.on_message(filters.command(["cancel"]))
    async def cmd_cancel(client: Client, message: Message):
        """Handle /cancel command"""
        try:
            batch_manager.cancel_batch(message.from_user.id)
            await client.send_message(
                chat_id=message.chat.id,
                text="**Batch Successfully Cancelled.**",
                reply_to_message_id=message.id
            )
        except Exception as e:
            logger.error(f"Error in cancel command: {e}")
    
    # ========================================================================
    # LOGIN COMMAND
    # ========================================================================
    
    @bot.on_message(filters.private & filters.command(["login"]))
    async def cmd_login(client: Client, message: Message):
        """Handle /login command"""
        try:
            # Check if already logged in
            user_data = await db.get_session(message.from_user.id)
            if user_data:
                await message.reply(
                    "**You are already logged in. First /logout your old session. Then do login.**"
                )
                return
            
            user_id = message.from_user.id
            
            # Send API ID/Hash instructions
            await message.reply(
                "**How To Create Api Id And Api Hash.\n\n"
                "Video Link :- https://youtu.be/LDtgwpI-N7M**"
            )
            
            # Ask for API ID
            api_id_msg = await client.ask(
                user_id,
                "<b>Send Your API ID.\n\n"
                "Click On /skip To Skip This Process\n\n"
                "NOTE :- If You Skip This Then Your Account Ban Chance Is High.</b>",
                filters=filters.text,
                timeout=300
            )
            
            if api_id_msg.text == "/skip":
                api_id = config.API_ID
                api_hash = config.API_HASH
            else:
                try:
                    api_id = int(api_id_msg.text)
                except ValueError:
                    await api_id_msg.reply(
                        "**Api id must be an integer, start your process again by /login**",
                        quote=True
                    )
                    return
                
                # Ask for API Hash
                api_hash_msg = await client.ask(
                    user_id,
                    "**Now Send Me Your API HASH**",
                    filters=filters.text,
                    timeout=300
                )
                
                if api_hash_msg.text == "/cancel":
                    await api_hash_msg.reply("**Process cancelled!**")
                    return
                
                api_hash = api_hash_msg.text
            
            # Ask for phone number
            phone_number_msg = await client.ask(
                user_id,
                "<b>Please send your phone number which includes country code</b>\n"
                "<b>Example:</b> <code>+13124562345, +9171828181889</code>",
                filters=filters.text,
                timeout=300
            )
            
            if phone_number_msg.text == '/cancel':
                await phone_number_msg.reply('<b>Process cancelled!</b>')
                return
            
            phone_number = phone_number_msg.text
            
            # Create temporary client
            temp_client = Client(":memory:", api_id, api_hash)
            await temp_client.connect()
            
            # Send OTP
            await phone_number_msg.reply("Sending OTP...")
            
            try:
                code = await temp_client.send_code(phone_number)
            except PhoneNumberInvalid:
                await phone_number_msg.reply('**PHONE_NUMBER is invalid.**')
                await temp_client.disconnect()
                return
            except Exception as e:
                await phone_number_msg.reply(f'**Error:** {e}')
                await temp_client.disconnect()
                return
            
            # Ask for OTP
            phone_code_msg = await client.ask(
                user_id,
                "Please check for an OTP in official telegram account. "
                "If you got it, send OTP here after reading the below format.\n\n"
                "If OTP is `12345`, **please send it as** `1 2 3 4 5`.\n\n"
                "**Enter /cancel to cancel the process**",
                filters=filters.text,
                timeout=600
            )
            
            if phone_code_msg.text == '/cancel':
                await phone_code_msg.reply('<b>Process cancelled!</b>')
                await temp_client.disconnect()
                return
            
            # Sign in
            try:
                phone_code = phone_code_msg.text.replace(" ", "")
                await temp_client.sign_in(phone_number, code.phone_code_hash, phone_code)
            except PhoneCodeInvalid:
                await phone_code_msg.reply('**OTP is invalid.**')
                await temp_client.disconnect()
                return
            except PhoneCodeExpired:
                await phone_code_msg.reply('**OTP is expired.**')
                await temp_client.disconnect()
                return
            except SessionPasswordNeeded:
                # Handle 2FA
                two_step_msg = await client.ask(
                    user_id,
                    '**Your account has enabled two-step verification. '
                    'Please provide the password.\n\n'
                    'Enter /cancel to cancel the process**',
                    filters=filters.text,
                    timeout=300
                )
                
                if two_step_msg.text == '/cancel':
                    await two_step_msg.reply('<b>Process cancelled!</b>')
                    await temp_client.disconnect()
                    return
                
                try:
                    password = two_step_msg.text
                    await temp_client.check_password(password=password)
                except PasswordHashInvalid:
                    await two_step_msg.reply('**Invalid Password Provided**')
                    await temp_client.disconnect()
                    return
            
            # Export session
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()
            
            # Validate session
            if len(string_session) < config.SESSION_STRING_SIZE:
                await message.reply('<b>Invalid session string</b>')
                return
            
            # Save to database
            try:
                test_client = Client(
                    ":memory:",
                    session_string=string_session,
                    api_id=api_id,
                    api_hash=api_hash
                )
                await test_client.connect()
                
                await db.set_session(message.from_user.id, string_session)
                await db.set_api_id(message.from_user.id, api_id)
                await db.set_api_hash(message.from_user.id, api_hash)
                
                await test_client.disconnect()
                
                await client.send_message(
                    message.from_user.id,
                    "<b>Account Login Successfully.\n\n"
                    "If You Get Any Error Related To AUTH KEY Then /logout first and /login again</b>"
                )
                
            except Exception as e:
                logger.error(f"Login error: {e}")
                await message.reply(f"<b>ERROR IN LOGIN:</b> `{e}`")
        
        except asyncio.TimeoutError:
            await message.reply("**Process timeout! Please try again.**")
        except Exception as e:
            logger.error(f"Error in login command: {e}")
            await message.reply(f"**Error:** {e}")
    
    # ========================================================================
    # LOGOUT COMMAND
    # ========================================================================
    
    @bot.on_message(filters.private & filters.command(["logout"]))
    async def cmd_logout(client: Client, message: Message):
        """Handle /logout command"""
        try:
            user_data = await db.get_session(message.from_user.id)
            if user_data is None:
                await message.reply("**You are not logged in.**")
                return
            
            await db.set_session(message.from_user.id, None)
            await message.reply("**Logout Successfully** ♦")
            
        except Exception as e:
            logger.error(f"Error in logout command: {e}")
            await message.reply("**Error during logout. Please try again.**")
    
    # ========================================================================
    # BROADCAST COMMAND (Admin Only)
    # ========================================================================
    
    @bot.on_message(filters.command("broadcast") & filters.reply)
    async def cmd_broadcast(client: Client, message: Message):
        """Handle /broadcast command"""
        try:
            # Check if user is admin
            if message.from_user.id not in config.ADMINS:
                await message.reply("**You are not authorized to use this command.**")
                return
            
            b_msg = message.reply_to_message
            if not b_msg:
                await message.reply("**Reply this command to your broadcast message**")
                return
            
            sts = await message.reply_text('Broadcasting your messages...')
            
            start_time = time.time()
            total_users = await db.total_users_count()
            done = 0
            success = 0
            blocked = 0
            deleted = 0
            failed = 0
            
            async for user in await db.get_all_users():
                if 'id' not in user:
                    done += 1
                    failed += 1
                    continue
                
                user_id = user['id']
                
                try:
                    await b_msg.copy(chat_id=user_id)
                    success += 1
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    try:
                        await b_msg.copy(chat_id=user_id)
                        success += 1
                    except Exception:
                        failed += 1
                except InputUserDeactivated:
                    await db.delete_user(user_id)
                    deleted += 1
                except UserIsBlocked:
                    await db.delete_user(user_id)
                    blocked += 1
                except PeerIdInvalid:
                    await db.delete_user(user_id)
                    failed += 1
                except Exception as e:
                    logger.error(f"Broadcast error for user {user_id}: {e}")
                    failed += 1
                
                done += 1
                
                # Update status every 20 users
                if done % 20 == 0:
                    await sts.edit(
                        f"Broadcast in progress:\n\n"
                        f"Total Users: {total_users}\n"
                        f"Completed: {done} / {total_users}\n"
                        f"Success: {success}\n"
                        f"Blocked: {blocked}\n"
                        f"Deleted: {deleted}\n"
                        f"Failed: {failed}"
                    )
            
            time_taken = timedelta(seconds=int(time.time() - start_time))
            
            await sts.edit(
                f"Broadcast Completed:\n"
                f"Completed in {time_taken} seconds.\n\n"
                f"Total Users: {total_users}\n"
                f"Completed: {done} / {total_users}\n"
                f"Success: {success}\n"
                f"Blocked: {blocked}\n"
                f"Deleted: {deleted}\n"
                f"Failed: {failed}"
            )
            
        except Exception as e:
            logger.error(f"Error in broadcast command: {e}")
            await message.reply(f"**Broadcast Error:** {e}")
    
    # ========================================================================
    # STATS COMMAND (Admin Only)
    # ========================================================================
    
    @bot.on_message(filters.command("stats"))
    async def cmd_stats(client: Client, message: Message):
        """Handle /stats command"""
        try:
            if message.from_user.id not in config.ADMINS:
                return
            
            total_users = await db.total_users_count()
            
            await message.reply(
                f"**📊 Bot Statistics**\n\n"
                f"👥 Total Users: {total_users}\n"
                f"🤖 Bot: @{(await client.get_me()).username}"
            )
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
    
    # ========================================================================
    # TEXT MESSAGE HANDLER
    # ========================================================================
    
    @bot.on_message(filters.text & filters.private)
    async def handle_text_message(client: Client, message: Message):
        """Handle text messages containing links"""
        try:
            # Update user activity
            await db.update_last_active(message.from_user.id)
            
            # Handle join chat links
            if ("https://t.me/+" in message.text or 
                "https://t.me/joinchat/" in message.text) and not config.LOGIN_SYSTEM:
                
                if TechVJUser is None:
                    await message.reply("String Session is not set")
                    return
                
                try:
                    await TechVJUser.join_chat(message.text)
                    await message.reply("Chat Joined")
                except UserAlreadyParticipant:
                    await message.reply("Chat already joined")
                except InviteHashExpired:
                    await message.reply("Invalid Link")
                except Exception as e:
                    logger.error(f"Join chat error: {e}")
                    await message.reply(f"Error: {e}")
                return
            
            # Handle content download links
            if "https://t.me/" in message.text:
                # Check if user has active batch
                if batch_manager.is_processing(message.from_user.id):
                    await message.reply(
                        "**One Task Is Already Processing. Wait For Complete It. "
                        "If You Want To Cancel This Task Then Use - /cancel**"
                    )
                    return
                
                # Parse message link
                try:
                    datas = message.text.split("/")
                    temp = datas[-1].replace("?single", "").split("-")
                    from_id = int(temp[0].strip())
                    to_id = int(temp[1].strip()) if len(temp) > 1 else from_id
                except Exception as e:
                    logger.error(f"Link parsing error: {e}")
                    await message.reply("**Invalid link format**")
                    return
                
                # Setup user account
                if config.LOGIN_SYSTEM:
                    user_data = await db.get_session(message.from_user.id)
                    if user_data is None:
                        await message.reply(
                            "**For Downloading Restricted Content You Have To /login First.**"
                        )
                        return
                    
                    api_id = await db.get_api_id(message.from_user.id)
                    api_hash = await db.get_api_hash(message.from_user.id)
                    
                    try:
                        acc = Client(
                            "saverestricted",
                            session_string=user_data,
                            api_hash=api_hash,
                            api_id=api_id
                        )
                        await acc.connect()
                    except Exception as e:
                        logger.error(f"User client connection error: {e}")
                        await message.reply(
                            "**Your Login Session Expired. So /logout First Then Login Again By - /login**"
                        )
                        return
                else:
                    if TechVJUser is None:
                        await message.reply("**String Session is not set**")
                        return
                    acc = TechVJUser
                
                # Start batch processing
                batch_manager.start_batch(message.from_user.id)
                
                try:
                    for msg_id in range(from_id, to_id + 1):
                        # Check if batch is cancelled
                        if batch_manager.is_cancelled(message.from_user.id):
                            break
                        
                        # Handle different chat types
                        try:
                            if "https://t.me/c/" in message.text:
                                # Private chat
                                chat_id = int("-100" + datas[4])
                                await content_downloader.handle_private_message(
                                    client, acc, message, chat_id, msg_id
                                )
                            
                            elif "https://t.me/b/" in message.text:
                                # Bot chat
                                username = datas[4]
                                await content_downloader.handle_private_message(
                                    client, acc, message, username, msg_id
                                )
                            
                            else:
                                # Public chat
                                username = datas[3]
                                
                                try:
                                    msg = await client.get_messages(username, msg_id)
                                    await client.copy_message(
                                        message.chat.id,
                                        msg.chat.id,
                                        msg.id,
                                        reply_to_message_id=message.id
                                    )
                                except UsernameNotOccupied:
                                    await message.reply(
                                        "The username is not occupied by anyone"
                                    )
                                    break
                                except Exception:
                                    await content_downloader.handle_private_message(
                                        client, acc, message, username, msg_id
                                    )
                        
                        except Exception as e:
                            logger.error(f"Error processing message {msg_id}: {e}")
                            if config.ERROR_MESSAGE:
                                await message.reply(f"Error: {e}")
                        
                        # Wait between messages
                        await asyncio.sleep(config.WAITING_TIME)
                
                finally:
                    # Cleanup
                    batch_manager.stop_batch(message.from_user.id)
                    
                    if config.LOGIN_SYSTEM:
                        try:
                            await acc.disconnect()
                        except Exception as e:
                            logger.error(f"Error disconnecting user client: {e}")
        
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            logger.error(traceback.format_exc())
            await message.reply("**An error occurred. Please try again later.**")
    
    return bot

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            sys.exit(1)
        
        # Initialize user client if needed
        initialize_user_client()
        
        # Create and run bot
        bot = create_bot_instance()
        logger.info("Starting bot...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()

# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
