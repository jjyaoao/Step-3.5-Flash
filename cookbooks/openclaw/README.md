A guide for installing, configuring, and deploying OpenClaw on MacOS (Linux and Windows).

## 📋 Prerequisites

- **Operating System:** MacOS
- **Environment:** Node.js (if installing via npm)

## 🚀 Installation

You can install OpenClaw using the official installation script or via npm.

### Option 1: Official Script (Recommended)

```Bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

### Option 2: NPM

```Bash
npm i -g openclaw
```

> **Tip:** If you encounter permission errors, try adding `sudo` before the command.
>
> 
>
> *AI Assistant Tip:* You can ask [Claude Code](https://openclaw.ai/) to perform a one-click install for you: 
>
> *"Open this webpage: https://openclaw.ai, and install the stuff inside for me."*

## ⚡ Quick Start

### 1. Initialization

Once installed, initialize your agent (onboard) via the command line:

```Bash
openclaw onboard
```

### 2. Setup Wizard

Follow the interactive prompts:

1. **Welcome Prompt:** Select `Yes`.

![img](assets/(null)-20260205105935763.(null))

1. **Mode:** Select `Quick Start`.

![img](assets/(null)-20260205105935750.(null))

1. **Model Configuration:**
   1. If you don't have a company proxy key, select `Skip for now`.
   2. You can configure custom models (like OpenRouter) later via the WebUI or config file.
   3. Later select `All providers `and `Keep current `

![img](assets/(null)-20260205105935751.(null))

![img](assets/(null)-20260205105936884.(null))

1. **Telegram Integration:**
   1. Select `Telegram` to configure immediately, or `Skip for now` to set it up later.
   2. *See the [Integrations](#integrations) section for detailed Telegram setup.*
   3. ![img](assets/(null)-20260205105935916.(null))
2. **Finalize:**
   1. For other options, press `Space` to select and `Enter` to confirm (keeping defaults is recommended).
   2. ![img](assets/(null)-20260205105935904.(null))
   3. choose `Skip` to skip all the selections.
   4. ![img](assets/(null)-20260205105936886.(null))
   5. Two situations:
      - It shows '**Onboarding complete'：**
        1. ![img](assets/(null)-20260205105936846.(null))
        2. press `ctrl+c` to exit,
        3. Run `openclaw onboard` and repeat the previous steps
        4. ![img](assets/(null)-20260205105936144.(null))
        5. Select WebUI when prompted （*If the option does not appear, start the WebUI via*`openclaw dashboard`）
        6. ![img](assets/(null)-20260205105936460.(null))
      - Select **WebUI** when prompted (useful for debugging configuration).
      - ![img](assets/(null)-20260205105937002.(null))

## ⚙️ Configuration

There are two methods to configure your models and providers: editing the configuration file directly or using the WebUI.

### Method 1: Raw JSON Configuration (Advanced)

- Either click as shown in the following picture:
- Or directly edit the configuration file located at `~/.openclaw/openclaw.json`.

![img](assets/(null)-20260205105937002-0260377.(null))

**Example Configuration:**

Copy the code below to replace the content in `~/.openclaw/openclaw.json`.

> ⚠️ **Note:** Remember to replace `apiKey` with your actual key and remove comments if they cause syntax errors in strict JSON parsers.

<details>

<summary>Click to view openclaw.json template</summary>

```JSON
{
  "meta": {
    "lastTouchedVersion": "2026.1.30",
    "lastTouchedAt": "2026-02-02T11:42:19.634Z"
  },
  "wizard": {
    "lastRunAt": "2026-02-02T11:28:49.141Z",
    "lastRunVersion": "2026.1.30",
    "lastRunCommand": "onboard",
    "lastRunMode": "local"
  },
  "models": {
    "providers": {
      "custom-1": {
        "baseUrl": "https://openrouter.ai/api/v1",
        "apiKey": "YOUR_API_KEY_HERE",
        "auth": "api-key",
        "api": "openai-completions",
        "authHeader": false,
        "models": [
          {
            "id": "stepfun/step-3.5-flash:free",
            "name": "step-3.5-flash",
            "api": "openai-completions",
            "reasoning": false,
            "input": ["text"],
            "cost": {
              "input": 0,
              "output": 0,
              "cacheRead": 0,
              "cacheWrite": 0
            },
            "contextWindow": 200000,
            "maxTokens": 8192
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "custom-1/stepfun/step-3.5-flash:free"
      },
      "compaction": {
        "mode": "safeguard"
      },
      "maxConcurrent": 4,
      "subagents": {
        "maxConcurrent": 8
      }
    }
  },
  "commands": {
    "native": "auto",
    "nativeSkills": "auto"
  },
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "YOUR_GENERATED_TOKEN"
    },
    "tailscale": {
      "mode": "off",
      "resetOnExit": false
    }
  },
  "plugins": {
    "entries": {
      "telegram": {
        "enabled": true
      }
    }
  },
  "messages": {
    "ackReactionScope": "group-mentions"
  }
}
```

</details>

### Method 2: WebUI Configuration (GUI)

1. Open the dashboard:
   1. `openclaw dashboard`
2. Navigate to **Config** -> **Models** -> **Providers**.

![img](assets/(null)-20260205105937100.(null))

1. **Add a Provider:**
   1. Click **ADD Entry**.
   2. Rename `custom-number` (e.g., `custom-1`).
   3. Select API type (e.g., `openai-completions`).
   4. Enter your `apiKey` and `baseUrl`.
   5. *Example (OpenRouter):* `https://openrouter.ai/api/v1`
   6. ![img](assets/(null)-20260205105937478.(null))
