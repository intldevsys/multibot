
<img width="2080" height="800" alt="image" src="https://github.com/user-attachments/assets/bfa0b063-2014-4ac4-97b8-a4d8af2b2c96" />




# **Multibot**

A multi-functional Telegram bot built with Python and Pyrogram. It offers a wide range of features, from interactive chat powered by Large Language Models (LLMs) to automated channel scanning and content aggregation.

### Key Features

- **Conversational AI:** 
    - **Casual Chat Mode:** The bot can be enabled to participate in group conversations, automatically analyzing the chat style to respond in a matching tone and manner.
    - **Multi-LLM Support:** Easily switch between different LLM providers, including:
        - Anthropic (Claude)
        - OpenAI (GPT)
        - Cohere
        - Google (Gemini)
        - DeepSeek
        - Alibaba (Qwen)

- **Content Aggregation:**
    - **News Service:** Fetch and display the latest news articles.
    - **Twitter Integration:** Get recent tweets from specified users.

- **Telegram Automation:**
    - **Channel Scanner:** Automatically scans specified Telegram channels for new messages and media.
    - **Search Functionality:** Search for messages across dialogues or within specific chats.

- **Administration & Usage:**
    - **Command-based Interface:** Simple commands to control all features.
    - **Rate Limiting:** Prevents spam and abuse.
    - **Admin-Only Controls:** Secure commands that can only be executed by administrators.
    - **Database Integration:** Uses MongoDB to store chat history, user settings, and more.

## Getting Started

### Prerequisites
NOTE: For gathering news and X posts, you will need free API keys from:

> * newsapi.org
> * content.guardianapis.com
> * newsdata.io
> * coinmarketcap.com
> * x.com

As well as: 

- Python 3.10+
- MongoDB database instance
- API keys for Telegram and desired LLM services

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd tgcrawl
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

The project uses an `.env` file for configuration. A sample file, `.env.example`, is provided.

1.  **Create your own `.env` file:**
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file with your credentials.** You must provide:
    - `API_ID` and `API_HASH` from your Telegram account.
    - `BOT_TOKEN` from Telegram's @BotFather.
    - `MONGO_DB_URI` for your MongoDB database.
    - API keys for any LLM services you intend to use (e.g., `QWEN_API_KEY`, `OPENAI_API_KEY`, etc.).

## Usage

Once the installation and configuration are complete, you can run the bot using:

```bash
python3 main.py
```

The bot will log in and start listening for commands and messages.

## Available Commands

- `/casual`: Toggles casual chat mode on/off in a group. (Admin-only)
- `/casual_status`: Shows the current status of casual mode in the chat.
- `/casual_reset`: Resets the interaction counters for casual mode. (Admin-only)
- `/news`: Fetches the latest news headlines.
- `/search <query>`: Searches for a message in the current chat.
- `/searchall <query>`: Searches for a message across all your chats.
- `/tweets <username>`: Fetches the latest tweets from a Twitter user.
- `/llm`: Manage and select the primary LLM for the bot.
- `/stats`: Show usage statistics for the bot.
- `/ping`: Checks if the bot is online and responsive.


