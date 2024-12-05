# strategies/utils.py

from dotenv import load_dotenv

import os
import openai
import anthropic

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
anthropic.api_key = os.getenv("ANTHROPIC_API_KEY")

def chat_with_openai(messages, model="gpt-4o"):
    """
    Sends messages to OpenAI's API and returns the response.
    
    Args:
        messages (list): List of message dictionaries.
        model (str): The OpenAI model to use.
        
    Returns:
        str: The assistant's response.
    """
    try:
        # If the model is 'o1-mini', update system messages to be user messages
        changed_messages = []
        if model == "o1-mini":
            for message in messages:
                if message.get("role") == "system":
                    message["role"] = "user"
                    changed_messages.append(message)
            messages = changed_messages
        response = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7 if model != "o1-mini" else 1.0,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")

def chat_with_anthropic(messages, model="claude-3-5-sonnet-20241022"):
    """
    Sends messages to Anthropic's API and returns the response.
    
    Args:
        messages (list): List of message dictionaries.
        model (str): The Anthropic model to use.
        
    Returns:
        str: The assistant's response.
    """
    try:
        client = anthropic.Anthropic()
        
        # Extract system messages and combine them
        system_messages = [msg["content"] for msg in messages if msg["role"] == "system"]
        system_prompt = "\n\n".join(system_messages) if system_messages else None
        
        # Filter out system messages for the messages list
        filtered_messages = [msg for msg in messages if msg["role"] != "system"]
        
        response = client.messages.create(
            model=model,
            messages=filtered_messages,
            system=system_prompt,
            max_tokens=4096,
        )
        
        return response.content[0].text.strip()
    except Exception as e:
        raise Exception(f"Anthropic API error: {str(e)}")
