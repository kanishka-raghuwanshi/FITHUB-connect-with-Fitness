import streamlit as st
import sqlite3
import hashlib
import secrets
import base64
from datetime import datetime, timedelta

st.set_page_config(
    page_title="FITHUB - Connect to Fitness",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== DATABASE SETUP ====================

def init_db():
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    
    # Users table with token authentication
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            account_type TEXT NOT NULL,
            auth_token TEXT,
            token_expiry TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Trainers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS trainers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            specialization TEXT,
            experience_years INTEGER,
            bio TEXT,
            profile_image TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Fitness Plans table
    c.execute('''
        CREATE TABLE IF NOT EXISTS fitness_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            duration_days INTEGER NOT NULL,
            difficulty TEXT DEFAULT 'Beginner',
            category TEXT DEFAULT 'General',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trainer_id) REFERENCES users(id)
        )
    ''')
    
    # Subscriptions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            payment_status TEXT DEFAULT 'completed',
            amount_paid REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (plan_id) REFERENCES fitness_plans(id),
            UNIQUE(user_id, plan_id)
        )
    ''')
    
    # Followers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trainer_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (trainer_id) REFERENCES users(id),
            UNIQUE(user_id, trainer_id)
        )
    ''')
    
    # Chat messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    ''')
    
    # Workouts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            workout_name TEXT NOT NULL,
            duration_minutes INTEGER,
            calories_burned INTEGER,
            workout_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Goals table
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal_type TEXT NOT NULL,
            target_value REAL,
            current_value REAL DEFAULT 0,
            deadline DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# ==================== PASSWORD HASHING & TOKEN AUTH ====================

def generate_salt():
    """Generate a random salt for password hashing"""
    return secrets.token_hex(32)

def hash_password(password, salt):
    """Hash password with salt using SHA-256"""
    salted = password + salt
    return hashlib.sha256(salted.encode()).hexdigest()

def generate_auth_token():
    """Generate a secure authentication token"""
    return secrets.token_urlsafe(64)

def create_user(name, email, mobile, password, account_type):
    """Create a new user with hashed password"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    try:
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        auth_token = generate_auth_token()
        token_expiry = datetime.now() + timedelta(days=7)
        
        c.execute('''
            INSERT INTO users (name, email, mobile, password_hash, salt, account_type, auth_token, token_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, mobile, password_hash, salt, account_type, auth_token, token_expiry))
        conn.commit()
        user_id = c.lastrowid
        
        if account_type == 'trainer':
            c.execute('INSERT INTO trainers (user_id) VALUES (?)', (user_id,))
            conn.commit()
        
        conn.close()
        return True, "Account created successfully!", auth_token
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already exists!", None
    except Exception as e:
        conn.close()
        return False, str(e), None

def verify_user(email, password):
    """Verify user credentials and return user data with new token"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    
    c.execute('SELECT id, name, email, account_type, password_hash, salt FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    
    if user:
        stored_hash = user[4]
        salt = user[5]
        computed_hash = hash_password(password, salt)
        
        if computed_hash == stored_hash:
            # Generate new token on login
            new_token = generate_auth_token()
            token_expiry = datetime.now() + timedelta(days=7)
            c.execute('UPDATE users SET auth_token = ?, token_expiry = ? WHERE id = ?', 
                     (new_token, token_expiry, user[0]))
            conn.commit()
            conn.close()
            return {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'account_type': user[3],
                'token': new_token
            }
    
    conn.close()
    return None

def verify_token(token):
    """Verify authentication token"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, name, email, account_type FROM users 
        WHERE auth_token = ? AND token_expiry > ?
    ''', (token, datetime.now()))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'name': user[1],
            'email': user[2],
            'account_type': user[3]
        }
    return None

# ==================== FITNESS PLANS FUNCTIONS ====================

def create_fitness_plan(trainer_id, title, description, price, duration_days, difficulty, category):
    """Create a new fitness plan"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO fitness_plans (trainer_id, title, description, price, duration_days, difficulty, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (trainer_id, title, description, price, duration_days, difficulty, category))
    conn.commit()
    conn.close()
    return True

def update_fitness_plan(plan_id, trainer_id, title, description, price, duration_days, difficulty, category):
    """Update an existing fitness plan"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        UPDATE fitness_plans 
        SET title = ?, description = ?, price = ?, duration_days = ?, difficulty = ?, category = ?, updated_at = ?
        WHERE id = ? AND trainer_id = ?
    ''', (title, description, price, duration_days, difficulty, category, datetime.now(), plan_id, trainer_id))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0

def delete_fitness_plan(plan_id, trainer_id):
    """Delete a fitness plan"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('DELETE FROM fitness_plans WHERE id = ? AND trainer_id = ?', (plan_id, trainer_id))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0

def get_trainer_plans(trainer_id):
    """Get all plans created by a trainer"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, title, description, price, duration_days, difficulty, category, is_active, created_at
        FROM fitness_plans WHERE trainer_id = ? ORDER BY created_at DESC
    ''', (trainer_id,))
    plans = c.fetchall()
    conn.close()
    return plans

def get_all_plans():
    """Get all active fitness plans with trainer info"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT fp.id, fp.title, fp.description, fp.price, fp.duration_days, fp.difficulty, fp.category,
               u.id as trainer_id, u.name as trainer_name, fp.created_at
        FROM fitness_plans fp
        JOIN users u ON fp.trainer_id = u.id
        WHERE fp.is_active = 1
        ORDER BY fp.created_at DESC
    ''')
    plans = c.fetchall()
    conn.close()
    return plans

def get_plan_details(plan_id):
    """Get full details of a plan"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT fp.id, fp.title, fp.description, fp.price, fp.duration_days, fp.difficulty, fp.category,
               u.id as trainer_id, u.name as trainer_name, fp.created_at
        FROM fitness_plans fp
        JOIN users u ON fp.trainer_id = u.id
        WHERE fp.id = ?
    ''', (plan_id,))
    plan = c.fetchone()
    conn.close()
    return plan

