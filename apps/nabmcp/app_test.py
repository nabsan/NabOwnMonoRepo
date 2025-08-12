import requests

OLLAMA_HOST = "http://172.21.32.1:11434"

MODEL = "llama3:latest"

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "こんにちは、元気ですか？"}
    ],
    "stream": False
}

response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload)
response.raise_for_status()

data = response.json()
print("Assistant:", data["message"]["content"])
