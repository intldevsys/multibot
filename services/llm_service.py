import asyncio
import random
from typing import List, Dict, Optional
from datetime import datetime
import anthropic
import openai
import cohere
import google.generativeai as genai
from config import (
    ANTHROPIC_API_KEY, OPENAI_API_KEY, COHERE_API_KEY, GOOGLE_API_KEY,
    DEEPSEEK_API_KEY, QWEN_API_KEY,
    CHAT_HISTORY_DAYS, MAX_INTERACTION_MESSAGES
)

class LLMService:
    def __init__(self):
        self.anthropic_client = None
        self.openai_client = None
        self.cohere_client = None
        self.deepseek_client = None
        self.qwen_client = None
        
        # Initialize clients
        if ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        if OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        if COHERE_API_KEY:
            self.cohere_client = cohere.AsyncClient(api_key=COHERE_API_KEY)
        
        if GOOGLE_API_KEY:
            genai.configure(api_key=GOOGLE_API_KEY)
        
        # DeepSeek uses OpenAI-compatible API
        if DEEPSEEK_API_KEY:
            self.deepseek_client = openai.AsyncOpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
        
        # Qwen uses OpenAI-compatible API
        if QWEN_API_KEY:
            self.qwen_client = openai.AsyncOpenAI(
                api_key=QWEN_API_KEY,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
            )

    async def analyze_chat_style(self, chat_history: List[Dict]) -> str:
        """Analyze chat history to understand the conversational style"""
        if not chat_history:
            return "casual and friendly"
        
        # Prepare chat messages for analysis
        messages_text = "\n".join([
            f"{msg.get('username', 'User')}: {msg['message_text']}"
            for msg in chat_history[-100:]  # Last 100 messages
        ])
        
        analysis_prompt = f"""
        Analyze the following chat conversation and describe the communication style, tone, and patterns:

        {messages_text}

        Please provide a brief analysis focusing on:
        1. Communication style (formal/casual/slang)
        2. Common topics and interests
        3. Humor style and frequency
        4. Typical message length and structure
        5. Emotional tone and energy level

        Respond with a concise analysis that can help me match this conversational style.
        """
        
        try:
            if self.qwen_client:
                response = await self.qwen_client.chat.completions.create(
                    model="qwen-max",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=500,
                    temperature=0.7
                )
                return response.choices[0].message.content
            elif self.anthropic_client:
                response = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model="claude-3-sonnet-20240229",
                    max_tokens=500,
                    messages=[{"role": "user", "content": analysis_prompt}]
                )
                return response.content[0].text
            elif self.deepseek_client:
                response = await self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=500,
                    temperature=0.7
                )
                return response.choices[0].message.content
            elif self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=500
                )
                return response.choices[0].message.content
            elif self.cohere_client:
                response = await self.cohere_client.generate(
                    model='command',
                    prompt=analysis_prompt,
                    max_tokens=500,
                    temperature=0.7
                )
                return response.generations[0].text.strip()
            elif GOOGLE_API_KEY:
                model_instance = genai.GenerativeModel('gemini-pro')
                response = await asyncio.to_thread(model_instance.generate_content, analysis_prompt)
                return response.text
        except Exception as e:
            print(f"Error analyzing chat style: {e}")
            return "casual and friendly"

    async def generate_casual_response(
        self, 
        message: str, 
        chat_style: str, 
        recent_context: List[Dict],
        model: str = "claude"
    ) -> str:
        """Generate a casual response matching the chat style"""
        
        # Build context from recent messages
        context = ""
        if recent_context:
            context = "\n".join([
                f"{msg.get('username', 'User')}: {msg['message_text']}"
                for msg in recent_context[-10:]  # Last 10 messages for context
            ])
        
        prompt = f"""
        You are chatting casually in a Telegram group. Here's the chat style analysis:
        {chat_style}

        Recent conversation context:
        {context}

        User just said: "{message}"

        Respond naturally as if you're a regular member of this chat group. Match the communication style, tone, and energy level. Keep responses conversational and engaging but not overly long. Don't mention that you're an AI.

        Some guidelines:
        - Use appropriate emojis if the group uses them
        - Match the formality level (casual/formal)
        - Reference the ongoing conversation naturally
        - Be helpful but conversational
        - Use humor if it fits the group's style
        - Keep responses 1-3 sentences typically
        """

        try:
            if model == "claude" and self.anthropic_client:
                response = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model="claude-3-sonnet-20240229",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
                
            elif model == "gpt" and self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.8
                )
                return response.choices[0].message.content
                
            elif model == "cohere" and self.cohere_client:
                response = await self.cohere_client.generate(
                    model='command',
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.8
                )
                return response.generations[0].text.strip()
                
            elif model == "gemini" and GOOGLE_API_KEY:
                model_instance = genai.GenerativeModel('gemini-pro')
                response = await asyncio.to_thread(model_instance.generate_content, prompt)
                return response.text
                
            elif model == "deepseek" and self.deepseek_client:
                response = await self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.8
                )
                return response.choices[0].message.content
                
            elif model == "qwen" and self.qwen_client:
                response = await self.qwen_client.chat.completions.create(
                    model="qwen-max",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.8
                )
                return response.choices[0].message.content
                
        except Exception as e:
            print(f"Error generating response with {model}: {e}")
            
        # Fallback responses
        fallback_responses = [
            "Interesting! 🤔",
            "I see what you mean",
            "That's a good point!",
            "Totally agree 👍",
            "Fair enough",
            "Makes sense to me",
            "I hear you",
            "Right on! 💯"
        ]
        return random.choice(fallback_responses)

    async def should_respond(
        self, 
        message: str, 
        mentioned: bool, 
        last_bot_message_count: int,
        chat_activity_level: str = "normal"
    ) -> bool:
        """Determine if bot should respond to a message"""
        
        # Always respond if mentioned
        if mentioned:
            return True
            
        # Don't respond too frequently
        if last_bot_message_count < 3:  # Only respond every few messages
            return False
            
        # Keywords that might trigger a response
        trigger_keywords = [
            "question", "help", "what", "how", "why", "anyone", "somebody",
            "opinion", "think", "agree", "disagree", "recommend"
        ]
        
        message_lower = message.lower()
        has_trigger = any(keyword in message_lower for keyword in trigger_keywords)
        
        # Random chance based on activity level and triggers
        if chat_activity_level == "high":
            base_chance = 0.1  # 10% chance in active chats
        elif chat_activity_level == "low":
            base_chance = 0.3  # 30% chance in quiet chats
        else:
            base_chance = 0.2  # 20% chance normally
            
        if has_trigger:
            base_chance *= 2  # Double chance for trigger words
            
        return random.random() < base_chance

    def get_available_models(self) -> List[str]:
        """Get list of available LLM models"""
        models = []
        
        if self.anthropic_client:
            models.append("claude")
        if self.openai_client:
            models.append("gpt")
        if self.cohere_client:
            models.append("cohere")
        if GOOGLE_API_KEY:
            models.append("gemini")
        if self.deepseek_client:
            models.append("deepseek")
        if self.qwen_client:
            models.append("qwen")
            
        return models

    async def generate_summary(self, text: str, max_length: int = 100) -> str:
        """Generate a summary of text content"""
        prompt = f"Summarize the following text in {max_length} characters or less:\n\n{text}"
        
        try:
            if self.anthropic_client:
                response = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model="claude-3-haiku-20240307",
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
        except Exception as e:
            print(f"Error generating summary: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text