# ==================== SUBSCRIPTION FUNCTIONS ====================

def subscribe_to_plan(user_id, plan_id, amount):
    """Subscribe user to a fitness plan"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    
    # Check if already subscribed
    c.execute('SELECT id FROM subscriptions WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    if c.fetchone():
        conn.close()
        return False, "Already subscribed to this plan"
    
    # Get plan duration
    c.execute('SELECT duration_days FROM fitness_plans WHERE id = ?', (plan_id,))
    plan = c.fetchone()
    if not plan:
        conn.close()
        return False, "Plan not found"
    
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=plan[0])
    
    c.execute('''
        INSERT INTO subscriptions (user_id, plan_id, start_date, end_date, amount_paid)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, plan_id, start_date, end_date, amount))
    conn.commit()
    conn.close()
    return True, "Subscription successful!"

def get_user_subscriptions(user_id):
    """Get all subscriptions for a user"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT s.id, fp.id, fp.title, fp.description, fp.price, fp.duration_days, 
               u.name as trainer_name, s.start_date, s.end_date, s.amount_paid
        FROM subscriptions s
        JOIN fitness_plans fp ON s.plan_id = fp.id
        JOIN users u ON fp.trainer_id = u.id
        WHERE s.user_id = ?
        ORDER BY s.created_at DESC
    ''', (user_id,))
    subs = c.fetchall()
    conn.close()
    return subs

def is_subscribed(user_id, plan_id):
    """Check if user is subscribed to a plan"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT id FROM subscriptions 
        WHERE user_id = ? AND plan_id = ? AND end_date >= ?
    ''', (user_id, plan_id, datetime.now().date()))
    result = c.fetchone()
    conn.close()
    return result is not None

# ==================== FOLLOWER FUNCTIONS ====================

def follow_trainer(user_id, trainer_id):
    """Follow a trainer"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO followers (user_id, trainer_id) VALUES (?, ?)', (user_id, trainer_id))
        conn.commit()
        conn.close()
        return True, "Now following trainer!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Already following this trainer"

def unfollow_trainer(user_id, trainer_id):
    """Unfollow a trainer"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('DELETE FROM followers WHERE user_id = ? AND trainer_id = ?', (user_id, trainer_id))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0

def is_following(user_id, trainer_id):
    """Check if user follows a trainer"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('SELECT id FROM followers WHERE user_id = ? AND trainer_id = ?', (user_id, trainer_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_followed_trainers(user_id):
    """Get list of trainers user follows"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.name, u.email, t.specialization, t.experience_years, t.bio
        FROM followers f
        JOIN users u ON f.trainer_id = u.id
        LEFT JOIN trainers t ON u.id = t.user_id
        WHERE f.user_id = ?
    ''', (user_id,))
    trainers = c.fetchall()
    conn.close()
    return trainers

def get_all_trainers():
    """Get all trainers"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.name, u.email, t.specialization, t.experience_years, t.bio
        FROM users u
        LEFT JOIN trainers t ON u.id = t.user_id
        WHERE u.account_type = 'trainer'
    ''')
    trainers = c.fetchall()
    conn.close()
    return trainers

