from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class NormalizedToolCall:
    tool_call_id: str
    name: str
    arguments: dict[str, Any]
    call_id: str | None
    customer_number: str | None


def normalize_tool_calls(payload: dict[str, Any]) -> list[NormalizedToolCall]:
    # Isolate Vapi payload variants here so services receive one stable request shape.
    message = payload["message"]
    call = message.get("call", {})
    customer = call.get("customer", {})
    normalized_calls: list[NormalizedToolCall] = []

    tool_calls = message.get("toolCallList")
    if tool_calls is None:
        tool_calls = [item.get("toolCall", item) for item in message.get("toolWithToolCallList", [])]

    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        arguments = tool_call.get("arguments")
        if arguments is None:
            arguments = function.get("arguments")
        if arguments is None:
            arguments = tool_call.get("parameters", function.get("parameters", {}))
        name = tool_call.get("name") or function["name"]
        if isinstance(arguments, str):
            # Some Vapi function calls encode arguments as a JSON string.
            arguments = json.loads(arguments)

        normalized_calls.append(
            NormalizedToolCall(
                tool_call_id=tool_call["id"],
                name=name,
                arguments=arguments,
                call_id=call.get("id"),
                customer_number=customer.get("number"),
            )
        )

    return normalized_calls