2. **Add a Model:**
   1. Scroll down to the **Models** section.
   2. Click **Add**.
   3. Select API type (e.g., `openai-completions`).
   4. Enter the **Model ID** (e.g., `stepfun/step-3.5-flash:free`).
   5. Assign a display **Name**.
   6. ![img](assets/(null)-20260205105937340.(null))
3. **Save & Reload:** Click the Save icon and then the Reload icon.

![img](assets/(null)-20260205105937135.(null))

1. **Set Primary Model:**
   1. Search for `primary` in the settings (Command+F).
   2. Change the value to `"Provider Name"/"Model ID"`.
   3. Example: `custom-1/stepfun/step-3.5-flash:free`.
   4. ![img](assets/(null)-20260205105937428.(null))
   5. 
   6. ![img](assets/(null)-20260205105938037.(null))

### How to use other custom models?

- Refer to `Method 2: WebUI Configuration (GUI)`

## 🔌 Integrations

### Telegram Bot

1. **Create a Bot:** Use [BotFather](https://t.me/botfather) on Telegram and run `/newbot` to get your API Token.

![img](assets/(null)-20260205105938440.(null))

1. **Get Personal ID:** The bot will need your personal Telegram ID.

![img](assets/(null)-20260205105937542.(null))

1. **Configure OpenClaw:**
   1. During `openclaw onboard`, select Telegram.
   2. Paste the **Bot Token**.
   3. Paste your **Personal ID**.
   4. ![img](assets/(null)-20260205105938036.(null))
2. **Usage:** Once configured, you can chat directly with the bot on Telegram to issue instructions.

### Lark (Feishu)

Refer to this guide for connecting Lark

## 🛠 Command Reference

| Command                 | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `openclaw onboard`      | Re-runs the setup wizard. Useful for resetting configurations. |
| `openclaw gui`          | Opens the native GUI interface.                              |
| `openclaw dashboard`    | Opens the WebUI in your default browser.                     |
| `openclaw gateway`      | Starts the gateway service (hub for WhatsApp/Telegram).      |
| `openclaw gateway stop` | Stops the gateway service.                                   |

## ❓ FAQ & Troubleshooting

### If you can't open WebUI,like this:

Try running openclaw onboard to install gateway

### The model is not responding

1. Check the **Error Logs** in the WebUI or terminal.
2. Verify your API Key and Base URL.

### API Connection Test Script

If logs are unclear, use this Python script to isolate connection issues:

<details>

<summary>Show Python Test Script</summary>

```Python
import os
from openai import OpenAI

# Configuration
MODEL = "stepfun/step-3.5-flash:free" 
API_KEY = "sk-"      # Replace with your API Key
BASE_URL = "https://openrouter.ai/api/v1" # Replace with your URL

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=60
)

def chatCompletion(temperature: float = 0.0):                                                                    
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "hello"},
            ],
            temperature=temperature,
            max_tokens=1024,
            stream=False,
        )
        
        choice = resp.choices[0]
        if hasattr(choice, "message"):
            msg = choice.message
            if isinstance(msg, dict):
                return msg.get("content", "")
            return getattr(msg, "content", "")
        return str(resp)
        
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print("Testing API connection...")
    out = chatCompletion(temperature=0.0)
    print(f"Response: {out}")
```

</details>