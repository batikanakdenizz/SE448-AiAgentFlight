import os
import json
import httpx
from datetime import date
from tools import TOOL_DEFINITIONS, execute_tool

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

_SYSTEM_PROMPT_TEMPLATE = """Today's date is {today}. You are a helpful airline assistant for an AI-powered flight booking system.
You can help users with three things:
1. Query Flights - Search for available flights between airports on specific dates
2. Book Flight - Purchase tickets for passengers on a specific flight
3. Check In - Check in passengers for their upcoming flights

Always be friendly and concise. Format flight results clearly with flight number, route, departure time, duration, and available seats. Confirm booking/check-in details clearly.

STRICT RULES — never call a tool with missing required info, always ask first:
- buy_ticket: MUST have flight number + departure date + at least one passenger full name. If passenger name is missing, ask: "What is the passenger's full name?"
- check_in: MUST have flight number + departure date + passenger full name.
- query_flights: MUST have origin, destination, and date.

Date rules:
- Flight queries: departure_date_from and departure_date_to in YYYY-MM-DD format
- Bookings and check-ins: departure_date in YYYY-MM-DDTHH:MM:SS format

Always call the appropriate tool rather than making up flight data.

Turkish airport codes (IMPORTANT — always use these exact codes):
- Istanbul: IST (Atatürk) or SAW (Sabiha Gökçen)
- Izmir / İzmir: ADB (Adnan Menderes) — NOT IZM
- Ankara: ESB (Esenboğa)
- Antalya: AYT
- Bodrum: BJV
- Trabzon: TZX
- Adana: ADA
- Dalaman: DLM"""


async def process_message(conversation_history: list, user_message: str) -> tuple[str, list]:
    conversation_history.append({"role": "user", "content": user_message})

    tool_calls_made = []

    # Build messages — system prompt + conversation history (user/assistant only)
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(today=date.today().isoformat())
    messages = [{"role": "system", "content": system_prompt}]
    for m in conversation_history:
        if m["role"] in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m.get("content", "")})

    async with httpx.AsyncClient(timeout=120.0) as client:
        while True:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "tools": TOOL_DEFINITIONS,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data["message"]

            tool_calls = msg.get("tool_calls")
            if tool_calls:
                # Append assistant message as plain dict — no SDK Pydantic involved
                messages.append(msg)

                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    # Native Ollama API returns arguments as a dict already
                    tool_args = tc["function"]["arguments"]
                    if isinstance(tool_args, str):
                        tool_args = json.loads(tool_args)

                    tool_calls_made.append({"tool": tool_name, "input": tool_args})
                    result = await execute_tool(tool_name, tool_args)

                    messages.append({"role": "tool", "content": result})
            else:
                response_text = msg.get("content", "")
                conversation_history.append({"role": "assistant", "content": response_text})
                return response_text, tool_calls_made
