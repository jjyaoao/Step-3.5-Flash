# Hybrid Local Agent on MacOS (Step 3.5 Flash + Qwen Janitor)

This cookbook demonstrates how to build a fully local, privacy-first Agentic Sandbox on MacOS (Apple Silicon).

It features a **Hybrid Architecture** that optimizes cost and latency:
1.  **The Brain (Step 3.5 Flash):** Handles complex reasoning, planning, and tool selection via `llama.cpp` server.
2.  **The Janitor (Qwen 2.5 Coder):** Handles high-volume/low-intelligence tasks (syntax fixing, summarization) via Ollama, saving bandwidth and tokens for the main model.
3.  **The Hands (MCP Server):** A Model Context Protocol server that provides safe access to local tools (Apple Mail, Playwright Web Fetch, Python Sandbox).

## 🌟 Features

* **Native MacOS Integration:** Reads/Sends emails via Apple Mail scripting (AppleScript).
* **Secure Python Sandbox:** AST-validated execution environment for generated code.
* **RAG Memory:** Local vector store (ChromaDB) for long-term conversation retention.
* **Low-Bandwidth Optimization:** Uses a local "Janitor" model to compress web content before sending it to the reasoning model (ideal for edge computing).

## 🛠 Prerequisites

* **Hardware:** Mac with Apple Silicon (M1/M2/M3). Tested on M3 Max (128GB).
* **Software:**
    * Python 3.10+
    * [Ollama](https://ollama.com/) (for the Janitor model)
    * `llama-server` (built from source or installed via brew) running Step 3.5 Flash.

## 📦 Installation

1.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

2.  **Prepare the Models:**
    * **Janitor:** Run `ollama run qwen2.5-coder:3b` in a terminal.
    * **Brain:** Ensure your Step 3.5 Flash `llama-server` is running on port 8080 (or update the URL in the configuration).

    *Tip for M3 Max users: Increase your GPU wired limit if running large contexts:*
    ```bash
    sudo sysctl iogpu.wired_limit_mb=125000
    ```

## 🚀 Usage

1.  **Start the MCP Server:**
    ```bash
    python main.py
    ```

2.  **Connect your Client:**
    Use an MCP-compatible client (like Claude Desktop or a custom script) and point it to this server command.

3.  **Example Prompts:**
    * *"Check my unread emails from the 'IA_INBOX' folder and summarize the newsletter."*
    * *"Go to [url], fetch the content, summarize it using the Janitor, and save the key points to memory."*

## ⚠️ Notes

* **Privacy:** All data (emails, memory, RAG) stays strictly local in the `./data` folder.
* **Safety:** The Python execution tool blocks dangerous imports (`os`, `sys`, `socket`) by default.