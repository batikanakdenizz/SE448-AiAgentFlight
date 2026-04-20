import httpx
import os
from typing import Optional


def _to_utc_start(date_str: str) -> str:
    """Start of day in UTC — for departureDateFrom."""
    date_str = date_str.strip()
    date_part = date_str.split("T")[0]
    return f"{date_part}T00:00:00Z"


def _to_utc_end(date_str: str) -> str:
    """End of day in UTC — for departureDateTo."""
    date_str = date_str.strip()
    date_part = date_str.split("T")[0]
    return f"{date_part}T23:59:59Z"


def _to_utc_datetime(date_str: str) -> str:
    """Ensure date string has UTC time component (for ticket/checkin departure dates)."""
    date_str = date_str.strip()
    if "T" not in date_str:
        return f"{date_str}T00:00:00Z"
    if not date_str.endswith("Z") and "+" not in date_str[-6:]:
        return f"{date_str}Z"
    return date_str

GATEWAY_BASE_URL = os.getenv(
    "GATEWAY_BASE_URL",
    "https://gateway-midterm-begsgfcubdhxaph0.francecentral-01.azurewebsites.net"
)

# OpenAI/Ollama-compatible tool definitions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_flights",
            "description": (
                "Search for available flights between two airports. Use this when the user wants to "
                "find, search, or list flights. The user may provide city names (e.g. Istanbul, Frankfurt) "
                "or airport codes (e.g. IST, FRA). Extract dates from natural language and convert to ISO format."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "airport_from": {
                        "type": "string",
                        "description": "Origin airport code or city (e.g. IST, Istanbul, FRA, Frankfurt)"
                    },
                    "airport_to": {
                        "type": "string",
                        "description": "Destination airport code or city (e.g. FRA, Frankfurt, IST, Istanbul)"
                    },
                    "departure_date_from": {
                        "type": "string",
                        "description": "Start of departure date range in ISO format (YYYY-MM-DD)"
                    },
                    "departure_date_to": {
                        "type": "string",
                        "description": "End of departure date range in ISO format (YYYY-MM-DD). Use same as departure_date_from for single-day search."
                    },
                    "number_of_people": {
                        "type": "integer",
                        "description": "Number of passengers (default: 1)"
                    },
                    "is_round_trip": {
                        "type": "boolean",
                        "description": "Whether it is a round trip (default: false)"
                    },
                    "page": {"type": "integer"},
                    "size": {"type": "integer"}
                },
                "required": ["airport_from", "airport_to", "departure_date_from", "departure_date_to"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buy_ticket",
            "description": (
                "Book/purchase a flight ticket for one or more passengers. Use this when the user wants "
                "to book, buy, or purchase a ticket for a specific flight. Requires flight number, "
                "departure date, and passenger name(s)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {
                        "type": "string",
                        "description": "The flight number to book (e.g. TK1523, LH1301)"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date and time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                    },
                    "passenger_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of full passenger names (e.g. ['John Doe', 'Jane Doe'])"
                    }
                },
                "required": ["flight_number", "departure_date", "passenger_names"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_in",
            "description": (
                "Check in a passenger for a flight. Use this when the user wants to check in, "
                "confirm their seat, or complete check-in for an existing booking. "
                "Requires flight number, departure date, and passenger name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {
                        "type": "string",
                        "description": "The flight number (e.g. TK1523)"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date and time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                    },
                    "passenger_name": {
                        "type": "string",
                        "description": "Full name of the passenger checking in"
                    }
                },
                "required": ["flight_number", "departure_date", "passenger_name"]
            }
        }
    }
]


async def _get_auth_token() -> Optional[str]:
    username = os.getenv("AIRLINE_USERNAME", "admin")
    password = os.getenv("AIRLINE_PASSWORD", "admin123")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GATEWAY_BASE_URL}/gateway/auth/login",
                json={"username": username, "password": password}
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("token")
    except Exception as e:
        return None
    return None


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    try:
        if tool_name == "query_flights":
            return await _query_flights(**tool_input)
        elif tool_name == "buy_ticket":
            return await _buy_ticket(**tool_input)
        elif tool_name == "check_in":
            return await _check_in(**tool_input)
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Tool execution error: {str(e)}"


async def _query_flights(
    airport_from: str,
    airport_to: str,
    departure_date_from: str,
    departure_date_to: str,
    number_of_people: int = 1,
    is_round_trip: bool = False,
    page: int = 1,
    size: int = 10
) -> str:
    params = {
        "airportFrom": airport_from.strip(),
        "airportTo": airport_to.strip(),
        "departureDateFrom": _to_utc_start(departure_date_from),
        "departureDateTo": _to_utc_end(departure_date_to),
        "numberOfPeople": number_of_people,
        "isRoundTrip": is_round_trip,
        "page": page,
        "size": size
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GATEWAY_BASE_URL}/gateway/flights/query",
            params=params,
            headers={"Client": "ai-agent"}
        )
        if resp.status_code == 200:
            return resp.text
        return f"Flight query failed with status {resp.status_code}: {resp.text}"


async def _buy_ticket(
    flight_number: str,
    departure_date: str,
    passenger_names: list
) -> str:
    token = await _get_auth_token()
    if not token:
        return "Authentication failed. Could not obtain access token."

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{GATEWAY_BASE_URL}/gateway/tickets",
            json={
                "flightNumber": flight_number,
                "departureDate": _to_utc_datetime(departure_date),
                "passengerNames": passenger_names
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code == 200:
            return resp.text
        return f"Ticket booking failed with status {resp.status_code}: {resp.text}"


async def _check_in(
    flight_number: str,
    departure_date: str,
    passenger_name: str
) -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{GATEWAY_BASE_URL}/gateway/checkin",
            json={
                "flightNumber": flight_number,
                "departureDate": _to_utc_datetime(departure_date),
                "passengerName": passenger_name
            }
        )
        if resp.status_code == 200:
            return resp.text
        return f"Check-in failed with status {resp.status_code}: {resp.text}"
