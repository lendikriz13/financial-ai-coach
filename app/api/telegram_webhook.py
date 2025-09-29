from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, ConversationHistory
from app.services.memory_service import MemoryService
import json
import os
import httpx
from datetime import datetime

router = APIRouter()

# Environment variables (Railway will provide these)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"Bot token loaded: {TELEGRAM_BOT_TOKEN is not None}")
print(f"OpenAI key loaded: {OPENAI_API_KEY is not None}")

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """
You are a seasoned financial consultant and mentor. You speak with the voice of an older, wiser professional who is approachable, thoughtful, and firm when needed. You are conversational, but not casual — you balance warmth with professionalism. You occasionally use emojis (sparingly) to emphasize encouragement or clarity.

Tone & Personality:
- Sound like a trusted mentor, similar in style to Jarvis: calm, confident, and insightful.
- Do not flatter unnecessarily; be supportive but direct.
- Offer pushback when the user’s ideas or assumptions seem unrealistic or unwise.

Scope of Coaching:
- Cover both personal and business finances, adapting to the user’s context.
- Alternate naturally between teaching (explaining concepts) and advising (giving actionable steps).
- Keep responses short, clear, and focused on next actions, while weaving in explanations when they help learning.

Memory & Relationship:
- Maintain continuity across conversations by recalling goals, transactions, and context.
- Use past data to personalize advice.
- Ask thoughtful questions often, but not every single turn, to keep the conversation flowing naturally.

Boundaries & Guardrails:
- ✅ Provide basic/general information on investments and stocks.
- ❌ Do NOT give detailed or personalized investment strategies, tax loopholes, or legal advice. Instead, politely redirect and suggest appropriate resources or professionals.
- Always clarify when something is outside your scope.
"""

async def send_telegram_message(chat_id: int, text: str):
    """Send message back to Telegram user"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            print(f"Telegram API response: {response.status_code}")
            return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")

async def get_ai_response(messages, deep_mode=False):
    """Call OpenAI API with fallback if needed"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY.strip()}"
    }

    # Try deep mode first if requested
    model_order = ["gpt-4.1", "gpt-4.1-mini"] if deep_mode else ["gpt-4.1-mini"]

    for model in model_order:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 500
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )

            if response.status_code == 200:
                resp_data = response.json()
                return resp_data["choices"][0]["message"]["content"]

            else:
                print(f"❌ OpenAI API Error {response.status_code}: {response.text}")
                continue

        except Exception as e:
            print(f"❌ Error with model {model}: {e}")
            continue

    return "I ran into an error with both models. Please try again."

@router.post("/telegram")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Process Telegram messages with AI financial coaching and memory"""
    try:
        data = await request.json()
        print(f"Received data: {json.dumps(data, indent=2)}")

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            telegram_id = message["from"]["id"]
            user_text = message.get("text", "")
            first_name = message["from"].get("first_name", "")

            # Get or create user in DB
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
                print(f"✅ Found existing user: {user.first_name}")

            # === SPECIAL COMMANDS ===
            if user_text.lower() in ['/reset', '/clear', '/restart']:
                deleted_count = db.query(ConversationHistory).filter(
                    ConversationHistory.user_id == user.id
                ).delete()
                user.conversation_summary = None
                user.business_context = None
                user.business_type = None
                user.last_interaction = datetime.utcnow()
                db.commit()

                response_text = f"Memory cleared! Deleted {deleted_count} conversations. Starting fresh as your business mentor."
                await send_telegram_message(chat_id, response_text)
                return {"status": "success", "action": "memory_reset"}

            elif user_text.lower() in ['/stats', '/info', '/status']:
                stats = MemoryService.get_user_stats(db, user.id)
                business_info = f"Business: {user.business_type or 'Not detected'}"

                stats_text = f"**Your Financial Coach Stats:**\n" \
                             f"• Total conversations: {stats['total_conversations']}\n" \
                             f"• Recent (7 days): {stats['recent_conversations']}\n" \
                             f"• {business_info}\n" \
                             f"• Last interaction: {user.last_interaction.strftime('%Y-%m-%d %H:%M') if user.last_interaction else 'Never'}\n\n" \
                             f"Commands: /reset (clear memory), /stats (this info), /deep (use advanced mode)"
                await send_telegram_message(chat_id, stats_text)
                return {"status": "success", "action": "stats_sent"}

            # === MAIN AI HANDLER ===
            elif user_text and not user_text.startswith('/'):
                if not OPENAI_API_KEY or len(OPENAI_API_KEY.strip()) < 10:
                    await send_telegram_message(chat_id, "AI service configuration error. Please contact support.")
                    return {"status": "error", "message": "Invalid OpenAI API key"}

                # Update context + fetch recent history
                MemoryService.update_user_context(db, user, user_text)
                recent_convos = MemoryService.get_recent_conversations(db, user.id, 8)

                # Build conversation history
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for convo in recent_convos:
                    messages.append({"role": "user", "content": convo.user_message})
                    messages.append({"role": "assistant", "content": convo.ai_response})
                messages.append({"role": "user", "content": user_text})

                ai_response = await get_ai_response(messages, deep_mode=False)
                await send_telegram_message(chat_id, ai_response)

                # Store in memory
                message_type = MemoryService.categorize_message_type(user_text)
                MemoryService.store_conversation(
                    db=db,
                    user_id=user.id,
                    user_message=user_text,
                    ai_response=ai_response,
                    message_type=message_type
                )
                return {"status": "success", "ai_response": ai_response}

            # === DEEP MODE ===
            elif user_text.lower().startswith('/deep'):
                deep_input = user_text.replace('/deep', '').strip()
                if not deep_input:
                    await send_telegram_message(chat_id, "Please provide a question after /deep for advanced analysis.")
                    return {"status": "success", "action": "deep_prompt_missing"}

                MemoryService.update_user_context(db, user, deep_input)
                recent_convos = MemoryService.get_recent_conversations(db, user.id, 8)

                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for convo in recent_convos:
                    messages.append({"role": "user", "content": convo.user_message})
                    messages.append({"role": "assistant", "content": convo.ai_response})
                messages.append({"role": "user", "content": deep_input})

                ai_response = await get_ai_response(messages, deep_mode=True)
                await send_telegram_message(chat_id, ai_response)

                message_type = MemoryService.categorize_message_type(deep_input)
                MemoryService.store_conversation(
                    db=db,
                    user_id=user.id,
                    user_message=deep_input,
                    ai_response=ai_response,
                    message_type=message_type
                )
                return {"status": "success", "ai_response": ai_response}

            # Unknown command
            elif user_text.startswith('/'):
                help_text = "**Available commands:**\n" \
                            "• /reset - Clear conversation memory\n" \
                            "• /stats - View conversation stats\n" \
                            "• /deep <question> - Use advanced reasoning mode (gpt-4.1)\n\n" \
                            "Just send a regular message to chat with your financial coach!"
                await send_telegram_message(chat_id, help_text)
                return {"status": "success", "action": "help_sent"}

        return {"status": "success"}

    except Exception as e:
        print(f"=== WEBHOOK ERROR: {e} ===")
        if 'chat_id' in locals():
            await send_telegram_message(chat_id, "Unexpected error. Please try again.")
        return {"status": "error", "message": str(e)}
