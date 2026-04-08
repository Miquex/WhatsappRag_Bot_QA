# Whasapp_Bot_QA
This is a bot that can help you to answer automatically answer about your business or personal information.
##Index
* [Prerequisites](#prerequisites)
* [Technologies Used](#technologies-used)
* [About tools used](#about-tools-used)
  * [Loguru](#why-use-loguru)
  * [Uv](#why-use-cachetools-instead-redis)
  * [Cachetools](#why-use-cachetools-instead-redis)
  * [Vectorized information](#why-should-we-use-vectorized-information-instead-of-a-single-markdown-or-text-file)
  * [Pydantic](#why-use-pydantic)
* [How to run in local](#how-to-run-in-local)
* [Environment Configuration](#environment-configuration)
* [Project Structure](#-project-structure)
## Prerequisites
-   Uv
-   Python 3.13 or higher.
-   A Meta Developer account with WhatsApp Cloud API access.
-   An OpenAI API Key.
## Technologies Used

| Technology | Use | How to install |
| ------------ | ------------ | ------------ |
| **Python 3.13+** | Core project language | ```uv python install 3.13``` |
| **uv** | Python and package manager | ```powershell -c "irmo https://astral.sh/uv/install.ps1 \| iex"``` |
| **FastAPI** | Web framework for Webhooks and API | ```uv add fastapi``` |
| **OpenAI** | LLM provider integration | ```uv add openai``` |
| **Uvicorn** | ASGI server to run the application | ```uv add uvicorn``` |
| **ChromaDB** | Vector database for RAG | ```uv add chromadb``` |
| **Tiktoken** | Token counting for OpenAI models | ```uv add tiktoken``` |
| **Pydantic** | Data validation and schemas | ```uv add pydantic``` |
| **Pydantic Settings** | Environment variables management (.env) | ```uv add pydantic-settings``` |
| **HTTPX** | Async HTTP client for WhatsApp API | ```uv add httpx``` |
| **Loguru** | Advanced logging system | ```uv add loguru``` |
| **Cachetools** | TTL-based memory and caching | ```uv add cachetools``` |
| **Pytest** | Testing framework | ```uv add pytest``` |
| **Pytest-asyncio** | Async support for testing | ```uv add pytest-asyncio``` |
| **Mypy** | Static type checker | ```uv add mypy``` |

You can run the ```uv sync``` command in the project folder to automatically install all dependencies
>[!IMPORTANT]
> Ensure that uv is installed on your computer before proceeding.
## About tools used
### Why use loguru?
 I'm using Loguru instead of the standard Python logging module because it makes logging simple, readable, and powerful with almost zero effort.
### Why uv is better than pip for this project:
I am using uv for this project because it is faster and more modern than pip. I could have used pip, but it is important to know that uv is rapidly becoming the standard due to benefits such as the following:

- **Lightning Speed** : uv is written in Rust and is typically 10x to 100x faster than pip. Installing dependencies that would take minutes with pip happens in seconds with uv.

- **Unified Tooling** : Instead of using multiple tools like pip (for packages), pyenv (for Python versions), virtualenv (for environments), and pip-tools (for locking versions), uv handles everything in one single tool.

- **Reproducible Builds with Lockfiles** : Unlike pip (which by default doesn't lock sub-dependencies), uv generates a uv.lock file. This ensures that every developer on your team—and your production server—installs the exact same version of every library, preventing the "it works on my machine" bug.

- **Native pyproject.toml Support** : uv is built to work with the modern Python packaging standard (pyproject.toml), which we are using in this project to manage dependencies and configurations in one place.

- **Smart Caching** : uv uses a global cache. If you have five different projects using the same version of OpenAI or FastAPI, uv only downloads it once and uses "hard links" to share it across environments, saving disk space and time.
### Why use **Cachetools** instead **Redis**
In this case, the agent is not complex; the objective of this bot is to answer common and frequently asked questions such as directions, prices, and menus. Therefore, persistent storage is not necessary, as it would cause an unnecessary drain on resources and make the project needlessly complex. Here are some benefits of using cachetools in this project:

**No External Infrastructure**: Cachetools is a pure Python library that runs inside the application's memory. To use it, you just install the package. To use Redis, you would need to:

  1. Install and run a Redis server (or a Docker container).
  2. Manage a connection pool.
  3. Handle network failures between the app and the database.
  4. Configure environment variables for host/port/password.
      
**Extreme Low Latency**: Since cachetools lives in the same RAM that your Python code is using, retrieving data is nearly instantaneous. Even though Redis is very fast, it still requires a tiny amount of time for the "network hop" (sending the request to the Redis service and back). For deduplicating incoming webhooks, in-process memory is the fastest possible option.

**Cost & Maintenance**:

**cachetools:** Free and requires zero maintenance.

**Redis:** If you deploy to the cloud, you often have to pay for a managed Redis instance or manage the server yourself, which increases the monthly cost and operational overhead of the project.

**Why Volatility is Acceptable here ?**:

Redis is usually used when you need the data to persist even if the server restarts. In this project, we use the cache for:

**Deduplication:** Preventing processing the same message twice in a 5-minute window.

**Short-term Memory:** Keeping the last 6 messages of a conversation.

### Why should we use vectorized information instead of a single Markdown or text file?

I am using vectorized information for two reasons: efficiency and resource conservation. To give you an example: if you use a ```.md``` or ```.txt``` file without vectorizing it first, the AI must read the entire document every time a user asks a question. If your data contains 50,000 tokens, the AI will spend 50,000 tokens on every single query. By using vectorized information, you avoid exhausting your token limit in one day or receiving an expensive bill at the end of the month. But how does vectorized information work? Let me explain.

Vectorization turns human language into a language of numbers that computers can navigate mathematically. First, a specialized model takes "chunks" of your text and converts them into an embedding, which is essentially a long list of coordinates (a vector) in a high-dimensional space. Instead of just looking for matching letters, the system treats every idea as a physical location.

Because these numbers represent meaning, concepts that are similar—like "price" and "cost"—end up mathematically close to each other. When a user asks a question, the computer converts that question into its own set of coordinates and simply looks for the "nearest neighbors" in that space. This geometric proximity is why the AI can find the right answer even if the user uses different words than those in your source files.

### **How works the vectorization in this project**

**Step A: Storage**

When the project starts, it reads your info.md file and splits it into small pieces (chunks). Then:

- We call self.collection.upsert(documents=chunks).
- ChromaDB sends those text chunks to OpenAI.
- OpenAI "translates" each chunk into a list of 1,536 numbers (the vector).
- ChromaDB saves both the Text and the Vector in your local data/chromadb folder.

**Step B: Retrieval**

When a user sends a WhatsApp message (e.g., "What are your opening hours?"):

- We call self.collection.query(query_texts=[query]).
- ChromaDB sends the user's question to OpenAI to get its vector.
- ChromaDB then compares the "Question Vector" against all the "Document Vectors" in its database using math (Cosine Similarity).
- It finds the 3 pieces of text that are "mathematically closest" in meaning to the question and returns them to be used as context for the AI.

### Why use Pydantic?

I'am using Pydantic in this project primarily because it acts as a structural shield for your data. In a Python application that talks to external APIs (like WhatsApp), Pydantic is essential for three main reasons:

**Data Integrity**

The WhatsApp API sends complex, nested JSON data. If you didn't have Pydantic, you would have to manually check if every field exists like this:

<prep> ```if "entry" in payload and "changes" in payload["entry"][0]:``` </prep>

With Pydantic (as seen in ```app/api/schemas.py```), you define a BaseModel. If WhatsApp sends a message that is missing a required field or has a string where a number should be, Pydantic catches it immediately and returns a clear error before your code even tries to process it.

**Modern Python Developer Experience** 

Pydantic turns raw JSON dictionaries into Python Objects. This gives you:

- Auto-completion: When you type payload.entry[0].changes[0].value, your code editor knows exactly what fields are available.
- Type Hinting: You know for sure that id is a str and messages is a List.
- Aliasing: In your MessageItem schema, we use Field(alias='from'). Since from is a reserved keyword in Python (you can't name a variable from), Pydantic handles the translation from WhatsApp's from to our from_number automatically.

**Smart Configuration Management** 

In ```app/core/config.py```, I use pydantic-settings. This allows the project to:

- Automatically read from a .env file.
- Validate that mandatory API keys (OPENAI_API_KEY) are present.
- Convert strings like "True" in your .env into actual Python True booleans for the DEBUG flag.

## How to run in local

To run the project locally, execute the command ```uv run main.py```. 

For the Callback URL requested by Meta, you can use a temporary local tunnel

First run ```npm install -g localtunnel``` in your terminal 
Then use the command ```lt --port 8000```
After that you will receive a temporary URL like this: ```https://great-comics-hope.loca.lt```
Finally add at the final of the url ```/webhook``` and paste it callback url in your meta app
>[!NOTE]
>The final URL should look like this: ```https://great-comics-hope.loca.lt/webhook```

## Environment Configuration

Create a `.env` file in the project root and fill in your credentials:

```env
# Project Settings
PROJECT_NAME="Whatsapp RAG Agent"
DEBUG=True (Use 'True' only for local development)

# WhatsApp API
WHATSAPP_TOKEN="your_access_token"
WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
WHATSAPP_VERIFY_TOKEN="your_verify_token"

# AI Providers
OPENAI_API_KEY="your_openai_api_key"

# Database Configuration
CHROMA_DB_DIR="./app/data/chromadb"
RAG_MD_PATH="./app/data/knowledge/info.md"
```

## 📂 Project Structure

```text
.
├── app/
│   ├── agent/             # RAG logic, memory, and vector store
│   ├── api/               # API routes (webhook, deduplication, schemas)
│   ├── core/              # Configuration and logging setup
│   ├── data/              # Local storage for documents and ChromaDB
│   └── services/          # External service integrations (WhatsApp)
├── tests/                 # Unit and integration tests
├── main.py                # Application entry point
├── pyproject.toml         # Project dependencies and configuration
└── .env                   # Environment variables
```

>[!NOTE]
> I built this project with a lot of heart, and I hope it helps you create your own intelligent bot and save time. If you don't have a business, you can use it as a personal secretary that provides information about you; I am currently using this bot for that exact purpose—to answer questions about me and my knowledge. I will be releasing more complex projects soon, so feel free to follow me!.






