from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
from dotenv import load_dotenv

load_dotenv()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

async def generate_daily_summary(dog_names: list, staff_notes: str, media_count: int) -> str:
    """
    Generate a warm, friendly daily summary using GPT-5.2
    """
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="daily-summary-generator",
            system_message="You are a warm, friendly kennel assistant writing daily updates for dog parents. Your tone is upbeat, personal, and reassuring. Focus on the joy and care their dogs received today."
        )
        chat.with_model("openai", "gpt-5.2")
        
        dog_list = ", ".join(dog_names[:-1]) + f" and {dog_names[-1]}" if len(dog_names) > 1 else dog_names[0]
        
        prompt = f"""Write a daily update for {dog_list}. 
        
Staff notes: {staff_notes}
        
We have {media_count} photos/videos captured today.
        
Write a warm, 2-3 sentence summary of their day. Be specific and joyful. Mention activities like playing, resting, treats, or interactions with staff/other dogs based on the notes."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
    except Exception as e:
        print(f"Error generating AI summary: {e}")
        return f"{dog_list} had a wonderful day with us! Check out the {media_count} photos we captured of their adventures."
