import httpx
import asyncio
import jdatetime
from datetime import time
import logging
import html
import time
import json
import os
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Tuple, Any
import pytz
import psycopg2
from psycopg2 import pool
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات اصلی
TOKEN = "8503709201:AAGSA_985sSxBrxQbjaO6mtPQnvFqjPFIC8"
ADMIN_IDS = [6680287530]
MAX_STUDY_TIME = 120
MIN_STUDY_TIME = 10

# تنظیمات دیتابیس PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "database": "focustodo_db",
    "user": "postgres",
    "password": "m13821382",
    "port": "5432"
}

# زمان ایران
IRAN_TZ = pytz.timezone('Asia/Tehran')

# دروس پیش‌فرض
SUBJECTS = [
    "فیزیک", "شیمی", "ریاضی", "زیست",
    "ادبیات", "عربی", "دینی", "زبان",
    "حسابان", "هندسه", "گسسته", "سایر"
]

# زمان‌های پیشنهادی
SUGGESTED_TIMES = [
    ("۳۰ دقیقه", 30),
    ("۴۵ دقیقه", 45),
    ("۱ ساعت", 60),
    ("۱.۵ ساعت", 90),
    ("۲ ساعت", 120)
]

# -----------------------------------------------------------
# مدیریت دیتابیس
# -----------------------------------------------------------

