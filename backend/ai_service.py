import os
from dotenv import load_dotenv

# ----------------------------
# Optional emergentintegrations import
# ----------------------------
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ModuleNotFoundError:
    LlmChat = None
    UserMessage = None

load_dotenv()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


async def generate_daily_summary(
    dog_names: list,
    staff_snippets: list,
    media_count: int
) -> str:
    """
    Generate a warm, friendly daily summary using GPT-5.2.
    Combines multiple staff snippets into one cohesive update.
    """

    # ----------------------------------------
    # Hard stop if AI dependency not installed
    # ----------------------------------------
    if LlmChat is None or UserMessage is None:
        print("AI dependency 'emergentintegrations' not installed — using fallback summary.")
        return _fallback_summary(dog_names, media_count)

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="daily-summary-generator",
            system_message=(
                "You are a warm, friendly kennel assistant writing daily updates "
                "for dog parents. Your tone is upbeat, personal, and reassuring."
            ),
        )

        chat.with_model("openai", "gpt-5.2")

        # Format dog list safely
        if not dog_names:
            dog_list = "your pup"
        elif len(dog_names) == 1:
            dog_list = dog_names[0]
        else:
            dog_list = ", ".join(dog_names[:-1]) + f" and {dog_names[-1]}"

        # Combine staff notes safely
        all_snippets = "\n\n".join(
            [
                f"Staff note from {snippet.get('staff_name', 'Staff')}: {snippet.get('text', '')}"
                for snippet in staff_snippets
            ]
        )

        prompt = f"""
Write a warm daily update for {dog_list}.

Staff observations throughout the day:
{all_snippets}

We captured {media_count} photos/videos today.

Combine all the staff notes into a cohesive, warm 3–4 sentence summary.
Be specific and joyful. Highlight the best moments and reassuring details.
"""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)

        return response

    except Exception as e:
        print(f"Error generating AI summary: {e}")
        return _fallback_summary(dog_names, media_count)


def _fallback_summary(dog_names: list, media_count: int) -> str:
    """
    Safe fallback summary when AI is unavailable.
    """
    if not dog_names:
        dog_list = "Your pup"
    elif len(dog_names) == 1:
        dog_list = dog_names[0]
    else:
        dog_list = ", ".join(dog_names[:-1]) + f" and {dog_names[-1]}"

    return (
        f"{dog_list} had a wonderful day with us! "
        f"We captured {media_count} photos of their adventures. "
        "They enjoyed playtime, social interaction, and plenty of tail wags. "
        "We can't wait to see them again!"
    )