def get_trainer_followers_count(trainer_id):
    """Get follower count for a trainer"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM followers WHERE trainer_id = ?', (trainer_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

# ==================== PERSONALIZED FEED FUNCTIONS ====================

def get_personalized_feed(user_id):
    """Get plans from followed trainers"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT fp.id, fp.title, fp.description, fp.price, fp.duration_days, fp.difficulty, fp.category,
               u.id as trainer_id, u.name as trainer_name, fp.created_at,
               CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END as is_purchased
        FROM fitness_plans fp
        JOIN users u ON fp.trainer_id = u.id
        JOIN followers f ON f.trainer_id = u.id AND f.user_id = ?
        LEFT JOIN subscriptions s ON s.plan_id = fp.id AND s.user_id = ?
        WHERE fp.is_active = 1
        ORDER BY fp.created_at DESC
    ''', (user_id, user_id))
    plans = c.fetchall()
    conn.close()
    return plans

# ==================== CHAT FUNCTIONS ====================

def send_message(sender_id, receiver_id, message):
    """Send a chat message"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (sender_id, receiver_id, message))
    conn.commit()
    conn.close()
    return True

def get_conversation(user1_id, user2_id):
    """Get conversation between two users"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT m.id, m.sender_id, m.receiver_id, m.message, m.created_at, u.name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC
    ''', (user1_id, user2_id, user2_id, user1_id))
    messages = c.fetchall()
    conn.close()
    return messages

def get_chat_contacts(user_id):
    """Get list of users this user has chatted with"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT DISTINCT 
            CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END as contact_id,
            u.name, u.account_type
        FROM messages m
        JOIN users u ON u.id = CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END
        WHERE m.sender_id = ? OR m.receiver_id = ?
    ''', (user_id, user_id, user_id, user_id))
    contacts = c.fetchall()
    conn.close()
    return contacts

def get_unread_count(user_id):
    """Get unread message count"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0', (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def mark_messages_read(user_id, sender_id):
    """Mark messages as read"""
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('UPDATE messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ?', (user_id, sender_id))
    conn.commit()
    conn.close()

# ==================== WORKOUT & GOALS FUNCTIONS ====================

def add_workout(user_id, workout_name, duration, calories, workout_date, notes):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO workouts (user_id, workout_name, duration_minutes, calories_burned, workout_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, workout_name, duration, calories, workout_date, notes))
    conn.commit()
    conn.close()

def get_user_workouts(user_id):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, workout_name, duration_minutes, calories_burned, workout_date, notes
        FROM workouts WHERE user_id = ? ORDER BY workout_date DESC
    ''', (user_id,))
    workouts = c.fetchall()
    conn.close()
    return workouts

def add_goal(user_id, goal_type, target_value, deadline):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO goals (user_id, goal_type, target_value, deadline)
        VALUES (?, ?, ?, ?)
    ''', (user_id, goal_type, target_value, deadline))
    conn.commit()
    conn.close()

