from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, Transaction
import json
import os
import httpx
from anthropic import Anthropic

router = APIRouter()

# Use environment variables (Railway will provide these)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(f"Bot token loaded: {TELEGRAM_BOT_TOKEN is not None}")
print(f"Anthropic key loaded: {ANTHROPIC_API_KEY is not None}")

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

async def send_telegram_message(chat_id: int, text: str):
    """Send message back to Telegram user"""
    try:
        print(f"Attempting to send message to chat_id: {chat_id}")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            print(f"Telegram API response: {response.status_code}")
            print(f"Response content: {response.text}")
            
    except Exception as e:
        print(f"Error sending message: {e}")

@router.post("/telegram")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Process Telegram messages with AI financial coaching"""
    try:
        print("=== WEBHOOK PROCESSING START ===")
        data = await request.json()
        print(f"Received data: {json.dumps(data, indent=2)}")
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            telegram_id = message["from"]["id"]
            user_text = message.get("text", "")
            first_name = message["from"].get("first_name", "")
            
            print(f"Chat ID: {chat_id}")
            print(f"User text: {user_text}")
            
            # Get or create user in database
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    first_name=first_name,
                    username=message["from"].get("username")
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"Created new user: {user.first_name}")
            
            # Process with Claude AI for financial coaching
            if user_text:
                print("Processing with Claude AI...")
                
                ai_prompt = f"""You are a helpful financial coach and business advisor for a clothing business owner. The user said: "{user_text}"

Provide helpful, encouraging financial advice. If they mention spending money, help them track expenses and categorize them as business or personal. If they ask about business calculations, help with breakeven analysis, profit margins, inventory planning, etc.

Keep responses conversational, supportive, and under 200 words. Act like a knowledgeable financial mentor who understands small business challenges."""
                
                # Get AI response from Claude
                message_response = anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=300,
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                
                ai_response = message_response.content[0].text
                print(f"Claude response: {ai_response}")
                
                # Send response back to Telegram user
                await send_telegram_message(chat_id, ai_response)
                print("Response sent to user")
        
        print("=== WEBHOOK PROCESSING END ===")
        return {"status": "success"}
        
    except Exception as e:
        print(f"=== WEBHOOK ERROR: {e} ===")
        if 'chat_id' in locals():
            await send_telegram_message(chat_id, "Sorry, I encountered an error. Please try again.")
        return {"status": "error", "message": str(e)}