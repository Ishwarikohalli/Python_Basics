
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import os
from dotenv import load_dotenv
import uvicorn
import mysql.connector
from mysql.connector import pooling, Error
from typing import Generator
import logging
from pydantic import BaseModel
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="EduBot API",
    description="AI-powered educational assistant",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatMessage(BaseModel):
    content: str
    subject: str = "general"
    user_id: str

class ChatResponse(BaseModel):
    response: str
    message_id: int
    timestamp: datetime

class SignupRequest(BaseModel):
    username: str
    password: str  # Store plain text password (not secure)

class LoginRequest(BaseModel):
    username: str
    password: str

# Database connection pool
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="edubot_pool",
        pool_size=5,
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        database="edubot",
        port=int(os.getenv("DB_PORT", "3306"))
    )
    logger.info("Database connection pool created successfully")
except Error as e:
    logger.error(f"Connection pool error: {e}")
    raise RuntimeError(f"Failed to create connection pool: {e}")

def get_db():
    db = None
    try:
        db = connection_pool.get_connection()
        yield db
    finally:
        if db:
            db.close()

# Initialize Groq client
try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    logger.info("Groq client initialized successfully")
except Exception as e:
    logger.error(f"Groq client error: {e}")
    raise RuntimeError(f"Failed to initialize Groq client: {e}")

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage, db=Depends(get_db)):
    cursor = None
    try:
        logger.info(f"Received message from user {message.user_id}")
        cursor = db.cursor()

        # Insert message
        insert_query = """
        INSERT INTO chat_history (user_id, message, subject)
        VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (
            message.user_id,
            message.content,
            message.subject
        ))
        message_id = cursor.lastrowid

        # Get AI response
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message.content}],
            temperature=0.7
        )
        response_content = response.choices[0].message.content

        # Update with AI response
        update_query = "UPDATE chat_history SET response = %s WHERE id = %s"
        cursor.execute(update_query, (response_content, message_id))
        db.commit()

        return {
            "response": response_content,
            "message_id": message_id,
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process message")
    finally:
        if cursor:
            cursor.close()

# Chat history
@app.get("/api/chat/history")
async def get_chat_history(user_id: str = None, limit: int = 50, db=Depends(get_db)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM chat_history"
        params = []

        if user_id:
            query += " WHERE user_id = %s"
            params.append(user_id)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        return cursor.fetchall()

    except Exception as e:
        logger.error(f"History error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve history")
    finally:
        if cursor:
            cursor.close()

# Signup endpoint (no password hashing)
@app.post("/api/signup")
async def signup(user: SignupRequest, db=Depends(get_db)):
    cursor = None
    try:
        cursor = db.cursor()

        # Check existing username
        cursor.execute("SELECT id FROM user WHERE username = %s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")

        # Store plain password (NOT SECURE in production)
        insert_query = """
        INSERT INTO user (username, password, created_at)
        VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (user.username, user.password, datetime.now()))
        db.commit()

        return {"message": "User registered successfully"}

    except Exception as e:
        logger.error(f"Signup error: {str(e)}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register user")
    finally:
        if cursor:
            cursor.close()

# Login endpoint
@app.post("/api/login")
async def login(user: LoginRequest, db=Depends(get_db)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, username FROM user WHERE username = %s AND password = %s", (user.username, user.password))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {"message": "Login successful", "user": result}
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to login")
    finally:
        if cursor:
            cursor.close()

# Run app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