def get_user_goals(user_id):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, goal_type, target_value, current_value, deadline, status
        FROM goals WHERE user_id = ? ORDER BY created_at DESC
    ''', (user_id,))
    goals = c.fetchall()
    conn.close()
    return goals

def update_goal_progress(goal_id, current_value):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('UPDATE goals SET current_value = ? WHERE id = ?', (current_value, goal_id))
    conn.commit()
    conn.close()

def update_trainer_profile(user_id, specialization, experience, bio):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('''
        UPDATE trainers SET specialization = ?, experience_years = ?, bio = ?
        WHERE user_id = ?
    ''', (specialization, experience, bio, user_id))
    conn.commit()
    conn.close()

def get_trainer_profile(user_id):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('SELECT specialization, experience_years, bio FROM trainers WHERE user_id = ?', (user_id,))
    profile = c.fetchone()
    conn.close()
    return profile

def get_all_users():
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute('SELECT id, name, email, account_type FROM users WHERE account_type = "user"')
    users = c.fetchall()
    conn.close()
    return users

# Initialize database
init_db()

# ==================== CUSTOM CSS ====================

st.markdown("""
<style>
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Background with fitness image overlay */
    .stApp {
        background: linear-gradient(rgba(10, 10, 30, 0.85), rgba(15, 25, 50, 0.85)), 
                    url('https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1920&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        min-height: 100vh;
    }
    
    /* Auth card styling */
    .auth-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 2.5rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
        max-width: 420px;
        margin: 0 auto;
    }
    
    /* Dashboard card */
    .dashboard-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(15px);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
        margin-bottom: 1rem;
    }
    
    /* Plan card */
    .plan-card {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(15px);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 1rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .plan-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    }
    
    /* Titles */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 1.5rem;
    }
    
    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: white;
        margin-bottom: 1rem;
    }
    
    .card-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: white;
        margin-bottom: 0.5rem;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #e63946 0%, #f72585 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(230, 57, 70, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(230, 57, 70, 0.5);
    }
    
    /* Price tag */
    .price-tag {
        background: linear-gradient(135deg, #e63946 0%, #f72585 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }
    
    /* Badge */
    .badge {
        background: rgba(230, 57, 70, 0.2);
        color: #f72585;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .badge-success {
        background: rgba(0, 200, 100, 0.2);
        color: #00c864;
    }
    
    /* Chat bubble */
    .chat-sent {
        background: linear-gradient(135deg, #e63946 0%, #f72585 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.5rem 0;
        max-width: 70%;
        margin-left: auto;
    }
    
    .chat-received {
        background: rgba(255, 255, 255, 0.15);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.5rem 0;
        max-width: 70%;
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    div[data-testid="stMetric"] label {
        color: rgba(255, 255, 255, 0.8) !important;
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: white !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: white;
        font-weight: 500;
        padding: 0.75rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #e63946 0%, #f72585 100%);
    }
    
    /* Form inputs in white cards */
    .auth-card .stTextInput label,
    .auth-card .stSelectbox label,
    .auth-card .stNumberInput label,
    .auth-card .stTextArea label {
        color: #1f2937 !important;
        font-weight: 600;
    }
    
    /* White text for dashboard forms */
    .stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label, .stDateInput label {
        color: white !important;
    }
    
    /* Link text */
    .link-text {
        text-align: center;
        color: #374151;
        background: rgba(255, 255, 255, 0.9);
        padding: 1rem;
        border-radius: 12px;
        margin-top: 1rem;
    }
    
    /* Scrollable chat container */
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        padding: 1rem;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 12px;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(135deg, #e63946 0%, #f72585 100%);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: white !important;
    }
    
    /* Text colors */
    p, span, div {
        color: white;
    }
    
    .auth-card p, .auth-card span, .auth-card div {
        color: #374151;
    }
</style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'chat_with' not in st.session_state:
    st.session_state.chat_with = None
if 'view_plan' not in st.session_state:
    st.session_state.view_plan = None
if 'edit_plan' not in st.session_state:
    st.session_state.edit_plan = None

# ==================== AUTH PAGES ====================

def show_login_page():
    st.markdown('<h1 class="main-title">FITHUB</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: rgba(255,255,255,0.8); margin-bottom: 2rem;">Connect to Fitness</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: #1f2937; margin-bottom: 1.5rem;">Welcome Back</h2>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if email and password:
                    user = verify_user(email, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
                else:
                    st.error("Please fill in all fields")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="link-text">Don\'t have an account?</div>', unsafe_allow_html=True)
        
        if st.button("Create Account", key="go_signup"):
            st.session_state.page = 'signup'
            st.rerun()

def show_signup_page():
    st.markdown('<h1 class="main-title">Join FITHUB</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        
        account_type = st.radio(
            "I am a:",
            ["User", "Trainer"],
            horizontal=True
        )
        
        with st.form("signup_form"):
            name = st.text_input("Full Name", placeholder="Enter your name")
            email = st.text_input("Email", placeholder="Enter your email")
            mobile = st.text_input("Mobile No.", placeholder="Enter your mobile number")
            password = st.text_input("Password", type="password", placeholder="Min 6 characters")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password")
            
            submit = st.form_submit_button("Sign Up", use_container_width=True)
            
            if submit:
                if not all([name, email, mobile, password, confirm_password]):
                    st.error("Please fill in all fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, message, token = create_user(
                        name, email, mobile, password, 
                        account_type.lower()
                    )
                    if success:
                        st.success(message + " Please login.")
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(message)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="link-text">Already have an account?</div>', unsafe_allow_html=True)
        
        if st.button("Back to Login", key="go_login"):
            st.session_state.page = 'login'
            st.rerun()

# ==================== USER DASHBOARD ====================

def show_user_dashboard():
    user = st.session_state.user
    
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f'<h1 class="main-title">Welcome, {user["name"]}!</h1>', unsafe_allow_html=True)
    with col2:
        if st.button("Logout", key="logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    # Stats
    workouts = get_user_workouts(user['id'])
    goals = get_user_goals(user['id'])
    subscriptions = get_user_subscriptions(user['id'])
    followed = get_followed_trainers(user['id'])
    unread = get_unread_count(user['id'])
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Workouts", len(workouts))
    with col2:
        st.metric("Active Plans", len(subscriptions))
    with col3:
        st.metric("Following", len(followed))
    with col4:
        st.metric("Goals", len([g for g in goals if g[5] == 'active']))
    with col5:
        st.metric("Messages", unread)
    
    st.markdown("---")
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Feed", "Browse Plans", "My Subscriptions", "Trainers", "Workouts", "Goals", "Chat"
    ])
    
    # Personalized Feed Tab
    with tab1:
        st.markdown('<p class="section-title">Your Personalized Feed</p>', unsafe_allow_html=True)
        
        if followed:
            feed = get_personalized_feed(user['id'])
            if feed:
                for plan in feed:
                    with st.container():
                        st.markdown('<div class="plan-card">', unsafe_allow_html=True)
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f'<p class="card-title">{plan[1]}</p>', unsafe_allow_html=True)
                            st.write(f"By **{plan[8]}** | {plan[5]} | {plan[4]} days")
                            if plan[10]:  # is_purchased
                                st.markdown('<span class="badge badge-success">Purchased</span>', unsafe_allow_html=True)
                        with col2:
                            st.markdown(f'<span class="price-tag">${plan[3]:.2f}</span>', unsafe_allow_html=True)
                            if not plan[10]:
                                if st.button("Subscribe", key=f"feed_sub_{plan[0]}"):
                                    success, msg = subscribe_to_plan(user['id'], plan[0], plan[3])
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Trainers you follow haven't created any plans yet.")
        else:
            st.info("Follow some trainers to see their plans in your feed!")
    
    # Browse Plans Tab
    with tab2:
        st.markdown('<p class="section-title">All Fitness Plans</p>', unsafe_allow_html=True)
        
        plans = get_all_plans()
        
        if plans:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                difficulty_filter = st.selectbox("Filter by Difficulty", ["All", "Beginner", "Intermediate", "Advanced"])
            with col2:
                category_filter = st.selectbox("Filter by Category", ["All", "Weight Loss", "Muscle Building", "Cardio", "Flexibility", "General"])
            
            for plan in plans:
                # Apply filters
                if difficulty_filter != "All" and plan[5] != difficulty_filter:
                    continue
                if category_filter != "All" and plan[6] != category_filter:
                    continue
                
                is_sub = is_subscribed(user['id'], plan[0])
                
                with st.container():
                    st.markdown('<div class="plan-card">', unsafe_allow_html=True)
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f'<p class="card-title">{plan[1]}</p>', unsafe_allow_html=True)
                        st.write(f"By **{plan[8]}**")
                        st.markdown(f'<span class="badge">{plan[5]}</span><span class="badge">{plan[6]}</span><span class="badge">{plan[4]} days</span>', unsafe_allow_html=True)
                        
                        # Show full description only if subscribed
                        if is_sub:
                            st.write(plan[2])
                            st.markdown('<span class="badge badge-success">Subscribed</span>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f'<span class="price-tag">${plan[3]:.2f}</span>', unsafe_allow_html=True)
                        if not is_sub:
                            if st.button("Subscribe", key=f"sub_{plan[0]}"):
                                success, msg = subscribe_to_plan(user['id'], plan[0], plan[3])
                                if success:
                                    st.success("Payment simulated successfully! " + msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No fitness plans available yet.")
    
    # My Subscriptions Tab
    with tab3:
        st.markdown('<p class="section-title">My Subscriptions</p>', unsafe_allow_html=True)
        
        subs = get_user_subscriptions(user['id'])
        
        if subs:
            for sub in subs:
                with st.container():
                    st.markdown('<div class="plan-card">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f'<p class="card-title">{sub[2]}</p>', unsafe_allow_html=True)
                        st.write(f"By **{sub[6]}**")
                        st.write(f"**Full Description:** {sub[3]}")
                        st.write(f"Duration: {sub[5]} days | Paid: ${sub[9]:.2f}")
                        st.write(f"Valid: {sub[7]} to {sub[8]}")
                    
                    with col2:
                        days_left = (datetime.strptime(str(sub[8]), '%Y-%m-%d').date() - datetime.now().date()).days
                        if days_left > 0:
                            st.markdown(f'<span class="badge badge-success">{days_left} days left</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="badge">Expired</span>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("You haven't subscribed to any plans yet. Browse plans to get started!")
    
    # Trainers Tab
    with tab4:
        st.markdown('<p class="section-title">Discover Trainers</p>', unsafe_allow_html=True)
        
        trainers = get_all_trainers()
        
        if trainers:
            for trainer in trainers:
                is_foll = is_following(user['id'], trainer[0])
                followers_count = get_trainer_followers_count(trainer[0])
                
                with st.container():
                    st.markdown('<div class="plan-card">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown(f'<p class="card-title">{trainer[1]}</p>', unsafe_allow_html=True)
                        if trainer[3]:
                            st.write(f"Specialization: {trainer[3]}")
                        if trainer[4]:
                            st.write(f"Experience: {trainer[4]} years")
                        st.write(f"Followers: {followers_count}")
                    
                    with col2:
                        if trainer[5]:
                            st.write(trainer[5])
                    
                    with col3:
                        if is_foll:
                            if st.button("Unfollow", key=f"unfollow_{trainer[0]}"):
                                unfollow_trainer(user['id'], trainer[0])
                                st.rerun()
                        else:
                            if st.button("Follow", key=f"follow_{trainer[0]}"):
                                follow_trainer(user['id'], trainer[0])
                                st.rerun()
                        
                        if st.button("Chat", key=f"chat_trainer_{trainer[0]}"):
                            st.session_state.chat_with = trainer[0]
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No trainers available yet.")
        
        # Following list
        st.markdown("---")
        st.markdown('<p class="section-title">Trainers You Follow</p>', unsafe_allow_html=True)
        
        followed_trainers = get_followed_trainers(user['id'])
        if followed_trainers:
            for trainer in followed_trainers:
                st.write(f"**{trainer[1]}** - {trainer[3] or 'Trainer'}")
        else:
            st.info("You're not following any trainers yet.")
    
    # Workouts Tab
    with tab5:
        st.markdown('<p class="section-title">Log Workout</p>', unsafe_allow_html=True)
        
        with st.form("workout_form"):
            col1, col2 = st.columns(2)
            with col1:
                workout_name = st.selectbox("Workout Type", ["Running", "Weight Training", "Cycling", "Swimming", "Yoga", "HIIT", "Walking", "Other"])
                duration = st.number_input("Duration (minutes)", min_value=1, max_value=300, value=30)
            with col2:
                calories = st.number_input("Calories Burned", min_value=0, max_value=5000, value=200)
                workout_date = st.date_input("Date", value=datetime.now())
            notes = st.text_area("Notes (optional)")
            
            if st.form_submit_button("Log Workout", use_container_width=True):
                add_workout(user['id'], workout_name, duration, calories, workout_date, notes)
                st.success("Workout logged!")
                st.rerun()
        
        st.markdown("---")
        st.markdown('<p class="section-title">Workout History</p>', unsafe_allow_html=True)
        
        for workout in workouts[:10]:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                with col1:
                    st.write(f"**{workout[1]}**")
                with col2:
                    st.write(f"{workout[2]} min")
                with col3:
                    st.write(f"{workout[3]} cal")
                with col4:
                    st.write(f"{workout[4]}")
    
    # Goals Tab
    with tab6:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<p class="section-title">Add Goal</p>', unsafe_allow_html=True)
            with st.form("goal_form"):
                goal_type = st.selectbox("Goal Type", ["Workouts per week", "Calories to burn", "Minutes to train", "Weight loss (kg)", "Weight gain (kg)"])
                target_value = st.number_input("Target Value", min_value=1, value=10)
                deadline = st.date_input("Target Date")
                
                if st.form_submit_button("Add Goal", use_container_width=True):
                    add_goal(user['id'], goal_type, target_value, deadline)
                    st.success("Goal added!")
                    st.rerun()
        
        with col2:
            st.markdown('<p class="section-title">Active Goals</p>', unsafe_allow_html=True)
            for goal in goals:
                if goal[5] == 'active':
                    progress = (goal[3] / goal[2]) * 100 if goal[2] > 0 else 0
                    st.write(f"**{goal[1]}**")
                    st.progress(min(progress / 100, 1.0))
                    st.caption(f"{goal[3]:.0f} / {goal[2]:.0f}")
                    
                    new_val = st.number_input("Update", min_value=0.0, value=float(goal[3]), key=f"goal_{goal[0]}")
                    if st.button("Update", key=f"upd_{goal[0]}"):
                        update_goal_progress(goal[0], new_val)
                        st.rerun()
    
    # Chat Tab
    with tab7:
        st.markdown('<p class="section-title">Messages</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("**Contacts**")
            contacts = get_chat_contacts(user['id'])
            
            # Also show trainers and users to start new chats
            all_users_to_chat = get_all_users() + [(t[0], t[1], 'trainer') for t in get_all_trainers()]
            
            for contact in contacts:
                if st.button(f"{contact[1]} ({contact[2]})", key=f"contact_{contact[0]}"):
                    st.session_state.chat_with = contact[0]
                    st.rerun()
            
            st.markdown("---")
            st.write("**Start New Chat**")
            chat_options = {f"{u[1]} ({u[2] if len(u) > 2 else 'user'})": u[0] for u in all_users_to_chat if u[0] != user['id']}
            selected_chat = st.selectbox("Select User", list(chat_options.keys()))
            if st.button("Open Chat"):
                st.session_state.chat_with = chat_options[selected_chat]
                st.rerun()
        
        with col2:
            if st.session_state.chat_with:
                # Get chat partner name
                conn = sqlite3.connect('fitness.db')
                c = conn.cursor()
                c.execute('SELECT name FROM users WHERE id = ?', (st.session_state.chat_with,))
                partner = c.fetchone()
                conn.close()
                
                if partner:
                    st.write(f"**Chat with {partner[0]}**")
                    
                    # Mark messages as read
                    mark_messages_read(user['id'], st.session_state.chat_with)
                    
                    # Show messages
                    messages = get_conversation(user['id'], st.session_state.chat_with)
                    
                    chat_container = st.container()
                    with chat_container:
                        for msg in messages:
                            if msg[1] == user['id']:
                                st.markdown(f'<div class="chat-sent"><small>{msg[4]}</small><br>{msg[3]}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="chat-received"><small>{msg[5]} - {msg[4]}</small><br>{msg[3]}</div>', unsafe_allow_html=True)
                    
                    # Send message
                    with st.form("send_message", clear_on_submit=True):
                        new_msg = st.text_input("Type a message...")
                        if st.form_submit_button("Send"):
                            if new_msg:
                                send_message(user['id'], st.session_state.chat_with, new_msg)
                                st.rerun()
            else:
                st.info("Select a contact to start chatting")

# ==================== TRAINER DASHBOARD ====================

def show_trainer_dashboard():
    user = st.session_state.user
    
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f'<h1 class="main-title">Trainer Dashboard - {user["name"]}</h1>', unsafe_allow_html=True)
    with col2:
        if st.button("Logout", key="logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    # Stats
    plans = get_trainer_plans(user['id'])
    followers = get_trainer_followers_count(user['id'])
    unread = get_unread_count(user['id'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("My Plans", len(plans))
    with col2:
        st.metric("Followers", followers)
    with col3:
        st.metric("Messages", unread)
    with col4:
        st.metric("Rating", "4.8")
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["My Plans", "Create Plan", "Users", "Profile", "Chat"])
    
    # My Plans Tab
    with tab1:
        st.markdown('<p class="section-title">My Fitness Plans</p>', unsafe_allow_html=True)
        
        if plans:
            for plan in plans:
                with st.container():
                    st.markdown('<div class="plan-card">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f'<p class="card-title">{plan[1]}</p>', unsafe_allow_html=True)
                        st.write(plan[2][:100] + "..." if len(plan[2]) > 100 else plan[2])
                        st.markdown(f'<span class="badge">{plan[5]}</span><span class="badge">{plan[6]}</span><span class="badge">{plan[4]} days</span>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f'<span class="price-tag">${plan[3]:.2f}</span>', unsafe_allow_html=True)
                    
                    with col3:
                        if st.button("Edit", key=f"edit_{plan[0]}"):
                            st.session_state.edit_plan = plan[0]
                            st.rerun()
                        if st.button("Delete", key=f"del_{plan[0]}"):
                            delete_fitness_plan(plan[0], user['id'])
                            st.success("Plan deleted!")
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Edit form
                    if st.session_state.edit_plan == plan[0]:
                        with st.form(f"edit_plan_form_{plan[0]}"):
                            st.subheader("Edit Plan")
                            edit_title = st.text_input("Title", value=plan[1])
                            edit_desc = st.text_area("Description", value=plan[2])
                            col1, col2 = st.columns(2)
                            with col1:
                                edit_price = st.number_input("Price ($)", value=float(plan[3]), min_value=0.0)
                                edit_duration = st.number_input("Duration (days)", value=plan[4], min_value=1)
                            with col2:
                                edit_diff = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"], index=["Beginner", "Intermediate", "Advanced"].index(plan[5]))
                                edit_cat = st.selectbox("Category", ["Weight Loss", "Muscle Building", "Cardio", "Flexibility", "General"], index=["Weight Loss", "Muscle Building", "Cardio", "Flexibility", "General"].index(plan[6]) if plan[6] in ["Weight Loss", "Muscle Building", "Cardio", "Flexibility", "General"] else 4)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Save Changes"):
                                    update_fitness_plan(plan[0], user['id'], edit_title, edit_desc, edit_price, edit_duration, edit_diff, edit_cat)
                                    st.session_state.edit_plan = None
                                    st.success("Plan updated!")
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("Cancel"):
                                    st.session_state.edit_plan = None
                                    st.rerun()
        else:
            st.info("You haven't created any plans yet.")
    
    # Create Plan Tab
    with tab2:
        st.markdown('<p class="section-title">Create New Fitness Plan</p>', unsafe_allow_html=True)
        
        with st.form("create_plan_form"):
            title = st.text_input("Plan Title", placeholder="e.g., Fat Loss Beginner Plan")
            description = st.text_area("Description", placeholder="Describe your fitness plan in detail...")
            
            col1, col2 = st.columns(2)
            with col1:
                price = st.number_input("Price ($)", min_value=0.0, value=29.99, step=0.01)
                duration = st.number_input("Duration (days)", min_value=1, value=30)
            with col2:
                difficulty = st.selectbox("Difficulty Level", ["Beginner", "Intermediate", "Advanced"])
                category = st.selectbox("Category", ["Weight Loss", "Muscle Building", "Cardio", "Flexibility", "General"])
            
            if st.form_submit_button("Create Plan", use_container_width=True):
                if title and description:
                    create_fitness_plan(user['id'], title, description, price, duration, difficulty, category)
                    st.success("Fitness plan created successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in title and description")
    
    # Users Tab
    with tab3:
        st.markdown('<p class="section-title">Registered Users</p>', unsafe_allow_html=True)
        
        users = get_all_users()
        if users:
            for u in users:
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**{u[1]}**")
                    with col2:
                        st.write(u[2])
                    with col3:
                        if st.button("Chat", key=f"chat_user_{u[0]}"):
                            st.session_state.chat_with = u[0]
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("No users registered yet.")
    
    # Profile Tab
    with tab4:
        st.markdown('<p class="section-title">My Profile</p>', unsafe_allow_html=True)
        
        profile = get_trainer_profile(user['id'])
        
        with st.form("profile_form"):
            specialization = st.selectbox(
                "Specialization",
                ["Weight Training", "Cardio", "Yoga", "CrossFit", "Swimming", "Martial Arts", "Other"],
                index=["Weight Training", "Cardio", "Yoga", "CrossFit", "Swimming", "Martial Arts", "Other"].index(profile[0]) if profile and profile[0] else 0
            )
            experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=profile[1] if profile and profile[1] else 0)
            bio = st.text_area("Bio", value=profile[2] if profile and profile[2] else "", placeholder="Tell users about yourself...")
            
            if st.form_submit_button("Update Profile", use_container_width=True):
                update_trainer_profile(user['id'], specialization, experience, bio)
                st.success("Profile updated!")
                st.rerun()
    
    # Chat Tab
    with tab5:
        st.markdown('<p class="section-title">Messages</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("**Contacts**")
            contacts = get_chat_contacts(user['id'])
            
            for contact in contacts:
                if st.button(f"{contact[1]}", key=f"contact_{contact[0]}"):
                    st.session_state.chat_with = contact[0]
                    st.rerun()
            
            st.markdown("---")
            st.write("**All Users**")
            all_users = get_all_users()
            for u in all_users:
                if st.button(f"{u[1]}", key=f"start_chat_{u[0]}"):
                    st.session_state.chat_with = u[0]
                    st.rerun()
        
        with col2:
            if st.session_state.chat_with:
                conn = sqlite3.connect('fitness.db')
                c = conn.cursor()
                c.execute('SELECT name FROM users WHERE id = ?', (st.session_state.chat_with,))
                partner = c.fetchone()
                conn.close()
                
                if partner:
                    st.write(f"**Chat with {partner[0]}**")
                    
                    mark_messages_read(user['id'], st.session_state.chat_with)
                    messages = get_conversation(user['id'], st.session_state.chat_with)
                    
                    for msg in messages:
                        if msg[1] == user['id']:
                            st.markdown(f'<div class="chat-sent"><small>{msg[4]}</small><br>{msg[3]}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="chat-received"><small>{msg[5]} - {msg[4]}</small><br>{msg[3]}</div>', unsafe_allow_html=True)
                    
                    with st.form("trainer_send_msg", clear_on_submit=True):
                        new_msg = st.text_input("Type a message...")
                        if st.form_submit_button("Send"):
                            if new_msg:
                                send_message(user['id'], st.session_state.chat_with, new_msg)
                                st.rerun()
            else:
                st.info("Select a user to start chatting")

# ==================== MAIN APP ====================

def main():
    if not st.session_state.logged_in:
        if st.session_state.page == 'login':
            show_login_page()
        else:
            show_signup_page()
    else:
        if st.session_state.user['account_type'] == 'trainer':
            show_trainer_dashboard()
        else:
            show_user_dashboard()

if __name__ == "__main__":
    main()
