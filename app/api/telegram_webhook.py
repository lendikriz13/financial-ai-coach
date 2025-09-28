from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, Transaction, ConversationHistory
from app.services.memory_service import MemoryService
import json
import os
import httpx
from datetime import datetime

router = APIRouter()

# Use environment variables (Railway will provide these)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(f"Bot token loaded: {TELEGRAM_BOT_TOKEN is not None}")
print(f"Anthropic key loaded: {ANTHROPIC_API_KEY is not None}")

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
    """Process Telegram messages with AI financial coaching, memory, and reset commands"""
    try:
        print("=== MEMORY-ENABLED WEBHOOK START ===")
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
                    username=message["from"].get("username"),
                    created_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"✅ Created new user: {user.first_name}")
            else:
                print(f"✅ Found existing user: {user.first_name} (Business: {user.business_type or 'Unknown'})")
            
            # Handle special commands first
            if user_text.lower() in ['/reset', '/clear', '/restart']:
                print("🔄 Memory reset command received")
                try:
                    # Clear conversation history
                    deleted_count = db.query(ConversationHistory).filter(ConversationHistory.user_id == user.id).delete()
                    
                    # Reset user context fields
                    user.conversation_summary = None
                    user.business_context = None
                    user.business_type = None
                    user.last_interaction = datetime.utcnow()
                    
                    db.commit()
                    
                    response_text = f"Memory cleared! Deleted {deleted_count} conversation(s). Starting fresh as your business mentor."
                    await send_telegram_message(chat_id, response_text)
                    print(f"✅ Memory reset complete - cleared {deleted_count} conversations")
                    return {"status": "success", "action": "memory_reset"}
                    
                except Exception as e:
                    print(f"❌ Error during memory reset: {e}")
                    db.rollback()
                    await send_telegram_message(chat_id, "Sorry, there was an error clearing memory. Please try again.")
                    return {"status": "error", "message": f"Memory reset failed: {str(e)}"}
            
            # Handle special info commands
            elif user_text.lower() in ['/stats', '/info', '/status']:
                print("📊 Stats command received")
                try:
                    stats = MemoryService.get_user_stats(db, user.id)
                    business_info = f"Business: {user.business_type or 'Not detected'}"
                    
                    stats_text = f"**Your Financial Coach Stats:**\n" \
                                f"• Total conversations: {stats['total_conversations']}\n" \
                                f"• Recent conversations (7 days): {stats['recent_conversations']}\n" \
                                f"• {business_info}\n" \
                                f"• Last interaction: {user.last_interaction.strftime('%Y-%m-%d %H:%M') if user.last_interaction else 'Never'}\n\n" \
                                f"Commands: /reset (clear memory), /stats (this info)"
                    
                    await send_telegram_message(chat_id, stats_text)
                    print("✅ Stats sent successfully")
                    return {"status": "success", "action": "stats_sent"}
                    
                except Exception as e:
                    print(f"❌ Error getting stats: {e}")
                    await send_telegram_message(chat_id, "Sorry, couldn't retrieve your stats right now.")
                    return {"status": "error", "message": f"Stats error: {str(e)}"}
            
            # Process regular messages with Claude AI
            elif user_text and not user_text.startswith('/'):
                print("Processing with memory-enabled Claude AI...")
                
                # Validate API key first
                if not ANTHROPIC_API_KEY or len(ANTHROPIC_API_KEY.strip()) < 10:
                    print("❌ Invalid or missing Anthropic API key")
                    await send_telegram_message(chat_id, "Sorry, AI service configuration error. Please contact support.")
                    return {"status": "error", "message": "Invalid API key"}
                
                # Update user context and interaction tracking
                MemoryService.update_user_context(db, user, user_text)
                print(f"✅ Updated user context (Business type: {user.business_type})")
                
                # Get recent conversation history
                recent_conversations = MemoryService.get_recent_conversations(db, user.id, 8)
                print(f"✅ Retrieved {len(recent_conversations)} recent conversations")
                
                # Build memory-aware prompt with conversation history
                ai_prompt = MemoryService.build_context_prompt(user, recent_conversations, user_text)
                print(f"✅ Built context-aware prompt (length: {len(ai_prompt)} chars)")
                
                try:
                    # Use current Claude model names from 2024/2025
                    headers = {
                        "Content-Type": "application/json",
                        "x-api-key": ANTHROPIC_API_KEY.strip(),
                        "anthropic-version": "2023-06-01"
                    }
                    
                    # Try multiple model names in order of preference
                    model_options = [
                        "claude-3-5-sonnet-20241022",  # Latest Claude 3.5 Sonnet
                        "claude-3-5-sonnet-20240620",  # Stable Claude 3.5 Sonnet 
                        "claude-3-sonnet-20240229",    # Original Claude 3 Sonnet
                        "claude-3-haiku-20240307"      # Fallback to Haiku
                    ]
                    
                    response_success = False
                    ai_response = ""
                    
                    for model_name in model_options:
                        try:
                            print(f"Trying model: {model_name}")
                            
                            payload = {
                                "model": model_name,
                                "max_tokens": 300,
                                "messages": [{"role": "user", "content": ai_prompt}]
                            }
                            
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                response = await client.post(
                                    "https://api.anthropic.com/v1/messages",
                                    headers=headers,
                                    json=payload
                                )
                                
                                print(f"API Response Status: {response.status_code}")
                                
                                if response.status_code == 200:
                                    response_data = response.json()
                                    ai_response = response_data["content"][0]["text"]
                                    print(f"✅ Claude response ({model_name}): {ai_response[:100]}...")
                                    
                                    # Send response back to Telegram user
                                    await send_telegram_message(chat_id, ai_response)
                                    print("✅ Response sent to user")
                                    response_success = True
                                    break
                                    
                                elif response.status_code == 404:
                                    print(f"❌ Model {model_name} not found, trying next...")
                                    continue
                                    
                                else:
                                    print(f"❌ API Error {response.status_code}: {response.text}")
                                    continue
                                    
                        except Exception as model_error:
                            print(f"❌ Error with model {model_name}: {model_error}")
                            continue
                    
                    if not response_success:
                        print("❌ All models failed")
                        await send_telegram_message(chat_id, "Sorry, AI service is temporarily unavailable. Please try again later.")
                        return {"status": "error", "message": "All Claude models failed"}
                    
                    # Store the conversation in memory system
                    if response_success and ai_response:
                        message_type = MemoryService.categorize_message_type(user_text)
                        conversation = MemoryService.store_conversation(
                            db=db,
                            user_id=user.id,
                            user_message=user_text,
                            ai_response=ai_response,
                            message_type=message_type
                        )
                        print(f"✅ Conversation stored (Type: {message_type}, ID: {conversation.id})")
                        
                        # Update conversation summary periodically
                        total_conversations = len(MemoryService.get_recent_conversations(db, user.id, 100))
                        
                        # Update summary every 5 conversations
                        if total_conversations % 5 == 0:
                            MemoryService.update_conversation_summary(db, user)
                            print("✅ Updated conversation summary")
                    
                except Exception as e:
                    print(f"❌ General Claude API error: {e}")
                    await send_telegram_message(chat_id, "Sorry, I encountered an error processing your request. Please try again.")
                    return {"status": "error", "message": f"Claude API error: {str(e)}"}
            
            # Handle unknown commands
            elif user_text.startswith('/'):
                print(f"❓ Unknown command: {user_text}")
                help_text = "**Available commands:**\n" \
                           "• /reset - Clear conversation memory\n" \
                           "• /stats - View conversation statistics\n\n" \
                           "Just send a regular message to chat with your financial coach!"
                await send_telegram_message(chat_id, help_text)
                return {"status": "success", "action": "help_sent"}
        
        print("=== MEMORY-ENABLED WEBHOOK END ===")
        return {"status": "success"}
        
    except Exception as e:
        print(f"=== WEBHOOK ERROR: {e} ===")
        if 'chat_id' in locals():
            await send_telegram_message(chat_id, "Sorry, I encountered an error. Please try again.")
        return {"status": "error", "message": str(e)}