class Database:
    """کلاس مدیریت دیتابیس PostgreSQL"""
    
    def __init__(self):
        self.connection_pool = None
        self.init_pool()
        self.create_tables()
    
    def init_pool(self):
        """ایجاد Connection Pool"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=DB_CONFIG["host"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                port=DB_CONFIG["port"]
            )
            logger.info("✅ Connection Pool ایجاد شد")
        except Exception as e:
            logger.error(f"❌ خطا در اتصال به دیتابیس: {e}")
            raise
    
    def get_connection(self):
        """دریافت یک Connection از Pool"""
        return self.connection_pool.getconn()
    
    def return_connection(self, connection):
        """بازگرداندن Connection به Pool"""
        self.connection_pool.putconn(connection)
    
    def execute_query(self, query, params=None, fetch=False, fetchall=False):
        """اجرای کوئری"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.rowcount
            
            return result
            
        except Exception as e:
            logger.error(f"❌ خطا در اجرای کوئری: {e}")
            if conn:
                conn.rollback()
            raise
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
    def create_tables(self):
        """ایجاد جداول دیتابیس"""
        queries = [
            # جداول موجود...
            
            # جدول جدید: کوپن‌ها
            
            
            # جدول جدید: تنظیمات سیستم
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_id SERIAL PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE,
                setting_value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                grade VARCHAR(50),
                field VARCHAR(50),
                message TEXT,
                is_active BOOLEAN DEFAULT FALSE,
                registration_date VARCHAR(50),
                total_study_time INTEGER DEFAULT 0,
                total_sessions INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                subject VARCHAR(100),
                topic TEXT,
                minutes INTEGER,
                start_time BIGINT,
                end_time BIGINT,
                completed BOOLEAN DEFAULT FALSE,
                date VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS files (
                file_id SERIAL PRIMARY KEY,
                grade VARCHAR(50),
                field VARCHAR(50),
                subject VARCHAR(100),
                topic TEXT,
                description TEXT,
                telegram_file_id VARCHAR(500),
                file_name VARCHAR(255),
                file_size INTEGER,
                mime_type VARCHAR(100),
                upload_date VARCHAR(50),
                download_count INTEGER DEFAULT 0,
                uploader_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_rankings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                date VARCHAR(50),
                total_minutes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS registration_requests (
                request_id SERIAL PRIMARY KEY,
                user_id BIGINT,
                username VARCHAR(255),
                grade VARCHAR(50),
                field VARCHAR(50),
                message TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # در بخش ایجاد جداول دیتابیس (class Database - create_tables):
            """
            CREATE TABLE IF NOT EXISTS weekly_rankings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                week_start_date VARCHAR(50),
                total_minutes INTEGER DEFAULT 0,
                rank INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, week_start_date)
           )
           """,
           """
           CREATE TABLE IF NOT EXISTS reward_coupons (
               coupon_id SERIAL PRIMARY KEY,
               user_id BIGINT REFERENCES users(user_id),
               coupon_code VARCHAR(50) UNIQUE,
               value INTEGER DEFAULT 20000,
               status VARCHAR(20) DEFAULT 'pending',
               study_session_id INTEGER,
               created_date VARCHAR(50),
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               expires_at VARCHAR(50),
               used_at TIMESTAMP
          )
          """,

            # جدول جدید: کوپن‌ها
          """
            CREATE TABLE IF NOT EXISTS coupons (
                coupon_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                coupon_code VARCHAR(50) UNIQUE,
                coupon_source VARCHAR(50),
                value INTEGER DEFAULT 400000,
                status VARCHAR(20) DEFAULT 'active',
                earned_date VARCHAR(50),
                used_date VARCHAR(50),
                used_for VARCHAR(50),
                purchase_receipt TEXT,
                admin_card_number VARCHAR(50),
                verified_by_admin BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS competition_rooms (
                room_code VARCHAR(10) PRIMARY KEY,
                creator_id BIGINT REFERENCES users(user_id),
                password VARCHAR(4),
                end_time VARCHAR(10),  -- مثل '20:00'
                min_players INT DEFAULT 5,
                status VARCHAR(20) DEFAULT 'waiting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS room_participants (
                room_code VARCHAR(10) REFERENCES competition_rooms(room_code),
                user_id BIGINT REFERENCES users(user_id),
                total_minutes INT DEFAULT 0,
                current_subject VARCHAR(50),
                current_topic VARCHAR(100),
                last_rank INT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (room_code, user_id)
            )
            """,
            
            # جدول جدید: استرک‌های مطالعه
            """
            CREATE TABLE IF NOT EXISTS user_study_streaks (
                streak_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                start_date VARCHAR(50),
                end_date VARCHAR(50),
                total_hours INTEGER,
                days_count INTEGER,
                earned_coupon BOOLEAN DEFAULT FALSE,
                coupon_id INTEGER REFERENCES coupons(coupon_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # جدول جدید: درخواست‌های کوپن
            """
            CREATE TABLE IF NOT EXISTS coupon_requests (
                request_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                request_type VARCHAR(50), -- 'purchase', 'usage'
                service_type VARCHAR(50), -- 'call', 'analysis', 'correction', 'exam', 'test_analysis'
                coupon_codes TEXT, -- کدهای کوپن برای استفاده
                amount INTEGER, -- مبلغ پرداختی
                status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'completed'
                receipt_image TEXT, -- عکس فیش
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
            except Exception as e:
                logger.warning(f"خطا در ایجاد جدول: {e}")
        
        logger.info("✅ جداول دیتابیس بررسی شدند")

# ایجاد نمونه دیتابیس
db = Database()

# -----------------------------------------------------------
# توابع کمکی
# -----------------------------------------------------------
# فقط یک تابع داشته باشید
def convert_jalali_to_gregorian(jalali_date_str: str) -> str:
    """تبدیل تاریخ شمسی به میلادی"""
    try:
        if '/' in jalali_date_str:
            parts = jalali_date_str.split('/')
            if len(parts) == 3:
                year, month, day = map(int, parts)
                # تبدیل تاریخ شمسی به میلادی
                jdate = jdatetime.date(year, month, day)
                gdate = jdate.togregorian()
                return gdate.strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"❌ خطا در تبدیل تاریخ {jalali_date_str}: {e}")
    
    # در صورت خطا، تاریخ امروز را برگردان
    return get_db_date()
def generate_coupon_code(user_id: Optional[int] = None) -> str:
    """تولید کد کوپن یکتا"""
    import random
    import string
    import time
    
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    if user_id:
        return f"FT{user_id:09d}{timestamp % 10000:04d}{random_str}"
    else:
        return f"FT{timestamp % 10000:04d}{random_str}"

def create_coupon(user_id: int, source: str, receipt_image: str = None) -> Optional[Dict]:
    """ایجاد کوپن جدید"""
    try:
        date_str, time_str = get_iran_time()
        coupon_code = generate_coupon_code(user_id)
        
        logger.info(f"🔍 در حال ایجاد کوپن برای کاربر {user_id}")
        logger.info(f"🎫 کد کوپن: {coupon_code}")
        logger.info(f"🏷️ منبع: {source}")
        logger.info(f"📅 تاریخ: {date_str}")
        logger.info(f"📸 فیش: {receipt_image}")
        
        query = """
        INSERT INTO coupons (user_id, coupon_code, coupon_source, value, earned_date, 
                           purchase_receipt, status, verified_by_admin)
        VALUES (%s, %s, %s, %s, %s, %s, 'active', TRUE)
        RETURNING coupon_id, coupon_code, earned_date, value
        """
        
        logger.info(f"🔍 اجرای کوئری INSERT برای کوپن...")
        result = db.execute_query(query, (user_id, coupon_code, source, 400000, date_str, receipt_image), fetch=True)
        
        if result:
            coupon_data = {
                "coupon_id": result[0],
                "coupon_code": result[1],
                "earned_date": result[2],
                "value": result[3] if len(result) > 3 else 400000,
                "source": source
            }
            
            logger.info(f"✅ کوپن ایجاد شد: {coupon_data}")
            
            # 🔍 تأیید ذخیره‌سازی
            query_check = """
            SELECT coupon_id, coupon_code, value, status 
            FROM coupons 
            WHERE coupon_id = %s
            """
            check_result = db.execute_query(query_check, (result[0],), fetch=True)
            
            if check_result:
                logger.info(f"✅ تأیید ذخیره‌سازی کوپن در دیتابیس:")
                logger.info(f"   🆔 ID: {check_result[0]}")
                logger.info(f"   🎫 کد: {check_result[1]}")
                logger.info(f"   💰 ارزش: {check_result[2]}")
                logger.info(f"   ✅ وضعیت: {check_result[3]}")
            else:
                logger.error(f"❌ کوپن در دیتابیس یافت نشد!")
            
            return coupon_data
        
        logger.error("❌ هیچ نتیجه‌ای از INSERT کوپن برگشت داده نشد")
        return None
        
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد کوپن: {e}", exc_info=True)
        return None


def get_user_coupons(user_id: int, status: str = "active") -> List[Dict]:
    """دریافت کوپن‌های کاربر"""
    try:
        logger.info(f"🔍 دریافت کوپن‌های کاربر {user_id} با وضعیت '{status}'")
        
        query = """
        SELECT coupon_id, coupon_code, coupon_source, value, status, 
               earned_date, used_date, used_for
        FROM coupons
        WHERE user_id = %s AND status = %s
        ORDER BY earned_date DESC
        """
        
        results = db.execute_query(query, (user_id, status), fetchall=True)
        
        logger.info(f"🔍 تعداد کوپن‌های یافت شده: {len(results) if results else 0}")
        
        coupons = []
        if results:
            for row in results:
                coupons.append({
                    "coupon_id": row[0],
                    "coupon_code": row[1],
                    "source": row[2],
                    "value": row[3],
                    "status": row[4],
                    "earned_date": row[5],
                    "used_date": row[6],
                    "used_for": row[7]
                })
                logger.info(f"  🎫 {row[1]} - {row[2]} - {row[3]} ریال")
        
        return coupons
        
    except Exception as e:
        logger.error(f"❌ خطا در دریافت کوپن‌های کاربر: {e}", exc_info=True)
        return []

def get_coupon_by_code(coupon_code: str) -> Optional[Dict]:
    """دریافت اطلاعات کوپن بر اساس کد"""
    try:
        query = """
        SELECT coupon_id, user_id, coupon_code, coupon_source, value, 
               status, earned_date, used_date, used_for
        FROM coupons
        WHERE coupon_code = %s
        """
        
        result = db.execute_query(query, (coupon_code,), fetch=True)
        
        if result:
            return {
                "coupon_id": result[0],
                "user_id": result[1],
                "coupon_code": result[2],
                "source": result[3],
                "value": result[4],
                "status": result[5],
                "earned_date": result[6],
                "used_date": result[7],
                "used_for": result[8]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"خطا در دریافت کوپن: {e}")
        return None


def use_coupon(coupon_code: str, service_type: str) -> bool:
    """استفاده از کوپن برای یک خدمت"""
    try:
        date_str, time_str = get_iran_time()
        
        query = """
        UPDATE coupons
        SET status = 'used', used_date = %s, used_for = %s
        WHERE coupon_code = %s AND status = 'active'
        """
        
        rows_updated = db.execute_query(query, (date_str, service_type, coupon_code))
        
        logger.info(f"🔍 استفاده از کوپن {coupon_code}: {rows_updated} ردیف به‌روزرسانی شد")
        
        return rows_updated > 0
        
    except Exception as e:
        logger.error(f"❌ خطا در استفاده از کوپن {coupon_code}: {e}")
        return False

def create_coupon_request(user_id: int, request_type: str, service_type: str = None, 
                         amount: int = None, receipt_image: str = None) -> Optional[Dict]:
    """ایجاد درخواست جدید کوپن"""
    conn = None
    cursor = None
    try:
        logger.info(f"🔍 ایجاد درخواست کوپن برای کاربر {user_id}")
        logger.info(f"📋 نوع: {request_type}, خدمت: {service_type}, مبلغ: {amount}")
        
        # استفاده مستقیم از connection (نه از execute_query)
        conn = db.get_connection()
        cursor = conn.cursor()
        
        logger.info(f"✅ Connection دریافت شد")
        
        query = """
        INSERT INTO coupon_requests (user_id, request_type, service_type, amount, receipt_image, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        RETURNING request_id, created_at
        """
        
        params = (user_id, request_type, service_type, amount, receipt_image)
        logger.info(f"🔍 اجرای INSERT با پارامترها: {params}")
        
        cursor.execute(query, params)
        
        result = cursor.fetchone()
        logger.info(f"🔍 نتیجه fetchone: {result}")
        
        if result:
            request_id, created_at = result
            logger.info(f"✅ INSERT موفق - درخواست #{request_id}")
            
            # حتماً commit کن
            conn.commit()
            logger.info(f"✅ Commit انجام شد برای درخواست #{request_id}")
            
            # فوراً بررسی کن که ذخیره شده
            cursor.execute("SELECT request_id FROM coupon_requests WHERE request_id = %s", (request_id,))
            verify = cursor.fetchone()
            logger.info(f"🔍 تأیید ذخیره‌سازی: {verify}")
            
            return {
                "request_id": request_id,
                "created_at": created_at
            }
        else:
            logger.error("❌ هیچ نتیجه‌ای از INSERT برگشت داده نشد")
            conn.rollback()
            return None
        
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد درخواست کوپن: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return None
        
    finally:
        if cursor:
            cursor.close()
            logger.info("🔒 Cursor بسته شد")
        if conn:
            db.return_connection(conn)
            logger.info("🔌 Connection بازگردانده شد")
def test_execute_query_directly():
    """تست مستقیم تابع execute_query"""
    try:
        logger.info("🧪 تست مستقیم execute_query...")
        
        # تست 1: INSERT ساده
        query = """
        INSERT INTO coupon_requests (user_id, request_type, amount, status)
        VALUES (999888777, 'test_execute', 5000, 'pending')
        RETURNING request_id
        """
        
        result = db.execute_query(query, fetch=True)
        logger.info(f"🔍 نتیجه execute_query: {result}")
        
        # تست 2: SELECT برای بررسی
        if result:
            query_select = "SELECT * FROM coupon_requests WHERE request_id = %s"
            select_result = db.execute_query(query_select, (result[0],), fetch=True)
            logger.info(f"🔍 نتیجه SELECT پس از INSERT: {select_result}")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ خطا در تست execute_query: {e}", exc_info=True)
        return None

async def debug_all_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش همه درخواست‌های کوپن"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    try:
        query = """
        SELECT request_id, user_id, request_type, service_type, 
               amount, status, created_at, admin_note, receipt_image
        FROM coupon_requests
        ORDER BY request_id DESC
        LIMIT 20
        """
        
        results = db.execute_query(query, fetchall=True)
        
        if not results:
            await update.message.reply_text("🔭 هیچ درخواست کوپنی وجود ندارد.")
            return
        
        text = "📋 **همه درخواست‌های کوپن**\n\n"
        
        for row in results:
            request_id, user_id_db, request_type, service_type, amount, status, created_at, admin_note, receipt_image = row
            
            text += f"🆔 **#{request_id}**\n"
            text += f"👤 کاربر: {user_id_db}\n"
            text += f"📋 نوع: {request_type}\n"
            text += f"💰 مبلغ: {amount or 0:,} تومان\n"
            text += f"✅ وضعیت: **{status}**\n"
            text += f"🖼️ فیش: {'✅ دارد' if receipt_image else '❌ ندارد'}\n"
            text += f"📅 تاریخ: {created_at.strftime('%Y/%m/%d %H:%M') if isinstance(created_at, datetime) else created_at}\n"
            
            if admin_note:
                text += f"📝 یادداشت: {admin_note[:50]}...\n" if len(admin_note) > 50 else f"📝 یادداشت: {admin_note}\n"
            
            text += f"🔧 دستور تأیید: `/verify_coupon {request_id}`\n"
            text += "─" * 20 + "\n"
        
        # اگر متن خیلی طولانی شد، به چند بخش تقسیم کن
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"خطا در نمایش همه درخواست‌ها: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}")
def get_pending_coupon_requests() -> List[Dict]:
    """دریافت درخواست‌های کوپن در انتظار"""
    try:
        query = """
        SELECT cr.request_id, cr.user_id, cr.request_type, cr.service_type, 
               cr.amount, cr.receipt_image, cr.created_at, u.username
        FROM coupon_requests cr
        JOIN users u ON cr.user_id = u.user_id
        WHERE cr.status = 'pending'
        ORDER BY cr.created_at DESC
        """
        
        results = db.execute_query(query, fetchall=True)
        
        requests = []
        if results:
            for row in results:
                requests.append({
                    "request_id": row[0],
                    "user_id": row[1],
                    "request_type": row[2],
                    "service_type": row[3],
                    "amount": row[4],
                    "receipt_image": row[5],
                    "created_at": row[6],
                    "username": row[7]
                })
        
        return requests
        
    except Exception as e:
        logger.error(f"خطا در دریافت درخواست‌های کوپن: {e}")
        return []


def approve_coupon_request(request_id: int, admin_note: str = "") -> bool:
    """تأیید درخواست کوپن"""
    conn = None
    cursor = None
    
    try:
        logger.info(f"🔍 شروع تأیید درخواست کوپن #{request_id}")
        
        # استفاده مستقیم از connection برای کنترل بهتر
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # دریافت اطلاعات درخواست
        query = """
        SELECT user_id, request_type, amount, receipt_image, status
        FROM coupon_requests
        WHERE request_id = %s
        """
        
        cursor.execute(query, (request_id,))
        request = cursor.fetchone()
        
        if not request:
            logger.error(f"❌ درخواست #{request_id} یافت نشد")
            return False
        
        user_id, request_type, amount, receipt_image, current_status = request
        logger.info(f"🔍 درخواست #{request_id} یافت شد: کاربر={user_id}, نوع={request_type}, وضعیت={current_status}")
        
        # بررسی وضعیت درخواست
        if current_status not in ['pending']:
            logger.error(f"❌ درخواست #{request_id} در وضعیت '{current_status}' است و قابل تأیید نیست")
            return False
        
        # ایجاد کوپن برای کاربر
        if request_type == "purchase":
            logger.info(f"🔍 ایجاد کوپن برای کاربر {user_id}")
            
            # ایجاد کوپن با connection یکسان
            date_str, time_str = get_iran_time()
            coupon_code = generate_coupon_code(user_id)
            
            logger.info(f"🎫 کد کوپن: {coupon_code}")
            logger.info(f"🏷️ منبع: purchased")
            
            # INSERT کوپن
            query_coupon = """
            INSERT INTO coupons (user_id, coupon_code, coupon_source, value, earned_date, 
                               purchase_receipt, status, verified_by_admin)
            VALUES (%s, %s, %s, %s, %s, %s, 'active', TRUE)
            RETURNING coupon_id, coupon_code, earned_date, value
            """
            
            cursor.execute(query_coupon, (user_id, coupon_code, "purchased", 400000, date_str, receipt_image))
            coupon_result = cursor.fetchone()
            
            if not coupon_result:
                logger.error(f"❌ خطا در ایجاد کوپن برای کاربر {user_id}")
                conn.rollback()
                return False
            
            coupon_id, coupon_code, earned_date, value = coupon_result
            logger.info(f"✅ کوپن ایجاد شد: {coupon_code} (ID: {coupon_id})")
            
            # بروزرسانی وضعیت درخواست
            query_update = """
            UPDATE coupon_requests
            SET status = 'approved', admin_note = %s
            WHERE request_id = %s
            """
            cursor.execute(query_update, (admin_note, request_id))
            
            # commit تمام تغییرات
            conn.commit()
            logger.info(f"✅ درخواست #{request_id} و کوپن {coupon_code} تأیید و ذخیره شد")
            
            # تأیید نهایی: بررسی کوپن در دیتابیس
            cursor.execute("SELECT coupon_code, status FROM coupons WHERE coupon_id = %s", (coupon_id,))
            verify = cursor.fetchone()
            if verify:
                logger.info(f"✅ تأیید نهایی: کوپن {verify[0]} با وضعیت {verify[1]} در دیتابیس ذخیره شد")
            else:
                logger.error(f"❌ کوپن {coupon_code} در دیتابیس یافت نشد!")
            
            # ایجاد پیام برای کاربر
            coupon_data = {
                "coupon_id": coupon_id,
                "coupon_code": coupon_code,
                "earned_date": earned_date,
                "value": value
            }
            
            return True
        
        logger.error(f"❌ نوع درخواست نامعتبر: {request_type}")
        return False
        
    except Exception as e:
        logger.error(f"❌ خطا در تأیید درخواست کوپن: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)

# -----------------------------------------------------------
# 3. توابع جدید برای مدیریت تنظیمات
# -----------------------------------------------------------

def get_admin_card_info() -> Dict:
    """دریافت اطلاعات کارت ادمین"""
    try:
        query = """
        SELECT setting_value FROM system_settings
        WHERE setting_key = 'admin_card_info'
        """
        
        result = db.execute_query(query, fetch=True)
        
        if result and result[0]:
            return json.loads(result[0])
        
        # اطلاعات پیش‌فرض
        return {
            "card_number": "۶۰۳۷-۹۹۹۹-۱۲۳۴-۵۶۷۸",
            "card_owner": "علی محمدی"
        }
        
    except Exception as e:
        logger.error(f"خطا در دریافت اطلاعات کارت: {e}")
        return {
            "card_number": "۶۰۳۷-۹۹۹۹-۱۲۳۴-۵۶۷۸",
            "card_owner": "علی محمدی"
        }

def set_admin_card_info(card_number: str, card_owner: str) -> bool:
    """ذخیره اطلاعات کارت ادمین"""
    try:
        card_info = json.dumps({
            "card_number": card_number,
            "card_owner": card_owner,
            "updated_at": datetime.now(IRAN_TZ).strftime("%Y/%m/%d %H:%M")
        })
        
        query = """
        INSERT INTO system_settings (setting_key, setting_value, description)
        VALUES ('admin_card_info', %s, 'شماره کارت و نام صاحب حساب ادمین')
        ON CONFLICT (setting_key) DO UPDATE SET
            setting_value = EXCLUDED.setting_value,
            updated_at = CURRENT_TIMESTAMP
        """
        
        db.execute_query(query, (card_info,))
        
        logger.info(f"✅ اطلاعات کارت ادمین به‌روزرسانی شد: {card_number}")
        return True
        
    except Exception as e:
        logger.error(f"خطا در ذخیره اطلاعات کارت: {e}")
        return False

def initialize_default_settings():
    """مقداردهی اولیه تنظیمات سیستم"""
    try:
        # کارت ادمین
        if not get_admin_card_info().get("card_number"):
            set_admin_card_info("۶۰۳۷-۹۹۹۹-۱۲۳۴-۵۶۷۸", "علی محمدی")
        
        logger.info("✅ تنظیمات پیش‌فرض سیستم مقداردهی شد")
        
    except Exception as e:
        logger.error(f"خطا در مقداردهی تنظیمات: {e}")

# -----------------------------------------------------------
# 4. توابع جدید برای سیستم کسب خودکار کوپن
# -----------------------------------------------------------


def check_study_streak(user_id: int) -> Optional[Dict]:
    """بررسی استرک مطالعه کاربر برای کسب کوپن"""
    try:
        now = datetime.now(IRAN_TZ)
        today_str = now.strftime("%Y-%m-%d")  # فرمت: 2025-12-26
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(f"🔍 بررسی استرک - تاریخ امروز: {today_str}")
        logger.info(f"🔍 بررسی استرک - تاریخ دیروز: {yesterday_str}")
        
        # دریافت آمار مطالعه از daily_rankings
        query_yesterday = """
        SELECT total_minutes FROM daily_rankings
        WHERE user_id = %s AND date = %s
        """
        yesterday_result = db.execute_query(query_yesterday, (user_id, yesterday_str), fetch=True)
        yesterday_minutes = yesterday_result[0] if yesterday_result else 0
        
        query_today = """
        SELECT total_minutes FROM daily_rankings
        WHERE user_id = %s AND date = %s
        """
        today_result = db.execute_query(query_today, (user_id, today_str), fetch=True)
        today_minutes = today_result[0] if today_result else 0
        
        logger.info(f"🔍 بررسی استرک برای کاربر {user_id}:")
        logger.info(f"  دیروز ({yesterday_str}): {yesterday_minutes} دقیقه")
        logger.info(f"  امروز ({today_str}): {today_minutes} دقیقه")
        
        # شرط کسب کوپن: هر روز حداقل ۶ ساعت (۳۶۰ دقیقه)
        if yesterday_minutes >= 360 and today_minutes >= 360:
            # بررسی نکرده باشد قبلاً برای این دوره کوپن گرفته
            query_check = """
            SELECT streak_id FROM user_study_streaks
            WHERE user_id = %s AND end_date = %s AND earned_coupon = TRUE
            """
            already_earned = db.execute_query(query_check, (user_id, today_str), fetch=True)
            
            if not already_earned:
                # ایجاد استرک
                query_streak = """
                INSERT INTO user_study_streaks (user_id, start_date, end_date, 
                                              total_hours, days_count, earned_coupon)
                VALUES (%s, %s, %s, %s, %s, FALSE)
                RETURNING streak_id
                """
                
                total_hours = (yesterday_minutes + today_minutes) // 60
                streak_result = db.execute_query(query_streak, 
                    (user_id, yesterday_str, today_str, total_hours, 2), fetch=True)
                
                if streak_result:
                    streak_id = streak_result[0]
                    logger.info(f"✅ استرک واجد شرایط ایجاد شد: ID={streak_id}")
                    return {
                        "eligible": True,
                        "yesterday_minutes": yesterday_minutes,
                        "today_minutes": today_minutes,
                        "total_hours": total_hours,
                        "streak_id": streak_id
                    }
        
        return {
            "eligible": False,
            "yesterday_minutes": yesterday_minutes,
            "today_minutes": today_minutes
        }
        
    except Exception as e:
        logger.error(f"خطا در بررسی استرک مطالعه: {e}", exc_info=True)
        return None

def award_streak_coupon(user_id: int, streak_id: int) -> Optional[Dict]:
    """اعطای کوپن به کاربر برای استرک مطالعه"""
    try:
        # ایجاد کوپن
        coupon = create_coupon(user_id, "study_streak")
        
        if not coupon:
            return None
        
        # بروزرسانی استرک
        query = """
        UPDATE user_study_streaks
        SET earned_coupon = TRUE, coupon_id = %s
        WHERE streak_id = %s
        """
        db.execute_query(query, (coupon["coupon_id"], streak_id))
        
        return coupon
        
    except Exception as e:
        logger.error(f"خطا در اعطای کوپن استرک: {e}")
        return None








def get_coupon_main_keyboard() -> ReplyKeyboardMarkup:
    """
    منوی اصلی کوپن با استفاده از style مجاز در Bot API 9.4
    (primary, success, danger)
    """
    keyboard = [
        [
            {"text": "📞 تماس تلفنی"},
            {"text": "📊 تحلیل گزارش", "style": "primary"},
        ],
        [
            {"text": "✏️ تصحیح آزمون"},
            {"text": "📝 آزمون شخصی", "style": "success"},
        ],
        [
            {"text": "📈 تحلیل آزمون"},
            {"text": "🔗 برنامه شخصی"},
        ],
        [
            {"text": "🎫 کوپن‌های من"},
            {"text": "🛒 خرید کوپن", "style": "primary"},
        ],
        [
            {"text": "🔙 بازگشت", "style": "danger"},
        ]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="یکی از گزینه‌ها را انتخاب کنید..."
    )

def get_coupon_method_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد روش‌های کسب کوپن"""
    keyboard = [
        ["⏰ کسب از مطالعه", "💳 خرید کوپن"],
        ["🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_coupon_services_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد خدمات کوپن"""
    keyboard = [
        ["📞 تماس تلفنی (۱ کوپن)", "📊 تحلیل گزارش (۱ کوپن)"],
        ["✏️ تصحیح آزمون (۱ کوپن)", "📈 تحلیل آزمون (۱ کوپن)"],
        ["📝 آزمون شخصی (۲ کوپن)", "🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_coupon_management_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد مدیریت کوپن برای کاربر"""
    keyboard = [
        ["🎫 کوپن‌های فعال", "📋 درخواست‌های من"],
        ["🛒 خرید کوپن جدید", "🏠 منوی اصلی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_admin_coupon_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد مدیریت کوپن برای ادمین"""
    keyboard = [
        ["📋 درخواست‌های کوپن", "🏦 تغییر کارت"],
        ["📊 آمار کوپن‌ها", "🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_start_of_week() -> str:
    """دریافت تاریخ شروع هفته (شنبه)"""
    today = datetime.now(IRAN_TZ)
    # در Python دوشنبه=0، یکشنبه=6. برای شنبه (آغاز هفته ایرانی) 5 روز کم می‌کنیم
    start_of_week = today - timedelta(days=(today.weekday() + 2) % 7)
    return start_of_week.strftime("%Y-%m-%d")

def get_weekly_rankings(limit: int = 50) -> List[Dict]:
    """دریافت رتبه‌بندی هفتگی"""
    try:
        week_start = get_start_of_week()
        
        query = """
        SELECT u.user_id, u.username, u.grade, u.field, 
               COALESCE(SUM(dr.total_minutes), 0) as weekly_total
        FROM users u
        LEFT JOIN daily_rankings dr ON u.user_id = dr.user_id AND dr.date >= %s
        WHERE u.is_active = TRUE
        GROUP BY u.user_id, u.username, u.grade, u.field
        ORDER BY weekly_total DESC
        LIMIT %s
        """
        
        results = db.execute_query(query, (week_start, limit), fetchall=True)
        
        rankings = []
        for row in results:
            rankings.append({
                "user_id": row[0],
                "username": row[1],
                "grade": row[2],
                "field": row[3],
                "total_minutes": row[4] or 0
            })
        
        # به‌روزرسانی رتبه در دیتابیس
        for i, rank in enumerate(rankings, 1):
            query = """
            INSERT INTO weekly_rankings (user_id, week_start_date, total_minutes, rank)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, week_start_date) DO UPDATE SET
                total_minutes = EXCLUDED.total_minutes,
                rank = EXCLUDED.rank
            """
            db.execute_query(query, (rank["user_id"], week_start, rank["total_minutes"], i))
        
        return rankings
        
    except Exception as e:
        logger.error(f"خطا در دریافت رتبه‌بندی هفتگی: {e}")
        return []

def get_user_weekly_rank(user_id: int) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """دریافت رتبه، زمان و فاصله با نفرات برتر هفتگی"""
    try:
        week_start = get_start_of_week()
        
        # دریافت رتبه‌بندی کامل هفتگی
        rankings = get_weekly_rankings(limit=100)
        
        # یافتن کاربر در رتبه‌بندی
        user_rank = None
        user_minutes = 0
        
        for i, rank in enumerate(rankings, 1):
            if rank["user_id"] == user_id:
                user_rank = i
                user_minutes = rank["total_minutes"]
                break
        
        if not user_rank:
            # اگر کاربر در رتبه‌بندی نیست
            query = """
            SELECT COALESCE(SUM(total_minutes), 0)
            FROM daily_rankings
            WHERE user_id = %s AND date >= %s
            """
            result = db.execute_query(query, (user_id, week_start), fetch=True)
            user_minutes = result[0] if result else 0
            
            # محاسبه رتبه تخمینی
            query = """
            SELECT COUNT(DISTINCT user_id) + 1
            FROM daily_rankings
            WHERE date >= %s 
            AND COALESCE(SUM(total_minutes), 0) > %s
            GROUP BY user_id
            """
            result = db.execute_query(query, (week_start, user_minutes), fetch=True)
            user_rank = result[0] if result else len(rankings) + 1
        
        # محاسبه فاصله با نفر پنجم
        gap_minutes = 0
        if user_rank > 5 and len(rankings) >= 5:
            fifth_minutes = rankings[4]["total_minutes"]  # ایندکس 4 = نفر پنجم
            gap_minutes = fifth_minutes - user_minutes
            gap_minutes = max(0, gap_minutes)
        
        return user_rank, user_minutes, gap_minutes
        
    except Exception as e:
        logger.error(f"خطا در محاسبه رتبه هفتگی: {e}")
        return None, 0, 0

def get_inactive_users_for_offer() -> List[Dict]:
    """دریافت کاربرانی که ۴ روز است مطالعه نکرده‌اند و در ۴ روز گذشته پیشنهاد دریافت نکرده‌اند"""
    try:
        now = datetime.now(IRAN_TZ)
        four_days_ago = now - timedelta(days=4)
        four_days_ago_str = four_days_ago.strftime("%Y-%m-%d")
        
        # کاربرانی که در ۴ روز گذشته مطالعه نداشته‌اند
        query = """
        SELECT DISTINCT u.user_id, u.username, u.grade, u.field
        FROM users u
        LEFT JOIN study_sessions ss ON u.user_id = ss.user_id 
            AND ss.completed = TRUE 
            AND ss.start_time >= %s
        WHERE u.is_active = TRUE 
            AND ss.session_id IS NULL
            AND u.user_id NOT IN (
                SELECT user_id FROM user_offers 
                WHERE offer_date >= %s
            )
        ORDER BY RANDOM()
        LIMIT 20
        """
        
        # تبدیل timestamp
        four_days_ago_timestamp = int(four_days_ago.timestamp())
        
        results = db.execute_query(query, (four_days_ago_timestamp, four_days_ago_str), fetchall=True)
        
        users = []
        for row in results:
            users.append({
                "user_id": row[0],
                "username": row[1],
                "grade": row[2],
                "field": row[3]
            })
        
        logger.info(f"📊 {len(users)} کاربر بدون مطالعه در ۴ روز گذشته پیدا شد")
        return users
        
    except Exception as e:
        logger.error(f"خطا در دریافت کاربران بدون مطالعه: {e}")
        return []

def mark_offer_sent(user_id: int) -> bool:
    """علامت‌گذاری ارسال پیشنهاد به کاربر"""
    try:
        now = datetime.now(IRAN_TZ)
        date_str = now.strftime("%Y-%m-%d")
        
        # ایجاد جدول اگر وجود ندارد
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_offers (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            offer_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, offer_date)
        )
        """)
        conn.commit()
        
        cursor.close()
        db.return_connection(conn)
        
        # ثبت ارسال پیشنهاد
        query = """
        INSERT INTO user_offers (user_id, offer_date)
        VALUES (%s, %s)
        ON CONFLICT (user_id, offer_date) DO NOTHING
        """
        
        db.execute_query(query, (user_id, date_str))
        return True
        
    except Exception as e:
        logger.error(f"خطا در علامت‌گذاری پیشنهاد: {e}")
        return False

async def send_random_offer_to_inactive(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال پیشنهاد رندوم به کاربران بدون مطالعه (هر ۴ روز یکبار)"""
    try:
        logger.info("🎁 شروع ارسال پیشنهاد به کاربران بدون مطالعه...")
        
        # دریافت کاربران واجد شرایط
        inactive_users = get_inactive_users_for_offer()
        
        if not inactive_users:
            logger.info("📭 هیچ کاربر واجد شرایطی برای دریافت پیشنهاد وجود ندارد")
            return
        
        # انتخاب حداکثر ۱۰ کاربر به صورت رندوم
        import random
        selected_users = random.sample(inactive_users, min(10, len(inactive_users)))
        
        total_sent = 0
        
        for user in selected_users:
            try:
                # متن‌های مختلف پیشنهاد
                offer_messages = [
                    "🎁 <b>پیشنهاد ویژه برای شما!</b>\n\n"
                    "سلام! ۴ روزه که مطالعه نکردی...\n\n"
                    "🔥 اگه همین امروز یک جلسه مطالعه ثبت کنی:\n"
                    "✅ <b>یک نیم‌کوپن ۲۰,۰۰۰ تومانی هدیه می‌گیری!</b>\n"
                    "🎯 شانس برنده شدن در قرعه‌کشی هفتگی\n"
                    "📈 رتبه‌ات در جدول هفتگی بهبود پیدا می‌کنه\n\n"
                    "💪 <b>همین الان شروع کن!</b>",
                    
                    "🔥 <b>یک فرصت طلایی!</b>\n\n"
                    "۴ روز گذشته و هنوز مطالعه‌ای ثبت نکردی...\n\n"
                    "💰 <b>ثبت مطالعه امروز = ۲۰,۰۰۰ تومان جایزه!</b>\n\n"
                    "✅ کافیه فقط ۳۰ دقیقه مطالعه کنی و:\n"
                    "• نیم‌کوپن ۲۰,۰۰۰ تومانی بگیری\n"
                    "• در قرعه‌کشی هفتگی شرکت کنی\n"
                    "• رتبه‌ات رو تو جدول هفتگی بالا ببری\n\n"
                    "🎯 <b>فرصت رو از دست نده!</b>",
                    
                    "💎 <b>یک خبر خوب!</b>\n\n"
                    "ما ۴ روزه تو رو ندیدیم... دلتنگ شدیم!\n\n"
                    "🎁 <b>یک هدیه ویژه برای بازگشت تو:</b>\n"
                    "• نیم‌کوپن ۲۰,۰۰۰ تومانی\n"
                    "• شرکت در قرعه‌کشی هفتگی\n"
                    "• شانس قرار گرفتن در جمع برترها\n\n"
                    "📊 آمار کاربرانی که امروز مطالعه کردن:\n"
                    "• ۷۰٪ حداقل ۶۰ دقیقه مطالعه کردن\n"
                    "• ۳۰٪ جایگاهشون تو جدول هفتگی بهتر شده\n\n"
                    "🏆 <b>تو هم می‌تونی یکی از اونا باشی!</b>"
                ]
                
                message = random.choice(offer_messages)
                
                # ارسال پیام
                await context.bot.send_message(
                    user["user_id"],
                    message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_main_menu_keyboard()
                )
                
                # علامت‌گذاری ارسال شده
                mark_offer_sent(user["user_id"])
                total_sent += 1
                
                logger.info(f"✅ پیشنهاد به کاربر {user['user_id']} ارسال شد")
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                if "Forbidden: bot was blocked by the user" in str(e):
                    logger.warning(f"🚫 کاربر {user['user_id']} ربات رو بلاک کرده")
                else:
                    logger.error(f"❌ خطا در ارسال پیشنهاد به کاربر {user['user_id']}: {e}")
                continue
        
        logger.info(f"🎁 پیشنهاد به {total_sent} کاربر ارسال شد")
        
    except Exception as e:
        logger.error(f"خطا در ارسال پیشنهاد: {e}", exc_info=True)


def create_coupon_for_user(user_id: int, study_session_id: int = None) -> Optional[Dict]:
    """ایجاد کوپن پاداش برای کاربر"""
    try:
        date_str, _ = get_iran_time()
        
        # تاریخ انقضا (۷ روز بعد)
        expires_date = (datetime.now(IRAN_TZ) + timedelta(days=7)).strftime("%Y-%m-%d")
        
        coupon_code = generate_coupon_code(user_id)
        query = """
        INSERT INTO reward_coupons (user_id, coupon_code, value, study_session_id, created_date, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING coupon_id, coupon_code, created_date
        """
        
        result = db.execute_query(query, (user_id, coupon_code, 20000, study_session_id, date_str, expires_date), fetch=True)
        
        if result:
            return {
                "coupon_id": result[0],
                "coupon_code": result[1],
                "created_date": result[2],
                "value": 20000
            }
        
        return None
        
    except Exception as e:
        logger.error(f"خطا در ایجاد کوپن: {e}")
        return None

def get_today_sessions(user_id: int) -> List[Dict]:
    """دریافت جلسات امروز کاربر"""
    try:
        date_str = datetime.now(IRAN_TZ).strftime("%Y/%m/%d")
        
        query = """
        SELECT session_id, subject, topic, minutes, 
               TO_TIMESTAMP(start_time) as start_time
        FROM study_sessions
        WHERE user_id = %s AND date = %s AND completed = TRUE
        ORDER BY start_time
        """
        
        results = db.execute_query(query, (user_id, date_str), fetchall=True)
        
        sessions = []
        for row in results:
            sessions.append({
                "session_id": row[0],
                "subject": row[1],
                "topic": row[2],
                "minutes": row[3],
                "start_time": row[4]
            })
        
        return sessions
        
    except Exception as e:
        logger.error(f"خطا در دریافت جلسات امروز: {e}", exc_info=True)
        return []
async def check_my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی آمار مطالعه کاربر"""
    user_id = update.effective_user.id
    
    try:
        date_str = datetime.now(IRAN_TZ).strftime("%Y/%m/%d")
        yesterday = (datetime.now(IRAN_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # آمار امروز از daily_rankings
        query_today = """
        SELECT total_minutes FROM daily_rankings
        WHERE user_id = %s AND date = %s
        """
        today_stats = db.execute_query(query_today, (user_id, date_str), fetch=True)
        today_minutes = today_stats[0] if today_stats else 0
        
        # آمار امروز از study_sessions
        query_sessions = """
        SELECT COUNT(*) as sessions, COALESCE(SUM(minutes), 0) as total
        FROM study_sessions
        WHERE user_id = %s AND date = %s AND completed = TRUE
        """
        sessions_stats = db.execute_query(query_sessions, (user_id, date_str), fetch=True)
        sessions_count = sessions_stats[0] if sessions_stats else 0
        sessions_total = sessions_stats[1] if sessions_stats else 0
        
        # آمار دیروز
        query_yesterday = """
        SELECT total_minutes FROM daily_rankings
        WHERE user_id = %s AND date = %s
        """
        yesterday_stats = db.execute_query(query_yesterday, (user_id, yesterday), fetch=True)
        yesterday_minutes = yesterday_stats[0] if yesterday_stats else 0
        
        text = f"""
🔍 **آمار مطالعه شما**

📅 **امروز ({date_str}):**
• از daily_rankings: {today_minutes} دقیقه
• از study_sessions: {sessions_total} دقیقه ({sessions_count} جلسه)

📅 **دیروز ({yesterday}):**
• مطالعه: {yesterday_minutes} دقیقه

📊 **تست سیستم کسب کوپن:**
• دیروز: {yesterday_minutes} دقیقه (نیاز: 360+)
• امروز: {today_minutes} دقیقه (نیاز: 360+)
• واجد شرایط: {"✅ بله" if yesterday_minutes >= 360 and today_minutes >= 360 else "❌ خیر"}
"""
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"خطا در بررسی آمار: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")


def mark_report_sent(user_id: int, report_type: str) -> bool:
    """علامت‌گذاری ارسال گزارش (midday/night)"""
    try:
        date_str, _ = get_iran_time()
        
        if report_type == "midday":
            field = "received_midday_report"
        elif report_type == "night":
            field = "received_night_report"
        else:
            return False
        
        query = f"""
        INSERT INTO user_activities (user_id, date, {field})
        VALUES (%s, %s, TRUE)
        ON CONFLICT (user_id, date) DO UPDATE SET
            {field} = TRUE
        """
        
        db.execute_query(query, (user_id, date_str))
        return True
        
    except Exception as e:
        logger.error(f"خطا در علامت‌گذاری گزارش: {e}")
        return False
def get_grade_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد انتخاب پایه تحصیلی"""
    keyboard = [
        [KeyboardButton("دهم")],
        [KeyboardButton("یازدهم")],
        [KeyboardButton("دوازدهم")],
        [KeyboardButton("فارغ‌التحصیل")],
        [KeyboardButton("دانشجو")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_field_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد انتخاب رشته"""
    keyboard = [
        [KeyboardButton("ریاضی"), KeyboardButton("انسانی")],
        [KeyboardButton("تجربی"), KeyboardButton("سایر")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد لغو"""
    keyboard = [[KeyboardButton("❌ لغو ثبت‌نام")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_iran_time() -> Tuple[str, str]:
    """دریافت تاریخ و زمان ایران - تاریخ شمسی (برای نمایش)"""
    now = datetime.now(IRAN_TZ)
    
    # تبدیل به تاریخ شمسی
    jdate = jdatetime.datetime.fromgregorian(datetime=now)
    
    # تاریخ شمسی (سال/ماه/روز) - برای نمایش
    date_str = jdate.strftime("%Y/%m/%d")
    
    # زمان
    time_str = now.strftime("%H:%M")
    
    return date_str, time_str

def get_db_date() -> str:
    """دریافت تاریخ برای دیتابیس (YYYY-MM-DD)"""
    now = datetime.now(IRAN_TZ)
    return now.strftime("%Y-%m-%d")
def format_time(minutes: int) -> str:
    """تبدیل دقیقه به فرمت خوانا"""
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0 and mins > 0:
        return f"{hours} ساعت و {mins} دقیقه"
    elif hours > 0:
        return f"{hours} ساعت"
    else:
        return f"{mins} دقیقه"

def calculate_score(minutes: int) -> int:
    """محاسبه امتیاز بر اساس زمان مطالعه"""
    return int(minutes * 1.5)

def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن کاربر"""
    return user_id in ADMIN_IDS

def validate_file_type(file_name: str) -> bool:
    """بررسی مجاز بودن نوع فایل"""
    allowed_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', 
                         '.xls', '.xlsx', '.txt', '.mp4', '.mp3',
                         '.jpg', '.jpeg', '.png', '.zip', '.rar']
    
    file_ext = os.path.splitext(file_name.lower())[1]
    return file_ext in allowed_extensions

def get_file_size_limit(file_name: str) -> int:
    """دریافت محدودیت حجم بر اساس نوع فایل"""
    return 500 * 1024 * 1024

# -----------------------------------------------------------
# مدیریت کاربران
# -----------------------------------------------------------

def register_user(user_id: int, username: str, grade: str, field: str, message: str = "") -> bool:
    """ثبت کاربر جدید در دیتابیس"""
    try:
        date_str, _ = get_iran_time()
        
        query = """
        INSERT INTO registration_requests (user_id, username, grade, field, message, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        """
        db.execute_query(query, (user_id, username, grade, field, message))
        
        logger.info(f"درخواست ثبت‌نام جدید: {username} ({user_id})")
        return True
        
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر: {e}")
        return False

def get_pending_requests() -> List[Dict]:
    """دریافت درخواست‌های ثبت‌نام در انتظار"""
    query = """
    SELECT request_id, user_id, username, grade, field, message, created_at
    FROM registration_requests
    WHERE status = 'pending'
    ORDER BY created_at DESC
    """
    
    results = db.execute_query(query, fetchall=True)
    
    requests = []
    if results:
        for row in results:
            requests.append({
                "request_id": row[0],
                "user_id": row[1],
                "username": row[2],
                "grade": row[3],
                "field": row[4],
                "message": row[5],
                "created_at": row[6]
            })
    
    return requests

def approve_registration(request_id: int, admin_note: str = "") -> bool:
    """تأیید درخواست ثبت‌نام"""
    try:
        query = """
        SELECT user_id, username, grade, field, message
        FROM registration_requests
        WHERE request_id = %s AND status = 'pending'
        """
        result = db.execute_query(query, (request_id,), fetch=True)
        
        if not result:
            return False
        
        user_id, username, grade, field, message = result
        
        date_str, _ = get_iran_time()
        query = """
        INSERT INTO users (user_id, username, grade, field, message, is_active, registration_date)
        VALUES (%s, %s, %s, %s, %s, TRUE, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            is_active = TRUE,
            grade = EXCLUDED.grade,
            field = EXCLUDED.field,
            message = EXCLUDED.message
        """
        db.execute_query(query, (user_id, username, grade, field, message, date_str))
        
        query = """
        UPDATE registration_requests
        SET status = 'approved', admin_note = %s
        WHERE request_id = %s
        """
        db.execute_query(query, (admin_note, request_id))
        
        logger.info(f"کاربر تأیید شد: {username} ({user_id})")
        return True
        
    except Exception as e:
        logger.error(f"خطا در تأیید کاربر: {e}")
        return False

def reject_registration(request_id: int, admin_note: str) -> bool:
    """رد درخواست ثبت‌نام"""
    try:
        query = """
        UPDATE registration_requests
        SET status = 'rejected', admin_note = %s
        WHERE request_id = %s AND status = 'pending'
        """
        db.execute_query(query, (admin_note, request_id))
        
        logger.info(f"درخواست رد شد: {request_id}")
        return True
        
    except Exception as e:
        logger.error(f"خطا در رد درخواست: {e}")
        return False

def activate_user(user_id: int) -> bool:
    """فعال‌سازی کاربر"""
    try:
        query = """
        UPDATE users
        SET is_active = TRUE
        WHERE user_id = %s
        """
        db.execute_query(query, (user_id,))
        
        logger.info(f"کاربر فعال شد: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"خطا در فعال‌سازی کاربر: {e}")
        return False

def deactivate_user(user_id: int) -> bool:
    """غیرفعال‌سازی کاربر"""
    try:
        query = """
        UPDATE users
        SET is_active = FALSE
        WHERE user_id = %s
        """
        db.execute_query(query, (user_id,))
        
        logger.info(f"کاربر غیرفعال شد: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"خطا در غیرفعال‌سازی کاربر: {e}")
        return False

def is_user_active(user_id: int) -> bool:
    """بررسی فعال بودن کاربر"""
    try:
        query = """
        SELECT is_active FROM users WHERE user_id = %s
        """
        result = db.execute_query(query, (user_id,), fetch=True)
        
        return result and result[0]
        
    except Exception as e:
        logger.error(f"خطا در بررسی وضعیت کاربر: {e}")
        return False

def get_user_info(user_id: int) -> Optional[Dict]:
    """دریافت اطلاعات کاربر"""
    try:
        query = """
        SELECT username, grade, field, total_study_time, total_sessions
        FROM users
        WHERE user_id = %s
        """
        result = db.execute_query(query, (user_id,), fetch=True)
        
        if result:
            return {
                "username": result[0],
                "grade": result[1],
                "field": result[2],
                "total_study_time": result[3],
                "total_sessions": result[4]
            }
        return None
        
    except Exception as e:
        logger.error(f"خطا در دریافت اطلاعات کاربر: {e}")
        return None

async def send_to_all_users(context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    """ارسال پیام به همه کاربران"""
    query = """
    SELECT user_id FROM registration_requests
    UNION
    SELECT user_id FROM users
    """
    results = db.execute_query(query, fetchall=True)
    
    if not results:
        return
    
    users = [row[0] for row in results]
    successful = 0
    
    for user_id in users:
        try:
            await context.bot.send_message(
                user_id,
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            successful += 1
            
            await asyncio.sleep(0.05)
            
        except Exception as e:
            logger.error(f"خطا در ارسال به کاربر {user_id}: {e}")
    
    logger.info(f"✅ پیام به {successful}/{len(users)} کاربر ارسال شد")

async def send_daily_top_ranks(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال ۳ رتبه برتر روز به همه کاربران"""
    rankings = get_today_rankings()
    date_str = datetime.now(IRAN_TZ).strftime("%Y/%m/%d")
    
    if not rankings or len(rankings) < 3:
        return
    
    message = "🏆 **رتبه‌های برتر امروز**\n\n"
    message += f"📅 تاریخ: {date_str}\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, rank in enumerate(rankings[:3]):
        hours = rank["total_minutes"] // 60
        mins = rank["total_minutes"] % 60
        time_display = f"{hours}س {mins}د" if hours > 0 else f"{mins}د"
        
        username = rank["username"] or "کاربر"
        if username == "None":
            username = "کاربر"
        
        message += f"{medals[i]} {username} ({rank['grade']} {rank['field']}): {time_display}\n"
    
    message += "\n🎯 فردا هم شرکت کنید!\n"
    message += "برای ثبت مطالعه جدید: /start"
    
    await send_to_all_users(context, message)

def update_user_info(user_id: int, grade: str, field: str) -> bool:
    """بروزرسانی اطلاعات کاربر"""
    try:
        query = """
        UPDATE users
        SET grade = %s, field = %s
        WHERE user_id = %s
        """
        rows_updated = db.execute_query(query, (grade, field, user_id))
        
        if rows_updated > 0:
            logger.info(f"✅ اطلاعات کاربر {user_id} بروزرسانی شد: {grade} {field}")
            return True
        else:
            logger.warning(f"⚠️ کاربر {user_id} یافت نشد")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطا در بروزرسانی اطلاعات کاربر: {e}")
        return False

# -----------------------------------------------------------
# مدیریت جلسات مطالعه
# -----------------------------------------------------------

def start_study_session(user_id: int, subject: str, topic: str, minutes: int) -> Optional[int]:
    """شروع جلسه مطالعه جدید با زمان ایران"""
    conn = None
    cursor = None
    
    try:
        logger.info(f"🔍 شروع جلسه مطالعه - کاربر: {user_id}, درس: {subject}, مبحث: {topic}, زمان: {minutes} دقیقه")
        
        # اعتبارسنجی ورودی‌ها
        if not subject or not subject.strip():
            logger.error(f"❌ درس وارد نشده است")
            return None
        
        if minutes < MIN_STUDY_TIME or minutes > MAX_STUDY_TIME:
            logger.error(f"❌ زمان نامعتبر: {minutes} (باید بین {MIN_STUDY_TIME} تا {MAX_STUDY_TIME} باشد)")
            return None
        
        # اتصال به دیتابیس
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود و فعال بودن کاربر
        query_check = "SELECT user_id, is_active, username FROM users WHERE user_id = %s"
        cursor.execute(query_check, (user_id,))
        user_check = cursor.fetchone()
        
        logger.info(f"🔍 نتیجه بررسی کاربر {user_id}: {user_check}")
        
        if not user_check:
            logger.error(f"❌ کاربر {user_id} در جدول users وجود ندارد")
            return None
        
        if not user_check[1]:  # is_active = False
            logger.error(f"❌ کاربر {user_id} فعال نیست")
            return None
        
        username = user_check[2] or "نامشخص"
        
        # زمان ایران
        now_iran = datetime.now(IRAN_TZ)
        start_timestamp = int(now_iran.timestamp())
        
        # تاریخ شمسی برای نمایش
        jdate = jdatetime.datetime.fromgregorian(datetime=now_iran)
        date_str = jdate.strftime("%Y/%m/%d")  # فرمت: 1404/12/02
        time_str = now_iran.strftime("%H:%M:%S")
        
        logger.info(f"   زمان شروع (ایران): {now_iran.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   timestamp: {start_timestamp}")
        logger.info(f"   تاریخ شمسی: {date_str}")
        logger.info(f"   ساعت: {time_str}")
        
        # ثبت جلسه در دیتابیس
        query_insert = """
        INSERT INTO study_sessions 
            (user_id, subject, topic, minutes, start_time, date, completed)
        VALUES (%s, %s, %s, %s, %s, %s, FALSE)
        RETURNING session_id
        """
        
        cursor.execute(query_insert, (user_id, subject.strip(), topic.strip(), minutes, start_timestamp, date_str))
        
        result = cursor.fetchone()
        
        if not result:
            logger.error(f"❌ خطا در ثبت جلسه در دیتابیس - هیچ session_id برگشت داده نشد")
            conn.rollback()
            return None
        
        session_id = result[0]
        conn.commit()
        
        logger.info(f"✅ جلسه مطالعه شروع شد: {session_id} برای کاربر {user_id}")
        logger.info(f"   جزئیات: درس={subject}, مبحث={topic}, زمان={minutes} دقیقه")
        
        # لاگ برای دیباگ بیشتر
        logger.info(f"   رکورد جلسه با موفقیت در دیتابیس ذخیره شد")
        
        # برگرداندن session_id
        return session_id
        
    except psycopg2.Error as e:
        logger.error(f"❌ خطای دیتابیس در شروع جلسه مطالعه: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return None
        
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره در شروع جلسه مطالعه: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return None
        
    finally:
        if cursor:
            cursor.close()
            logger.info("🔒 Cursor بسته شد")
        if conn:
            db.return_connection(conn)
            logger.info("🔌 Connection بازگردانده شد")


        
        
        # 🔴 اضافه شده: بروزرسانی اتاق‌های رقابت
def complete_study_session(session_id: int) -> Optional[Dict]:
    """اتمام جلسه مطالعه با زمان ایران"""
    conn = None
    cursor = None
    
    try:
        logger.info(f"🔍 تکمیل جلسه مطالعه - session_id: {session_id}")
        
        # زمان اتمام بر اساس ایران
        now_iran = datetime.now(IRAN_TZ)
        end_timestamp = int(now_iran.timestamp())
        
        logger.info(f"   زمان اتمام (ایران): {now_iran.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   end_timestamp: {end_timestamp}")
        
        # دریافت اطلاعات جلسه
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query_check = """
        SELECT user_id, subject, topic, minutes, start_time, completed, date 
        FROM study_sessions 
        WHERE session_id = %s
        """
        cursor.execute(query_check, (session_id,))
        session_check = cursor.fetchone()
        
        if not session_check:
            logger.error(f"❌ جلسه {session_id} یافت نشد")
            return None
        
        user_id, subject, topic, planned_minutes, start_time, completed, session_date = session_check
        
        logger.info(f"🔍 اطلاعات جلسه: کاربر={user_id}, درس={subject}, تاریخ={session_date}, تکمیل شده={completed}")
        
        if completed:
            logger.warning(f"⚠️ جلسه {session_id} قبلاً تکمیل شده است")
            return None
        
        # محاسبه زمان واقعی مطالعه
        if start_time and start_time > 0:
            actual_seconds = end_timestamp - start_time
            actual_minutes = max(1, actual_seconds // 60)
        else:
            logger.warning(f"⚠️ جلسه {session_id} start_time ندارد، از زمان برنامه‌ریزی شده استفاده می‌شود")
            actual_minutes = planned_minutes
            actual_seconds = planned_minutes * 60
        
        logger.info(f"⏱ زمان برنامه‌ریزی شده: {planned_minutes} دقیقه")
        logger.info(f"⏱ زمان واقعی: {actual_minutes} دقیقه ({actual_seconds} ثانیه)")
        
        # زمان نهایی (حداکثر به اندازه زمان برنامه‌ریزی شده)
        final_minutes = min(actual_minutes, planned_minutes)
        
        logger.info(f"✅ زمان نهایی محاسبه: {final_minutes} دقیقه")
        
        # بروزرسانی جلسه
        query_update = """
        UPDATE study_sessions
        SET end_time = %s, completed = TRUE, minutes = %s
        WHERE session_id = %s AND completed = FALSE
        RETURNING user_id, subject, topic, start_time, date
        """
        
        cursor.execute(query_update, (end_timestamp, final_minutes, session_id))
        result = cursor.fetchone()
        
        if not result:
            logger.error(f"❌ بروزرسانی جلسه ناموفق بود")
            conn.rollback()
            return None
        
        user_id, subject, topic, start_time, session_date = result
        conn.commit()
        
        logger.info(f"✅ جلسه {session_id} با موفقیت بروزرسانی شد")
        
        # بروزرسانی آمار کلی کاربر
        try:
            query_user = """
            UPDATE users
            SET 
                total_study_time = total_study_time + %s,
                total_sessions = total_sessions + 1
            WHERE user_id = %s
            """
            cursor.execute(query_user, (final_minutes, user_id))
            conn.commit()
            logger.info(f"✅ آمار کاربر {user_id} بروزرسانی شد")
        except Exception as e:
            logger.warning(f"⚠️ خطا در بروزرسانی آمار کاربر {user_id}: {e}")
            conn.rollback()
        
        # بروزرسانی رتبه‌بندی روزانه
        try:
            # تبدیل تاریخ شمسی به میلادی برای دیتابیس
            if '/' in session_date:
                session_date_formatted = convert_jalali_to_gregorian(session_date)
                logger.info(f"📅 تاریخ شمسی {session_date} → میلادی {session_date_formatted}")
            else:
                session_date_formatted = session_date
            
            logger.info(f"📅 بروزرسانی daily_rankings برای تاریخ: {session_date_formatted}")
            
            query_rank = """
            INSERT INTO daily_rankings (user_id, date, total_minutes)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, date) DO UPDATE SET
                total_minutes = daily_rankings.total_minutes + EXCLUDED.total_minutes
            """
            cursor.execute(query_rank, (user_id, session_date_formatted, final_minutes))
            conn.commit()
            logger.info(f"✅ رتبه‌بندی روزانه برای کاربر {user_id} بروزرسانی شد")
        except Exception as e:
            logger.warning(f"⚠️ خطا در بروزرسانی رتبه‌بندی: {e}", exc_info=True)
            conn.rollback()
        
        # بروزرسانی اتاق‌های رقابت
        try:
            # بررسی آیا کاربر در اتاق رقابتی فعال است
            query_room = """
            SELECT rp.room_code 
            FROM room_participants rp
            JOIN competition_rooms cr ON rp.room_code = cr.room_code
            WHERE rp.user_id = %s AND cr.status = 'active'
            """
            cursor.execute(query_room, (user_id,))
            active_rooms = cursor.fetchall()
            
            if active_rooms:
                for room in active_rooms:
                    room_code = room[0]
                    # بروزرسانی مطالعه کاربر در اتاق
                    query_update_room = """
                    UPDATE room_participants
                    SET total_minutes = total_minutes + %s,
                        current_subject = %s,
                        current_topic = %s
                    WHERE user_id = %s AND room_code = %s
                    """
                    cursor.execute(query_update_room, (final_minutes, subject, topic, user_id, room_code))
                    
                    logger.info(f"🏆 بروزرسانی اتاق رقابت: کاربر {user_id} در اتاق {room_code} - {final_minutes} دقیقه")
                conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ خطا در بروزرسانی اتاق رقابت: {e}")
            conn.rollback()
        
        # آماده‌سازی داده‌های برگشتی
        session_data = {
            "user_id": user_id,
            "subject": subject,
            "topic": topic,
            "minutes": final_minutes,
            "planned_minutes": planned_minutes,
            "actual_seconds": actual_seconds,
            "start_time": start_time,
            "end_time": end_timestamp,
            "session_id": session_id,
            "date": session_date,
            "start_time_iran": datetime.fromtimestamp(start_time, IRAN_TZ).strftime("%Y-%m-%d %H:%M:%S") if start_time else None,
            "end_time_iran": now_iran.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info(f"✅ جلسه مطالعه تکمیل شد: {session_id} - زمان: {final_minutes} دقیقه")
        return session_data
        
    except Exception as e:
        logger.error(f"❌ خطا در تکمیل جلسه مطالعه: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return None
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)
            logger.info("🔌 Connection بازگردانده شد")
def convert_jalali_to_gregorian(jalali_date_str: str) -> str:
    """تبدیل تاریخ شمسی به میلادی (YYYY-MM-DD)"""
    try:
        if '/' in jalali_date_str:
            parts = jalali_date_str.split('/')
            if len(parts) == 3:
                year, month, day = map(int, parts)
                # تبدیل تاریخ شمسی به میلادی
                jdate = jdatetime.date(year, month, day)
                gdate = jdate.togregorian()
                return gdate.strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"❌ خطا در تبدیل تاریخ {jalali_date_str}: {e}")
    
    # در صورت خطا، تاریخ امروز را برگردان
    return datetime.now(IRAN_TZ).strftime("%Y-%m-%d")
async def complete_study_button(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """اتمام جلسه مطالعه با دکمه"""
    if "current_session" not in context.user_data:
        await update.message.reply_text(
            "❌ جلسه‌ای فعال نیست.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    session_id = context.user_data["current_session"]
    jobs = context.job_queue.get_jobs_by_name(str(session_id))
    for job in jobs:
        job.schedule_removal()
        logger.info(f"⏰ تایمر جلسه {session_id} لغو شد")
    
    session = complete_study_session(session_id)
    
    if session:
        date_str, time_str = get_iran_time()
        score = calculate_score(session["minutes"])
        
        rank, total_minutes = get_user_rank_today(user_id)
        
        rank_text = f"🏆 رتبه شما امروز: {rank}" if rank else ""
        
        time_info = ""
        if session.get("planned_minutes") != session["minutes"]:
            time_info = f"⏱ زمان واقعی: {format_time(session['minutes'])} (از {format_time(session['planned_minutes'])})"
        else:
            time_info = f"⏱ مدت: {format_time(session['minutes'])}"
        
        await update.message.reply_text(
            f"✅ مطالعه تکمیل شد!\n\n"
            f"📚 درس: {session['subject']}\n"
            f"🎯 مبحث: {session['topic']}\n"
            f"{time_info}\n"
            f"🏆 امتیاز: +{score}\n"
            f"📅 تاریخ: {date_str}\n"
            f"🕒 زمان: {time_str}\n\n"
            f"{rank_text}",
            reply_markup=get_after_study_keyboard()
        )
        
        context.user_data["last_subject"] = session['subject']
        
        # 🔴 اضافه شده: بررسی و اعطای پاداش (از قبل موجود)
        await check_and_reward_user(user_id, session_id, context)
        
        # 🔴 اضافه شده: ارسال هشدارهای رقابتی
        try:
            # بررسی اتاق‌های فعال کاربر
            query = """
            SELECT rp.room_code 
            FROM room_participants rp
            JOIN competition_rooms cr ON rp.room_code = cr.room_code
            WHERE rp.user_id = %s AND cr.status = 'active'
            """
            
            active_rooms = db.execute_query(query, (user_id,), fetchall=True)
            
            if active_rooms:
                for room in active_rooms:
                    room_code = room[0]
                    # ارسال هشدار رقابتی
                    await send_competition_alerts(context, user_id, room_code, session)
                    
        except Exception as e:
            logger.error(f"❌ خطا در ارسال هشدار رقابتی: {e}")
        
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت اطلاعات.",
            reply_markup=get_main_menu_keyboard()
        )
    
    context.user_data.pop("current_session", None)

def get_user_sessions(user_id: int, limit: int = 10) -> List[Dict]:
    """دریافت جلسات اخیر کاربر"""
    try:
        query = """
        SELECT session_id, subject, topic, minutes, date, start_time, completed
        FROM study_sessions
        WHERE user_id = %s
        ORDER BY start_time DESC
        LIMIT %s
        """
        
        results = db.execute_query(query, (user_id, limit), fetchall=True)
        
        sessions = []
        if results:
            for row in results:
                sessions.append({
                    "session_id": row[0],
                    "subject": row[1],
                    "topic": row[2],
                    "minutes": row[3],
                    "date": row[4],
                    "start_time": row[5],
                    "completed": row[6]
                })
        
        return sessions
        
    except Exception as e:
        logger.error(f"خطا در دریافت جلسات کاربر: {e}")
        return []

# -----------------------------------------------------------
# سیستم رتبه‌بندی
# -----------------------------------------------------------
async def send_competition_alerts(context: ContextTypes.DEFAULT_TYPE, user_id: int, room_code: str, session_data: Dict) -> None:
    """ارسال هشدارهای رقابتی"""
    try:
        # دریافت رتبه‌بندی جدید
        rankings = get_room_ranking(room_code)
        
        # یافتن کاربر در رتبه‌بندی
        user_rank = None
        for rank in rankings:
            if rank["user_id"] == user_id:
                user_rank = rank["rank"]
                break
        
        if not user_rank:
            return
        
        # دریافت رتبه قبلی کاربر
        query = """
        SELECT last_rank FROM room_participants
        WHERE user_id = %s AND room_code = %s
        """
        result = db.execute_query(query, (user_id, room_code), fetch=True)
        
        old_rank = result[0] if result else None
        
        # بروزرسانی رتبه آخر
        query_update = """
        UPDATE room_participants
        SET last_rank = %s
        WHERE user_id = %s AND room_code = %s
        """
        db.execute_query(query_update, (user_rank, user_id, room_code))
        
        # ارسال هشدار اگر رتبه تغییر کرد
        if old_rank and old_rank != user_rank:
            if user_rank < old_rank:  # ارتقا رتبه
                message = f"🎉 **صعود کردی!**\nرتبه {old_rank} → {user_rank}"
                try:
                    await context.bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
                except:
                    pass
            elif user_rank > old_rank:  # نزول رتبه
                message = f"⚠️ **عقب افتادی!**\nرتبه {old_rank} → {user_rank}"
                try:
                    await context.bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
                except:
                    pass
        
        # هشدار نزدیکی به نفر اول
        if user_rank > 1 and len(rankings) > 0:
            first_place = rankings[0]
            user_minutes = session_data["minutes"]
            gap = first_place["total_minutes"] - user_minutes
            
            if 0 < gap <= 30:  # کمتر از ۳۰ دقیقه فاصله
                message = f"🚀 **نزدیکی!**\nفقط {gap} دقیقه با نفر اول فاصله داری!"
                try:
                    await context.bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
                except:
                    pass
        
    except Exception as e:
        logger.error(f"خطا در ارسال هشدار رقابتی: {e}")
def get_today_rankings() -> List[Dict]:
    """دریافت رتبه‌بندی امروز"""
    try:
        # دریافت تاریخ امروز در فرمت دیتابیس
        date_str_db = get_db_date()
        date_str_display, time_str = get_iran_time()
        
        logger.info(f"🔍 دریافت رتبه‌بندی برای تاریخ: {date_str_db}")
        
        query = """
        SELECT u.user_id, u.username, u.grade, u.field, dr.total_minutes
        FROM daily_rankings dr
        JOIN users u ON dr.user_id = u.user_id
        WHERE dr.date = %s AND u.is_active = TRUE
        ORDER BY dr.total_minutes DESC
        LIMIT 20
        """
        
        results = db.execute_query(query, (date_str_db,), fetchall=True)
        
        logger.info(f"🔍 تعداد رکوردهای یافت شده: {len(results) if results else 0}")
        
        rankings = []
        if results:
            for row in results:
                rankings.append({
                    "user_id": row[0],
                    "username": row[1],
                    "grade": row[2],
                    "field": row[3],
                    "total_minutes": row[4]
                })
                logger.info(f"  👤 {row[0]}: {row[4]} دقیقه")
        
        return rankings
        
    except Exception as e:
        logger.error(f"خطا در دریافت رتبه‌بندی: {e}", exc_info=True)
        return []

def get_user_rank_today(user_id: int) -> Tuple[Optional[int], Optional[int]]:
    """دریافت رتبه و زمان کاربر در امروز"""
    try:
        date_str, _ = get_iran_time()
        
        query = """
        SELECT total_minutes FROM daily_rankings
        WHERE user_id = %s AND date = %s
        """
        result = db.execute_query(query, (user_id, date_str), fetch=True)
        
        if not result:
            return None, 0
        
        user_minutes = result[0]
        
        query = """
        SELECT COUNT(*) FROM daily_rankings
        WHERE date = %s AND total_minutes > %s
        """
        result = db.execute_query(query, (date_str, user_minutes), fetch=True)
        
        rank = result[0] + 1 if result else 1
        return rank, user_minutes
        
    except Exception as e:
        logger.error(f"خطا در محاسبه رتبه کاربر: {e}")
        return None, 0

# -----------------------------------------------------------
# مدیریت فایل‌ها
# -----------------------------------------------------------

def add_file(grade: str, field: str, subject: str, topic: str, 
             description: str, telegram_file_id: str, file_name: str,
             file_size: int, mime_type: str, uploader_id: int) -> Optional[Dict]:
    """افزودن فایل جدید به دیتابیس"""
    conn = None
    cursor = None
    
    try:
        logger.info(f"🔍 شروع اضافه کردن فایل به دیتابیس:")
        logger.info(f"  🎓 پایه: {grade}")
        logger.info(f"  🧪 رشته: {field}")
        logger.info(f"  📚 درس: {subject}")
        logger.info(f"  📄 نام فایل: {file_name}")
        logger.info(f"  📦 حجم: {file_size}")
        logger.info(f"  👤 آپلودکننده: {uploader_id}")
        
        upload_date, time_str = get_iran_time()
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO files (grade, field, subject, topic, description, 
                          telegram_file_id, file_name, file_size, mime_type, 
                          upload_date, uploader_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING file_id, upload_date
        """
        
        params = (
            grade, field, subject, topic, description,
            telegram_file_id, file_name, file_size, mime_type,
            upload_date, uploader_id
        )
        
        logger.info(f"🔍 اجرای کوئری INSERT...")
        cursor.execute(query, params)
        
        conn.commit()
        
        result = cursor.fetchone()
        
        if result:
            file_data = {
                "file_id": result[0],
                "grade": grade,
                "field": field,
                "subject": subject,
                "topic": topic,
                "description": description,
                "file_name": file_name,
                "file_size": file_size,
                "upload_date": result[1]
            }
            
            logger.info(f"✅ فایل با موفقیت در دیتابیس ذخیره شد: {file_name} (ID: {result[0]})")
            
            cursor.execute("SELECT COUNT(*) FROM files WHERE file_id = %s", (result[0],))
            count = cursor.fetchone()[0]
            logger.info(f"🔍 تأیید ذخیره‌سازی: {count} رکورد با ID {result[0]} وجود دارد")
            
            return file_data
        
        logger.error("❌ هیچ نتیجه‌ای از INSERT برگشت داده نشد")
        return None
        
    except Exception as e:
        logger.error(f"❌ خطا در آپلود فایل: {e}", exc_info=True)
        if conn:
            conn.rollback()
            logger.info("🔁 Rollback انجام شد")
        return None
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)
            logger.info("🔌 Connection بازگردانده شد")

def get_user_files(user_id: int) -> List[Dict]:
    """دریافت فایل‌های مرتبط با کاربر"""
    try:
        logger.info(f"🔍 دریافت فایل‌های کاربر {user_id}")
        user_info = get_user_info(user_id)
        
        if not user_info:
            logger.warning(f"⚠️ اطلاعات کاربر {user_id} یافت نشد")
            return []
        
        logger.info(f"🔍 اطلاعات کاربر {user_id}: {user_info}")
        
        grade = user_info["grade"]
        field = user_info["field"]
        
        logger.info(f"🔍 جستجوی فایل‌ها برای: {grade} {field}")
        
        if grade == "فارغ‌التحصیل":
            query = """
            SELECT file_id, subject, topic, description, file_name, file_size, upload_date, download_count
            FROM files
            WHERE (grade = %s OR grade = 'دوازدهم') AND field = %s
            ORDER BY upload_date DESC
            LIMIT 50
            """
            results = db.execute_query(query, (grade, field), fetchall=True)
        else:
            query = """
            SELECT file_id, subject, topic, description, file_name, file_size, upload_date, download_count
            FROM files
            WHERE grade = %s AND field = %s
            ORDER BY upload_date DESC
            LIMIT 50
            """
            results = db.execute_query(query, (grade, field), fetchall=True)
        
        logger.info(f"🔍 تعداد فایل‌های یافت شده: {len(results) if results else 0}")
        
        files = []
        if results:
            for row in results:
                files.append({
                    "file_id": row[0],
                    "subject": row[1],
                    "topic": row[2],
                    "description": row[3],
                    "file_name": row[4],
                    "file_size": row[5],
                    "upload_date": row[6],
                    "download_count": row[7]
                })
        
        logger.info(f"🔍 فایل‌های بازگشتی: {[f['file_name'] for f in files]}")
        return files
        
    except Exception as e:
        logger.error(f"❌ خطا در دریافت فایل‌های کاربر: {e}", exc_info=True)
        return []

def get_files_by_subject(user_id: int, subject: str) -> List[Dict]:
    """دریافت فایل‌های یک درس خاص"""
    try:
        user_info = get_user_info(user_id)
        if not user_info:
            return []
        
        grade = user_info["grade"]
        field = user_info["field"]
        
        if grade == "فارغ‌التحصیل":
            query = """
            SELECT file_id, topic, description, file_name, file_size, upload_date, download_count
            FROM files
            WHERE (grade = %s OR grade = 'دوازدهم') AND field = %s AND subject = %s
            ORDER BY upload_date DESC
            """
            results = db.execute_query(query, (grade, field, subject), fetchall=True)
        else:
            query = """
            SELECT file_id, topic, description, file_name, file_size, upload_date, download_count
            FROM files
            WHERE grade = %s AND field = %s AND subject = %s
            ORDER BY upload_date DESC
            """
            results = db.execute_query(query, (grade, field, subject), fetchall=True)
        
        files = []
        if results:
            for row in results:
                files.append({
                    "file_id": row[0],
                    "topic": row[1],
                    "description": row[2],
                    "file_name": row[3],
                    "file_size": row[4],
                    "upload_date": row[5],
                    "download_count": row[6]
                })
        
        return files
        
    except Exception as e:
        logger.error(f"خطا در دریافت فایل‌های درس: {e}")
        return []

def get_file_by_id(file_id: int) -> Optional[Dict]:
    """دریافت اطلاعات فایل بر اساس ID"""
    try:
        query = """
        SELECT file_id, grade, field, subject, topic, description,
               telegram_file_id, file_name, file_size, mime_type,
               upload_date, download_count, uploader_id
        FROM files
        WHERE file_id = %s
        """
        
        result = db.execute_query(query, (file_id,), fetch=True)
        
        if result:
            return {
                "file_id": result[0],
                "grade": result[1],
                "field": result[2],
                "subject": result[3],
                "topic": result[4],
                "description": result[5],
                "telegram_file_id": result[6],
                "file_name": result[7],
                "file_size": result[8],
                "mime_type": result[9],
                "upload_date": result[10],
                "download_count": result[11],
                "uploader_id": result[12]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"خطا در دریافت فایل: {e}")
        return None

def increment_download_count(file_id: int) -> bool:
    """افزایش شمارنده دانلود فایل"""
    try:
        query = """
        UPDATE files
        SET download_count = download_count + 1
        WHERE file_id = %s
        """
        db.execute_query(query, (file_id,))
        return True
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی شمارنده دانلود: {e}")
        return False

def get_all_files() -> List[Dict]:
    """دریافت همه فایل‌ها (برای ادمین)"""
    try:
        logger.info("🔍 دریافت همه فایل‌ها از دیتابیس")
        
        query = """
        SELECT file_id, grade, field, subject, topic, file_name, 
               file_size, upload_date, download_count
        FROM files
        ORDER BY upload_date DESC
        LIMIT 100
        """
        
        results = db.execute_query(query, fetchall=True)
        
        logger.info(f"🔍 تعداد کل فایل‌ها در دیتابیس: {len(results) if results else 0}")
        
        files = []
        if results:
            for row in results:
                files.append({
                    "file_id": row[0],
                    "grade": row[1],
                    "field": row[2],
                    "subject": row[3],
                    "topic": row[4],
                    "file_name": row[5],
                    "file_size": row[6],
                    "upload_date": row[7],
                    "download_count": row[8]
                })
                logger.info(f"📄 فایل {row[0]}: {row[1]} {row[2]} - {row[3]} - {row[5]}")
        
        return files
        
    except Exception as e:
        logger.error(f"❌ خطا در دریافت همه فایل‌ها: {e}", exc_info=True)
        return []

def delete_file(file_id: int) -> bool:
    """حذف فایل"""
    try:
        query = "DELETE FROM files WHERE file_id = %s"
        db.execute_query(query, (file_id,))
        logger.info(f"فایل حذف شد: {file_id}")
        return True
    except Exception as e:
        logger.error(f"خطا در حذف فایل: {e}")
        return False

# -----------------------------------------------------------
# کیبوردهای ساده (بدون اینلاین)
# -----------------------------------------------------------

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """منوی اصلی"""
    keyboard = [
        ["➕ ثبت مطالعه"],
        ["📚 منابع"],
        ["🎫 کوپن"],
        ["🏆 رقابت گروهی"],  # 🔴 اضافه شد
        ["🏅 رتبه‌بندی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
def get_subjects_keyboard_reply() -> ReplyKeyboardMarkup:
    """کیبورد انتخاب درس"""
    keyboard = []
    row = []
    
    # اضافه کردن 11 درس اول در 3 ردیف
    for i, subject in enumerate(SUBJECTS[:-1]):  # همه به جز "سایر"
        row.append(subject)
        if len(row) == 3:  # هر ردیف 3 دکمه
            keyboard.append(row)
            row = []
    
    # اضافه کردن ردیف آخر اگر درس‌های باقی مانده وجود دارد
    if row:
        keyboard.append(row)
    
    # اضافه کردن "سایر" در یک ردیف جداگانه
    keyboard.append(["سایر"])
    
    keyboard.append(["🔙 بازگشت"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_time_selection_keyboard_reply() -> ReplyKeyboardMarkup:
    """کیبورد انتخاب زمان"""
    keyboard = []
    
    for text, minutes in SUGGESTED_TIMES:
        keyboard.append([text])
    
    keyboard.append(["✏️ زمان دلخواه", "🔙 بازگشت"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_admin_keyboard_reply() -> ReplyKeyboardMarkup:
    """منوی ادمین - به‌روزرسانی شده"""
    keyboard = [
        ["📤 آپلود فایل", "👥 درخواست‌ها"],
        ["👤 لیست کاربران", "📩 ارسال پیام"],
        ["📁 مدیریت فایل‌ها", "🎫 مدیریت کوپن"],  # تغییر اینجا
        ["📊 آمار ربات", "🏠 منوی اصلی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_admin_requests_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد مدیریت درخواست‌های ادمین"""
    keyboard = [
        ["✅ تأیید همه", "❌ رد همه"],
        ["👁 مشاهده جزئیات", "🔄 به‌روزرسانی"],
        ["🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_file_subjects_keyboard(user_files: List[Dict]) -> ReplyKeyboardMarkup:
    """کیبورد انتخاب درس برای منابع"""
    subjects = list(set([f["subject"] for f in user_files]))
    keyboard = []
    row = []
    
    for subject in subjects[:6]:
        row.append(subject)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append(["🔙 بازگشت"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_admin_file_management_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد مدیریت فایل‌های ادمین"""
    keyboard = [
        ["🗑 حذف فایل", "📋 لیست فایل‌ها"],
        ["🔄 به‌روزرسانی", "🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_after_study_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد پس از اتمام مطالعه"""
    keyboard = [
        ["📖 منابع این درس", "🏆 رتبه‌بندی"],
        ["➕ مطالعه جدید", "🏠 منوی اصلی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_complete_study_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد اتمام مطالعه"""
    keyboard = [[KeyboardButton("✅ اتمام مطالعه")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
def get_competition_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد رقابت گروهی"""
    keyboard = [
        ["🏆 ساخت رقابت جدید"],
        ["🔗 پیوستن به رقابت"],
        ["📊 اتاق‌های من"],
        ["🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_end_time_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد انتخاب زمان پایان"""
    keyboard = [
        ["🕐 ۱۸:۰۰", "🕐 ۱۹:۰۰", "🕐 ۲۰:۰۰"],
        ["🕐 ۲۱:۰۰", "🕐 ۲۲:۰۰", "✏️ زمان دلخواه"],
        ["🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_room_management_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد مدیریت اتاق"""
    keyboard = [
        ["📊 مشاهده رتبه‌بندی"],
        ["👥 لیست شرکت‌کنندگان"],
        ["🏁 پایان دادن"],
        ["🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
# -----------------------------------------------------------
# هندلرهای دستورات
# -----------------------------------------------------------
async def coupon_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر منوی کوپن"""
    user_id = update.effective_user.id
    
    if not is_user_active(user_id):
        await update.message.reply_text(
            "❌ حساب کاربری شما فعال نیست.\n"
            "لطفا منتظر تأیید ادمین باشید."
        )
        return
    
    await update.message.reply_text(
        "🎫 **سیستم کوپن‌ها**\n\n"
        "هر کوپن معادل ۴۰,۰۰۰ تومان ارزش دارد\n\n"
        "📋 خدمات قابل خرید با کوپن:",
        reply_markup=get_coupon_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# -----------------------------------------------------------
# 9. هندلر انتخاب خدمت کوپن
# -----------------------------------------------------------

async def handle_coupon_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, service: str) -> None:
    """پردازش انتخاب خدمت کوپن"""
    user_id = update.effective_user.id
    
    # تعیین قیمت خدمت
    service_prices = {
        "📞 تماس تلفنی": {"price": 1, "name": "تماس تلفنی (۱۰ دقیقه)"},  # تغییر اینجا
        "📊 تحلیل گزارش": {"price": 1, "name": "تحلیل گزارش کار"},
        "✏️ تصحیح آزمون": {"price": 1, "name": "تصحیح آزمون تشریحی"},
        "📈 تحلیل آزمون": {"price": 1, "name": "تحلیل آزمون"},
        "📝 آزمون شخصی": {"price": 2, "name": "آزمون شخصی"}
    }
    
    # 🔴 اصلاح: نام خدمت با کیبورد مطابقت ندارد
    # از service که مستقیماً دریافت شده استفاده می‌کنیم
    
    if service == "🔗 برنامه شخصی":
        await handle_free_program(update, context)
        return
    
    # 🔴 اصلاح: بررسی نام خدمت در دیکشنری
    # برخی خدمات ممکن است پسوند قیمت داشته باشند
    service_key = service
    if "(" in service:
        # اگر فرمت "خدمت (X کوپن)" بود
        service_key = service.split("(")[0].strip()
    
    # اگر هنوز پیدا نشد، سعی کن با مقایسه بخشی از نام پیدا کنی
    if service_key not in service_prices:
        for key in service_prices:
            if key in service_key or service_key in key:
                service_key = key
                break
    
    if service_key not in service_prices:
        await update.message.reply_text("❌ خدمت انتخاب شده نامعتبر است.")
        return
    
    service_info = service_prices[service_key]
    context.user_data["selected_service"] = service_info
    
    # بررسی کوپن‌های کاربر
    active_coupons = get_user_coupons(user_id, "active")
    
    if len(active_coupons) >= service_info["price"]:
        # کاربر کوپن کافی دارد
        context.user_data["awaiting_coupon_selection"] = True
        
        coupon_list = "📋 **کوپن‌های فعال شما:**\n\n"
        for i, coupon in enumerate(active_coupons[:5], 1):
            source_emoji = "⏰" if coupon["source"] == "study_streak" else "💳"
            coupon_list += f"{i}. {source_emoji} `{coupon['coupon_code']}` - {coupon['earned_date']}\n"
        
        if len(active_coupons) > 5:
            coupon_list += f"\n📊 و {len(active_coupons)-5} کوپن دیگر...\n"
        
        coupon_list += f"\n🎯 برای {service_info['name']} نیاز به {service_info['price']} کوپن دارید."
        
        if service_info["price"] == 1:
            coupon_list += "\n📝 لطفا کد کوپن مورد نظر را وارد کنید:"
            await update.message.reply_text(
                coupon_list,
                reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            coupon_list += "\n📝 لطفا کدهای کوپن را با کاما جدا کنید (مثال: FT123,FT456):"
            await update.message.reply_text(
                coupon_list,
                reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        # کاربر کوپن کافی ندارد
        context.user_data["awaiting_purchase_method"] = True
        
        missing = service_info["price"] - len(active_coupons)
        
        text = f"""
📋 **{service_info['name']}**

💰 قیمت: {service_info['price']} کوپن

📊 **وضعیت کوپن‌های شما:**
• کوپن‌های فعال: {len(active_coupons)}
• نیاز به {missing} کوپن دیگر

🛒 **روش‌های دریافت کوپن:**
"""
        await update.message.reply_text(
            text,
            reply_markup=get_coupon_method_keyboard(),
            parse_mode=ParseMode.MARKDOWN
)

# -----------------------------------------------------------
# 10. هندلر برنامه شخصی رایگان
# -----------------------------------------------------------

async def handle_free_program(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش برنامه شخصی رایگان"""
    text = """
🔗 **برنامه شخصی رایگان**

📋 شرایط دریافت:
۱. عضویت در کانل KonkorofKings
۲. فعال بودن اشتراک

📢 **لینک کانال:**
https://t.me/konkorofkings

✅ پس از عضویت، دکمه زیر را بزنید:
"""
    
    keyboard = [
        ["✅ تأیید عضویت"],
        ["🔙 بازگشت"]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode=ParseMode.MARKDOWN
    )

# -----------------------------------------------------------
# 11. هندلر خرید کوپن
# -----------------------------------------------------------

async def handle_coupon_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش خرید کوپن"""
    user_id = update.effective_user.id
    
    # دریافت اطلاعات کارت ادمین
    card_info = get_admin_card_info()
    
    text = f"""
💳 <b>خرید کوپن</b>

💰 <b>مبلغ:</b> ۴۰,۰۰۰ تومان

🏦 <b>لطفا مبلغ را به شماره کارت زیر واریز کنید:</b>
<code>{card_info['card_number']}</code>
به نام: {escape_html_for_telegram(card_info['card_owner'])}

📸 <b>پس از واریز، عکس فیش پرداختی را ارسال کنید.</b>

⚠️ <b>توجه:</b>
• پس از تأیید ادمین، ۱ کوپن عمومی به حساب شما اضافه می‌شود
• این کوپن را می‌توانید برای هر خدمتی استفاده کنید
• کوپن‌ها تاریخ انقضا ندارند

🔙 بازگشت
"""
    
    context.user_data["awaiting_payment_receipt"] = True
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True),
        parse_mode=ParseMode.HTML
    )

# -----------------------------------------------------------
# 3. اضافه کردن تابع هندلر عکس فیش
# -----------------------------------------------------------
async def handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش عکس فیش پرداختی"""
    user_id = update.effective_user.id
    
    # بررسی آیا کاربر در انتظار ارسال فیش است
    if not context.user_data.get("awaiting_payment_receipt"):
        await update.message.reply_text(
            "❌ شما در حال خرید کوپن نیستید.\n"
            "لطفا از منوی کوپن استفاده کنید."
        )
        return
    
    # بررسی وجود عکس
    if not update.message.photo:
        await update.message.reply_text(
            "❌ لطفا یک عکس از فیش پرداختی ارسال کنید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True)
        )
        return
    
    # دریافت عکس با کیفیت مناسب
    photo = update.message.photo[-1]  # آخرین عکس با بیشترین کیفیت
    file_id = photo.file_id
    
    # دریافت اطلاعات کاربر
    user_info = get_user_info(user_id)
    username = user_info["username"] if user_info else "نامشخص"
    user_full_name = update.effective_user.full_name or "نامشخص"
    
    # ایجاد درخواست خرید کوپن
    request_data = create_coupon_request(
        user_id=user_id,
        request_type="purchase",
        amount=400000,
        receipt_image=file_id  # ذخیره file_id برای نمایش به ادمین
    )
    
    if not request_data:
        await update.message.reply_text(
            "❌ خطا در ثبت درخواست. لطفا مجدد تلاش کنید.",
            reply_markup=get_coupon_main_keyboard()
        )
        return
    
    date_str, time_str = get_iran_time()
    
    # اطلاع به کاربر
    await update.message.reply_text(
        f"✅ <b>عکس فیش دریافت شد!</b>\n\n"
        f"📋 <b>اطلاعات درخواست:</b>\n"
        f"• شماره درخواست: #{request_data['request_id']}\n"
        f"• مبلغ: ۴۰,۰۰۰ تومان\n"
        f"• تاریخ: {date_str}\n"
        f"• زمان: {time_str}\n\n"
        f"⏳ درخواست شما برای بررسی به ادمین ارسال شد.\n"
        f"پس از تأیید، کوپن به حساب شما اضافه می‌شود.",
        reply_markup=get_coupon_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    # پاک کردن وضعیت انتظار
    context.user_data.pop("awaiting_payment_receipt", None)
    context.user_data.pop("selected_service", None)
    context.user_data.pop("awaiting_purchase_method", None)
    
    # ارسال خودکار به همه ادمین‌ها
    for admin_id in ADMIN_IDS:
        try:
            # ارسال عکس به ادمین
            caption = f"""
🏦 <b>درخواست خرید کوپن جدید</b>

📋 <b>اطلاعات درخواست:</b>
• شماره درخواست: #{request_data['request_id']}
• کاربر: {escape_html_for_telegram(user_full_name)}
• آیدی: <code>{user_id}</code>
• نام کاربری: @{username or 'ندارد'}
• مبلغ: ۴۰,۰۰۰ تومان
• تاریخ: {date_str}
• زمان: {time_str}

📝 برای تأیید دستور زیر را وارد کنید:
<code>/verify_coupon {request_data['request_id']}</code>

🔍 برای مشاهده درخواست‌ها:
/coupon_requests
"""
            
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"خطا در ارسال به ادمین {admin_id}: {e}")
    
    logger.info(f"درخواست خرید کوپن ثبت شد: کاربر {user_id} - درخواست #{request_data['request_id']}")
async def handle_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str) -> None:
    """پردازش متن ارسال شده به جای عکس فیش"""
    if text == "🔙 بازگشت":
        context.user_data.pop("awaiting_payment_receipt", None)
        await coupon_menu_handler(update, context)
        return
    
    # اگر کاربر متن ارسال کرد، راهنمایی به ارسال عکس
    await update.message.reply_text(
        "❌ لطفا عکس فیش پرداختی را ارسال کنید.\n\n"
        "📸 باید از روی فیش بانکی یا رسید پرداخت عکس بگیرید و ارسال کنید.\n\n"
        "⚠️ ارسال متن پذیرفته نیست.",
        reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True)
    )
# -----------------------------------------------------------
# 12. هندلر کسب کوپن از مطالعه
# -----------------------------------------------------------

async def handle_study_coupon_earning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش کسب کوپن از طریق مطالعه"""
    user_id = update.effective_user.id
    
    # بررسی استرک کاربر
    streak_info = check_study_streak(user_id)
    
    text = """
⏰ **کسب کوپن از طریق مطالعه**

📋 شرایط کسب کوپن:
• ۲ روز متوالی مطالعه
• هر روز حداقل ۶ ساعت (۳۶۰ دقیقه) مطالعه
• جلسات معتبر (حداقل ۳۰ دقیقه)

🎯 **آمار مطالعه ۲ روز اخیر شما:**
"""
    
    if streak_info:
        if streak_info["eligible"]:
            text += f"""
✅ دیروز: {streak_info['yesterday_minutes'] // 60} ساعت و {streak_info['yesterday_minutes'] % 60} دقیقه
✅ امروز: {streak_info['today_minutes'] // 60} ساعت و {streak_info['today_minutes'] % 60} دقیقه
🎯 مجموع: {streak_info['total_hours']} ساعت در ۲ روز

🎉 **شما واجد شرایط کسب کوپن هستید!**

💰 **آیا می‌خواهید کوپن دریافت کنید؟**
"""
            
            keyboard = [
                ["✅ دریافت کوپن"],
                ["🔙 بازگشت"]
            ]
            
            context.user_data["eligible_for_coupon"] = streak_info
            
        else:
            yesterday_hours = streak_info["yesterday_minutes"] // 60
            yesterday_mins = streak_info["yesterday_minutes"] % 60
            today_hours = streak_info["today_minutes"] // 60
            today_mins = streak_info["today_minutes"] % 60
            
            # نمایش اعداد واقعی
            text += f"""
📊 دیروز: {yesterday_hours} ساعت و {yesterday_mins} دقیقه
📊 امروز: {today_hours} ساعت و {today_mins} دقیقه

⚠️ **برای کسب کوپن نیاز دارید:**
• هر روز حداقل ۶ ساعت (۳۶۰ دقیقه) مطالعه کنید
• این روند را برای ۲ روز متوالی ادامه دهید

💡 **نکته:** سیستم به صورت خودکار بررسی می‌کند و هنگام واجد شرایط بودن، کوپن را اعطا می‌کند.
"""
            
            keyboard = [
                ["🔄 بررسی مجدد"],
                ["🔙 بازگشت"]
            ]
    else:
        text += """
❌ **خطا در دریافت اطلاعات مطالعه**

لطفا بعداً مجدد تلاش کنید.
"""
        keyboard = [["🔙 بازگشت"]]
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode=ParseMode.MARKDOWN
)

# -----------------------------------------------------------
# 13. دستورات ادمین جدید
# -----------------------------------------------------------
async def competition_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """منوی رقابت گروهی"""
    user_id = update.effective_user.id
    
    if not is_user_active(user_id):
        await update.message.reply_text("❌ حساب شما فعال نیست.")
        return
    
    await update.message.reply_text(
        "🏆 **سیستم رقابت گروهی**\n\n"
        "با دوستانت رقابت کن و جایزه ببر!\n\n"
        "📋 شرایط:\n"
        "• حداقل ۵ نفر\n"
        "• هر اتاق یک رمز دارد\n"
        "• نفر اول ۱ کوپن کامل می‌گیرد\n"
        "• رتبه‌بندی لحظه‌ای\n"
        "• هشدار رقابتی\n\n"
        "لطفا انتخاب کنید:",
        reply_markup=get_competition_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def create_competition_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ایجاد رقابت جدید"""
    user_id = update.effective_user.id
    context.user_data["creating_competition"] = True
    
    await update.message.reply_text(
        "🕒 **ساعت پایان رقابت**\n\n"
        "لطفا ساعت پایان رو انتخاب کنید:",
        reply_markup=get_end_time_keyboard()
    )

async def handle_end_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, end_time: str) -> None:
    """پردازش انتخاب زمان پایان"""
    user_id = update.effective_user.id
    
    if end_time == "✏️ زمان دلخواه":
        await update.message.reply_text(
            "⏰ زمان دلخواه را به فرمت زیر وارد کنید:\n"
            "مثال: 20:30 یا 21:15"
        )
        context.user_data["awaiting_custom_time"] = True
        return
    
    # حذف ایموجی از زمان
    clean_time = end_time.replace("🕐 ", "")
    context.user_data["competition_end_time"] = clean_time
    context.user_data["awaiting_password"] = True
    
    await update.message.reply_text(
        f"🕒 ساعت پایان: **{clean_time}**\n\n"
        f"🔐 **رمز ۴ رقمی برای اتاق وارد کنید:**\n"
        f"(این رمز رو به دوستانت بده تا بتونن بیایند)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True)
    )

async def handle_competition_password(update: Update, context: ContextTypes.DEFAULT_TYPE, password: str) -> None:
    """پردازش رمز اتاق"""
    user_id = update.effective_user.id
    
    if not password.isdigit() or len(password) != 4:
        await update.message.reply_text(
            "❌ رمز باید ۴ رقم باشد.\n"
            "لطفا مجدد وارد کنید:"
        )
        return
    
    end_time = context.user_data.get("competition_end_time")
    if not end_time:
        await update.message.reply_text("❌ خطا در اطلاعات.")
        return
    
    # ایجاد اتاق
    room_code = create_competition_room(user_id, end_time, password)
    
    if room_code:
        # دریافت نام واقعی کاربر
        try:
            chat_member = await context.bot.get_chat(user_id)
            if chat_member.first_name:
                user_display = chat_member.first_name
                if chat_member.last_name:
                    user_display += f" {chat_member.last_name}"
            elif chat_member.username:
                user_display = f"@{chat_member.username}"
            else:
                user_info = get_user_info(user_id)
                user_display = user_info["username"] if user_info else "شما"
        except Exception:
            user_info = get_user_info(user_id)
            user_display = user_info["username"] if user_info else "شما"
        
        # دریافت تاریخ و زمان ایران
        now_iran = datetime.now(IRAN_TZ)
        date_str = now_iran.strftime("%Y/%m/%d")
        time_str = now_iran.strftime("%H:%M")
        
        # ایجاد لینک دعوت
        invite_link = f"https://t.me/{context.bot.username}?start=join_{room_code}"
        
        # متن پیام با HTML
        message_text = (
            f"<b>✅ اتاق رقابت ساخته شد!</b>\n\n"
            f"<b>🏷 کد اتاق:</b> <code>{room_code}</code>\n"
            f"<b>🔐 رمز:</b> <code>{password}</code>\n"
            f"<b>🕒 تا ساعت:</b> <code>{end_time}</code>\n"
            f"<b>👥 حداقل:</b> ۵ نفر\n\n"
            f"<b>📅 تاریخ ایجاد:</b> {date_str}\n"
            f"<b>⏰ ساعت ایجاد:</b> {time_str}\n\n"
            f"<b>🔗 لینک دعوت:</b>\n"
            f"<code>{invite_link}</code>\n\n"
            f"<b>📋 دستورات مدیریت:</b>\n"
            f"برای مشاهده رتبه‌بندی: /room_{room_code}\n\n"
            f"<b>👥 اعضای اتاق:</b>\n"
            f"✅ {html.escape(user_display)} (سازنده)"
        )
        
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_competition_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ایجاد اتاق.\n"
            "ممکن است کد اتاق تکراری باشد یا مشکلی در دیتابیس وجود داشته باشد.",
            reply_markup=get_competition_keyboard()
        )
    
    # پاک کردن اطلاعات
    context.user_data.pop("creating_competition", None)
    context.user_data.pop("competition_end_time", None)
    context.user_data.pop("awaiting_password", None)
async def show_room_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE, room_code: str = None) -> None:
    """نمایش رتبه‌بندی اتاق"""
    # اگر room_code مستقیماً به عنوان آرگومان نیامده باشد
    if not room_code:
        if context.args:
            room_code = context.args[0]
        else:
            # اگر از پیام متنی آمده (/room_ABC123)
            if update.message and update.message.text:
                text = update.message.text.strip()
                if text.startswith('/room_'):
                    room_code = text.replace('/room_', '').upper()
    
    if not room_code or len(room_code) != 6:
        await update.message.reply_text(
            "❌ لطفا کد اتاق را وارد کنید.\n"
            "مثال: /room_D9L9B7"
        )
        return
    
    user_id = update.effective_user.id
    logger.info(f"🔍 نمایش رتبه‌بندی اتاق {room_code} برای کاربر {user_id}")
    
    try:
        # بررسی آیا کاربر در اتاق است
        user_room_info = get_user_room_info(user_id, room_code)
        if not user_room_info:
            await update.message.reply_text(
                f"❌ شما در اتاق {room_code} عضو نیستید.\n\n"
                f"برای پیوستن به اتاق:\n"
                f"۱. لینک دعوت را از سازنده اتاق بگیرید\n"
                f"۲. یا از دستور زیر استفاده کنید:\n"
                f"`/join_{room_code}`"
            )
            return
        
        room_info = get_room_info(room_code)
        if not room_info:
            await update.message.reply_text("❌ اتاق یافت نشد.")
            return
        
        rankings = get_room_ranking(room_code)
        
        # ساخت پیام با HTML
        text = f"<b>🏆 اتاق #{room_code}</b>\n"
        text += f"🕒 <b>تا ساعت:</b> {room_info['end_time']}\n"
        text += f"👥 <b>شرکت‌کنندگان:</b> {room_info['player_count']} نفر\n"
        text += f"📊 <b>وضعیت:</b> {'فعال' if room_info['status'] == 'active' else 'در انتظار'}\n\n"
        
        if room_info['status'] != 'active':
            text += f"⏳ منتظر {5 - room_info['player_count']} نفر دیگر...\n\n"
        
        text += "<b>🏅 رتبه‌بندی لحظه‌ای:</b>\n\n"
        
        # فقط ۵ نفر اول را نمایش بده
        for rank in rankings[:5]:
            medal = ""
            if rank["rank"] == 1:
                medal = "🥇"
            elif rank["rank"] == 2:
                medal = "🥈"
            elif rank["rank"] == 3:
                medal = "🥉"
            else:
                medal = f"{rank['rank']}."
            
            # دریافت نام واقعی کاربر از تلگرام
            try:
                chat_member = await context.bot.get_chat(rank["user_id"])
                if chat_member.first_name:
                    user_display = chat_member.first_name
                    if chat_member.last_name:
                        user_display += f" {chat_member.last_name}"
                elif chat_member.username:
                    user_display = f"@{chat_member.username}"
                else:
                    user_display = "کاربر"
            except Exception as e:
                logger.error(f"خطا در دریافت اطلاعات کاربر {rank['user_id']}: {e}")
                user_display = "کاربر"
            
            # اگر کاربر جاری هستیم
            is_you = " 👈 شما" if rank["user_id"] == user_id else ""
            
            # تبدیل زمان به فرمت زیبا
            total_minutes = rank["total_minutes"]
            hours = total_minutes // 60
            mins = total_minutes % 60
            
            if hours > 0 and mins > 0:
                time_display = f"{hours}h {mins}m"
            elif hours > 0:
                time_display = f"{hours}h"
            else:
                time_display = f"{mins}m"
            
            text += f"{medal} <b>{html.escape(user_display)}</b> ({time_display}){is_you}\n"
        
        # اطلاعات کاربر جاری
        if user_room_info:
            current_rank = next((r["rank"] for r in rankings if r["user_id"] == user_id), None)
            if current_rank:
                text += f"\n🎯 <b>موقعیت شما:</b> رتبه {current_rank}\n"
                
                # هشدار رقابتی
                if current_rank > 1 and len(rankings) > 0:
                    first_place = rankings[0]
                    gap = first_place["total_minutes"] - user_room_info["total_minutes"]
                    if gap > 0:
                        text += f"🔥 {gap} دقیقه با نفر اول فاصله داری!\n"
        
        text += f"\n⏰ هر لحظه می‌تونی رتبه‌ت رو بهتر کنی!"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_competition_keyboard()
        )
        
    except Exception as e:
        logger.error(f"❌ خطا در نمایش رتبه‌بندی اتاق: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ خطا در دریافت اطلاعات اتاق {room_code}.\n"
            "لطفا بعداً مجدد تلاش کنید.",
            reply_markup=get_competition_keyboard()
)
def create_competition_room(creator_id: int, end_time: str, password: str) -> Optional[str]:
    """ایجاد اتاق رقابت جدید با زمان ایران"""
    conn = None
    cursor = None
    
    try:
        room_code = generate_room_code()
        logger.info(f"🔍 ایجاد اتاق با کد: {room_code}")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # دریافت تاریخ و زمان ایران
        now_iran = datetime.now(IRAN_TZ)
        
        # ذخیره در دیتابیس به صورت UTC
        now_utc = now_iran.astimezone(pytz.UTC)
        
        logger.info(f"📅 زمان ایران: {now_iran.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📅 زمان UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ایجاد اتاق
        query = """
        INSERT INTO competition_rooms (room_code, creator_id, password, end_time, status, created_at)
        VALUES (%s, %s, %s, %s, 'waiting', %s)
        RETURNING room_code
        """
        
        cursor.execute(query, (room_code, creator_id, password, end_time, now_utc))
        result = cursor.fetchone()
        
        if not result:
            logger.error("❌ هیچ نتیجه‌ای از INSERT اتاق برگشت داده نشد")
            conn.rollback()
            return None
        
        # اضافه کردن سازنده به اتاق
        query2 = """
        INSERT INTO room_participants (room_code, user_id, joined_at)
        VALUES (%s, %s, %s)
        """
        
        cursor.execute(query2, (room_code, creator_id, now_utc))
        conn.commit()
        
        logger.info(f"✅ اتاق {room_code} با موفقیت ایجاد شد")
        return room_code
        
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد اتاق رقابت: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return None
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)
def join_competition_room(room_code: str, user_id: int, password: str) -> bool:
    """پیوستن به اتاق رقابت"""
    try:
        # بررسی وجود اتاق و رمز
        query = """
        SELECT room_code FROM competition_rooms 
        WHERE room_code = %s AND password = %s AND status != 'finished'
        """
        result = db.execute_query(query, (room_code, password), fetch=True)
        
        if not result:
            return False
        
        # بررسی آیا کاربر قبلاً عضو شده
        query_check = """
        SELECT user_id FROM room_participants 
        WHERE room_code = %s AND user_id = %s
        """
        check = db.execute_query(query_check, (room_code, user_id), fetch=True)
        
        if check:
            return True  # قبلاً عضو است
        
        # اضافه کردن کاربر به اتاق با زمان ایران
        now_iran = datetime.now(IRAN_TZ)
        query_join = """
        INSERT INTO room_participants (room_code, user_id, joined_at)
        VALUES (%s, %s, %s)
        """
        
        # 🔴 اصلاح: استفاده از now_iran به جای time.time()
        result = db.execute_query(query_join, (room_code, user_id, now_iran))
        
        # بررسی آیا حداقل تعداد رسیده
        query_count = """
        SELECT COUNT(*) FROM room_participants WHERE room_code = %s
        """
        count = db.execute_query(query_count, (room_code,), fetch=True)
        
        if count and count[0] >= 5:
            # شروع رقابت
            query_start = """
            UPDATE competition_rooms 
            SET status = 'active' 
            WHERE room_code = %s
            """
            db.execute_query(query_start, (room_code,))
        
        return True
        
    except Exception as e:
        logger.error(f"خطا در پیوستن به اتاق: {e}")
        return False

def get_room_info(room_code: str) -> Optional[Dict]:
    """دریافت اطلاعات اتاق با زمان ایران"""
    try:
        query = """
        SELECT cr.room_code, cr.creator_id, cr.end_time, cr.status,
               cr.created_at, u.username as creator_name,
               COUNT(rp.user_id) as player_count
        FROM competition_rooms cr
        JOIN users u ON cr.creator_id = u.user_id
        LEFT JOIN room_participants rp ON cr.room_code = rp.room_code
        WHERE cr.room_code = %s
        GROUP BY cr.room_code, cr.creator_id, cr.end_time, cr.status,
                 cr.created_at, u.username
        """
        
        result = db.execute_query(query, (room_code,), fetch=True)
        
        if result:
            room_code_db, creator_id, end_time, status, created_at, creator_name, player_count = result
            
            # تبدیل زمان ایجاد به وقت ایران
            if created_at:
                if isinstance(created_at, datetime):
                    if created_at.tzinfo is None:
                        created_at_utc = pytz.UTC.localize(created_at)
                        created_at_iran = created_at_utc.astimezone(IRAN_TZ)
                    else:
                        created_at_iran = created_at.astimezone(IRAN_TZ)
                    
                    created_at_str = created_at_iran.strftime("%Y/%m/%d %H:%M")
                else:
                    created_at_str = str(created_at)
            else:
                created_at_str = "نامشخص"
            
            return {
                "room_code": room_code_db,
                "creator_id": creator_id,
                "end_time": end_time,
                "status": status,
                "created_at": created_at_str,
                "creator_name": creator_name,
                "player_count": player_count
            }
        return None
        
    except Exception as e:
        logger.error(f"خطا در دریافت اطلاعات اتاق: {e}")
        return None
def get_room_ranking(room_code: str) -> List[Dict]:
    """دریافت رتبه‌بندی اتاق"""
    try:
        query = """
        SELECT rp.user_id, u.username, rp.total_minutes, 
               rp.current_subject, rp.current_topic,
               RANK() OVER (ORDER BY rp.total_minutes DESC) as rank
        FROM room_participants rp
        JOIN users u ON rp.user_id = u.user_id
        WHERE rp.room_code = %s
        ORDER BY rp.total_minutes DESC
        LIMIT 20
        """
        
        results = db.execute_query(query, (room_code,), fetchall=True)
        
        rankings = []
        for row in results:
            rankings.append({
                "user_id": row[0],
                "username": row[1],
                "total_minutes": row[2] or 0,
                "current_subject": row[3] or "",
                "current_topic": row[4] or "",
                "rank": row[5]
            })
        
        return rankings
        
    except Exception as e:
        logger.error(f"خطا در دریافت رتبه‌بندی اتاق: {e}")
        return []

def update_user_study_in_room(user_id: int, room_code: str, minutes: int, 
                             subject: str, topic: str) -> bool:
    """به‌روزرسانی مطالعه کاربر در اتاق"""
    try:
        query = """
        UPDATE room_participants
        SET total_minutes = total_minutes + %s,
            current_subject = %s,
            current_topic = %s
        WHERE user_id = %s AND room_code = %s
        """
        
        db.execute_query(query, (minutes, subject, topic, user_id, room_code))
        return True
        
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی مطالعه اتاق: {e}")
        return False

def get_user_room_info(user_id: int, room_code: str) -> Optional[Dict]:
    """دریافت اطلاعات کاربر در اتاق"""
    try:
        query = """
        SELECT rp.total_minutes, rp.current_subject, rp.current_topic,
               rp.last_rank, cr.end_time, cr.status,
               (SELECT COUNT(*) FROM room_participants WHERE room_code = %s) as total_players
        FROM room_participants rp
        JOIN competition_rooms cr ON rp.room_code = cr.room_code
        WHERE rp.user_id = %s AND rp.room_code = %s
        """
        
        result = db.execute_query(query, (room_code, user_id, room_code), fetch=True)
        
        if result:
            return {
                "total_minutes": result[0] or 0,
                "current_subject": result[1] or "",
                "current_topic": result[2] or "",
                "last_rank": result[3],
                "end_time": result[4],
                "room_status": result[5],
                "total_players": result[6] or 0
            }
        return None
        
    except Exception as e:
        logger.error(f"خطا در دریافت اطلاعات کاربر در اتاق: {e}")
        return None

def generate_room_code() -> str:
    """تولید کد اتاق"""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def award_room_winner(room_code: str) -> Optional[Dict]:
    """اعطای جایزه به برنده اتاق"""
    try:
        # دریافت نفر اول
        query = """
        SELECT user_id FROM room_participants
        WHERE room_code = %s
        ORDER BY total_minutes DESC
        LIMIT 1
        """
        
        result = db.execute_query(query, (room_code,), fetch=True)
        
        if not result:
            return None
        
        winner_id = result[0]
        
        # ایجاد کوپن برای برنده
        coupon = create_coupon(winner_id, "competition_winner")
        
        if coupon:
            return {
                "winner_id": winner_id,
                "coupon_code": coupon["coupon_code"],
                "value": coupon["value"]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"خطا در اعطای جایزه اتاق: {e}")
        return None


                    
async def check_and_finish_rooms_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی و اتمام اتاق‌های تمام‌شده (برنامه زمان‌بندی شده)"""
    try:
        now = datetime.now(IRAN_TZ)
        current_time_obj = now.time()  # دریافت time object
        current_time_str = now.strftime("%H:%M")  # برای نمایش
        current_date_str = now.strftime("%Y-%m-%d")
        
        logger.info(f"🔍 بررسی اتاق‌های تمام‌شده در ساعت {current_time_str}")
        
        # دریافت اتاق‌های فعال
        query = """
        SELECT room_code, end_time FROM competition_rooms
        WHERE status = 'active'
        """
        
        results = db.execute_query(query, fetchall=True)
        
        if results:
            logger.info(f"🔍 بررسی {len(results)} اتاق فعال...")
            
            for row in results:
                room_code, end_time_str = row
                
                # تبدیل end_time از رشته به time object
                try:
                    end_time_obj = datetime.strptime(end_time_str, "%H:%M").time()
                except ValueError:
                    logger.error(f"❌ فرمت زمان نامعتبر برای اتاق {room_code}: {end_time_str}")
                    continue
                
                logger.info(f"🔍 بررسی اتاق {room_code}: زمان پایان={end_time_str}, زمان جاری={current_time_str}")
                
                # مقایسه زمان‌ها
                # اگر زمان جاری بعد از زمان پایان باشد
                if current_time_obj >= end_time_obj:
                    logger.info(f"⏰ زمان اتاق {room_code} به پایان رسیده (پایان: {end_time_str}, جاری: {current_time_str})")
                    
                    # بررسی تعداد شرکت‌کنندگان
                    query_count = """
                    SELECT COUNT(*) FROM room_participants WHERE room_code = %s
                    """
                    count_result = db.execute_query(query_count, (room_code,), fetch=True)
                    player_count = count_result[0] if count_result else 0
                    
                    # اگر کمتر از ۵ نفر باشد، اتاق کنسل شود
                    if player_count < 5:
                        logger.info(f"❌ اتاق {room_code} کنسل شد: فقط {player_count} نفر")
                        
                        # تغییر وضعیت به کنسل شده
                        query_cancel = """
                        UPDATE competition_rooms
                        SET status = 'cancelled'
                        WHERE room_code = %s
                        """
                        db.execute_query(query_cancel, (room_code,))
                        
                        # اطلاع‌رسانی به همه شرکت‌کنندگان
                        query_participants = """
                        SELECT user_id FROM room_participants WHERE room_code = %s
                        """
                        participants = db.execute_query(query_participants, (room_code,), fetchall=True)
                        
                        if participants:
                            for participant in participants:
                                user_id = participant[0]
                                try:
                                    await context.bot.send_message(
                                        user_id,
                                        f"❌ <b>اتاق رقابت #{room_code} کنسل شد!</b>\n\n"
                                        f"متاسفانه تعداد شرکت‌کنندگان به حد نصاب ۵ نفر نرسید.\n"
                                        f"👥 تعداد شرکت‌کنندگان: {player_count} نفر\n\n"
                                        f"💡 می‌توانید با تعداد بیشتری از دوستان یک اتاق جدید بسازید.",
                                        parse_mode=ParseMode.HTML
                                    )
                                except Exception as e:
                                    logger.error(f"خطا در اطلاع کنسل شدن به کاربر {user_id}: {e}")
                    
                    # اگر ۵ نفر یا بیشتر باشد، اتاق پایان یابد و جایزه داده شود
                    else:
                        logger.info(f"✅ اتاق {room_code} پایان یافت: {player_count} نفر")
                        
                        # تغییر وضعیت به پایان یافته
                        query_finish = """
                        UPDATE competition_rooms
                        SET status = 'finished'
                        WHERE room_code = %s
                        """
                        db.execute_query(query_finish, (room_code,))
                        
                        # دریافت نفر اول
                        query_winner = """
                        SELECT rp.user_id, rp.total_minutes 
                        FROM room_participants rp
                        WHERE rp.room_code = %s
                        ORDER BY rp.total_minutes DESC
                        LIMIT 1
                        """
                        winner_result = db.execute_query(query_winner, (room_code,), fetch=True)
                        
                        if winner_result:
                            winner_id, winner_minutes = winner_result
                            
                            # ایجاد کوپن برای برنده
                            coupon = create_coupon(winner_id, "competition_winner")
                            
                            # اطلاع‌رسانی به همه شرکت‌کنندگان
                            query_participants = """
                            SELECT user_id, total_minutes 
                            FROM room_participants 
                            WHERE room_code = %s
                            ORDER BY total_minutes DESC
                            """
                            all_participants = db.execute_query(query_participants, (room_code,), fetchall=True)
                            
                            if all_participants:
                                # دریافت نام برنده از تلگرام
                                try:
                                    winner_chat = await context.bot.get_chat(winner_id)
                                    if winner_chat.first_name:
                                        winner_name = winner_chat.first_name
                                        if winner_chat.last_name:
                                            winner_name += f" {winner_chat.last_name}"
                                    elif winner_chat.username:
                                        winner_name = f"@{winner_chat.username}"
                                    else:
                                        winner_name = "برنده"
                                except:
                                    winner_name = "برنده"
                                
                                # متن رتبه‌بندی نهایی
                                ranking_text = "🏆 <b>رتبه‌بندی نهایی:</b>\n\n"
                                for i, (p_id, p_minutes) in enumerate(all_participants[:5], 1):
                                    # دریافت نام هر شرکت‌کننده
                                    try:
                                        p_chat = await context.bot.get_chat(p_id)
                                        if p_chat.first_name:
                                            p_name = p_chat.first_name
                                            if p_chat.last_name:
                                                p_name += f" {p_chat.last_name}"
                                        elif p_chat.username:
                                            p_name = f"@{p_chat.username}"
                                        else:
                                            p_name = "شرکت‌کننده"
                                    except:
                                        p_name = "شرکت‌کننده"
                                    
                                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1 if i <= 5 else 4]
                                    
                                    # تبدیل زمان
                                    hours = p_minutes // 60
                                    mins = p_minutes % 60
                                    time_display = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
                                    
                                    is_winner = " 🎉" if p_id == winner_id else ""
                                    ranking_text += f"{medal} {html.escape(p_name)}: {time_display}{is_winner}\n"
                                
                                # ارسال به همه شرکت‌کنندگان
                                for participant in all_participants:
                                    p_id = participant[0]
                                    
                                    is_winner = p_id == winner_id
                                    winner_message = ""
                                    
                                    if is_winner and coupon:
                                        winner_message = (
                                            f"\n🎉 <b>تبریک! شما برنده شدید!</b>\n"
                                            f"🎫 <b>کوپن جایزه:</b> <code>{coupon['coupon_code']}</code>\n"
                                            f"💰 <b>ارزش:</b> ۴۰,۰۰۰ تومان\n"
                                            f"📅 <b>تاریخ:</b> {coupon['earned_date']}\n\n"
                                            f"💡 از این کوپن برای خدمات مختلف استفاده کنید!"
                                        )
                                    
                                    try:
                                        await context.bot.send_message(
                                            p_id,
                                            f"🏁 <b>اتاق رقابت #{room_code} پایان یافت!</b>\n\n"
                                            f"🕒 <b>ساعت پایان:</b> {end_time_str}\n"
                                            f"📅 <b>تاریخ:</b> {current_date_str.replace('-', '/')}\n"
                                            f"👥 <b>تعداد شرکت‌کنندگان:</b> {player_count} نفر\n\n"
                                            f"{ranking_text}"
                                            f"{winner_message}",
                                            parse_mode=ParseMode.HTML
                                        )
                                    except Exception as e:
                                        logger.error(f"خطا در اطلاع پایان اتاق به کاربر {p_id}: {e}")
        
        logger.info(f"✅ بررسی اتاق‌ها تکمیل شد")
        
    except Exception as e:
        logger.error(f"❌ خطا در بررسی اتاق‌ها: {e}", exc_info=True)


async def set_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور تغییر شماره کارت ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if len(context.args) < 2:
        current_card = get_admin_card_info()
        
        text = f"""
🏦 <b>شماره کارت فعلی:</b>

📋 <b>اطلاعات کارت:</b>
• شماره: <code>{current_card['card_number']}</code>
• صاحب حساب: {escape_html_for_telegram(current_card['card_owner'])}
📝 <b>برای تغییر، از فرمت زیر استفاده کنید:</b>
<code>/set_card &lt;شماره_کارت&gt; &lt;نام_صاحب_کارت&gt;</code>

مثال:
<code>/set_card ۶۰۳۷-۹۹۹۹-۱۲۳۴-۵۶۷۸ علی_محمدی</code>
"""
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return
    
    card_number = context.args[0]
    card_owner = " ".join(context.args[1:])
    
    if set_admin_card_info(card_number, card_owner):
        date_str, time_str = get_iran_time()
        
        text = f"""
✅ <b>شماره کارت ذخیره شد!</b>

🏦 <b>اطلاعات جدید:</b>
• شماره کارت: <code>{card_number}</code>
• صاحب حساب: {escape_html_for_telegram(card_owner)}
• تاریخ تغییر: {date_str}
• زمان: {time_str}

📌 این شماره کارت از این پس برای خرید کوپن نمایش داده می‌شود.
"""
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
        # اطلاع به همه ادمین‌ها
        for admin_id in ADMIN_IDS:
            if admin_id != user_id:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"🏦 <b>شماره کارت تغییر کرد</b>\n\n"
                        f"توسط: {escape_html_for_telegram(update.effective_user.full_name or 'نامشخص')}\n"
                        f"شماره جدید: <code>{card_number}</code>\n"
                        f"صاحب حساب: {escape_html_for_telegram(card_owner)}\n"
                        f"زمان: {time_str}",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"خطا در اطلاع به ادمین {admin_id}: {e}")
    else:
        await update.message.reply_text("❌ خطا در ذخیره اطلاعات کارت.")


async def coupon_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش درخواست‌های کوپن برای ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    requests = get_pending_coupon_requests()
    
    if not requests:
        await update.message.reply_text(
            "📭 هیچ درخواست کوپنی در انتظار نیست.",
            reply_markup=get_admin_coupon_keyboard()
        )
        return
    
    text = f"📋 **درخواست‌های کوپن در انتظار: {len(requests)}**\n\n"
    
    for req in requests[:5]:
        username = req['username'] or "نامشخص"
        amount = f"{req['amount']:,} تومان" if req['amount'] else "رایگان"
        request_type = "🛒 خرید" if req['request_type'] == "purchase" else "🎫 استفاده"
        
        text += f"**{request_type}** - #{req['request_id']}\n"
        text += f"👤 {html.escape(username)} (آیدی: `{req['user_id']}`)\n"
        
        if req['service_type']:
            service_names = {
                'call': '📞 تماس تلفنی',
                'analysis': '📊 تحلیل گزارش',
                'correction': '✏️ تصحیح آزمون',
                'exam': '📝 آزمون شخصی',
                'test_analysis': '📈 تحلیل آزمون'
            }
            service = service_names.get(req['service_type'], req['service_type'])
            text += f"📋 خدمت: {service}\n"
        
        if req['amount']:
            text += f"💰 مبلغ: {amount}\n"
        
        text += f"📅 {req['created_at'].strftime('%Y/%m/%d %H:%M')}\n\n"
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_coupon_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def verify_coupon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأیید درخواست کوپن توسط ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت صحیح:\n"
            "/verify_coupon <شناسه_درخواست>\n\n"
            "مثال:\n"
            "/verify_coupon 123"
        )
        return
    
    try:
        request_id = int(context.args[0])
        
        if approve_coupon_request(request_id, f"تأیید شده توسط ادمین {user_id}"):
            await update.message.reply_text(
                f"✅ درخواست #{request_id} تأیید شد.\n"
                f"کوپن برای کاربر ایجاد و ارسال شد."
            )
        else:
            await update.message.reply_text(
                f"❌ خطا در تأیید درخواست #{request_id}.\n"
                f"ممکن است قبلاً تأیید شده باشد."
            )
            
    except ValueError:
        await update.message.reply_text("❌ شناسه باید عددی باشد.")
    except Exception as e:
        logger.error(f"خطا در تأیید کوپن: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")

async def coupon_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش آمار کوپن‌ها برای ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    try:
        # آمار کلی
        query_total = """
        SELECT 
            COUNT(*) as total_coupons,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_coupons,
            COUNT(CASE WHEN status = 'used' THEN 1 END) as used_coupons,
            COUNT(CASE WHEN coupon_source = 'study_streak' THEN 1 END) as study_coupons,
            COUNT(CASE WHEN coupon_source = 'purchased' THEN 1 END) as purchased_coupons,
            COALESCE(SUM(value), 0) as total_value
        FROM coupons
        """
        total_stats = db.execute_query(query_total, fetch=True)
        
        # آمار امروز
        date_str, _ = get_iran_time()
        query_today = """
        SELECT 
            COUNT(*) as today_coupons,
            COUNT(CASE WHEN coupon_source = 'study_streak' THEN 1 END) as today_study,
            COUNT(CASE WHEN coupon_source = 'purchased' THEN 1 END) as today_purchased,
            COALESCE(SUM(value), 0) as today_value
        FROM coupons
        WHERE earned_date = %s
        """
        today_stats = db.execute_query(query_today, (date_str,), fetch=True)
        
        # درخواست‌های در انتظار
        query_pending = """
        SELECT COUNT(*) FROM coupon_requests WHERE status = 'pending'
        """
        pending_count = db.execute_query(query_pending, fetch=True)
        
        text = f"""
📊 **آمار کامل سیستم کوپن**
────────────────────
📅 تاریخ: {date_str}

📈 **آمار کلی:**
• کل کوپن‌ها: {total_stats[0]:,}
• کوپن‌های فعال: {total_stats[1]:,}
• کوپن‌های استفاده‌شده: {total_stats[2]:,}
• کسب از مطالعه: {total_stats[3]:,}
• خریداری شده: {total_stats[4]:,}
• مجموع ارزش: {total_stats[5]:,} ریال

🎯 **امروز:**
• کوپن‌های امروز: {today_stats[0] if today_stats else 0}
• کسب از مطالعه: {today_stats[1] if today_stats else 0}
• خریداری شده: {today_stats[2] if today_stats else 0}
• ارزش امروز: {today_stats[3] if today_stats else 0:,} ریال

⏳ **در انتظار:**
• درخواست‌های بررسی: {pending_count[0] if pending_count else 0}

💎 **میانگین‌ها:**
• ارزش هر کوپن: ۴۰,۰۰۰ تومان
• ارزش کل: {total_stats[5] // 10:,} تومان
"""
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"خطا در دریافت آمار کوپن: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")
async def show_user_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """نمایش کوپن‌های کاربر"""
    logger.info(f"🔍 نمایش کوپن‌های کاربر {user_id}")
    
    try:
        # ابتدا بررسی کنیم که آیا کاربر فعال است
        if not is_user_active(user_id):
            await update.message.reply_text(
                "❌ حساب کاربری شما فعال نیست.\nلطفا منتظر تأیید ادمین باشید.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # دریافت کوپن‌های کاربر
        logger.info(f"🔍 فراخوانی get_user_coupons برای کاربر {user_id}...")
        active_coupons = get_user_coupons(user_id, "active")
        all_coupons = get_user_coupons(user_id)  # همه کوپن‌ها
        
        logger.info(f"🔍 نتایج: فعال={len(active_coupons)}، کل={len(all_coupons)}")
        
        # نمایش لاگ برای دیباگ
        for i, coupon in enumerate(all_coupons[:5]):
            logger.info(f"  🎫 کوپن {i+1}: {coupon['coupon_code']} - {coupon['status']} - {coupon['value']} ریال")
        
        if not all_coupons:
            logger.info(f"📭 کاربر {user_id} هیچ کوپنی ندارد")
            await update.message.reply_text(
                "📭 **شما هیچ کوپنی ندارید.**\n\n"
                "🛒 برای خرید کوپن از گزینه «🛒 خرید کوپن» استفاده کنید.\n"
                "⏰ یا با مطالعه مستمر می‌توانید کوپن کسب کنید.",
                reply_markup=get_coupon_management_keyboard()
            )
            return
        
        # محاسبه مجموع ارزش
        total_value = sum(c["value"] for c in all_coupons)
        used_coupons = [c for c in all_coupons if c["status"] == "used"]
        
        # ساخت پیام
        text = f"""
🎫 **کوپن‌های من**

📊 **آمار کلی:**
• کل کوپن‌ها: {len(all_coupons)}
• فعال: {len(active_coupons)}
• استفاده‌شده: {len(used_coupons)}
• مجموع ارزش: {total_value // 10:,} تومان
"""
        
        if active_coupons:
            text += "\n✅ **کوپن‌های فعال شما:**\n\n"
            for i, coupon in enumerate(active_coupons[:10], 1):
                source_emoji = "⏰" if coupon.get("source") == "study_streak" else "💳"
                text += f"{i}. {source_emoji} `{coupon['coupon_code']}`\n"
                text += f"   📅 {coupon.get('earned_date', 'نامشخص')} | "
                text += f"💰 {coupon['value'] // 10:,} تومان\n"
            
            if len(active_coupons) > 10:
                text += f"\n📊 و {len(active_coupons)-10} کوپن دیگر...\n"
        else:
            text += "\n📭 **هیچ کوپن فعالی ندارید.**\n"
        
        if used_coupons:
            text += "\n📋 **کوپن‌های استفاده‌شده:**\n"
            for i, coupon in enumerate(used_coupons[:3], 1):
                text += f"{i}. `{coupon['coupon_code']}` - "
                text += f"برای: {coupon.get('used_for', 'نامشخص')} | "
                text += f"تاریخ: {coupon.get('used_date', 'نامشخص')}\n"
            
            if len(used_coupons) > 3:
                text += f"... و {len(used_coupons)-3} کوپن دیگر\n"
        
        text += "\n💡 هر کوپن را می‌توانید برای هر خدمتی استفاده کنید."
        
        # ارسال پیام
        await update.message.reply_text(
            text,
            reply_markup=get_coupon_management_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ کوپن‌های کاربر {user_id} نمایش داده شد")
        
    except Exception as e:
        logger.error(f"❌ خطا در نمایش کوپن‌های کاربر {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ خطا در دریافت اطلاعات کوپن‌ها.\nلطفا مجدد تلاش کنید.",
            reply_markup=get_main_menu_keyboard()
        )

async def show_user_requests(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """نمایش درخواست‌های کاربر"""
    try:
        query = """
        SELECT request_id, request_type, service_type, amount, status, 
               created_at, admin_note
        FROM coupon_requests
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        results = db.execute_query(query, (user_id,), fetchall=True)
        
        if not results:
            text = "📭 **هیچ درخواستی ثبت نکرده‌اید.**"
        else:
            text = "📋 **درخواست‌های شما**\n\n"
            
            for row in results:
                request_id, request_type, service_type, amount, status, created_at, admin_note = row
                
                type_emoji = "🛒" if request_type == "purchase" else "🎫"
                status_emoji = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "completed": "🎉"
                }.get(status, "❓")
                
                text += f"{type_emoji} **درخواست #{request_id}**\n"
                text += f"{status_emoji} وضعیت: {status}\n"
                
                if service_type:
                    service_names = {
                        'call': '📞 تماس تلفنی',
                        'analysis': '📊 تحلیل گزارش',
                        'correction': '✏️ تصحیح آزمون',
                        'exam': '📝 آزمون شخصی',
                        'test_analysis': '📈 تحلیل آزمون'
                    }
                    service = service_names.get(service_type, service_type)
                    text += f"📋 خدمت: {service}\n"
                
                if amount:
                    text += f"💰 مبلغ: {amount:,} تومان\n"
                
                text += f"📅 تاریخ: {created_at.strftime('%Y/%m/%d %H:%M')}\n"
                
                if admin_note:
                    text += f"📝 پیام ادمین: {admin_note}\n"
                
                text += "─" * 15 + "\n"
        
        await update.message.reply_text(
            text,
            reply_markup=get_coupon_management_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"خطا در نمایش درخواست‌های کاربر: {e}")
        await update.message.reply_text(
            "❌ خطا در دریافت درخواست‌ها.",
            reply_markup=get_coupon_management_keyboard()
                )

async def send_midday_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال گزارش نیم‌روز ساعت 15:00 با تاریخ و ساعت شمسی"""
    try:
        logger.info("🕒 شروع ارسال گزارش‌های نیم‌روز...")
        
        now_iran = datetime.now(IRAN_TZ)
        
        # تبدیل به تاریخ و ساعت شمسی
        now_jdate = jdatetime.datetime.fromgregorian(datetime=now_iran)
        date_str = now_jdate.strftime("%Y/%m/%d")  # تاریخ شمسی
        time_str = now_iran.strftime("%H:%M")      # ساعت
        
        logger.info(f"📅 تاریخ گزارش: {date_str}")
        logger.info(f"⏰ ساعت گزارش: {time_str}")
        
        # دریافت کاربران فعال
        query = """
        SELECT user_id, username, grade, field
        FROM users
        WHERE is_active = TRUE
        """
        
        results = db.execute_query(query, fetchall=True)
        
        if not results:
            logger.info("📭 هیچ کاربر فعالی وجود ندارد")
            return
        
        total_sent = 0
        
        for row in results:
            user_id, username, grade, field = row
            
            # بررسی آیا قبلاً گزارش ارسال شده
            if check_report_sent_today(user_id, "midday"):
                continue
            
            try:
                # دریافت جلسات امروز
                today_jalali = date_str  # تاریخ شمسی امروز
                
                query_sessions = """
                SELECT subject, topic, minutes, start_time
                FROM study_sessions
                WHERE user_id = %s AND date = %s AND completed = TRUE
                ORDER BY start_time
                """
                
                today_sessions = db.execute_query(query_sessions, (user_id, today_jalali), fetchall=True)
                
                # دریافت رتبه هفتگی
                weekly_rank, weekly_minutes, gap_minutes = get_user_weekly_rank(user_id)
                
                # دریافت ۵ نفر برتر هفتگی
                top_weekly = get_weekly_rankings(limit=5)
                
                # ساخت گزارش با تاریخ و ساعت شمسی
                text = f"📊 <b>گزارش نیم‌روز شما</b>\n\n"
                text += f"📅 <b>تاریخ:</b> {date_str}\n"
                text += f"🕒 <b>زمان:</b> {time_str}\n\n"
                
                if today_sessions:
                    text += f"✅ <b>فعالیت‌های امروز:</b>\n"
                    
                    total_today = 0
                    for session in today_sessions:
                        subject, topic, minutes, start_time = session
                        total_today += minutes
                        
                        # زمان شروع جلسه
                        if start_time:
                            dt = datetime.fromtimestamp(start_time, IRAN_TZ)
                            session_time = dt.strftime("%H:%M")
                        else:
                            session_time = "??:??"
                        
                        # کوتاه کردن مبحث
                        topic_display = topic if topic and topic.strip() else "بدون مبحث"
                        if len(topic_display) > 30:
                            topic_display = topic_display[:30] + "..."
                        
                        text += f"• {session_time} | {subject} - {topic_display} | {minutes} دقیقه\n"
                    
                    text += f"\n📈 <b>آمار امروز:</b>\n"
                    text += f"⏰ مجموع: {total_today} دقیقه ({total_today//60} ساعت و {total_today%60} دقیقه)\n"
                    text += f"📖 جلسات: {len(today_sessions)} جلسه\n"
                else:
                    text += f"📭 <b>هیچ فعالیتی امروز ثبت نکرده‌اید.</b>\n\n"
                    text += f"🔥 <i>هنوز فرصت داری! همین الان یک جلسه شروع کن!</i>\n\n"
                
                text += f"\n🏆 <b>۵ نفر برتر هفتگی:</b>\n"
                for i, rank in enumerate(top_weekly[:5], 1):
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
                    
                    user_display = rank["username"] or "کاربر"
                    if user_display == "None":
                        user_display = "کاربر"
                    
                    hours = rank["total_minutes"] // 60
                    mins = rank["total_minutes"] % 60
                    
                    if hours > 0 and mins > 0:
                        time_display = f"{hours}h {mins}m"
                    elif hours > 0:
                        time_display = f"{hours}h"
                    else:
                        time_display = f"{mins}m"
                    
                    text += f"{medal} {user_display} ({rank['grade']} {rank['field']}): {time_display}\n"
                
                if weekly_rank:
                    text += f"\n📊 <b>موقعیت شما در هفته:</b>\n"
                    text += f"🎯 شما در رتبه <b>{weekly_rank}</b> جدول هفتگی هستید\n"
                    
                    if gap_minutes > 0 and weekly_rank > 5:
                        text += f"⏳ <b>{gap_minutes}</b> دقیقه تا ۵ نفر اول فاصله دارید\n"
                    
                    weekly_hours = weekly_minutes // 60
                    weekly_mins = weekly_minutes % 60
                    if weekly_hours > 0 and weekly_mins > 0:
                        weekly_display = f"{weekly_hours}h {weekly_mins}m"
                    elif weekly_hours > 0:
                        weekly_display = f"{weekly_hours}h"
                    else:
                        weekly_display = f"{weekly_mins}m"
                    
                    text += f"⏰ مطالعه هفتگی شما: {weekly_display}\n"
                
                # نقل قول انگیزشی
                import random
                midday_quotes = [
                    "💪 نصف روز فوق‌العاده بود! ادامه بده!",
                    "🌟 تا اینجا عالی بودی، نصفه روز مونده!",
                    "🔥 انرژی‌ت رو حفظ کن! بعدازظهر هم می‌توني بدرخشی!",
                    "📚 هر دقیقه مطالعه، یک قدم به هدفت نزدیکترت می‌کنه!",
                    "🎯 نصف روز تموم شد، ولی هنوز فرصت برای بهتر کردی!",
                    "✨ ادامه بده! عصر هم می‌تونی عالی باشی!"
                ]
                
                text += f"\n\n<i>{random.choice(midday_quotes)}</i>"
                
                # ارسال گزارش
                await context.bot.send_message(
                    user_id,
                    text,
                    parse_mode=ParseMode.HTML
                )
                
                # علامت‌گذاری ارسال شده
                mark_report_sent(user_id, "midday")
                total_sent += 1
                
                logger.info(f"✅ گزارش نیم‌روز برای کاربر {user_id} ارسال شد - {len(today_sessions) if today_sessions else 0} جلسه")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"خطا در ارسال گزارش به کاربر {user_id}: {e}")
                continue
        
        logger.info(f"✅ گزارش نیم‌روز به {total_sent} کاربر ارسال شد")
        
    except Exception as e:
        logger.error(f"خطا در ارسال گزارش‌های نیم‌روز: {e}", exc_info=True)

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /report - نمایش گزارش مطالعه ۲۴ ساعت گذشته"""
    user_id = update.effective_user.id
    
    if not is_user_active(user_id):
        await update.message.reply_text("❌ حساب کاربری شما فعال نیست.")
        return
    
    try:
        now_iran = datetime.now(IRAN_TZ)
        yesterday_iran = now_iran - timedelta(hours=24)
        
        # تبدیل به تاریخ شمسی
        now_jdate = jdatetime.datetime.fromgregorian(datetime=now_iran)
        now_jalali = now_jdate.strftime("%Y/%m/%d")
        
        now_timestamp = int(now_iran.timestamp())
        yesterday_timestamp = int(yesterday_iran.timestamp())
        
        logger.info(f"📊 گزارش ۲۴ساعته برای کاربر {user_id}")
        logger.info(f"   الان در ایران: {now_iran.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   ۲۴ ساعت قبل: {yesterday_iran.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   بازه تایم‌استمپ: {yesterday_timestamp} تا {now_timestamp}")
        
        # دریافت جلسات ۲۴ ساعت گذشته
        query = """
        SELECT 
            session_id,
            subject,
            topic,
            minutes,
            start_time,
            date
        FROM study_sessions
        WHERE 
            user_id = %s 
            AND completed = TRUE
            AND start_time >= %s
            AND start_time <= %s
        ORDER BY start_time DESC
        """
        
        results = db.execute_query(query, (user_id, yesterday_timestamp, now_timestamp), fetchall=True)
        
        logger.info(f"   تعداد جلسات پیدا شده: {len(results) if results else 0}")
        
        if results:
            for r in results:
                dt = datetime.fromtimestamp(r[4], IRAN_TZ)
                logger.info(f"     → {r[1]} | {r[3]}د | {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # محاسبه آمار
            total_minutes = sum(r[3] for r in results)
            total_sessions = len(results)
            
            # گروه‌بندی بر اساس درس
            subjects_summary = {}
            sessions_by_hour = {}
            
            for r in results:
                session_id, subject, topic, minutes, start_time, date = r
                
                # خلاصه دروس
                subjects_summary[subject] = subjects_summary.get(subject, 0) + minutes
                
                # گروه‌بندی ساعتی
                dt = datetime.fromtimestamp(start_time, IRAN_TZ)
                hour_key = dt.strftime("%H:00")
                sessions_by_hour[hour_key] = sessions_by_hour.get(hour_key, 0) + 1
            
            # ساخت گزارش با تاریخ شمسی
            text = f"📊 <b>گزارش ۲۴ ساعت گذشته</b>\n\n"
            text += f"⏰ بازه: {yesterday_iran.strftime('%H:%M')} - {now_iran.strftime('%H:%M')}\n"
            text += f"📅 تاریخ: {now_jalali}\n\n"
            
            # آمار کلی
            text += f"📈 <b>آمار کلی:</b>\n"
            text += f"• مجموع مطالعه: <b>{total_minutes}</b> دقیقه ({total_minutes//60} ساعت و {total_minutes%60} دقیقه)\n"
            text += f"• تعداد جلسات: <b>{total_sessions}</b> جلسه\n"
            avg_minutes = total_minutes // total_sessions if total_sessions > 0 else 0
            text += f"• میانگین هر جلسه: <b>{avg_minutes}</b> دقیقه\n\n"
            
            # خلاصه دروس
            if subjects_summary:
                text += f"📚 <b>خلاصه دروس:</b>\n"
                sorted_subjects = sorted(subjects_summary.items(), key=lambda x: x[1], reverse=True)
                for subject, minutes in sorted_subjects:
                    percentage = (minutes / total_minutes) * 100 if total_minutes > 0 else 0
                    bar_length = int(percentage / 5)
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    text += f"• {subject}: <b>{minutes}</b> دقیقه ({percentage:.1f}%)\n"
                    text += f"  {bar}\n"
                text += "\n"
            
            # جزئیات جلسات
            text += f"📋 <b>جزئیات جلسات (از جدید به قدیم):</b>\n\n"
            
            for i, r in enumerate(results[:10], 1):
                session_id, subject, topic, minutes, start_time, date = r
                
                dt = datetime.fromtimestamp(start_time, IRAN_TZ)
                time_str = dt.strftime("%H:%M")
                
                # تبدیل تاریخ هر جلسه به شمسی
                session_jdate = jdatetime.datetime.fromgregorian(datetime=dt)
                date_str = session_jdate.strftime("%Y/%m/%d")
                
                topic_display = topic if topic and topic.strip() else "بدون مبحث"
                if len(topic_display) > 35:
                    topic_display = topic_display[:35] + "..."
                
                text += f"{i}. <b>{date_str} {time_str}</b>\n"
                text += f"   📚 {subject} - {topic_display}\n"
                text += f"   ⏱ {minutes} دقیقه\n\n"
            
            if len(results) > 10:
                text += f"📌 و {len(results) - 10} جلسه دیگر...\n\n"
            
            # توزیع ساعتی
            if sessions_by_hour:
                text += f"⏰ <b>توزیع ساعتی مطالعه:</b>\n"
                sorted_hours = sorted(sessions_by_hour.items())
                for hour, count in sorted_hours:
                    bar_length = count * 2
                    bar = "█" * bar_length
                    text += f"• {hour}: {bar} {count} جلسه\n"
                text += "\n"
            
            # رکوردها
            if results:
                max_session = max(results, key=lambda x: x[3])
                text += f"🏆 <b>رکوردها:</b>\n"
                text += f"• طولانی‌ترین جلسه: <b>{max_session[3]}</b> دقیقه ({max_session[1]})\n"
            
            # مقایسه با دیروز
            two_days_ago = now_iran - timedelta(hours=48)
            two_days_ago_timestamp = int(two_days_ago.timestamp())
            
            query_yesterday = """
            SELECT COALESCE(SUM(minutes), 0)
            FROM study_sessions
            WHERE 
                user_id = %s 
                AND completed = TRUE
                AND start_time >= %s
                AND start_time < %s
            """
            
            yesterday_total = db.execute_query(
                query_yesterday,
                (user_id, two_days_ago_timestamp, yesterday_timestamp),
                fetch=True
            )
            yesterday_total = yesterday_total[0] if yesterday_total else 0
            
            if yesterday_total > 0:
                diff = total_minutes - yesterday_total
                if diff > 0:
                    text += f"📈 نسبت به دیروز (همین بازه): <b>+{diff}</b> دقیقه 🎉\n"
                elif diff < 0:
                    text += f"📉 نسبت به دیروز (همین بازه): <b>{diff}</b> دقیقه 😔\n"
                else:
                    text += f"📊 نسبت به دیروز (همین بازه): بدون تغییر\n"
            
            # نقل قول انگیزشی
            import random
            
            if total_minutes >= 300:
                quotes = [
                    "🔥 عالی بود! این یعنی پیشرفت فوق‌العاده!",
                    "🌟 تو یک ستاره‌ای! ادامه بده!",
                    "💪 این حجم مطالعه یعنی اراده پولادین!"
                ]
            elif total_minutes >= 180:
                quotes = [
                    "👍 خیلی خوب بود! فردا بهتر می‌شه!",
                    "📚 مسیر درست رو داری می‌ری!",
                    "✨ با همین روند ادامه بده!"
                ]
            elif total_minutes >= 60:
                quotes = [
                    "🔄 خوب بود، ولی می‌تونی بهتر بشی!",
                    "🎯 فردا بیشتر تلاش کن!",
                    "💡 شروع خوبی داشتی!"
                ]
            else:
                quotes = [
                    "🌱 از یه جا باید شروع کرد! فردا بیشتر!",
                    "⏰ فردا روز بهتری می‌سازیم!",
                    "💪 فردا رو قول بده بیشتر بخونی!"
                ]
            
            text += f"\n<i>{random.choice(quotes)}</i>"
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_main_menu_keyboard()
            )
            
        else:
            # اگر جلسه‌ای پیدا نشد - با تاریخ شمسی
            query_last = """
            SELECT 
                session_id,
                subject,
                topic,
                minutes,
                start_time,
                date
            FROM study_sessions
            WHERE user_id = %s AND completed = TRUE
            ORDER BY start_time DESC
            LIMIT 3
            """
            
            last_sessions = db.execute_query(query_last, (user_id,), fetchall=True)
            
            text = f"""📭 <b>گزارش ۲۴ ساعت گذشته</b>

⏰ بازه: {yesterday_iran.strftime('%H:%M')} - {now_iran.strftime('%H:%M')}
📅 تاریخ: {now_jalali}

❌ <b>هیچ جلسه‌ای در ۲۴ ساعت گذشته ثبت نشده!</b>"""

            if last_sessions:
                text += "\n\n📊 <b>آخرین جلسات شما:</b>"
                for session in last_sessions:
                    dt = datetime.fromtimestamp(session[4], IRAN_TZ)
                    hours_ago = (now_iran - dt).total_seconds() / 3600
                    
                    # تبدیل تاریخ به شمسی
                    session_jdate = jdatetime.datetime.fromgregorian(datetime=dt)
                    date_str = session_jdate.strftime("%Y/%m/%d")
                    
                    topic_display = session[2] if session[2] and session[2].strip() else "بدون مبحث"
                    if len(topic_display) > 30:
                        topic_display = topic_display[:30] + "..."
                    
                    text += f"\n• {session[1]} - {topic_display}"
                    text += f"\n  {session[3]} دقیقه | {date_str} {dt.strftime('%H:%M')} ({hours_ago:.1f} ساعت پیش)\n"
            
            text += "\n\n🔥 برای شروع یک جلسه جدید از منوی اصلی استفاده کن!"
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_main_menu_keyboard()
            )
        
        logger.info(f"✅ گزارش برای کاربر {user_id} ارسال شد - {len(results) if results else 0} جلسه")
        
    except Exception as e:
        logger.error(f"❌ خطا در گزارش ۲۴ ساعت برای کاربر {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ خطا در دریافت گزارش. لطفا مجدد تلاش کنید.",
            reply_markup=get_main_menu_keyboard()
            )            
            

    

                
                
                
async def send_night_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال گزارش شبانه ساعت 23:00 با تاریخ و ساعت شمسی"""
    try:
        logger.info("🌙 شروع ارسال گزارش‌های شبانه...")
        
        now_iran = datetime.now(IRAN_TZ)
        
        # تبدیل به تاریخ و ساعت شمسی
        now_jdate = jdatetime.datetime.fromgregorian(datetime=now_iran)
        date_str = now_jdate.strftime("%Y/%m/%d")  # تاریخ شمسی
        time_str = now_iran.strftime("%H:%M")      # ساعت
        
        # تاریخ دیروز به شمسی
        yesterday_iran = now_iran - timedelta(days=1)
        yesterday_jdate = jdatetime.datetime.fromgregorian(datetime=yesterday_iran)
        yesterday_str = yesterday_jdate.strftime("%Y/%m/%d")
        
        logger.info(f"📅 تاریخ گزارش: {date_str}")
        logger.info(f"⏰ ساعت گزارش: {time_str}")
        
        # دریافت کاربران فعال
        query = """
        SELECT user_id, username, grade, field
        FROM users
        WHERE is_active = TRUE
        """
        
        results = db.execute_query(query, fetchall=True)
        
        if not results:
            logger.info("📭 هیچ کاربر فعالی وجود ندارد")
            return
        
        total_sent = 0
        
        for row in results:
            user_id, username, grade, field = row
            
            # بررسی آیا قبلاً گزارش ارسال شده
            if check_report_sent_today(user_id, "night"):
                continue
            
            try:
                # دریافت جلسات امروز با جزئیات کامل
                query_sessions_detail = """
                SELECT subject, topic, minutes, start_time
                FROM study_sessions
                WHERE user_id = %s AND date = %s AND completed = TRUE
                ORDER BY start_time
                """
                
                today_sessions = db.execute_query(query_sessions_detail, (user_id, date_str), fetchall=True)
                
                # دریافت آمار دیروز
                query_yesterday_total = """
                SELECT COALESCE(SUM(minutes), 0)
                FROM study_sessions
                WHERE user_id = %s AND date = %s AND completed = TRUE
                """
                
                yesterday_total = db.execute_query(query_yesterday_total, (user_id, yesterday_str), fetch=True)
                yesterday_minutes = yesterday_total[0] if yesterday_total else 0
                
                # دریافت رتبه هفتگی
                weekly_rank, weekly_minutes, gap_minutes = get_user_weekly_rank(user_id)
                
                # ساخت گزارش
                text = f"🌙 <b>گزارش پایان روز شما</b>\n\n"
                text += f"📅 <b>تاریخ:</b> {date_str}\n"
                text += f"🕒 <b>زمان:</b> {time_str}\n\n"
                
                if today_sessions:
                    text += f"✅ <b>جلسات امروز (به تفکیک مبحث):</b>\n"
                    
                    subjects = {}
                    total_today = 0
                    
                    for session in today_sessions:
                        subject, topic, minutes, start_time = session
                        total_today += minutes
                        
                        # زمان شروع جلسه
                        if start_time:
                            dt = datetime.fromtimestamp(start_time, IRAN_TZ)
                            start_time_str = dt.strftime("%H:%M")
                        else:
                            start_time_str = "??:??"
                        
                        # کوتاه کردن مبحث
                        topic_display = topic if topic and topic.strip() else "بدون مبحث"
                        if len(topic_display) > 40:
                            topic_display = topic_display[:40] + "..."
                        
                        text += f"• {start_time_str} | <b>{subject}</b> - {topic_display} | {minutes} دقیقه\n"
                        
                        # جمع‌زنی برای خلاصه دروس
                        subjects[subject] = subjects.get(subject, 0) + minutes
                    
                    # نمایش خلاصه دروس
                    if len(subjects) > 1:
                        text += f"\n📊 <b>خلاصه دروس:</b>\n"
                        for subject, total in subjects.items():
                            text += f"• {subject}: {total} دقیقه\n"
                    
                    text += f"\n📈 <b>آمار کامل امروز:</b>\n"
                    text += f"⏰ مجموع مطالعه: {total_today} دقیقه ({total_today//60} ساعت و {total_today%60} دقیقه)\n"
                    text += f"📖 تعداد جلسات: {len(today_sessions)}\n"
                    
                    # مقایسه با دیروز
                    if yesterday_minutes > 0:
                        difference = total_today - yesterday_minutes
                        if difference > 0:
                            text += f"📈 نسبت به دیروز ({yesterday_str}): <b>+{difference}</b> دقیقه بهبود 🎉\n"
                        elif difference < 0:
                            text += f"📉 نسبت به دیروز ({yesterday_str}): <b>{abs(difference)}</b> دقیقه کاهش 😔\n"
                        else:
                            text += f"📊 نسبت به دیروز ({yesterday_str}): بدون تغییر\n"
                    else:
                        text += f"🎯 اولین روز مطالعه! آفرین! 🎉\n"
                    
                    # دریافت رتبه امروز
                    query_rank_today = """
                    SELECT COUNT(*) + 1 
                    FROM daily_rankings dr
                    JOIN users u ON dr.user_id = u.user_id
                    WHERE dr.date = %s AND dr.total_minutes > %s AND u.is_active = TRUE
                    """
                    
                    # تبدیل تاریخ شمسی به میلادی برای جستجو در daily_rankings
                    today_gregorian = now_iran.strftime("%Y-%m-%d")
                    
                    rank_today = db.execute_query(query_rank_today, (today_gregorian, total_today), fetch=True)
                    if rank_today and rank_today[0]:
                        text += f"🏅 رتبه امروز: {rank_today[0]}\n"
                
                else:
                    text += f"📭 <b>امروز هیچ مطالعه‌ای ثبت نکردید.</b>\n\n"
                    text += f"😔 نگران نباش! فردا یک روز جدید است!\n"
                    text += f"💪 می‌تونی فردا با یک جلسه ۳۰ دقیقه‌ای شروع کنی.\n\n"
                    total_today = 0
                
                # اطلاعات هفتگی
                if weekly_rank:
                    text += f"\n📅 <b>آمار هفتگی:</b>\n"
                    text += f"🎯 رتبه هفتگی: {weekly_rank}\n"
                    
                    weekly_hours = weekly_minutes // 60
                    weekly_mins = weekly_minutes % 60
                    if weekly_hours > 0 and weekly_mins > 0:
                        weekly_display = f"{weekly_hours} ساعت و {weekly_mins} دقیقه"
                    elif weekly_hours > 0:
                        weekly_display = f"{weekly_hours} ساعت"
                    else:
                        weekly_display = f"{weekly_mins} دقیقه"
                    
                    text += f"⏰ مطالعه هفتگی: {weekly_display}\n"
                    
                    if gap_minutes > 0 and weekly_rank > 5:
                        text += f"🎯 <b>{gap_minutes}</b> دقیقه تا ۵ نفر اول فاصله دارید\n"
                    elif weekly_rank <= 5:
                        text += f"🏆 شما جزو ۵ نفر برتر هفته هستید! تبریک!\n"
                
                # پیشنهاد هدف فردا
                text += f"\n💡 <b>هدف پیشنهادی برای فردا:</b>\n"
                if total_today > 0:
                    target = total_today + 30
                    target_hours = target // 60
                    target_mins = target % 60
                    if target_hours > 0 and target_mins > 0:
                        target_display = f"{target_hours} ساعت و {target_mins} دقیقه"
                    elif target_hours > 0:
                        target_display = f"{target_hours} ساعت"
                    else:
                        target_display = f"{target_mins} دقیقه"
                    
                    text += f"🎯 <b>{target_display}</b> (۳۰ دقیقه بیشتر از امروز)\n"
                    
                    # پیشنهاد درس خاص بر اساس بیشترین مطالعه امروز
                    if today_sessions and subjects:
                        most_studied = max(subjects.items(), key=lambda x: x[1])
                        text += f"📚 ادامه دادن <b>{most_studied[0]}</b> می‌تونه عالی باشه!\n"
                else:
                    text += f"🎯 حداقل <b>۶۰ دقیقه</b> مطالعه\n"
                    text += f"📚 با یک درس مورد علاقه شروع کن!\n"
                
                # اضافه کردن نقل قول انگیزشی
                import random
                night_quotes = [
                    "✨ هر دقیقه‌ای که می‌خونی، به هدفت نزدیک‌تر می‌شی!",
                    "🌟 فردا روز بهتری می‌سازیم!",
                    "💪 تو می‌تونی! فقط کافیه شروع کنی.",
                    "🎯 موفقیت یعنی تکرار کارهای کوچک هر روز.",
                    "📚 مطالعه امروز، سرمایه فرداست.",
                    "⭐ فردا فرصت جدیدیه برای درخشیدن!",
                    "🌙 شب بخیر و فردایی پر از موفقیت!",
                    "📖 کتاب‌هایی که امروز خوندی، فردا تو رو می‌سازن!"
                ]
                
                text += f"\n\n<i>{random.choice(night_quotes)}</i>\n"
                text += f"\n🌙 شب بخیر و فردایی پرانرژی! ✨"
                
                # ارسال گزارش
                await context.bot.send_message(
                    user_id,
                    text,
                    parse_mode=ParseMode.HTML
                )
                
                # علامت‌گذاری ارسال شده
                mark_report_sent(user_id, "night")
                total_sent += 1
                
                logger.info(f"✅ گزارش شبانه برای کاربر {user_id} ارسال شد - {len(today_sessions) if today_sessions else 0} جلسه")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"خطا در ارسال گزارش شبانه به کاربر {user_id}: {e}")
                continue
        
        logger.info(f"✅ گزارش شبانه به {total_sent} کاربر ارسال شد")
        
    except Exception as e:
        logger.error(f"خطا در ارسال گزارش‌های شبانه: {e}", exc_info=True)
def convert_date_format(date_str: str) -> str:
    """تبدیل تاریخ از YYYY/MM/DD به YYYY-MM-DD"""
    if '/' in date_str:
        return date_str.replace('/', '-')
    return date_str
async def debug_daily_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی آمار daily_rankings"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    try:
        date_str, _ = get_iran_time()
        yesterday = (datetime.now(IRAN_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        query = """
        SELECT date, user_id, total_minutes 
        FROM daily_rankings 
        WHERE date IN (%s, %s)
        ORDER BY date DESC, total_minutes DESC
        """
        
        results = db.execute_query(query, (date_str, yesterday), fetchall=True)
        
        text = f"📊 آمار daily_rankings\n\n"
        text += f"📅 امروز ({date_str}):\n"
        today_users = [r for r in results if r[0] == date_str]
        
        if today_users:
            for row in today_users:
                text += f"👤 {row[1]}: {row[2]} دقیقه\n"
        else:
            text += "📭 هیچ رکوردی\n"
        
        text += f"\n📅 دیروز ({yesterday}):\n"
        yesterday_users = [r for r in results if r[0] == yesterday]
        
        if yesterday_users:
            for row in yesterday_users:
                text += f"👤 {row[1]}: {row[2]} دقیقه\n"
        else:
            text += "📭 هیچ رکوردی\n"
        
        # همچنین آمار از study_sessions
        query_sessions = """
        SELECT date, COUNT(*), SUM(minutes)
        FROM study_sessions 
        WHERE completed = TRUE AND date LIKE '2025-12-%'
        GROUP BY date
        ORDER BY date DESC
        LIMIT 5
        """
        sessions_stats = db.execute_query(query_sessions, fetchall=True)
        
        text += f"\n📋 آمار جلسات ۵ روز اخیر:\n"
        if sessions_stats:
            for date, count, total in sessions_stats:
                text += f"📅 {date}: {count} جلسه، {total or 0} دقیقه\n"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        logger.error(f"خطا در بررسی آمار daily_rankings: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")

def check_report_sent_today(user_id: int, report_type: str) -> bool:
    """بررسی آیا گزارش امروز ارسال شده است"""
    try:
        date_str, _ = get_iran_time()
        
        if report_type == "midday":
            field = "received_midday_report"
        elif report_type == "night":
            field = "received_night_report"
        else:
            return True  # اگر نوع ناشناخته، ارسال نکن
        
        query = f"""
        SELECT {field} FROM user_activities
        WHERE user_id = %s AND date = %s
        """
        
        result = db.execute_query(query, (user_id, date_str), fetch=True)
        
        if result and result[0]:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"خطا در بررسی گزارش ارسال شده: {e}")
        return False  # اگر خطا، ارسال کن
def create_half_coupon(user_id: int, source: str = "encouragement") -> Optional[Dict]:
    """ایجاد نیم‌کوپن ۲۰,۰۰۰ تومانی با اعتبار نامحدود"""
    try:
        date_str, time_str = get_iran_time()
        coupon_code = generate_coupon_code(user_id)
        
        # اضافه کردن ستون is_half_coupon اگر وجود ندارد
        # ابتدا بررسی کنیم ستون وجود دارد یا نه
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود ستون is_half_coupon
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='coupons' AND column_name='is_half_coupon'
        """)
        
        if not cursor.fetchone():
            # اضافه کردن ستون
            cursor.execute("ALTER TABLE coupons ADD COLUMN is_half_coupon BOOLEAN DEFAULT FALSE")
            conn.commit()
            logger.info("✅ ستون is_half_coupon به جدول coupons اضافه شد")
        
        cursor.close()
        db.return_connection(conn)
        
        # درج نیم‌کوپن (بدون تاریخ انقضا)
        query = """
        INSERT INTO coupons (user_id, coupon_code, coupon_source, value, 
                           earned_date, status, verified_by_admin, is_half_coupon)
        VALUES (%s, %s, %s, %s, %s, 'active', TRUE, TRUE)
        RETURNING coupon_id, coupon_code, earned_date, value
        """
        
        result = db.execute_query(query, 
            (user_id, coupon_code, source, 20000, date_str), fetch=True)
        
        if result:
            logger.info(f"✅ نیم‌کوپن ایجاد شد: {coupon_code} برای کاربر {user_id} (اعتبار نامحدود)")
            return {
                "coupon_id": result[0],
                "coupon_code": result[1],
                "earned_date": result[2],
                "value": result[3] if len(result) > 3 else 20000,
                "is_half_coupon": True,
                "source": source
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد نیم‌کوپن: {e}", exc_info=True)
        return None
def combine_half_coupons(user_id: int, coupon_code1: str, coupon_code2: str) -> Optional[str]:
    """ترکیب دو نیم‌کوپن برای ساخت یک کوپن کامل"""
    conn = None
    cursor = None
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        logger.info(f"🔄 تلاش برای ترکیب نیم‌کوپن‌ها: {coupon_code1} و {coupon_code2} برای کاربر {user_id}")
        
        # بررسی کوپن‌ها
        cursor.execute("""
        SELECT coupon_id, coupon_code, status, is_half_coupon, user_id, value
        FROM coupons 
        WHERE coupon_code IN (%s, %s) AND status = 'active'
        """, (coupon_code1, coupon_code2))
        
        coupons = cursor.fetchall()
        
        if len(coupons) != 2:
            logger.error(f"❌ کوپن‌ها معتبر نیستند - تعداد پیدا شده: {len(coupons)}")
            return None
        
        # بررسی مالکیت و نوع کوپن‌ها
        for coupon in coupons:
            if coupon[4] != user_id:
                logger.error(f"❌ کوپن {coupon[1]} متعلق به کاربر {coupon[4]} است نه کاربر {user_id}")
                return None
            if not coupon[3]:  # اگر نیم‌کوپن نباشد
                logger.error(f"❌ کوپن {coupon[1]} نیم‌کوپن نیست (is_half_coupon={coupon[3]})")
                return None
        
        # ایجاد کوپن کامل جدید
        date_str, time_str = get_iran_time()
        full_coupon_code = generate_coupon_code(user_id)
        
        logger.info(f"🎫 ایجاد کوپن کامل جدید: {full_coupon_code}")
        
        cursor.execute("""
        INSERT INTO coupons (user_id, coupon_code, coupon_source, value, 
                           earned_date, status, verified_by_admin, is_half_coupon)
        VALUES (%s, %s, %s, %s, %s, 'active', TRUE, FALSE)
        RETURNING coupon_id
        """, (user_id, full_coupon_code, "combined", 40000, date_str))
        
        full_coupon_id = cursor.fetchone()[0]
        
        # غیرفعال کردن نیم‌کوپن‌ها
        for coupon in coupons:
            logger.info(f"🔄 غیرفعال کردن نیم‌کوپن: {coupon[1]}")
            cursor.execute("""
            UPDATE coupons 
            SET status = 'used', 
                used_date = %s,
                used_for = %s
            WHERE coupon_id = %s
            """, (date_str, f"combined_to_{full_coupon_code}", coupon[0]))
        
        conn.commit()
        logger.info(f"✅ نیم‌کوپن‌ها ترکیب شدند: {coupon_code1} + {coupon_code2} = {full_coupon_code}")
        
        return full_coupon_code
        
    except Exception as e:
        logger.error(f"❌ خطا در ترکیب نیم‌کوپن‌ها: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return None
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)
async def combine_coupons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ترکیب دو نیم‌کوپن"""
    user_id = update.effective_user.id
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "🔄 <b>ترکیب نیم‌کوپن‌ها</b>\n\n"
            "📋 فرمت صحیح:\n"
            "<code>/combine_coupons کد_نیم‌کوپن_اول کد_نیم‌کوپن_دوم</code>\n\n"
            "مثال:\n"
            "<code>/combine_coupons FT123ABC FT456DEF</code>\n\n"
            "💡 هر نیم‌کوپن: ۲۰,۰۰۰ تومان\n"
            "✅ پس از ترکیب: ۱ کوپن کامل ۴۰,۰۰۰ تومانی",
            parse_mode=ParseMode.HTML
        )
        return
    
    coupon_code1 = context.args[0].upper()
    coupon_code2 = context.args[1].upper()
    
    full_coupon = combine_half_coupons(user_id, coupon_code1, coupon_code2)
    
    if full_coupon:
        await update.message.reply_text(
            f"✅ <b>ترکیب موفق!</b>\n\n"
            f"🎫 <b>کوپن کامل جدید:</b> <code>{full_coupon}</code>\n"
            f"💰 <b>ارزش:</b> ۴۰,۰۰۰ تومان\n\n"
            f"🎯 اکنون می‌توانید از این کوپن برای خدمات مختلف استفاده کنید!",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "❌ <b>ترکیب ناموفق!</b>\n\n"
            "ممکن است:\n"
            "• کوپن‌ها معتبر نباشند\n"
            "• قبلاً استفاده شده‌اند\n"
            "• متعلق به شما نیستند\n"
            "• نیم‌کوپن نیستند",
            parse_mode=ParseMode.HTML
        )
async def my_coupons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش کوپن‌های کاربر با تفکیک نوع"""
    user_id = update.effective_user.id
    
    try:
        # دریافت همه کوپن‌های کاربر
        query = """
        SELECT coupon_code, coupon_source, value, status, 
               earned_date, used_date, used_for, is_half_coupon
        FROM coupons
        WHERE user_id = %s
        ORDER BY earned_date DESC
        """
        
        results = db.execute_query(query, (user_id,), fetchall=True)
        
        if not results:
            await update.message.reply_text(
                "📭 شما هیچ کوپنی ندارید.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        half_coupons = []
        full_coupons = []
        
        for row in results:
            coupon_data = {
                "code": row[0],
                "source": row[1],
                "value": row[2],
                "status": row[3],
                "earned_date": row[4],
                "used_date": row[5],
                "used_for": row[6],
                "is_half": row[7]
            }
            
            if row[7]:  # is_half_coupon
                half_coupons.append(coupon_data)
            else:
                full_coupons.append(coupon_data)
        
        # ساخت پیام
        text = "🎫 <b>کوپن‌های شما</b>\n\n"
        
        if half_coupons:
            text += "🟡 <b>نیم‌کوپن‌ها (۲۰,۰۰۰ تومان):</b>\n"
            for i, coupon in enumerate(half_coupons[:5], 1):
                if coupon["status"] == "active":
                    text += f"{i}. <code>{coupon['code']}</code> - {coupon['earned_date']}\n"
            
            if len(half_coupons) >= 2:
                text += f"\n🔄 <b>شما {len(half_coupons)} نیم‌کوپن دارید!</b>\n"
                text += f"می‌توانید ۲ تا را ترکیب کنید:\n"
                text += f"<code>/combine_coupons {half_coupons[0]['code']} {half_coupons[1]['code']}</code>\n"
        
        if full_coupons:
            text += "\n🟢 <b>کوپن‌های کامل (۴۰,۰۰۰ تومان):</b>\n"
            for i, coupon in enumerate(full_coupons[:5], 1):
                status_emoji = "✅" if coupon["status"] == "active" else "📝"
                text += f"{i}. {status_emoji} <code>{coupon['code']}</code> - {coupon['earned_date']}\n"
                if coupon["status"] == "used":
                    text += f"   📍 استفاده شده برای: {coupon['used_for'] or 'نامشخص'}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"خطا در نمایش کوپن‌ها: {e}")
        await update.message.reply_text("❌ خطا در دریافت اطلاعات کوپن‌ها.")
async def send_random_encouragement(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال پیام تشویقی رندوم به کاربران بی‌فعال"""
    try:
        logger.info("🎁 شروع ارسال پیام‌های تشویقی...")
        
        # دریافت کاربران بی‌فعال امروز
        inactive_users = get_inactive_users_today()
        
        if not inactive_users:
            logger.info("📭 هیچ کاربر بی‌فعالی وجود ندارد")
            return
        
        # انتخاب حداکثر 20 کاربر به صورت رندوم
        import random
        selected_users = random.sample(inactive_users, min(20, len(inactive_users)))
        
        total_sent = 0
        
        for user in selected_users:
            try:
                # ساخت پیام تشویقی
                encouragement_messages = [
                    "🎁 <b>فرصت ویژه!</b>\n\nسلام! می‌دونم امروز هنوز مطالعه‌ای ثبت نکردی...\n\n⏰ اگه همین الان یک جلسه مطالعه ثبت کنی:\n✅ <b>نیم کوپن به ارزش ۲۰,۰۰۰ تومان میگیری!</b>\n🎯 شانس برنده شدن در قرعه‌کشی هفتگی بیشتر می‌شه\n📈 رتبه‌ت در جدول هفتگی بهبود پیدا می‌کنه\n\n🔥 <b>همین الان دکمه «➕ ثبت مطالعه» رو بزن!</b>\n\n⏳ این پیشنهاد فقط امروز معتبره!",
                    
                    "🔥 <b>آخرین فرصت امروز!</b>\n\nهنوز امروز رو به پایان نرسوندی! یه فرصت طلایی داری:\n\n💰 <b>ثبت مطالعه = دریافت ۲۰,۰۰۰ تومان تخفیف!</b>\n\n⏰ فقط کافیه یک جلسه ۳۰ دقیقه‌ای شروع کنی و:\n✅ کوپن تخفیف ۲۰,۰۰۰ تومانی دریافت کنی\n✅ در قرعه‌کشی هفتگی شرکت کنی\n✅ رتبه‌ت رو در جدول هفتگی بالا ببری\n\n🎯 <b>همین الان شروع کن!</b>",
                    
                    "💎 <b>پیشنهاد محدود!</b>\n\nامروز رو بدون مطالعه نگذار بگذره! این فرصت رو از دست نده:\n\n🎁 <b>هر مطالعه امروز = نیم کوپن ۲۰,۰۰۰ تومانی</b>\n\n📊 آمار کاربرانی که امروز مطالعه کردن:\n• ۷۵٪ بیشتر از ۶۰ دقیقه مطالعه کردن\n• ۴۰٪ جایگاهشون در جدول هفتگی بهتر شده\n• ۲۵٪ برنده جوایز هفتگی شدن\n\n🏆 <b>تو هم می‌تونی یکی از برندگان باشی!</b>"
                ]
                
                message = random.choice(encouragement_messages)
                
                # ارسال پیام
                await context.bot.send_message(
                    user["user_id"],
                    message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_main_menu_keyboard()
                )
                
                # علامت‌گذاری ارسال شده
                mark_encouragement_sent(user["user_id"])
                total_sent += 1
                
                await asyncio.sleep(0.15)  # تأخیر بیشتر برای جلوگیری از محدودیت
                
            except Exception as e:
                logger.error(f"خطا در ارسال پیام تشویقی به کاربر {user['user_id']}: {e}")
                continue
        
        logger.info(f"🎁 پیام تشویقی به {total_sent} کاربر ارسال شد")
        
    except Exception as e:
        logger.error(f"خطا در ارسال پیام‌های تشویقی: {e}")

async def check_and_reward_user(user_id: int, session_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """بررسی و اعطای پاداش نیم‌کوپن - فرصت ۲۴ ساعته"""
    try:
        now = datetime.now(IRAN_TZ)
        
        # بررسی آیا در ۲۴ ساعت گذشته پیام تشویقی دریافت کرده
        # 🔴 تغییر: بررسی بازه ۲۴ ساعت گذشته
        query = """
        SELECT MIN(date) as first_encouragement_date 
        FROM user_activities 
        WHERE user_id = %s 
        AND received_encouragement = TRUE
        AND created_at >= %s
        """
        
        # تاریخ ۲۴ ساعت پیش
        twenty_four_hours_ago = now - timedelta(hours=24)
        check_time = twenty_four_hours_ago.strftime("%Y-%m-%d %H:%M:%S")
        
        result = db.execute_query(query, (user_id, check_time), fetch=True)
        
        if result and result[0]:  # اگر در ۲۴ ساعت گذشته پیام تشویقی گرفته
            # ایجاد نیم‌کوپن پاداش
            coupon = create_half_coupon(user_id, "encouragement_reward")
            
            if coupon:
                # ارسال پیام تبریک
                if context:
                    try:
                        await context.bot.send_message(
                            user_id,
                            f"🎉 <b>پاداش ۲۴ ساعته دریافت شد!</b>\n\n"
                            f"✅ شما برای ثبت مطالعه در عرض ۲۴ ساعت بعد از دریافت پیام تشویقی، پاداش گرفتید!\n\n"
                            f"⏳ <b>فرصت:</b> ۲۴ ساعت از لحظه دریافت پیام\n"
                            f"🎁 <b>نیم‌کوپن:</b> <code>{coupon['coupon_code']}</code>\n"
                            f"💰 <b>مبلغ:</b> ۲۰,۰۰۰ تومان\n"
                            f"📅 <b>تاریخ ایجاد:</b> {coupon['earned_date']}\n\n"
                            f"💡 <b>نکته مهم:</b>\n"
                            f"• این یک <b>نیم‌کوپن</b> است\n"
                            f"• نیاز به ۲ نیم‌کوپن برای یک خدمت کامل دارید\n"
                            f"• می‌توانید آن را با نیم‌کوپن دیگر ترکیب کنید\n\n"
                            f"🔄 <b>برای ترکیب:</b>\n"
                            f"دستور: /combine_coupons کد۱ کد۲\n\n"
                            f"✅ نیم‌کوپن‌های شما: /my_coupons",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f"خطا در اطلاع پاداش به کاربر {user_id}: {e}")
                
                logger.info(f"🎁 نیم‌کوپن به کاربر {user_id} داده شد: {coupon['coupon_code']}")
                
                # پاک کردن تمام پیام‌های تشویقی قبلی کاربر
                cleanup_query = """
                UPDATE user_activities
                SET received_encouragement = FALSE
                WHERE user_id = %s
                """
                db.execute_query(cleanup_query, (user_id,))
        
    except Exception as e:
        logger.error(f"خطا در بررسی و اعطای پاداش: {e}")


    
    # بقیه کد بدون تغییر...
    

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /start"""
    user = update.effective_user
    user_id = user.id
    
    # بررسی پارامتر لینک
    if context.args:
        if context.args[0] == "special":
            # ارسال عکس و متن تبلیغی مخصوص
            photo_url = "https://github.com/Mostafafar/Focustodo/blob/main/welcome.jpg?raw=true"
            
            try:
                await update.message.reply_photo(
                    photo=photo_url,
                    caption="""
🎁 <b>پیشنهاد محدود!</b>

امروز رو بدون مطالعه نگذار بگذره! این فرصت رو از دست نده:

<b>هر مطالعه امروز = نیم کوپن ۲۰,۰۰۰ تومانی</b>

<b>📊 آمار کاربرانی که امروز مطالعه کردن:</b>
• ۷۵٪ بیشتر از ۶۰ دقیقه مطالعه کردن
• ۴۰٪ جایگاهشون در جدول هفتگی بهتر شده
• ۲۵٪ برنده جوایز هفتگی شدن

<b>🏆 تو هم می‌تونی یکی از برندگان باشی!</b>

🔥 همین الان شروع کن!
""",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_main_menu_keyboard()
                )
                return  # بعد از نمایش پیام تبلیغاتی، خروج کن
            except Exception as e:
                logger.error(f"خطا در ارسال عکس: {e}")
                # اگر ارسال عکس خطا خورد، فقط متن را بفرست
                await update.message.reply_text(
                    """
🎁 <b>پیشنهاد محدود!</b>

امروز رو بدون مطالعه نگذار بگذره! این فرصت رو از دست نده:

<b>هر مطالعه امروز = نیم کوپن ۲۰,۰۰۰ تومانی</b>

<b>📊 آمار کاربرانی که امروز مطالعه کردن:</b>
• ۷۵٪ بیشتر از ۶۰ دقیقه مطالعه کردن
• ۴۰٪ جایگاهشون در جدول هفتگی بهتر شده
• ۲۵٪ برنده جوایز هفتگی شدن

<b>🏆 تو هم می‌تونی یکی از برندگان باشی!</b>

🔥 همین الان شروع کن!
""",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_main_menu_keyboard()
                )
                return
        
        elif context.args[0].startswith("join_"):
            room_code = context.args[0].replace("join_", "")
            
            # دریافت اطلاعات اتاق
            room_info = get_room_info(room_code)
            
            if not room_info:
                await update.message.reply_text("❌ اتاق یافت نشد.")
                return
            
            # ذخیره room_code برای مرحله بعد
            context.user_data["joining_room"] = room_code
            
            await update.message.reply_text(
                f"<b>🔐 ورود به اتاق #{room_code}</b>\n\n"
                f"سازنده: {room_info['creator_name'] or 'نامشخص'}\n"
                f"تا ساعت: {room_info['end_time']}\n"
                f"شرکت‌کنندگان: {room_info['player_count']} نفر\n\n"
                f"⚠️ این اتاق رمز دارد.\n"
                f"لطفا رمز ۴ رقمی را وارد کنید:",
                reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True),
                parse_mode=ParseMode.HTML
            )
            return
    
    # ادامه کد اصلی (بدون پارامتر)...
    logger.info(f"🔍 بررسی کاربر {user_id} در دیتابیس...")
    
    query = "SELECT user_id, is_active FROM users WHERE user_id = %s"
    result = db.execute_query(query, (user_id,), fetch=True)
    
    if not result:
        logger.info(f"📝 کاربر جدید {user_id} - شروع فرآیند ثبت‌نام")
        context.user_data["registration_step"] = "grade"
        
        # ارسال اطلاع به ادمین‌ها
        await notify_admin_new_user(context, user)
        
        await update.message.reply_text(
            "👋 به ربات کمپ خوش آمدید!\n\n"
            "📝 برای استفاده از ربات، ابتدا باید ثبت‌نام کنید.\n\n"
            "🎓 <b>لطفا پایه تحصیلی خود را انتخاب کنید:</b>",
            reply_markup=get_grade_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return
    
    is_active = result[1]
    if not is_active:
        await update.message.reply_text(
            "⏳ حساب کاربری شما در حال بررسی است.\n"
            "لطفا منتظر تأیید ادمین باشید.\n\n"
            "🔔 پس از تأیید، می‌توانید از ربات استفاده کنید."
        )
        return
    
    await update.message.reply_text(
        """
🎯 <b>به کمپ خوش آمدید!</b>

<b>📚 سیستم مدیریت مطالعه و رقابت سالم</b>
⏰ تایمر هوشمند | 🏆 رتبه‌بندی آنلاین
📖 منابع شخصی‌سازی شده

<b>لطفا یک گزینه انتخاب کنید:</b>
""",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /admin (فقط برای ادمین‌ها)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    context.user_data["admin_mode"] = True
    await update.message.reply_text(
        "👨‍💼 پنل مدیریت\n"
        "لطفا یک عملیات انتخاب کنید:",
        reply_markup=get_admin_keyboard_reply()
    )
async def notify_admin_new_user(context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
    """ارسال اطلاع کاربر جدید به ادمین‌ها"""
    try:
        date_str, time_str = get_iran_time()
        
        message = f"👤 **کاربر جدید /start زده**\n\n"
        message += f"🆔 آیدی عددی: `{user.id}`\n"
        message += f"👤 نام: {user.full_name or 'نامشخص'}\n"
        message += f"📛 نام کاربری: @{user.username or 'ندارد'}\n"
        message += f"📅 تاریخ: {date_str}\n"
        message += f"🕒 زمان: {time_str}\n\n"
        message += f"✅ منتظر ثبت‌نام است."
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    message,
                    parse_mode=ParseMode.MARKDOWN
                )
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"خطا در اطلاع‌رسانی به ادمین‌ها: {e}")
async def deactive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """غیرفعال‌سازی کاربر توسط ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت صحیح:\n"
            "/deactive <آیدی_کاربر>\n\n"
            "مثال:\n"
            "/deactive 123456789\n\n"
            "📌 آیدی کاربر را می‌توانید از لیست کاربران (/users) دریافت کنید."
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        # بررسی وجود کاربر
        query = "SELECT username, is_active FROM users WHERE user_id = %s"
        user_check = db.execute_query(query, (target_user_id,), fetch=True)
        
        if not user_check:
            await update.message.reply_text(f"❌ کاربر با آیدی `{target_user_id}` یافت نشد.")
            return
        
        username, is_currently_active = user_check
        
        # اگر کاربر قبلاً غیرفعال است
        if not is_currently_active:
            await update.message.reply_text(
                f"⚠️ کاربر `{target_user_id}` از قبل غیرفعال است.\n"
                f"👤 نام: {username or 'نامشخص'}"
            )
            return
        
        # غیرفعال‌سازی
        query = """
        UPDATE users
        SET is_active = FALSE
        WHERE user_id = %s
        """
        rows_updated = db.execute_query(query, (target_user_id,))
        
        if rows_updated > 0:
            date_str, time_str = get_iran_time()
            
            # اطلاع به کاربر (اگر امکان داشت)
            try:
                await context.bot.send_message(
                    target_user_id,
                    "🚫 **حساب کاربری شما غیرفعال شد!**\n\n"
                    "❌ شما دیگر نمی‌توانید از ربات استفاده کنید.\n"
                    "📞 برای فعال‌سازی مجدد با پشتیبانی تماس بگیرید."
                )
            except Exception as e:
                logger.warning(f"⚠️ خطا در اطلاع به کاربر {target_user_id}: {e}")
            
            await update.message.reply_text(
                f"✅ کاربر غیرفعال شد!\n\n"
                f"🆔 آیدی: `{target_user_id}`\n"
                f"👤 نام: {username or 'نامشخص'}\n"
                f"📅 تاریخ: {date_str}\n"
                f"🕒 زمان: {time_str}\n\n"
                f"🔔 به کاربر اطلاع داده شد (در صورت امکان).",
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"کاربر غیرفعال شد: {username} ({target_user_id}) توسط ادمین {user_id}")
        else:
            await update.message.reply_text(f"❌ خطا در غیرفعال‌سازی کاربر.")
            
    except ValueError:
        await update.message.reply_text("❌ آیدی باید عددی باشد.")
    except Exception as e:
        logger.error(f"خطا در غیرفعال‌سازی کاربر: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /users - نمایش لیست کاربران"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    try:
        # دریافت شماره صفحه (اگر وارد شده)
        page = int(context.args[0]) if context.args else 1
        page = max(1, page)
        limit = 8
        offset = (page - 1) * limit
        
        # 🔴 اصلاح شده: حذف کامنت فارسی از کوئری SQL
        query = """
        SELECT user_id, username, grade, field, is_active, 
               registration_date, total_study_time, total_sessions
        FROM users
        WHERE is_active = TRUE
        ORDER BY total_study_time DESC NULLS LAST, user_id DESC
        LIMIT %s OFFSET %s
        """
        
        results = db.execute_query(query, (limit, offset), fetchall=True)
        
        if not results:
            await update.message.reply_text("📭 هیچ کاربر فعالی وجود ندارد.")
            return
        
        # شمارش کل کاربران فعال
        count_query = "SELECT COUNT(*) FROM users WHERE is_active = TRUE"
        total_users = db.execute_query(count_query, fetch=True)[0]
        total_pages = (total_users + limit - 1) // limit
        
        # ساخت متن با HTML
        text = "<b>📋 رتبه‌بندی کاربران بر اساس مطالعه کلی</b>\n\n"
        text += f"📊 <b>تعداد کاربران فعال:</b> {total_users}\n"
        text += f"📄 <b>صفحه {page} از {total_pages}</b>\n\n"
        
        for i, row in enumerate(results, 1):
            user_id_db, username, grade, field, is_active, reg_date, total_time, total_sessions = row
            
            # نمایش رتبه در صفحه
            rank_position = offset + i
            
            # ایموجی برای رتبه‌های برتر
            if rank_position == 1:
                rank_emoji = "🥇"
            elif rank_position == 2:
                rank_emoji = "🥈"
            elif rank_position == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = f"{rank_position}."
            
            text += f"<b>{rank_emoji} 👤 کاربر</b>\n"
            text += f"🆔 <code>{user_id_db}</code>\n"
            text += f"📛 {html.escape(username or 'ندارد')}\n"
            text += f"🎓 {html.escape(grade)} | 🧪 {html.escape(field)}\n"
            
            # نمایش زمان مطالعه با فرمت زیبا
            if total_time:
                hours = total_time // 60
                mins = total_time % 60
                if hours > 0 and mins > 0:
                    time_display = f"<b>{hours}h {mins}m</b>"
                elif hours > 0:
                    time_display = f"<b>{hours}h</b>"
                else:
                    time_display = f"<b>{mins}m</b>"
                text += f"⏰ <b>کل مطالعه:</b> {time_display}\n"
                text += f"📖 <b>جلسات:</b> {total_sessions}\n"
            else:
                text += f"⏰ <b>کل مطالعه:</b> ۰ دقیقه\n"
                text += f"📖 <b>جلسات:</b> ۰\n"
            
            text += f"📅 <b>ثبت‌نام:</b> {html.escape(reg_date or 'نامشخص')}\n"
            text += "─" * 15 + "\n"
        
        # بررسی طول متن
        if len(text) > 4000:
            text = text[:4000] + "\n\n⚠️ <i>(متن برش خورده)</i>"
        
        keyboard = []
        if page > 1:
            keyboard.append(["◀️ صفحه قبل"])
        if page < total_pages:
            keyboard.append(["▶️ صفحه بعد"])
        keyboard.append(["🔙 بازگشت"])
        
        context.user_data["users_page"] = page
        
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"خطا در نمایش لیست کاربران: {e}")
        await update.message.reply_text(f"❌ خطا: {str(e)[:100]}")
async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /send - ارسال پیام مستقیم به کاربر"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ فرمت صحیح:\n"
            "/send <آیدی_کاربر> <پیام>\n\n"
            "مثال:\n"
            "/send 6680287530 سلام! به ربات خوش آمدید.\n\n"
            "📌 آیدی کاربر را می‌توانید از لیست کاربران (/users) دریافت کنید."
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        message = " ".join(context.args[1:])
        
        # بررسی وجود کاربر
        query = "SELECT username FROM users WHERE user_id = %s"
        user_check = db.execute_query(query, (target_user_id,), fetch=True)
        
        if not user_check:
            await update.message.reply_text(f"❌ کاربر با آیدی {target_user_id} یافت نشد.")
            return
        
        username = user_check[0] or "کاربر"
        
        # ارسال پیام
        try:
            await context.bot.send_message(
                target_user_id,
                f"📩 **پیام از مدیریت:**\n\n{message}\n\n👨‍💼 مدیر ربات",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # تأیید به ادمین
            date_str, time_str = get_iran_time()
            await update.message.reply_text(
                f"✅ پیام ارسال شد!\n\n"
                f"👤 گیرنده: {username} (آیدی: `{target_user_id}`)\n"
                f"📩 پیام: {message[:100]}{'...' if len(message) > 100 else ''}\n"
                f"📅 تاریخ: {date_str}\n"
                f"🕒 زمان: {time_str}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # لاگ ارسال پیام
            logger.info(f"پیام از ادمین {user_id} به کاربر {target_user_id}: {message}")
            
        except Exception as e:
            logger.error(f"خطا در ارسال پیام به کاربر {target_user_id}: {e}")
            await update.message.reply_text(
                f"❌ خطا در ارسال پیام!\n"
                f"کاربر ممکن است ربات را بلاک کرده باشد یا دیگر عضو نباشد."
            )
            
    except ValueError:
        await update.message.reply_text("❌ آیدی کاربر باید عددی باشد.")
    except Exception as e:
        logger.error(f"خطا در دستور /send: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")

async def active_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """فعال‌سازی کاربر توسط ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفا آیدی کاربر را وارد کنید:\n"
            "مثال: /active 123456789"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        if activate_user(target_user_id):
            await update.message.reply_text(f"✅ کاربر {target_user_id} فعال شد.")
        else:
            await update.message.reply_text("❌ کاربر یافت نشد.")
    except ValueError:
        await update.message.reply_text("❌ آیدی باید عددی باشد.")

async def deactive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """غیرفعال‌سازی کاربر توسط ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفا آیدی کاربر را وارد کنید:\n"
            "مثال: /deactive 123456789"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        if deactivate_user(target_user_id):
            await update.message.reply_text(f"✅ کاربر {target_user_id} غیرفعال شد.")
        else:
            await update.message.reply_text("❌ کاربر یافت نشد.")
    except ValueError:
        await update.message.reply_text("❌ آیدی باید عددی باشد.")

async def addfile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """افزودن فایل توسط ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            "⚠️ فرمت صحیح:\n"
            "/addfile <پایه> <رشته> <درس> <مبحث>\n\n"
            "مثال:\n"
            "/addfile دوازدهم تجربی فیزیک دینامیک\n\n"
            "📝 توضیح اختیاری را در خط بعدی بنویسید."
        )
        return
    
    grade = context.args[0]
    field = context.args[1]
    subject = context.args[2]
    topic = context.args[3]
    
    context.user_data["awaiting_file"] = {
        "grade": grade,
        "field": field,
        "subject": subject,
        "topic": topic,
        "description": "",
        "uploader_id": user_id
    }
    
    await update.message.reply_text(
        f"📤 آماده آپلود فایل:\n\n"
        f"🎓 پایه: {grade}\n"
        f"🧪 رشته: {field}\n"
        f"📚 درس: {subject}\n"
        f"🎯 مبحث: {topic}\n\n"
        f"📝 لطفا توضیحی برای فایل وارد کنید (اختیاری):\n"
        f"یا برای رد شدن از این مرحله /skip بزنید."
    )

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رد شدن از مرحله"""
    user_id = update.effective_user.id
    
    if context.user_data.get("registration_step") == "message":
        grade = context.user_data.get("grade")
        field = context.user_data.get("field")
        
        if register_user(user_id, update.effective_user.username, grade, field, ""):
            await update.message.reply_text(
                "✅ درخواست شما ثبت شد!\n\n"
                "📋 اطلاعات ثبت‌نام:\n"
                f"🎓 پایه: {grade}\n"
                f"🧪 رشته: {field}\n\n"
                "⏳ درخواست شما برای ادمین ارسال شد.\n"
                "پس از تأیید، می‌توانید از ربات استفاده کنید.\n\n"
                "برای بررسی وضعیت /start را بزنید.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ثبت اطلاعات.\n"
                "لطفا مجدد تلاش کنید.",
                reply_markup=ReplyKeyboardRemove()
            )
        
        context.user_data.clear()
        return
    
    if not is_admin(user_id) or "awaiting_file" not in context.user_data:
        await update.message.reply_text("❌ دستور نامعتبر.")
        return
    
    await update.message.reply_text(
        "✅ مرحله توضیح رد شد.\n"
        "📎 لطفا فایل را ارسال کنید..."
    )

async def updateuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بروزرسانی اطلاعات کاربر توسط ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ فرمت صحیح:\n"
            "/updateuser <آیدی کاربر> <پایه جدید> <رشته جدید>\n\n"
            "مثال:\n"
            "/updateuser 6680287530 دوازدهم تجربی\n\n"
            "📋 پایه‌های مجاز:\n"
            "دهم، یازدهم، دوازدهم، فارغ‌التحصیل، دانشجو\n\n"
            "📋 رشته‌های مجاز:\n"
            "تجربی، ریاضی، انسانی، هنر، سایر"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        new_grade = context.args[1]
        new_field = context.args[2]
        
        valid_grades = ["دهم", "یازدهم", "دوازدهم", "فارغ‌التحصیل", "دانشجو"]
        valid_fields = ["تجربی", "ریاضی", "انسانی", "هنر", "سایر"]
        
        if new_grade not in valid_grades:
            await update.message.reply_text(
                f"❌ پایه نامعتبر!\n"
                f"پایه‌های مجاز: {', '.join(valid_grades)}"
            )
            return
        
        if new_field not in valid_fields:
            await update.message.reply_text(
                f"❌ رشته نامعتبر!\n"
                f"رشته‌های مجاز: {', '.join(valid_fields)}"
            )
            return
        
        query = """
        SELECT username, grade, field 
        FROM users 
        WHERE user_id = %s
        """
        user_info = db.execute_query(query, (target_user_id,), fetch=True)
        
        if not user_info:
            await update.message.reply_text(
                f"❌ کاربر با آیدی {target_user_id} یافت نشد."
            )
            return
        
        username, old_grade, old_field = user_info
        
        if update_user_info(target_user_id, new_grade, new_field):
            
            try:
                await context.bot.send_message(
                    target_user_id,
                    f"📋 **اطلاعات حساب شما بروزرسانی شد!**\n\n"
                    f"👤 کاربر: {username}\n"
                    f"🎓 پایه قبلی: {old_grade} → جدید: {new_grade}\n"
                    f"🧪 رشته قبلی: {old_field} → جدید: {new_field}\n\n"
                    f"✅ تغییرات توسط ادمین اعمال شد.\n"
                    f"فایل‌های در دسترس شما مطابق با پایه و رشته جدید به‌روزرسانی شدند."
                )
            except Exception as e:
                logger.warning(f"⚠️ خطا در اطلاع به کاربر {target_user_id}: {e}")
            
            await update.message.reply_text(
                f"✅ اطلاعات کاربر بروزرسانی شد:\n\n"
                f"👤 کاربر: {username}\n"
                f"🆔 آیدی: {target_user_id}\n"
                f"🎓 پایه: {old_grade} → {new_grade}\n"
                f"🧪 رشته: {old_field} → {new_field}"
            )
        else:
            await update.message.reply_text(
                "❌ خطا در بروزرسانی اطلاعات کاربر."
            )
        
    except ValueError:
        await update.message.reply_text("❌ آیدی کاربر باید عددی باشد.")
    except Exception as e:
        logger.error(f"خطا در بروزرسانی کاربر: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش اطلاعات کاربر"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفا آیدی کاربر را وارد کنید:\n"
            "/userinfo <آیدی کاربر>\n\n"
            "یا بدون آیدی برای مشاهده اطلاعات خودتان:\n"
            "/userinfo"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        query = """
        SELECT user_id, username, grade, field, message, 
               is_active, registration_date, 
               total_study_time, total_sessions, created_at
        FROM users
        WHERE user_id = %s
        """
        user_data = db.execute_query(query, (target_user_id,), fetch=True)
        
        if not user_data:
            await update.message.reply_text(f"❌ کاربر با آیدی {target_user_id} یافت نشد.")
            return
        
        date_str, _ = get_iran_time()
        query_today = """
        SELECT total_minutes FROM daily_rankings
        WHERE user_id = %s AND date = %s
        """
        today_stats = db.execute_query(query_today, (target_user_id, date_str), fetch=True)
        
        query_sessions = """
        SELECT subject, topic, minutes, date 
        FROM study_sessions 
        WHERE user_id = %s 
        ORDER BY session_id DESC 
        LIMIT 3
        """
        sessions = db.execute_query(query_sessions, (target_user_id,), fetchall=True)
        
        user_id_db, username, grade, field, message, is_active, reg_date, \
        total_time, total_sessions, created_at = user_data
        
        text = f"📋 **اطلاعات کاربر**\n\n"
        text += f"👤 نام: {username or 'نامشخص'}\n"
        text += f"🆔 آیدی: `{user_id_db}`\n"
        text += f"🎓 پایه: {grade or 'نامشخص'}\n"
        text += f"🧪 رشته: {field or 'نامشخص'}\n"
        text += f"📅 تاریخ ثبت‌نام: {reg_date or 'نامشخص'}\n"
        text += f"✅ وضعیت: {'فعال' if is_active else 'غیرفعال'}\n\n"
        
        text += f"📊 **آمار کلی:**\n"
        text += f"⏰ مجموع مطالعه: {format_time(total_time or 0)}\n"
        text += f"📖 تعداد جلسات: {total_sessions or 0}\n"
        
        if today_stats:
            today_minutes = today_stats[0]
            text += f"🎯 مطالعه امروز: {format_time(today_minutes)}\n"
        else:
            text += f"🎯 مطالعه امروز: ۰ دقیقه\n"
        
        if message and message.strip():
            text += f"\n📝 پیام کاربر:\n`{message[:100]}`\n"
            if len(message) > 100:
                text += "...\n"
        
        if sessions:
            text += f"\n📚 **آخرین جلسات:**\n"
            for i, session in enumerate(sessions, 1):
                subject, topic, minutes, date = session
                text += f"{i}. {subject} - {topic[:30]} ({minutes}د) در {date}\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except ValueError:
        await update.message.reply_text("❌ آیدی باید عددی باشد.")
    except Exception as e:
        logger.error(f"خطا در دریافت اطلاعات کاربر: {e}")
        await update.message.reply_text(f"❌ خطا: {e}")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال پیام همگانی به همه کاربران"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت صحیح:\n"
            "/broadcast <پیام>\n\n"
            "مثال:\n"
            "/broadcast اطلاعیه مهم: جلسه فردا لغو شد."
        )
        return
    
    message = " ".join(context.args)
    broadcast_message = f"📢 **پیام همگانی از مدیریت:**\n\n{message}"
    
    await update.message.reply_text("📤 شروع ارسال پیام به همه کاربران...")
    
    await send_to_all_users(context, broadcast_message)
    
    await update.message.reply_text("✅ ارسال پیام همگانی تکمیل شد")

async def sendtop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال دستی رتبه‌های برتر (برای تست)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    await update.message.reply_text("📤 ارسال رتبه‌های برتر...")
    await send_daily_top_ranks(context)
    await update.message.reply_text("✅ ارسال تکمیل شد")

async def debug_sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی جلسات مطالعه"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, user_id, subject, topic, minutes, 
                   TO_TIMESTAMP(start_time) as start_time, completed
            FROM study_sessions 
            ORDER BY session_id DESC 
            LIMIT 10
        """)
        sessions = cursor.fetchall()
        
        text = "🔍 آخرین جلسات مطالعه:\n\n"
        
        if sessions:
            for session in sessions:
                text += f"🆔 {session[0]}\n"
                text += f"👤 کاربر: {session[1]}\n"
                text += f"📚 درس: {session[2]}\n"
                text += f"🎯 مبحث: {session[3]}\n"
                text += f"⏰ زمان: {session[4]} دقیقه\n"
                text += f"📅 شروع: {session[5]}\n"
                text += f"✅ تکمیل: {'بله' if session[6] else 'خیر'}\n"
                text += "─" * 20 + "\n"
        else:
            text += "📭 هیچ جلسه‌ای ثبت نشده\n"
        
        cursor.close()
        db.return_connection(conn)
        
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")

async def debug_files_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور دیباگ فایل‌ها"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    all_files = get_all_files()
    
    text = f"📊 دیباگ فایل‌ها دیتابیس:\n\n"
    text += f"📁 تعداد کل فایل‌ها: {len(all_files)}\n\n"
    
    if all_files:
        for file in all_files:
            text += f"🆔 {file['file_id']}: {file['grade']} {file['field']}\n"
            text += f"   📚 {file['subject']} - {file['topic']}\n"
            text += f"   📄 {file['file_name']}\n"
            text += f"   📦 {file['file_size'] // 1024} KB\n"
            text += f"   📅 {file['upload_date']}\n"
            text += f"   📥 {file['download_count']} دانلود\n\n"
    else:
        text += "📭 هیچ فایلی در دیتابیس وجود ندارد\n\n"
    
    try:
        query = "SELECT COUNT(*) FROM files"
        count = db.execute_query(query, fetch=True)
        text += f"🔢 تعداد رکوردها در جدول files: {count[0] if count else 0}\n"
        
        query_structure = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'files'
        """
        columns = db.execute_query(query_structure, fetchall=True)
        
        if columns:
            text += "\n🗃️ ساختار جدول files:\n"
            for col in columns:
                text += f"  • {col[0]}: {col[1]}\n"
    
    except Exception as e:
        text += f"\n❌ خطا در بررسی دیتابیس: {e}"
    
    await update.message.reply_text(text)

async def check_database_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی مستقیم دیتابیس"""
    if not is_admin(update.effective_user.id):
        return
    
    try:
        query = """
        SELECT file_id, grade, field, subject, topic, file_name, 
               upload_date, uploader_id
        FROM files
        """
        
        results = db.execute_query(query, fetchall=True)
        
        if not results:
            await update.message.reply_text("📭 جدول files خالی است")
            return
        
        text = "📊 رکوردهای جدول files:\n\n"
        for row in results:
            text += f"🆔 ID: {row[0]}\n"
            text += f"🎓 پایه: {row[1]}\n"
            text += f"🧪 رشته: {row[2]}\n"
            text += f"📚 درس: {row[3]}\n"
            text += f"🎯 مبحث: {row[4]}\n"
            text += f"📄 نام فایل: {row[5]}\n"
            text += f"📅 تاریخ: {row[6]}\n"
            text += f"👤 آپلودکننده: {row[7]}\n"
            text += "─" * 20 + "\n"
        
        if len(text) > 4000:
            text = text[:4000] + "\n... (متن برش خورد)"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        logger.error(f"خطا در بررسی دیتابیس: {e}")
        await update.message.reply_text(f"❌ خطا در بررسی دیتابیس: {e}")

async def debug_user_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی تطابق کاربر با فایل‌ها"""
    if not context.args:
        target_user_id = update.effective_user.id
    else:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ آیدی باید عددی باشد.")
            return
    
    user_info = get_user_info(target_user_id)
    
    if not user_info:
        await update.message.reply_text(f"❌ کاربر {target_user_id} یافت نشد.")
        return
    
    grade = user_info["grade"]
    field = user_info["field"]
    
    user_files = get_user_files(target_user_id)
    all_files = get_all_files()
    
    text = f"🔍 تطابق فایل‌ها برای کاربر {target_user_id}:\n\n"
    text += f"👤 کاربر: {user_info['username']}\n"
    text += f"🎓 پایه: {grade}\n"
    text += f"🧪 رشته: {field}\n\n"
    
    text += f"📁 فایل‌های مرتبط: {len(user_files)}\n"
    for f in user_files:
        text += f"  • {f['file_name']} ({f['subject']})\n"
    
    text += f"\n📊 تمام فایل‌های دیتابیس: {len(all_files)}\n"
    
    if all_files:
        for f in all_files:
            match = f["grade"] == grade and f["field"] == field
            match_symbol = "✅" if match else "❌"
            text += f"\n{match_symbol} {f['file_id']}: {f['grade']} {f['field']} - {f['subject']} - {f['file_name']}"
    
    await update.message.reply_text(text)

# -----------------------------------------------------------
# هندلرهای پیام متنی (تمام تعاملات)
# -----------------------------------------------------------


    
    # مدیریت درخواست‌های ادمین
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش تمام پیام‌های متنی"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    logger.info(f"📝 دریافت پیام متنی از کاربر {user_id}: '{text}'")
    
    # ========== پردازش دستورات خاص ==========
    # 1. پردازش دستور /room_...
    if text.startswith("/room_"):
        room_code = text.replace("/room_", "")
        if len(room_code) == 6 and room_code.isalnum():
            await show_room_ranking(update, context, room_code)
            return
    
    # 2. پردازش دستور /join_...
    elif text.startswith("/join_"):
        room_code = text.replace("/join_", "")
        if len(room_code) == 6 and room_code.isalnum():
            # ذخیره room_code برای مرحله بعد
            context.user_data["joining_room"] = room_code
            
            room_info = get_room_info(room_code)
            if not room_info:
                await update.message.reply_text("❌ اتاق یافت نشد.")
                return
            
            await update.message.reply_text(
                "🔐 **ورود به اتاق**\n\n"
                f"کد اتاق: {room_code}\n"
                f"سازنده: {room_info['creator_name'] or 'نامشخص'}\n"
                f"تا ساعت: {room_info['end_time']}\n"
                f"شرکت‌کنندگان: {room_info['player_count']} نفر\n\n"
                "⚠️ این اتاق رمز دارد.\n"
                "لطفا رمز ۴ رقمی را وارد کنید:",
                reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True),
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # ========== پردازش منوهای اصلی ==========
    # ... بقیه کد منوها
    # منوی اصلی
    if text == "🏆 رتبه‌بندی":
        await show_rankings_text(update, context, user_id)
        return
        
    elif text == "📚 منابع":
        await show_files_menu_text(update, context, user_id)
        return
        
    elif text == "➕ ثبت مطالعه":
        await start_study_process_text(update, context)
        return
        
    elif text == "🎫 کوپن":
        await coupon_menu_handler(update, context)
        return
    elif text == "🏆 رقابت گروهی":
        await competition_menu_handler(update, context)
        return
        
    elif text == "🏠 منوی اصلی" or text == "🔙 بازگشت":
        # پاک کردن تمام حالت‌های مربوط به منابع
        context.user_data.pop("viewing_files", None)
        context.user_data.pop("downloading_file", None)
        context.user_data.pop("last_subject", None)
        
        # پاک کردن تمام حالت‌های مربوط به کوپن
        context.user_data.pop("awaiting_coupon_selection", None)
        context.user_data.pop("selected_service", None)
        context.user_data.pop("awaiting_purchase_method", None)
        context.user_data.pop("awaiting_payment_receipt", None)
        context.user_data.pop("eligible_for_coupon", None)
        
        await show_main_menu_text(update, context)
        return
    
    # ادمین منو
    elif text == "📤 آپلود فایل":
        await admin_upload_file(update, context)
        return
        
    elif text == "👥 درخواست‌ها":
        await admin_show_requests(update, context)
        return
        
    elif text == "📁 مدیریت فایل‌ها":
        await admin_manage_files(update, context)
        return
        
    elif text == "🎫 مدیریت کوپن":
        context.user_data["admin_mode"] = True
        await update.message.reply_text(
            "🎫 **پنل مدیریت کوپن**\n\n"
            "لطفا یک عملیات انتخاب کنید:",
            reply_markup=get_admin_coupon_keyboard()
        )
        return
    
    elif text == "👤 لیست کاربران":
        await users_command(update, context)
        return
    
    elif text == "📩 ارسال پیام":
        await update.message.reply_text(
            "📩 ارسال پیام مستقیم\n\n"
            "برای ارسال پیام از دستور زیر استفاده کنید:\n"
            "/send <آیدی_کاربر> <پیام>\n\n"
            "مثال:\n"
            "/send 6680287530 سلام! آزمون فردا لغو شد.\n\n"
            "📌 آیدی کاربر را از لیست کاربران (/users) دریافت کنید."
        )
        return
        
    elif text == "📊 آمار ربات":
        await admin_show_stats(update, context)
        return
    
    elif text == "◀️ صفحه قبل" and context.user_data.get("users_page"):
        page = context.user_data.get("users_page", 1) - 1
        if page < 1:
            page = 1
        context.args = [str(page)]
        await users_command(update, context)
        return
    
    elif text == "▶️ صفحه بعد" and context.user_data.get("users_page"):
        page = context.user_data.get("users_page", 1) + 1
        context.args = [str(page)]
        await users_command(update, context)
        return
    
    # مدیریت کوپن ادمین
    elif text == "📋 درخواست‌های کوپن":
        await coupon_requests_command(update, context)
        return
        
    elif text == "🏦 تغییر کارت":
        await update.message.reply_text(
            "🏦 **تغییر شماره کارت**\n\n"
            "برای تغییر شماره کارت از دستور زیر استفاده کنید:\n"
            "/set_card <شماره_کارت> <نام_صاحب_کارت>\n\n"
            "مثال:\n"
            "/set_card ۶۰۳۷-۹۹۹۹-۱۲۳۴-۵۶۷۸ علی_محمدی\n\n"
            "برای مشاهده شماره کارت فعلی: /set_card"
        )
        return
        
    elif text == "📊 آمار کوپن‌ها":
        await coupon_stats_command(update, context)
        return
    
    # اتمام مطالعه
    elif text == "✅ اتمام مطالعه":
        await complete_study_button(update, context, user_id)
        return
    
    # مدیریت فایل‌های ادمین
    elif text == "🗑 حذف فایل":
        await admin_delete_file_prompt(update, context)
        return
        
    elif text == "📋 لیست فایل‌ها":
        await admin_list_files(update, context)
        return
        
    elif text == "🔄 به‌روزرسانی":
        if context.user_data.get("admin_mode"):
            if context.user_data.get("showing_requests"):
                await admin_show_requests(update, context)
            elif context.user_data.get("managing_files"):
                await admin_manage_files(update, context)
            elif context.user_data.get("showing_stats"):
                await admin_show_stats(update, context)
        return
    
    # مدیریت درخواست‌های ادمین
    elif text == "✅ تأیید همه":
        await admin_approve_all(update, context)
        return
        
    elif text == "❌ رد همه":
        await admin_reject_all_prompt(update, context)
        return
        
    elif text == "👁 مشاهده جزئیات":
        await admin_view_request_details_prompt(update, context)
        return
    
    # پس از مطالعه
    elif text == "📖 منابع این درس":
        if "last_subject" in context.user_data:
            await show_subject_files_text(update, context, user_id, context.user_data["last_subject"])
        else:
            await update.message.reply_text("❌ درس مشخصی یافت نشد.")
        return
        
    elif text == "➕ مطالعه جدید":
        await start_study_process_text(update, context)
        return
    
    # خدمات کوپن   
    elif text in ["📞 تماس تلفنی", "📊 تحلیل گزارش", 
                  "✏️ تصحیح آزمون", "📈 تحلیل آزمون", 
                  "📝 آزمون شخصی", "🔗 برنامه شخصی"]:
        await handle_coupon_service_selection(update, context, text)
        return
    
    # مدیریت کوپن کاربر
    # در تابع handle_text، بخش خرید کوپن:
    elif text == "🛒 خرید کوپن" or text == "💳 خرید کوپن":
        await handle_coupon_purchase(update, context)
        return
    # مدیریت کوپن کاربر
    elif text == "🎫 کوپن‌های من":
        await show_user_coupons(update, context, user_id)
        return
    # منوی رقابت


# زیرمنوهای رقابت
    elif text == "🏆 ساخت رقابت جدید":
        await create_competition_handler(update, context)
        return

    elif text == "🔗 پیوستن به رقابت":
        await update.message.reply_text(
            "برای پیوستن به رقابت، لینک دعوت رو از دوستت بگیر\n"
            "یا اگر کد اتاق رو داری، دستور زیر رو وارد کن:\n"
            "/join <کد_اتاق>\n\n"
            "مثال: /join ABC123"
        )
        return
 
    elif text == "📊 اتاق‌های من":
        await show_my_rooms(update, context, user_id)
        return

# پردازش انتخاب زمان پایان
    if context.user_data.get("creating_competition") and text in ["🕐 ۱۸:۰۰", "🕐 ۱۹:۰۰", "🕐 ۲۰:۰۰", "🕐 ۲۱:۰۰", "🕐 ۲۲:۰۰", "✏️ زمان دلخواه"]:
        await handle_end_time_selection(update, context, text)
        return

    # پردازش رمز اتاق
    elif context.user_data.get("awaiting_password"):
        await handle_competition_password(update, context, text)
        return

# پردازش زمان دلخواه
    elif context.user_data.get("awaiting_custom_time"):
        # تشخیص نوع درخواست
        if context.user_data.get("creating_competition"):
        # اتاق رقابتی - فرمت ساعت:دقیقه
            if ":" in text and text.replace(":", "").isdigit():
                context.user_data["competition_end_time"] = text
                context.user_data["awaiting_password"] = True
                context.user_data.pop("awaiting_custom_time", None)
            
                await update.message.reply_text(
                    f"🕒 ساعت پایان: **{text}**\n\n"
                    f"🔐 **رمز ۴ رقمی برای اتاق وارد کنید:**",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True)
                )
            else:
                await update.message.reply_text("❌ فرمت زمان نامعتبر. مثال: 20:30")
        else:
        # ثبت مطالعه - فرمت دقیقه (عدد ساده)
            try:
                minutes = int(text)
                if MIN_STUDY_TIME <= minutes <= MAX_STUDY_TIME:
                    context.user_data["study_minutes"] = minutes
                
                    await update.message.reply_text(
                        f"⏰ زمان مطالعه: {minutes} دقیقه\n\n"
                        f"🎯 لطفا مبحث مطالعه را وارد کنید:",
                        reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True)
                    )
                
                    context.user_data["awaiting_topic"] = True
                    context.user_data.pop("awaiting_custom_time", None)
                else:
                    await update.message.reply_text(
                        f"❌ زمان باید بین {MIN_STUDY_TIME} تا {MAX_STUDY_TIME} دقیقه باشد."
                    )
            except ValueError:
                await update.message.reply_text(
                    f"❌ لطفا عدد وارد کنید (دقیقه). مثال: ۴۵\n"
                    f"حداقل: {MIN_STUDY_TIME} دقیقه\n"
                    f"حداکثر: {MAX_STUDY_TIME} دقیقه"
                )
        return

# پردازش رمز ورود به اتاق
    
    elif context.user_data.get("joining_room"):
        room_code = context.user_data["joining_room"]
        
        # پیوستن به اتاق
        if join_competition_room(room_code, user_id, text):
            room_info = get_room_info(room_code)
            if room_info:
                # متن پیام با HTML صحیح
                message_text = f"""
<b>✅ وارد اتاق شدی!</b>

<b>🏷 کد اتاق:</b> <code>{room_code}</code>
<b>🕒 تا ساعت:</b> <code>{room_info['end_time']}</code>
<b>👥 حالا</b> {room_info['player_count']} <b>نفریم</b>

<b>برای مشاهده رتبه‌بندی:</b>
/room_{room_code}
"""
                
                await update.message.reply_text(
                    message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_competition_keyboard()
                )
            else:
                # اگر اطلاعات اتاق را نتوانستیم دریافت کنیم
                await update.message.reply_text(
                    f"✅ وارد اتاق {room_code} شدی!\n\nبرای مشاهده رتبه‌بندی:\n/room_{room_code}",
                    reply_markup=get_competition_keyboard()
                )
        else:
            await update.message.reply_text(
                "❌ رمز اشتباه است یا اتاق وجود ندارد.",
                reply_markup=get_competition_keyboard()
            )
        
        context.user_data.pop("joining_room", None)
        return

    # مشاهده رتبه‌بندی اتاق
    elif text.startswith("/room_"):
        room_code = text.replace("/room_", "")
        await show_room_ranking(update, context, room_code)
        return

# و در بخش پردازش عکس فیش:

        
    elif text == "📋 درخواست‌های من":
        await show_user_requests(update, context, user_id)
        return
    
    # روش‌های کسب کوپن
    elif text == "⏰ کسب از مطالعه":
        await handle_study_coupon_earning(update, context)
        return
        
    elif text == "💳 خرید کوپن":
        await handle_coupon_purchase(update, context)
        return
    
    # دریافت کوپن از مطالعه
    elif text == "✅ دریافت کوپن":
        if "eligible_for_coupon" in context.user_data:
            streak_info = context.user_data["eligible_for_coupon"]
            coupon = award_streak_coupon(user_id, streak_info["streak_id"])
            
            if coupon:
                text = f"""
🎉 **تبریک! شما یک کوپن کسب کردید!**

📊 عملکرد ۲ روز اخیر شما:
✅ دیروز: {streak_info['yesterday_minutes'] // 60} ساعت و {streak_info['yesterday_minutes'] % 60} دقیقه
✅ امروز: {streak_info['today_minutes'] // 60} ساعت و {streak_info['today_minutes'] % 60} دقیقه
🎯 مجموع: {streak_info['total_hours']} ساعت در ۲ روز

🎫 **کوپن عمومی جدید شما:**
کد: `{coupon['coupon_code']}`
ارزش: ۴۰,۰۰۰ تومان
منبع: کسب از طریق مطالعه
تاریخ: {coupon['earned_date']}

💡 این کوپن را می‌توانید برای هر خدمتی استفاده کنید!

📋 برای مشاهده کوپن‌ها: «🎫 کوپن‌های من»
"""
                await update.message.reply_text(
                    text,
                    reply_markup=get_coupon_main_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    "❌ خطا در ایجاد کوپن. لطفا مجدد تلاش کنید.",
                    reply_markup=get_coupon_main_keyboard()
                )
            
            context.user_data.pop("eligible_for_coupon", None)
        return
    
    # تأیید عضویت در کانال
    elif text == "✅ تأیید عضویت":
        await handle_channel_subscription(update, context, user_id)
        return
    
    # پردازش انتخاب درس
    if context.user_data.get("downloading_file") and text.startswith("دانلود"):
        try:
            file_id = int(text.split(" ")[1])
            await download_file_text(update, context, user_id, file_id)
        except:
            await update.message.reply_text("❌ فرمت نامعتبر.")
        return

    # پردازش انتخاب درس
    if text in SUBJECTS:
        # بررسی اینکه آیا کاربر در حال مشاهده منابع است؟
        if context.user_data.get("viewing_files"):
            await show_subject_files_text(update, context, user_id, text)
            return
        else:
            await select_subject_text(update, context, text)
            return
    
    # پردازش انتخاب زمان
    for display_text, minutes in SUGGESTED_TIMES:
        if text == display_text:
            await select_time_text(update, context, minutes)
            return
    
    if text == "✏️ زمان دلخواه":
        await request_custom_time_text(update, context)
        return
    
    # پردازش وارد کردن کد کوپن برای استفاده
    # پردازش وارد کردن کد کوپن برای استفاده
    if context.user_data.get("awaiting_coupon_selection"):
        await handle_coupon_usage(update, context, user_id, text)
        return
    
    # پردازش فیش پرداختی
    if context.user_data.get("awaiting_payment_receipt") and text != "🔙 بازگشت":
        await handle_payment_receipt(update, context, user_id, text)
        return
    
    # ثبت‌نام کاربر جدید
    if context.user_data.get("registration_step") == "grade":
        await handle_registration_grade(update, context, text)
        return
    
    if context.user_data.get("registration_step") == "field":
        await handle_registration_field(update, context, text)
        return
    
    if context.user_data.get("registration_step") == "message":
        await handle_registration_message(update, context, user_id, text)
        return
    
    # پردازش فایل‌های درس
    if context.user_data.get("viewing_files") and text != "🔙 بازگشت":
        await show_subject_files_text(update, context, user_id, text)
        return
    
    # مدیریت ادمین
    if context.user_data.get("awaiting_file_id_to_delete"):
        await admin_delete_file_process(update, context, text)
        return
    
    if context.user_data.get("awaiting_request_id"):
        await admin_view_request_details(update, context, text)
        return
    
    if context.user_data.get("rejecting_all"):
        await admin_reject_all_process(update, context, text)
        return
    
    # سایر موارد
    if context.user_data.get("awaiting_custom_subject"):
        await handle_custom_subject(update, context, text)
        return
    
    if context.user_data.get("awaiting_topic"):
        await handle_study_topic(update, context, user_id, text)
        return
    
    if context.user_data.get("awaiting_custom_time"):
        await handle_custom_time(update, context, text)
        return
    
    if context.user_data.get("awaiting_file_description"):
        await handle_file_description(update, context, text)
        return
    
    if context.user_data.get("rejecting_request"):
        await handle_reject_request(update, context, text)
        return
    
    if context.user_data.get("awaiting_user_grade"):
        await handle_user_update_grade(update, context, text)
        return
    
    if context.user_data.get("awaiting_user_field"):
        await handle_user_update_field(update, context, text)
        return
    
    # پیام پیش‌فرض
    await update.message.reply_text(
        "لطفا از منوی ربات استفاده کنید.",
        reply_markup=get_main_menu_keyboard()
        )
async def handle_coupon_usage(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str) -> None:
    """پردازش استفاده از کوپن"""
    logger.info(f"🔍 پردازش استفاده از کوپن: کاربر {user_id}، متن: {text}")
    
    if text == "🔙 بازگشت":
        context.user_data.pop("awaiting_coupon_selection", None)
        context.user_data.pop("selected_service", None)
        await coupon_menu_handler(update, context)
        return
    
    # بررسی کد کوپن
    coupon_code = text.strip().upper()
    
    # اگر کاربر چند کوپن وارد کرده (برای خدمت‌هایی که نیاز به چند کوپن دارند)
    if "," in coupon_code:
        coupon_codes = [code.strip().upper() for code in coupon_code.split(",")]
    else:
        coupon_codes = [coupon_code]
    
    logger.info(f"🔍 کدهای کوپن وارد شده: {coupon_codes}")
    
    # دریافت اطلاعات خدمت انتخاب شده
    service_info = context.user_data.get("selected_service")
    if not service_info:
        await update.message.reply_text(
            "❌ اطلاعات خدمت یافت نشد. لطفا مجدد تلاش کنید.",
            reply_markup=get_coupon_main_keyboard()
        )
        return
    
    # بررسی تعداد کوپن‌های لازم
    if len(coupon_codes) != service_info["price"]:
        await update.message.reply_text(
            f"❌ تعداد کوپن نامعتبر!\n\n"
            f"برای {service_info['name']} نیاز به {service_info['price']} کوپن دارید.\n"
            f"شما {len(coupon_codes)} کوپن وارد کردید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True)
        )
        return
    
    # بررسی اعتبار هر کوپن
    valid_coupons = []
    invalid_coupons = []
    
    for code in coupon_codes:
        coupon = get_coupon_by_code(code)
        
        if not coupon:
            invalid_coupons.append(f"{code} (پیدا نشد)")
        elif coupon["status"] != "active":
            invalid_coupons.append(f"{code} (وضعیت: {coupon['status']})")
        elif coupon["user_id"] != user_id:
            invalid_coupons.append(f"{code} (متعلق به شما نیست)")
        else:
            valid_coupons.append(coupon)
    
    if invalid_coupons:
        error_text = "❌ کوپن‌های نامعتبر:\n"
        for invalid in invalid_coupons:
            error_text += f"• {invalid}\n"
        
        await update.message.reply_text(
            error_text + "\nلطفا کدهای صحیح را وارد کنید:",
            reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True)
        )
        return
    
    # استفاده از کوپن‌ها و ثبت درخواست
    try:
        # استفاده از کوپن‌ها
        for coupon in valid_coupons:
            if not use_coupon(coupon["coupon_code"], service_info["name"]):
                logger.error(f"❌ خطا در استفاده از کوپن {coupon['coupon_code']}")
                await update.message.reply_text(
                    f"❌ خطا در استفاده از کوپن {coupon['coupon_code']}",
                    reply_markup=get_coupon_main_keyboard()
                )
                return
        
        # ایجاد درخواست استفاده از کوپن
        coupon_codes_str = ",".join([c["coupon_code"] for c in valid_coupons])
        
        request_data = create_coupon_request(
            user_id=user_id,
            request_type="usage",
            service_type=get_service_type_key(service_info["name"]),
            amount=0,  # چون با کوپن پرداخت شده
            receipt_image=None
        )
        
        if not request_data:
            await update.message.reply_text(
                "❌ خطا در ثبت درخواست. لطفا با پشتیبانی تماس بگیرید.",
                reply_markup=get_coupon_main_keyboard()
            )
            return
        
        date_str, time_str = get_iran_time()
        
        # نمایش موفقیت
        text = f"""
✅ **درخواست شما ثبت شد!**

🎯 خدمت: {service_info['name']}
💰 روش پرداخت: {len(valid_coupons)} کوپن
🎫 کدهای استفاده شده: {coupon_codes_str}
📅 تاریخ: {date_str}
🕒 زمان: {time_str}

⏳ درخواست شما برای بررسی به ادمین ارسال شد.
پس از تأیید، با شما تماس گرفته می‌شود.

📋 شماره درخواست: #{request_data['request_id']}
"""
        
        await update.message.reply_text(
            text,
            reply_markup=get_coupon_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # ارسال اطلاع به ادمین‌ها
        user_info = get_user_info(user_id)
        username = user_info["username"] if user_info else "نامشخص"
        user_full_name = update.effective_user.full_name or "نامشخص"
        
        for admin_id in ADMIN_IDS:
            try:
                admin_text = f"""
🎫 **درخواست جدید استفاده از کوپن**

📋 **اطلاعات درخواست:**
• شماره درخواست: #{request_data['request_id']}
• کاربر: {escape_html_for_telegram(user_full_name)}
• آیدی: `{user_id}`
• نام کاربری: @{username or 'ندارد'}
• خدمت: {service_info['name']}
• کدهای کوپن: {coupon_codes_str}
• تاریخ: {date_str}
• زمان: {time_str}

📝 برای تأیید دستور زیر را وارد کنید:
<code>/verify_coupon {request_data['request_id']}</code>
"""
                
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین {admin_id}: {e}")
        
        # پاک کردن حالت‌ها
        context.user_data.pop("awaiting_coupon_selection", None)
        context.user_data.pop("selected_service", None)
        
    except Exception as e:
        logger.error(f"❌ خطا در پردازش استفاده از کوپن: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ خطا در پردازش درخواست. لطفا مجدد تلاش کنید.",
            reply_markup=get_coupon_main_keyboard()
        )

def get_service_type_key(service_name: str) -> str:
    """تبدیل نام خدمت به کلید"""
    service_map = {
        "تماس تلفنی": "call",
        "تحلیل گزارش کار": "analysis",
        "تصحیح آزمون تشریحی": "correction",
        "تحلیل آزمون": "test_analysis",
        "آزمون شخصی": "exam"
    }
    return service_map.get(service_name, service_name.lower())

async def switch_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                     message: str, reply_markup: ReplyKeyboardMarkup) -> None:
    """تغییر منو با انیمیشن و حذف کیبورد قدیمی"""
    # ارسال انیمیشن تایپ
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )
    
    # حذف کیبورد قدیمی (اگر پیام از کاربر است)
    if update.message:
        try:
            await update.message.reply_text(
                "🔄",
                reply_markup=ReplyKeyboardRemove()
            )
        except:
            pass
    
    await asyncio.sleep(0.15)  # تأخیر بسیار کوتاه
    
    # نمایش منوی جدید
    await update.message.reply_text(
        message,
        reply_markup=reply_markup
    )

# -----------------------------------------------------------
# توابع کمکی برای هندلرهای متن
# -----------------------------------------------------------

async def show_main_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی اصلی"""
    await update.message.reply_text(
        "🎯 به Focus Todo خوش آمدید!\n\n"
        "📚 سیستم مدیریت مطالعه و رقابت سالم\n"
        "⏰ تایمر هوشمند | 🏆 رتبه‌بندی آنلاین\n"
        "📖 منابع شخصی‌سازی شده\n\n"
        "لطفا یک گزینه انتخاب کنید:",
        reply_markup=get_main_menu_keyboard()
    )

async def show_rankings_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """نمایش رتبه‌بندی"""
    rankings = get_today_rankings()
    date_str, time_str = get_iran_time()
    
    if not rankings:
        text = f"🏆 جدول برترین‌ها\n\n📅 {date_str}\n🕒 {time_str}\n\n📭 هنوز کسی مطالعه نکرده است!"
    else:
        text = f"🏆 جدول برترین‌های امروز\n\n"
        text += f"📅 {date_str}\n🕒 {time_str}\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, rank in enumerate(rankings[:3]):
            if i < 3:
                medal = medals[i]
                
                # تبدیل دقیقه به ساعت و دقیقه
                hours = rank["total_minutes"] // 60
                mins = rank["total_minutes"] % 60
                
                # فرمت زمان: 2h 30m
                if hours > 0 and mins > 0:
                    time_display = f"{hours}h {mins}m"
                elif hours > 0:
                    time_display = f"{hours}h"
                else:
                    time_display = f"{mins}m"
                
                # دریافت نام کامل کاربر از تلگرام
                try:
                    # تلاش برای دریافت اطلاعات کاربر
                    chat_member = await context.bot.get_chat(rank["user_id"])
                    # استفاده از first_name یا username
                    if chat_member.first_name:
                        user_display = chat_member.first_name
                        if chat_member.last_name:
                            user_display += f" {chat_member.last_name}"
                    elif chat_member.username:
                        user_display = f"@{chat_member.username}"
                    else:
                        user_display = rank["username"] or "کاربر"
                except Exception:
                    # اگر خطا خورد، از username دیتابیس استفاده کن
                    user_display = rank["username"] or "کاربر"
                
                # اگر None بود
                if user_display == "None" or not user_display:
                    user_display = "کاربر"
                
                grade_field = f"({rank['grade']} {rank['field']})"
                
                if rank["user_id"] == user_id:
                    text += f"{medal} {user_display} {grade_field}: {time_display} ← **شما**\n"
                else:
                    text += f"{medal} {user_display} {grade_field}: {time_display}\n"
        
        user_rank, user_minutes = get_user_rank_today(user_id)
        
        if user_rank:
            # تبدیل دقیقه به ساعت و دقیقه برای کاربر
            hours = user_minutes // 60
            mins = user_minutes % 60
            
            if hours > 0 and mins > 0:
                user_time_display = f"{hours}h {mins}m"
            elif hours > 0:
                user_time_display = f"{hours}h"
            else:
                user_time_display = f"{mins}m"
            
            if user_rank > 3 and user_minutes > 0:
                # دریافت نام کاربر جاری
                try:
                    chat_member = await context.bot.get_chat(user_id)
                    if chat_member.first_name:
                        current_user_display = chat_member.first_name
                        if chat_member.last_name:
                            current_user_display += f" {chat_member.last_name}"
                    elif chat_member.username:
                        current_user_display = f"@{chat_member.username}"
                    else:
                        user_info = get_user_info(user_id)
                        current_user_display = user_info["username"] if user_info else "شما"
                except Exception:
                    user_info = get_user_info(user_id)
                    current_user_display = user_info["username"] if user_info else "شما"
                
                if current_user_display == "None" or not current_user_display:
                    current_user_display = "شما"
                    
                user_info = get_user_info(user_id)
                grade = user_info["grade"] if user_info else ""
                field = user_info["field"] if user_info else ""
                grade_field = f"({grade} {field})" if grade and field else ""
                
                text += f"\n📊 موقعیت شما:\n"
                text += f"🏅 رتبه {user_rank}: {current_user_display} {grade_field}: {user_time_display}\n"
            
            elif user_rank <= 3:
                text += f"\n🎉 آفرین! شما در بین ۳ نفر برتر هستید!\n"
            else:
                text += f"\n📊 شروع کنید تا در جدول قرار بگیرید!\n"
        
        text += f"\n👥 تعداد کل شرکت‌کنندگان امروز: {len(rankings)} نفر"
    
    await update.message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def start_study_process_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند ثبت مطالعه"""
    await update.message.reply_text(
        "📚 لطفا درس مورد نظر را انتخاب کنید:",
        reply_markup=get_subjects_keyboard_reply()
    )

async def show_files_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """نمایش منوی منابع"""
    user_files = get_user_files(user_id)
    
    if not user_files:
        await update.message.reply_text(
            "📭 فایلی برای شما موجود نیست.\n"
            "ادمین به زودی فایل‌های مرتبط را اضافه می‌کند.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    context.user_data["viewing_files"] = True
    await update.message.reply_text(
        "📚 منابع آموزشی شما\n\n"
        "لطفا درس مورد نظر را انتخاب کنید:",
        reply_markup=get_file_subjects_keyboard(user_files)
    )

async def show_subject_files_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, subject: str) -> None:
    """نمایش فایل‌های یک درس خاص"""
    files = get_files_by_subject(user_id, subject)
    context.user_data["last_subject"] = subject
    context.user_data["viewing_files"] = True
    
    if not files:
        await update.message.reply_text(
            f"📭 فایلی برای درس {subject} موجود نیست.",
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data.pop("viewing_files", None)
        return
    
    text = f"📚 منابع {subject}\n\n"
    
    keyboard = []
    
    for i, file in enumerate(files[:5], 1):
        # تعیین عنوان برای دکمه
        if file['topic'] and file['topic'].strip():
            # اگر مبحث وجود دارد، از آن استفاده کن
            display_title = file['topic']
        else:
            # اگر مبحث نداریم، نام فایل بدون پسوند را نمایش بده
            display_title = os.path.splitext(file['file_name'])[0]
        
        # کوتاه کردن عنوان برای نمایش در لیست
        list_title = display_title[:50] + "..." if len(display_title) > 50 else display_title
        
        text += f"{i}. **{list_title}**\n"
        text += f"   📄 {file['file_name']}\n"
        
        if file['description'] and file['description'].strip():
            desc = file['description'][:50]
            text += f"   📝 {desc}"
            if len(file['description']) > 50:
                text += "..."
            text += "\n"
        
        size_mb = file['file_size'] / (1024 * 1024)
        text += f"   📦 {size_mb:.1f} MB | 📥 {file['download_count']} بار\n\n"
        
        if i <= 3:
            # ایجاد دکمه با مبحث یا عنوان مناسب
            # کوتاه کردن عنوان برای دکمه (حداکثر 30 کاراکتر)
            button_title = display_title[:30] + "..." if len(display_title) > 30 else display_title
            keyboard.append([f"دانلود {file['file_id']} - {button_title}"])
    
    if len(files) > 5:
        text += f"📊 و {len(files)-5} فایل دیگر...\n"
    
    keyboard.append(["🔙 بازگشت"])
    
    context.user_data["downloading_file"] = True
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode=ParseMode.MARKDOWN
    )
async def download_file_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, file_id: int) -> None:
    """ارسال فایل به کاربر"""
    file_data = get_file_by_id(file_id)
    
    if not file_data:
        await update.message.reply_text("❌ فایل یافت نشد.")
        return
    
    user_info = get_user_info(user_id)
    if not user_info:
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    user_grade = user_info["grade"]
    user_field = user_info["field"]
    file_grade = file_data["grade"]
    file_field = file_data["field"]
    
    has_access = False
    
    if user_field == file_field:
        if user_grade == file_grade:
            has_access = True
        elif user_grade == "فارغ‌التحصیل" and file_grade == "دوازدهم":
            has_access = True
    
    if not has_access:
        await update.message.reply_text("❌ شما به این فایل دسترسی ندارید.")
        return
    
    try:
        caption_parts = []
        caption_parts.append(f"📄 **{file_data['file_name']}**\n")
        
        if file_data['topic'] and file_data['topic'].strip():
            caption_parts.append(f"🎯 مبحث: {file_data['topic']}\n")
        
        caption_parts.append(f"📚 درس: {file_data['subject']}\n")
        caption_parts.append(f"🎓 پایه: {file_data['grade']}\n")
        caption_parts.append(f"🧪 رشته: {file_data['field']}\n")
        
        if file_data['description'] and file_data['description'].strip():
            caption_parts.append(f"📝 توضیح: {file_data['description']}\n")
        
        caption_parts.append(f"📦 حجم: {file_data['file_size'] // 1024} KB\n")
        caption_parts.append(f"📅 تاریخ آپلود: {file_data['upload_date']}\n\n")
        caption_parts.append("✅ با موفقیت دانلود شد!")
        
        caption = "".join(caption_parts)
        
        await update.message.reply_document(
            document=file_data["telegram_file_id"],
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
        
        increment_download_count(file_id)
        
        context.user_data.pop("downloading_file", None)
        context.user_data.pop("viewing_files", None)  # پاک کردن حالت منابع
        await update.message.reply_text(
            "✅ فایل ارسال شد!",
            reply_markup=get_main_menu_keyboard()  # بازگشت به منوی اصلی
        )
        
    except Exception as e:
        logger.error(f"خطا در ارسال فایل: {e}")
        await update.message.reply_text("❌ خطا در ارسال فایل.")

async def select_subject_text(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str) -> None:
    """ذخیره درس انتخاب شده"""
    if subject == "سایر":
        await update.message.reply_text(
            "📝 لطفا نام درس را وارد کنید:\n"
            "(مثال: هندسه، علوم کامپیوتر، منطق و ...)"
        )
        context.user_data["awaiting_custom_subject"] = True
        return
    
    context.user_data["selected_subject"] = subject
    
    await update.message.reply_text(
        f"⏰ تنظیم تایمر\n\n"
        f"📝 درس انتخاب شده: **{subject}**\n\n"
        f"⏱ لطفا مدت زمان مطالعه را انتخاب کنید:\n"
        f"(حداکثر {MAX_STUDY_TIME//60} ساعت)",
        reply_markup=get_time_selection_keyboard_reply(),
        parse_mode=ParseMode.MARKDOWN
    )

async def select_time_text(update: Update, context: ContextTypes.DEFAULT_TYPE, minutes: int) -> None:
    """ذخیره زمان انتخاب شده"""
    context.user_data["selected_time"] = minutes
    context.user_data["awaiting_topic"] = True
    
    subject = context.user_data.get("selected_subject", "نامشخص")
    
    await update.message.reply_text(
        f"⏱ زمان انتخاب شده: {format_time(minutes)}\n\n"
        f"📚 درس: {subject}\n\n"
        f"✏️ لطفا مبحث مطالعه را وارد کنید:\n"
        f"(مثال: حل مسائل فصل ۳)"
    )

async def request_custom_time_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست زمان دلخواه"""
    context.user_data["awaiting_custom_time"] = True
    
    await update.message.reply_text(
        f"✏️ زمان دلخواه\n\n"
        f"⏱ لطفا زمان را به دقیقه وارد کنید:\n"
        f"(بین {MIN_STUDY_TIME} تا {MAX_STUDY_TIME} دقیقه)\n\n"
        f"مثال: ۹۰ (برای ۱ ساعت و ۳۰ دقیقه)"
    )

async def complete_study_button(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """اتمام جلسه مطالعه با دکمه"""
    if "current_session" not in context.user_data:
        await update.message.reply_text(
            "❌ جلسه‌ای فعال نیست.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    session_id = context.user_data["current_session"]
    jobs = context.job_queue.get_jobs_by_name(str(session_id))
    for job in jobs:
        job.schedule_removal()
        logger.info(f"⏰ تایمر جلسه {session_id} لغو شد")
    
    session = complete_study_session(session_id)
    
    if session:
        date_str, time_str = get_iran_time()
        score = calculate_score(session["minutes"])
        
        rank, total_minutes = get_user_rank_today(user_id)
        
        rank_text = f"🏆 رتبه شما امروز: {rank}" if rank else ""
        
        time_info = ""
        if session.get("planned_minutes") != session["minutes"]:
            time_info = f"⏱ زمان واقعی: {format_time(session['minutes'])} (از {format_time(session['planned_minutes'])})"
        else:
            time_info = f"⏱ مدت: {format_time(session['minutes'])}"
        
        await update.message.reply_text(
            f"✅ مطالعه تکمیل شد!\n\n"
            f"📚 درس: {session['subject']}\n"
            f"🎯 مبحث: {session['topic']}\n"
            f"{time_info}\n"
            f"🏆 امتیاز: +{score}\n"
            f"📅 تاریخ: {date_str}\n"
            f"🕒 زمان: {time_str}\n\n"
            f"{rank_text}",
            reply_markup=get_after_study_keyboard()
        )
        
        context.user_data["last_subject"] = session['subject']
        
        # 🔴 اضافه شده: بررسی و اعطای پاداش
        await check_and_reward_user(user_id, session_id, context)
        
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت اطلاعات.",
            reply_markup=get_main_menu_keyboard()
        )
    
    context.user_data.pop("current_session", None)

async def auto_complete_study(context) -> None:
    """اتمام خودکار جلسه مطالعه بعد از اتمام زمان"""
    job_data = context.job.data
    session_id = job_data["session_id"]
    chat_id = job_data["chat_id"]
    user_id = job_data["user_id"]
    
    session = complete_study_session(session_id)
    
    if session:
        date_str, time_str = get_iran_time()
        score = calculate_score(session["minutes"])
        
        await context.bot.send_message(
            chat_id,
            f"⏰ <b>زمان به پایان رسید!</b>\n\n"
            f"✅ مطالعه به صورت خودکار ثبت شد.\n\n"
            f"📚 درس: {session['subject']}\n"
            f"🎯 مبحث: {session['topic']}\n"
            f"⏰ مدت: {format_time(session['minutes'])}\n"
            f"🏆 امتیاز: +{score}\n"
            f"📅 تاریخ: {date_str}\n"
            f"🕒 زمان: {time_str}\n\n"
            f"🎉 آفرین! یک جلسه مفید داشتید.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        
        # 🔴 اضافه شده: بررسی و اعطای پاداش
        await check_and_reward_user(user_id, session_id, context)
        
    else:
        await context.bot.send_message(
            chat_id,
            "❌ خطا در ثبت خودکار جلسه.",
            reply_markup=get_main_menu_keyboard()
            )
# -----------------------------------------------------------
# توابع ثبت‌نام
# -----------------------------------------------------------

async def handle_registration_grade(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش مرحله پایه در ثبت‌نام"""
    valid_grades = ["دهم", "یازدهم", "دوازدهم", "فارغ‌التحصیل", "دانشجو"]
    
    if text == "❌ لغو ثبت‌نام":
        await update.message.reply_text(
            "❌ ثبت‌نام لغو شد.\n\n"
            "برای شروع مجدد /start را بزنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return
    
    if text not in valid_grades:
        await update.message.reply_text(
            "❌ لطفا یکی از پایه‌های نمایش‌داده‌شده را انتخاب کنید.",
            reply_markup=get_grade_keyboard()
        )
        return
    
    context.user_data["grade"] = text
    context.user_data["registration_step"] = "field"
    
    await update.message.reply_text(
        f"✅ پایه تحصیلی: **{text}**\n\n"
        f"🧪 **لطفا رشته تحصیلی خود را انتخاب کنید:**",
        reply_markup=get_field_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_registration_field(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش مرحله رشته در ثبت‌نام"""
    valid_fields = ["ریاضی", "انسانی", "تجربی", "سایر"]
    
    if text == "❌ لغو ثبت‌نام":
        await update.message.reply_text(
            "❌ ثبت‌نام لغو شد.\n\n"
            "برای شروع مجدد /start را بزنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return
    
    if text not in valid_fields:
        await update.message.reply_text(
            "❌ لطفا یکی از رشته‌های نمایش‌داده‌شده را انتخاب کنید.",
            reply_markup=get_field_keyboard()
        )
        return
    
    context.user_data["field"] = text
    context.user_data["registration_step"] = "message"
    
    await update.message.reply_text(
        f"✅ اطلاعات شما:\n"
        f"🎓 پایه: {context.user_data['grade']}\n"
        f"🧪 رشته: {text}\n\n"
        f"📝 **لطفا یک پیام کوتاه درباره خودتان بنویسید:**\n"
        f"(حداکثر ۲۰۰ کاراکتر)\n\n"
        f"مثال: علاقه‌مند به یادگیری و پیشرفت\n"
        f"یا: دانش‌آموز علاقه‌مند به ریاضی\n\n"
        f"برای رد شدن از این مرحله /skip را بزنید.",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_registration_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str) -> None:
    """پردازش مرحله پیام در ثبت‌نام"""
    if text == "❌ لغو ثبت‌نام":
        await update.message.reply_text(
            "❌ ثبت‌نام لغو شد.\n\n"
            "برای شروع مجدد /start را بزنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return
    
    message = text[:200]
    grade = context.user_data.get("grade")
    field = context.user_data.get("field")
    
    if register_user(user_id, update.effective_user.username, grade, field, message):
        await update.message.reply_text(
            "✅ درخواست شما ثبت شد!\n\n"
            "📋 اطلاعات ثبت‌نام:\n"
            f"🎓 پایه: {grade}\n"
            f"🧪 رشته: {field}\n"
            f"📝 پیام: {message}\n\n"
            "⏳ درخواست شما برای ادمین ارسال شد.\n"
            "پس از تأیید، می‌توانید از ربات استفاده کنید.\n\n"
            "برای بررسی وضعیت /start را بزنید.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت اطلاعات.\n"
            "لطفا مجدد تلاش کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    context.user_data.clear()

# -----------------------------------------------------------
# توابع مطالعه
# -----------------------------------------------------------

async def handle_custom_subject(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش درس دلخواه"""
    if len(text) < 2 or len(text) > 50:
        await update.message.reply_text(
            "❌ نام درس باید بین ۲ تا ۵۰ کاراکتر باشد.\n"
            "لطفا مجدد وارد کنید:"
        )
        return
    
    context.user_data["selected_subject"] = text
    context.user_data.pop("awaiting_custom_subject", None)
    
    await update.message.reply_text(
        f"✅ درس انتخاب شده: **{text}**\n\n"
        f"⏱ لطفا مدت زمان مطالعه را انتخاب کنید:",
        reply_markup=get_time_selection_keyboard_reply(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_study_topic(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str) -> None:
    """پردازش مبحث مطالعه"""
    topic = text
    subject = context.user_data.get("selected_subject", "نامشخص")
    minutes = context.user_data.get("selected_time", 60)
    
    session_id = start_study_session(user_id, subject, topic, minutes)
    
    if session_id:
        context.user_data["current_session"] = session_id
        date_str, time_str = get_iran_time()
        
        await update.message.reply_text(
            f"✅ تایمر شروع شد!\n\n"
            f"📚 درس: {subject}\n"
            f"🎯 مبحث: {topic}\n"
            f"⏱ مدت: {format_time(minutes)}\n"
            f"📅 تاریخ: {date_str}\n"
            f"🕒 شروع: {time_str}\n\n"
            f"⏳ تایمر در حال اجرا...\n\n"
            f"برای اتمام زودتر دکمه زیر را بزنید:",
            reply_markup=get_complete_study_keyboard()
        )
        
        context.user_data.pop("awaiting_topic", None)
        context.user_data.pop("selected_subject", None)
        context.user_data.pop("selected_time", None)
        
        context.job_queue.run_once(
            auto_complete_study,
            minutes * 60,
            data={"session_id": session_id, "chat_id": update.effective_chat.id, "user_id": user_id},
            name=str(session_id)
        )
    else:
        await update.message.reply_text(
            "❌ خطا در شروع تایمر.\n"
            "لطفا مجدد تلاش کنید.",
            reply_markup=get_main_menu_keyboard()
        )

async def handle_custom_time(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش زمان دلخواه"""
    try:
        minutes = int(text)
        if minutes < MIN_STUDY_TIME:
            await update.message.reply_text(
                f"❌ زمان باید حداقل {MIN_STUDY_TIME} دقیقه باشد."
            )
        elif minutes > MAX_STUDY_TIME:
            await update.message.reply_text(
                f"❌ زمان نباید بیشتر از {MAX_STUDY_TIME} دقیقه (۲ ساعت) باشد."
            )
        else:
            context.user_data["selected_time"] = minutes
            context.user_data["awaiting_topic"] = True
            context.user_data.pop("awaiting_custom_time", None)
            
            subject = context.user_data.get("selected_subject", "نامشخص")
            await update.message.reply_text(
                f"⏱ زمان انتخاب شده: {format_time(minutes)}\n\n"
                f"📚 درس: {subject}\n\n"
                f"✏️ لطفا مبحث مطالعه را وارد کنید:\n"
                f"(مثال: حل مسائل فصل ۳)"
            )
    except ValueError:
        await update.message.reply_text(
            "❌ لطفا یک عدد وارد کنید.\n"
            f"(بین {MIN_STUDY_TIME} تا {MAX_STUDY_TIME} دقیقه)"
        )

# -----------------------------------------------------------
# توابع ادمین
# -----------------------------------------------------------

async def admin_upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """آپلود فایل توسط ادمین"""
    await update.message.reply_text(
        "📤 آپلود فایل\n\n"
        "روش‌های آپلود:\n\n"
        "۱. دستوری سریع:\n"
        "/addfile <پایه> <رشته> <درس> <مبحث>\n\n"
        "مثال:\n"
        "/addfile دوازدهم تجربی فیزیک دینامیک\n\n"
        "۲. مرحله‌ای:\n"
        "ابتدا اطلاعات را به صورت دستی وارد کنید.\n\n"
        "لطفا اطلاعات را به فرمت زیر وارد کنید:\n"
        "پایه،رشته،درس،مبحث\n\n"
        "مثال: دوازدهم,تجربی,فیزیک,دینامیک"
    )

async def admin_show_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش درخواست‌های ثبت‌نام"""
    requests = get_pending_requests()
    context.user_data["showing_requests"] = True
    
    if not requests:
        await update.message.reply_text(
            "📭 هیچ درخواست ثبت‌نامی در انتظار نیست.",
            reply_markup=get_admin_keyboard_reply()
        )
        return
    
    # ساخت متن با HTML ایمن
    text = f"📋 <b>درخواست‌های در انتظار:</b> {len(requests)}\n\n"
    
    for req in requests[:5]:  # فقط ۵ مورد اول
        username = req['username'] or "نامشخص"
        grade = req['grade'] or "نامشخص"
        field = req['field'] or "نامشخص"
        message = req['message'] or "بدون پیام"
        user_id = req['user_id']
        created_at = req['created_at']
        
        if isinstance(created_at, datetime):
            date_str = created_at.strftime('%Y/%m/%d %H:%M')
        else:
            date_str = str(created_at)
        
        # فرار کردن متن برای HTML
        safe_username = safe_html(username)
        safe_grade = safe_html(grade)
        safe_field = safe_html(field)
        safe_date = safe_html(date_str)
        
        text += f"👤 <b>{safe_username}</b>\n"
        text += f"🆔 آیدی: <code>{user_id}</code>\n"
        text += f"🎓 {safe_grade} | 🧪 {safe_field}\n"
        text += f"📅 {safe_date}\n"
        
        if message and message.strip():
            safe_message = safe_html(message[:50])
            text += f"📝 پیام: {safe_message}"
            if len(message) > 50:
                text += "..."
            text += "\n"
        
        text += f"شناسه درخواست: <b>{req['request_id']}</b>\n\n"
    
    # اطمینان از اینکه همه تگ‌ها بسته شده‌اند
    text = text.replace('<br/>', '<br>')
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_requests_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def admin_manage_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت فایل‌های ادمین"""
    context.user_data["managing_files"] = True
    await update.message.reply_text(
        "📁 مدیریت فایل‌ها\n\n"
        "لطفا یک عملیات انتخاب کنید:",
        reply_markup=get_admin_file_management_keyboard()
    )

async def admin_show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش آمار ربات"""
    context.user_data["showing_stats"] = True
    
    try:
        query_users = """
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN is_active THEN 1 END) as active_users,
            COALESCE(SUM(total_study_time), 0) as total_study_minutes
        FROM users
        """
        user_stats = db.execute_query(query_users, fetch=True)
        
        query_sessions = """
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN completed THEN 1 END) as completed_sessions,
            COALESCE(SUM(minutes), 0) as total_session_minutes
        FROM study_sessions
        """
        session_stats = db.execute_query(query_sessions, fetch=True)
        
        query_files = """
        SELECT 
            COUNT(*) as total_files,
            COALESCE(SUM(download_count), 0) as total_downloads,
            COUNT(DISTINCT subject) as unique_subjects
        FROM files
        """
        file_stats = db.execute_query(query_files, fetch=True)
        
        date_str, _ = get_iran_time()
        query_today = """
        SELECT 
            COUNT(DISTINCT user_id) as active_today,
            COALESCE(SUM(total_minutes), 0) as minutes_today
        FROM daily_rankings
        WHERE date = %s
        """
        today_stats = db.execute_query(query_today, (date_str,), fetch=True)
        
        text = f"📊 **آمار کامل ربات**\n\n"
        text += f"📅 تاریخ: {date_str}\n\n"
        
        text += f"👥 **کاربران:**\n"
        text += f"• کل کاربران: {user_stats[0]}\n"
        text += f"• کاربران فعال: {user_stats[1]}\n"
        text += f"• مجموع دقیقه مطالعه: {user_stats[2]:,}\n\n"
        
        text += f"⏰ **جلسات مطالعه:**\n"
        text += f"• کل جلسات: {session_stats[0]}\n"
        text += f"• جلسات تکمیل‌شده: {session_stats[1]}\n"
        text += f"• مجموع زمان: {session_stats[2]:,} دقیقه\n\n"
        
        text += f"📁 **فایل‌ها:**\n"
        text += f"• کل فایل‌ها: {file_stats[0]}\n"
        text += f"• کل دانلودها: {file_stats[1]:,}\n"
        text += f"• درس‌های منحصربه‌فرد: {file_stats[2]}\n\n"
        
        text += f"🎯 **امروز:**\n"
        text += f"• کاربران فعال: {today_stats[0] if today_stats else 0}\n"
        text += f"• مجموع زمان: {today_stats[1] if today_stats else 0} دقیقه\n"
        
        await update.message.reply_text(
            text,
            reply_markup=get_admin_keyboard_reply(),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"خطا در دریافت آمار: {e}")
        await update.message.reply_text(
            "❌ خطا در دریافت آمار.",
            reply_markup=get_admin_keyboard_reply()
        )

async def admin_delete_file_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست شناسه فایل برای حذف"""
    await update.message.reply_text(
        "🗑 حذف فایل\n\n"
        "لطفا شناسه فایل را برای حذف وارد کنید:\n"
        "(شناسه فایل را می‌توانید از لیست فایل‌ها مشاهده کنید)"
    )
    context.user_data["awaiting_file_id_to_delete"] = True

async def admin_list_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لیست فایل‌های ادمین"""
    files = get_all_files()
    
    if not files:
        await update.message.reply_text(
            "📭 هیچ فایلی در سیستم وجود ندارد.",
            reply_markup=get_admin_file_management_keyboard()
        )
        return
    
    text = f"📁 لیست فایل‌ها\n\nتعداد کل: {len(files)}\n\n"
    for file in files[:10]:
        text += f"📄 **{file['file_name']}**\n"
        text += f"🆔 شناسه: {file['file_id']}\n"
        text += f"🎓 {file['grade']} | 🧪 {file['field']}\n"
        text += f"📚 {file['subject']}"
        
        if 'topic' in file and file['topic'] and file['topic'].strip():
            text += f" - {file['topic'][:30]}\n"
        else:
            text += "\n"
            
        text += f"📥 {file['download_count']} دانلود | 📅 {file['upload_date']}\n\n"
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_file_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_delete_file_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش حذف فایل"""
    try:
        file_id = int(text)
        file_data = get_file_by_id(file_id)
        
        if not file_data:
            await update.message.reply_text("❌ فایل یافت نشد.")
            context.user_data.pop("awaiting_file_id_to_delete", None)
            return
        
        if delete_file(file_id):
            await update.message.reply_text(
                f"✅ فایل حذف شد:\n\n"
                f"📄 نام: {file_data['file_name']}\n"
                f"🎓 پایه: {file_data['grade']}\n"
                f"🧪 رشته: {file_data['field']}\n"
                f"📚 درس: {file_data['subject']}",
                reply_markup=get_admin_file_management_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ خطا در حذف فایل.",
                reply_markup=get_admin_file_management_keyboard()
            )
        
        context.user_data.pop("awaiting_file_id_to_delete", None)
        
    except ValueError:
        await update.message.reply_text("❌ شناسه باید عددی باشد.")

async def admin_approve_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأیید همه درخواست‌ها"""
    requests = get_pending_requests()
    
    if not requests:
        await update.message.reply_text("📭 هیچ درخواستی برای تأیید وجود ندارد.")
        return
    
    approved_count = 0
    for req in requests:
        if approve_registration(req["request_id"], "تأیید دسته‌جمعی"):
            approved_count += 1
            try:
                await context.bot.send_message(
                    req["user_id"],
                    "🎉 **درخواست شما تأیید شد!**\n\n"
                    "✅ اکنون می‌توانید از ربات استفاده کنید.\n"
                    "برای شروع /start را بزنید."
                )
            except Exception as e:
                logger.error(f"خطا در اطلاع به کاربر {req['user_id']}: {e}")
    
    await update.message.reply_text(
        f"✅ {approved_count} درخواست تأیید شد.",
        reply_markup=get_admin_keyboard_reply()
    )

async def admin_reject_all_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست دلیل برای رد همه"""
    await update.message.reply_text(
        "❌ رد همه درخواست‌ها\n\n"
        "لطفا دلیل رد همه درخواست‌ها را وارد کنید:"
    )
    context.user_data["rejecting_all"] = True

async def admin_view_request_details_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست شناسه برای مشاهده جزئیات"""
    await update.message.reply_text(
        "👁 مشاهده جزئیات درخواست\n\n"
        "لطفا شناسه درخواست را وارد کنید:"
    )
    context.user_data["awaiting_request_id"] = True

async def admin_view_request_details(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """نمایش جزئیات یک درخواست"""
    try:
        request_id = int(text)
        requests = get_pending_requests()
        request = next((r for r in requests if r["request_id"] == request_id), None)
        
        if not request:
            await update.message.reply_text("❌ درخواست یافت نشد.")
            context.user_data.pop("awaiting_request_id", None)
            return
        
        username = request['username'] or "نامشخص"
        grade = request['grade'] or "نامشخص"
        field = request['field'] or "نامشخص"
        message = request['message'] or "بدون پیام"
        
        text = (
            f"📋 جزئیات درخواست #{request_id}\n\n"
            f"👤 کاربر: **{html.escape(username)}**\n"
            f"🆔 آیدی: `{request['user_id']}`\n"
            f"🎓 پایه: {html.escape(grade)}\n"
            f"🧪 رشته: {html.escape(field)}\n"
            f"📅 تاریخ درخواست: {html.escape(request['created_at'].strftime('%Y/%m/%d %H:%M'))}\n\n"
            f"📝 پیام کاربر:\n"
            f"_{html.escape(message)}_\n\n"
            f"برای تأیید یا رد، از دستورات استفاده کنید."
        )
        
        await update.message.reply_text(
            text,
            reply_markup=get_admin_requests_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data.pop("awaiting_request_id", None)
        
    except ValueError:
        await update.message.reply_text("❌ شناسه باید عددی باشد.")

async def admin_reject_all_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش رد همه درخواست‌ها"""
    requests = get_pending_requests()
    
    if not requests:
        await update.message.reply_text("📭 هیچ درخواستی برای رد وجود ندارد.")
        context.user_data.pop("rejecting_all", None)
        return
    
    admin_note = text
    rejected_count = 0
    
    for req in requests:
        if reject_registration(req["request_id"], admin_note):
            rejected_count += 1
    
    await update.message.reply_text(
        f"❌ {rejected_count} درخواست رد شد.\n"
        f"دلیل: {admin_note}",
        reply_markup=get_admin_keyboard_reply()
    )
    
    context.user_data.pop("rejecting_all", None)

async def handle_file_description(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش توضیح فایل"""
    context.user_data["awaiting_file"]["description"] = text
    context.user_data["awaiting_file_document"] = True
    
    file_info = context.user_data["awaiting_file"]
    await update.message.reply_text(
        f"✅ توضیح ذخیره شد.\n\n"
        f"📤 آماده آپلود فایل:\n\n"
        f"🎓 پایه: {file_info['grade']}\n"
        f"🧪 رشته: {file_info['field']}\n"
        f"📚 درس: {file_info['subject']}\n"
        f"📝 توضیح: {text}\n\n"
        f"📎 لطفا فایل را ارسال کنید..."
    )

async def handle_reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش رد درخواست"""
    request_id = context.user_data["rejecting_request"]
    admin_note = text
    
    if reject_registration(request_id, admin_note):
        await update.message.reply_text(
            f"✅ درخواست #{request_id} رد شد.\n"
            f"دلیل: {admin_note}"
        )
    else:
        await update.message.reply_text(
            "❌ خطا در رد درخواست."
        )
    
    context.user_data.pop("rejecting_request", None)

async def handle_user_update_grade(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش بروزرسانی پایه کاربر"""
    valid_grades = ["دهم", "یازدهم", "دوازدهم", "فارغ‌التحصیل", "دانشجو"]
    
    if text not in valid_grades:
        await update.message.reply_text(
            f"❌ پایه نامعتبر!\n"
            f"پایه‌های مجاز: {', '.join(valid_grades)}\n"
            f"لطفا مجدد وارد کنید:"
        )
        return
    
    context.user_data["new_grade"] = text
    context.user_data["awaiting_user_grade"] = False
    context.user_data["awaiting_user_field"] = True
    
    await update.message.reply_text(
        f"✅ پایه ذخیره شد: {text}\n\n"
        f"لطفا رشته جدید را وارد کنید:\n"
        f"(تجربی، ریاضی، انسانی، هنر، سایر)"
    )

async def handle_user_update_field(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """پردازش بروزرسانی رشته کاربر"""
    valid_fields = ["تجربی", "ریاضی", "انسانی", "هنر", "سایر"]
    
    if text not in valid_fields:
        await update.message.reply_text(
            f"❌ رشته نامعتبر!\n"
            f"رشته‌های مجاز: {', '.join(valid_fields)}\n"
            f"لطفا مجدد وارد کنید:"
        )
        return
    
    new_field = text
    new_grade = context.user_data["new_grade"]
    target_user_id = context.user_data["editing_user"]
    
    if update_user_info(target_user_id, new_grade, new_field):
        query = """
        SELECT username, grade, field 
        FROM users 
        WHERE user_id = %s
        """
        user_info = db.execute_query(query, (target_user_id,), fetch=True)
        
        if user_info:
            username, old_grade, old_field = user_info
            
            try:
                await context.bot.send_message(
                    target_user_id,
                    f"📋 **اطلاعات حساب شما بروزرسانی شد!**\n\n"
                    f"👤 کاربر: {username}\n"
                    f"🎓 پایه قبلی: {old_grade} → جدید: {new_grade}\n"
                    f"🧪 رشته قبلی: {old_field} → جدید: {new_field}\n\n"
                    f"✅ تغییرات توسط ادمین اعمال شد.\n"
                    f"فایل‌های در دسترس شما مطابق با پایه و رشته جدید به‌روزرسانی شدند."
                )
            except Exception as e:
                logger.warning(f"⚠️ خطا در اطلاع به کاربر {target_user_id}: {e}")
            
            await update.message.reply_text(
                f"✅ اطلاعات کاربر بروزرسانی شد:\n\n"
                f"👤 کاربر: {username}\n"
                f"🆔 آیدی: {target_user_id}\n"
                f"🎓 پایه: {old_grade} → {new_grade}\n"
                f"🧪 رشته: {old_field} → {new_field}",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                f"✅ اطلاعات کاربر بروزرسانی شد:\n\n"
                f"🆔 آیدی: {target_user_id}\n"
                f"🎓 پایه جدید: {new_grade}\n"
                f"🧪 رشته جدید: {new_field}",
                reply_markup=get_main_menu_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ خطا در بروزرسانی اطلاعات کاربر.",
            reply_markup=get_main_menu_keyboard()
        )
    
    context.user_data.pop("editing_user", None)
    context.user_data.pop("new_grade", None)
    context.user_data.pop("awaiting_user_field", None)

# -----------------------------------------------------------
# هندلرهای فایل
# -----------------------------------------------------------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش فایل‌های ارسالی"""
    user_id = update.effective_user.id
    document = update.message.document
    
    if ("awaiting_file" in context.user_data or "awaiting_file_document" in context.user_data) and is_admin(user_id):
        
        if "awaiting_file" not in context.user_data:
            await update.message.reply_text("❌ ابتدا اطلاعات فایل را وارد کنید.")
            return
        
        file_info = context.user_data["awaiting_file"]
        
        if not validate_file_type(document.file_name):
            await update.message.reply_text(
                f"❌ نوع فایل مجاز نیست.\n\n"
                f"✅ فرمت‌های مجاز:\n"
                f"PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX\n"
                f"TXT, MP4, MP3, JPG, JPEG, PNG, ZIP, RAR"
            )
            return
        
        file_size_limit = get_file_size_limit(document.file_name)
        if document.file_size > file_size_limit:
            size_mb = file_size_limit / (1024 * 1024)
            await update.message.reply_text(
                f"❌ حجم فایل زیاد است.\n"
                f"حداکثر حجم برای این نوع فایل: {size_mb:.1f} MB"
            )
            return
        
        file_data = add_file(
            grade=file_info["grade"],
            field=file_info["field"],
            subject=file_info["subject"],
            topic=file_info["topic"],
            description=file_info.get("description", ""),
            telegram_file_id=document.file_id,
            file_name=document.file_name,
            file_size=document.file_size,
            mime_type=document.mime_type,
            uploader_id=user_id
        )
        
        if file_data:
            await update.message.reply_text(
                f"✅ فایل با موفقیت آپلود شد!\n\n"
                f"📄 نام: {file_data['file_name']}\n"
                f"📦 حجم: {file_data['file_size'] // 1024} KB\n"
                f"🎓 پایه: {file_data['grade']}\n"
                f"🧪 رشته: {file_data['field']}\n"
                f"📚 درس: {file_data['subject']}\n"
                f"🎯 مبحث: {file_data['topic']}\n"
                f"🆔 کد فایل: FD-{file_data['file_id']}\n\n"
                f"این فایل در دسترس دانش‌آموزان مرتبط قرار گرفت."
            )
        else:
            await update.message.reply_text("❌ خطا در آپلود فایل.")
        
        context.user_data.pop("awaiting_file", None)
        context.user_data.pop("awaiting_file_description", None)
        context.user_data.pop("awaiting_file_document", None)
        return
    
    await update.message.reply_text("📎 فایل دریافت شد.")

# -----------------------------------------------------------
# توابع زمان‌بندی شده
# -----------------------------------------------------------


# -----------------------------------------------------------
# تابع اصلی
# -----------------------------------------------------------
async def check_competition_rooms_job(context: ContextTypes.DEFAULT_TYPE):
    """بررسی اتاق‌های تمام‌شده"""
    try:
        finished_rooms = check_and_finish_rooms()
        
        for room_info in finished_rooms:
            room_code = room_info["room_code"]
            winner_info = room_info["winner_info"]
            
            # دریافت همه شرکت‌کنندگان
            query = """
            SELECT user_id FROM room_participants
            WHERE room_code = %s
            """
            participants = db.execute_query(query, (room_code,), fetchall=True)
            
            if participants:
                # ارسال پیام به همه
                message = f"⏰ **رقابت #{room_code} به پایان رسید!**\n\n"
                
                # اضافه کردن اطلاعات برنده
                if winner_info:
                    message += f"🏆 **برنده:** کاربر {winner_info['winner_id']}\n"
                    message += f"🎫 **جایزه:** کوپن {winner_info['coupon_code']}\n\n"
                
                message += "🎉 به همه شرکت‌کنندگان ۵۰ امتیاز تعلق گرفت!\n"
                message += "برای رقابت جدید به منوی رقابت مراجعه کنید."
                
                for participant in participants:
                    user_id = participant[0]
                    try:
                        await context.bot.send_message(
                            user_id,
                            message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"خطا در ارسال به کاربر {user_id}: {e}")
                        
    except Exception as e:
        logger.error(f"خطا در Job بررسی اتاق‌ها: {e}")

# همچنین یک هندلر برای پیام‌های متنی که با /room_ شروع می‌شوند
async def join_room_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور پیوستن به اتاق با کد"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت صحیح:\n"
            "/join <کد_اتاق>\n\n"
            "مثال:\n"
            "/join ABC123"
        )
        return
    
    room_code = context.args[0].upper()
    room_info = get_room_info(room_code)
    
    if not room_info:
        await update.message.reply_text("❌ اتاق یافت نشد.")
        return
    
    context.user_data["joining_room"] = room_code
    
    await update.message.reply_text(
        f"🔐 **ورود به اتاق #{room_code}**\n\n"
        f"لطفا رمز ۴ رقمی را وارد کنید:",
        reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True),
        parse_mode=ParseMode.MARKDOWN
    )

async def show_my_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """نمایش اتاق‌های کاربر با زمان ایران"""
    try:
        # دریافت اتاق‌های کاربر
        query = """
        SELECT cr.room_code, cr.end_time, cr.status, 
               COUNT(rp.user_id) as player_count,
               cr.created_at
        FROM room_participants rp
        JOIN competition_rooms cr ON rp.room_code = cr.room_code
        WHERE rp.user_id = %s
        GROUP BY cr.room_code, cr.end_time, cr.status, cr.created_at
        ORDER BY cr.created_at DESC
        LIMIT 10
        """
        
        results = db.execute_query(query, (user_id,), fetchall=True)
        
        if not results:
            await update.message.reply_text(
                "📭 شما در هیچ اتاق رقابتی عضو نیستید.",
                reply_markup=get_competition_keyboard()
            )
            return
        
        text = "<b>🏆 اتاق‌های شما</b>\n\n"
        
        for row in results:
            room_code, end_time, status, player_count, created_at = row
            
            # ========== تبدیل زمان ایجاد به وقت ایران ==========
            if created_at:
                if isinstance(created_at, datetime):
                    # اگر datetime با timezone نداره، فرض کنیم UTC هست
                    if created_at.tzinfo is None:
                        created_at_utc = pytz.UTC.localize(created_at)
                        created_at_iran = created_at_utc.astimezone(IRAN_TZ)
                    else:
                        # اگر timezone داره، مستقیم تبدیل کن
                        created_at_iran = created_at.astimezone(IRAN_TZ)
                    
                    created_str = created_at_iran.strftime("%H:%M")
                else:
                    # اگر string هست، تبدیلش کن
                    try:
                        created_at_dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                        created_at_utc = pytz.UTC.localize(created_at_dt) if created_at_dt.tzinfo is None else created_at_dt
                        created_at_iran = created_at_utc.astimezone(IRAN_TZ)
                        created_str = created_at_iran.strftime("%H:%M")
                    except:
                        created_str = str(created_at)
            else:
                created_str = "نامشخص"
            # ====================================================
            
            # وضعیت اتاق
            status_emoji = {
                'waiting': '⏳',
                'active': '🔥',
                'finished': '✅',
                'cancelled': '❌'
            }.get(status, '❓')
            
            status_text = {
                'waiting': 'در انتظار',
                'active': 'فعال',
                'finished': 'اتمام یافته',
                'cancelled': 'لغو شده'
            }.get(status, 'نامشخص')
            
            text += f"<b>{status_emoji} اتاق {room_code}</b>\n"
            text += f"🕒 تا: {end_time}\n"
            text += f"👥 {player_count} نفر | وضعیت: {status_text}\n"
            text += f"🕐 ایجاد: {created_str}\n"
            
            # دکمه‌های عملیاتی
            if status == 'waiting':
                text += f"🔗 برای دعوت دوستان:\n"
                text += f"<code>/join_{room_code}</code>\n"
            elif status == 'active':
                text += f"📊 مشاهده رتبه‌بندی:\n"
                text += f"<code>/room_{room_code}</code>\n"
            elif status == 'finished':
                text += f"🏆 نتیجه: /room_{room_code}\n"
            
            text += "─" * 15 + "\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_competition_keyboard()
        )
        
    except Exception as e:
        logger.error(f"خطا در نمایش اتاق‌های کاربر: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ خطا در دریافت اطلاعات اتاق‌ها.",
            reply_markup=get_competition_keyboard()
    )

async def handle_room_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /room برای مشاهده رتبه‌بندی اتاق"""
    # اگر از فرمت /room_ABCDEF استفاده شده
    if context.args:
        room_code = context.args[0]
    else:
        # ممکن است از فرمت /room_ABCDEF مستقیم استفاده شده باشد
        command_text = update.message.text
        if "_" in command_text:
            room_code = command_text.split("_")[1]
        else:
            await update.message.reply_text(
                "❌ لطفا کد اتاق را وارد کنید.\n"
                "مثال: /room D9L9B7\n"
                "یا: /room_D9L9B7"
            )
            return
    
    await show_room_ranking(update, context, room_code)

async def handle_room_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش پیام‌های /room_..."""
    text = update.message.text.strip()
    room_code = text.replace("/room_", "")
    
    if len(room_code) == 6 and room_code.isalnum():
        await show_room_ranking(update, context, room_code)
    else:
        await update.message.reply_text(
            "❌ فرمت کد اتاق نامعتبر است.\n"
            "کد اتاق باید ۶ کاراکتر باشد.\n"
            "مثال: /room_D9L9B7"
        )

# -----------------------------------------------------------
# همچنین تابع handle_join_underscore باید در فایل اصلی وجود داشته باشد:
# -----------------------------------------------------------
# (این تابع را قبلاً در فایل اصلی داشتید، برای اطمینان اینجا هم می‌آورم)

async def handle_join_underscore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش فرمان‌های /join_XXXXXX (لینک‌های دعوت)"""
    text = update.message.text.strip()
    room_code = text.replace('/join_', '').upper()
    
    # اعتبارسنجی ساده
    if not room_code or len(room_code) != 6:
        await update.message.reply_text("❌ کد اتاق نامعتبر است. مثال: /join_ABC123")
        return

    room_info = get_room_info(room_code)
    if not room_info:
        await update.message.reply_text("❌ اتاق یافت نشد.")
        return

    context.user_data["joining_room"] = room_code
    await update.message.reply_text(
        f"<b>🔐 ورود به اتاق #{room_code}</b>\n\n"
        f"سازنده: {room_info['creator_name'] or 'نامشخص'}\n"
        f"تا ساعت: {room_info['end_time']}\n"
        f"شرکت‌کنندگان: {room_info['player_count']} نفر\n\n"
        "⚠️ این اتاق رمز دارد.\n"
        "لطفا رمز ۴ رقمی را وارد کنید:",
        reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت"]], resize_keyboard=True),
        parse_mode=ParseMode.HTML
        )
def escape_html_for_telegram(text: str) -> str:
    """پاکسازی متن برای استفاده در HTML تلگرام"""
    if not text:
        return ""
    
    # جایگزینی کاراکترهای مخصوص HTML
    text = html.escape(text)
    
    # اما در تلگرام برخی کاراکترها نیاز به جایگزینی خاص دارند
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text
def main() -> None:
    """تابع اصلی اجرای ربات"""
    application = Application.builder().token(TOKEN).build()
    
    # Job زمان‌بندی شده برای گزارش‌ها
    application.job_queue.run_daily(
        send_midday_report,
        time=dt_time(hour=15, minute=0, second=0, tzinfo=IRAN_TZ),  # 15:00
        days=(0, 1, 2, 3, 4, 5, 6),
        name="midday_report"
    )
    
    application.job_queue.run_daily(
        send_night_report,
        time=dt_time(hour=23, minute=0, second=0, tzinfo=IRAN_TZ),  # 23:00
        days=(0, 1, 2, 3, 4, 5, 6),
        name="night_report"
    )
    
    # Job برای پیام‌های تشویقی رندوم (هر روز ساعت 14:00)
    # ارسال پیشنهاد به کاربران بدون مطالعه (هر ۴ روز یکبار در ساعت ۱۲ ظهر)
    application.job_queue.run_daily(
        send_random_offer_to_inactive,
        time=dt_time(hour=12, minute=0, second=0, tzinfo=IRAN_TZ),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="inactive_users_offer"
    )
    
    # Job برای بررسی اتاق‌های تمام‌شده (هر ۵ دقیقه)
    application.job_queue.run_repeating(
        lambda context: check_and_finish_rooms_job(context),
        interval=300,  # هر ۵ دقیقه
        first=10,
        name="check_competition_rooms"
    )
    
    # ثبت هندلرهای دستورات اصلی
    print("\n📝 ثبت هندلرهای دستورات...")
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("active", active_command))
    application.add_handler(CommandHandler("deactive", deactive_command))
    application.add_handler(CommandHandler("addfile", addfile_command))
    application.add_handler(CommandHandler("skip", skip_command))
    application.add_handler(CommandHandler("updateuser", updateuser_command))
    application.add_handler(CommandHandler("userinfo", userinfo_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("sendtop", sendtop_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("send", send_command))
    application.add_handler(CommandHandler("my_coupons", my_coupons_command))
    application.add_handler(CommandHandler("report", report_command))
    print("   ✓ 13 دستور اصلی ثبت شد")
    
    # ثبت دستورات دیباگ
    print("\n🔍 ثبت دستورات دیباگ...")
    application.add_handler(CommandHandler("sessions", debug_sessions_command))
    application.add_handler(CommandHandler("debugfiles", debug_files_command))
    application.add_handler(CommandHandler("checkdb", check_database_command))
    application.add_handler(CommandHandler("debugmatch", debug_user_match_command))
    application.add_handler(CommandHandler("dailystats", debug_daily_stats_command))
    print("   ✓ 5 دستور دیباگ ثبت شد")
    
    # ثبت هندلرهای پیام و فایل
    print("\n📨 ثبت هندلرهای پیام و فایل...")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_photo))
    print("   ✓ هندلرهای متن، فایل و عکس ثبت شد")
    
    # ثبت دستورات سیستم کوپن
    print("\n🎫 ثبت دستورات سیستم کوپن...")
    application.add_handler(CommandHandler("set_card", set_card_command))
    application.add_handler(CommandHandler("coupon_requests", coupon_requests_command))
    application.add_handler(CommandHandler("verify_coupon", verify_coupon_command))
    application.add_handler(CommandHandler("coupon_stats", coupon_stats_command))
    application.add_handler(CommandHandler("debug_all_requests", debug_all_requests_command))
    application.add_handler(CommandHandler("check_stats", check_my_stats_command))
    application.add_handler(CommandHandler("combine_coupons", combine_coupons_command))
    print("   ✓ 7 دستور کوپن و نیم‌کوپن ثبت شد")
    
    # ثبت دستورات رقابت
    print("\n🏆 ثبت دستورات رقابت...")
    application.add_handler(CommandHandler("room", show_room_ranking))
    application.add_handler(
        MessageHandler(
            filters.Regex(r'^/room_[A-Za-z0-9]{6}$') & filters.COMMAND,
            handle_room_message
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(r'^/join_[A-Za-z0-9]{6}$') & filters.COMMAND,
            handle_join_underscore
        )
    )
    print("   ✓ دستورات رقابت ثبت شد")
    
    try:
        print("\n" + "=" * 70)
        print("🤖 ربات Focus Todo آماده اجراست!")
        print("=" * 70)
        print(f"👨‍💼 ادمین‌ها: {ADMIN_IDS}")
        print(f"⏰ حداکثر زمان مطالعه: {MAX_STUDY_TIME} دقیقه")
        print(f"🗄️  دیتابیس: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"🌍 منطقه زمانی: ایران ({IRAN_TZ})")
        print(f"🔑 توکن: {TOKEN[:10]}...{TOKEN[-10:]}")
        print("=" * 70)
        print("🔄 شروع Polling...")
        print("📱 ربات اکنون در حال گوش دادن به پیام‌هاست")
        print("⚠️  برای توقف: Ctrl + C فشار دهید")
        print("=" * 70 + "\n")
        
        logger.info("🚀 ربات شروع به کار کرد - Polling فعال شد")
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=2.0,
            timeout=30
        )
        
        print("\nℹ️  Polling متوقف شد. ربات خاموش شد.")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  ربات توسط کاربر متوقف شد (Ctrl+C)")
        logger.info("ربات توسط کاربر متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطای بحرانی: {e}", exc_info=True)
        print(f"\n❌ خطای بحرانی در اجرای ربات:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
