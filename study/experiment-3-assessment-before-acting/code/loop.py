"""A small agent loop over the OpenAI-compatible chat API (OpenAI direct, OpenRouter).

One instrument for every model: the same messages, the same tool definitions, the same loop.
A turn is: send the user message, let the model call tools as many times as it wants (bounded),
answer each call from a handler, stop when it replies with no tool call. The first call of turn 1
may force the reference tool (TOOL_FORCED); every later call is the model's choice.
"""
import json
import os
import time

from openai import OpenAI

RETRY_WORDS = ("rate", "429", "overloaded", "529", "too many", "quota", "resource_exhausted",
               "capacity", "503", "502", "timeout", "timed out", "connection")
MAX_RETRIES = 6


class Provider:
    def __init__(self, provider: str, model_id: str):
        self.provider = provider
        self.model_id = model_id
        if provider == "openai":
            self.client = OpenAI(timeout=120)
        elif provider == "openrouter":
            self.client = OpenAI(base_url="https://openrouter.ai/api/v1",
                                 api_key=os.environ["OPENROUTER_API_KEY"], timeout=120)
        else:
            raise KeyError(provider)

    def _kwargs(self, messages, tools, tool_choice, max_tokens, temperature):
        kw = {"model": self.model_id, "messages": messages, "temperature": temperature}
        if tools:
            kw["tools"] = tools
            if tool_choice is not None:
                kw["tool_choice"] = tool_choice
        if self.provider == "openai":
            kw["max_completion_tokens"] = max_tokens * 2
        else:
            kw["max_tokens"] = max_tokens
            kw["extra_body"] = {"usage": {"include": True}}  # OpenRouter returns the billed cost per request
            # optional reasoning effort (OpenRouter unified field); set prov.reasoning_effort = "high"
            eff = getattr(self, "reasoning_effort", None)
            if eff:
                kw["extra_body"]["reasoning"] = {"effort": eff}
                kw["max_tokens"] = max(max_tokens, 8000)  # room for the reasoning budget
        return kw

    def chat(self, messages, tools=None, tool_choice=None, max_tokens=1024, temperature=1.0):
        last = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self.client.chat.completions.create(
                    **self._kwargs(messages, tools, tool_choice, max_tokens, temperature))
            except Exception as e:  # noqa: BLE001
                last = e
                s = str(e).lower()
                if attempt < MAX_RETRIES and any(w in s for w in RETRY_WORDS):
                    time.sleep(min(2 ** attempt * 3, 60))
                    continue
                raise
        raise last


def _tool_def(t: dict) -> dict:
    return {"type": "function",
            "function": {"name": t["name"], "description": t["description"], "parameters": t["schema"]}}


def _usage(r):
    u = getattr(r, "usage", None)
    return ((u.prompt_tokens or 0) if u else 0, (u.completion_tokens or 0) if u else 0)


def run_turn(prov: Provider, messages: list, tools: list, first_choice, handlers: dict,
             calls_log: list, max_steps: int = 6, max_tokens: int = 1024, temperature: float = 1.0):
    """Drive one user turn to completion. Appends to messages in place.

    Returns (assistant_texts, in_tokens, out_tokens, steps_used).
    handlers: {tool_name: fn(args) -> str result}
    calls_log: list that receives {"tool", "args", "step"} for every call made.
    """
    texts = []
    tin = tout = 0
    tool_defs = [_tool_def(t) for t in tools] if tools else None
    for step in range(max_steps):
        choice = first_choice if step == 0 else "auto"
        r = prov.chat(messages, tool_defs, choice if tool_defs else None, max_tokens, temperature)
        a, b = _usage(r)
        tin += a
        tout += b
        msg = r.choices[0].message
        content = msg.content or ""
        if content.strip():
            texts.append(content.strip())
        tcs = list(msg.tool_calls or [])
        if tcs:
            messages.append({
                "role": "assistant", "content": content,
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name,
                                             "arguments": tc.function.arguments or "{}"}}
                               for tc in tcs],
            })
            for tc in tcs:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:  # noqa: BLE001
                    args = {"_raw": tc.function.arguments}
                calls_log.append({"tool": name, "args": args, "step": step})
                if name in handlers:
                    result = handlers[name](args)
                else:
                    result = json.dumps({"error": f"unknown tool {name}"})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue
        messages.append({"role": "assistant", "content": content})
        return texts, tin, tout, step + 1
    # ran out of steps while still calling tools
    return texts, tin, tout, max_steps


def run_trial(prov: Provider, trial: dict, max_tokens: int = 1024, temperature: float = 1.0) -> dict:
    """Two user turns. Turn 1 may force the reference tool. Turn 2 asks for the executed action."""
    ref = trial["ref_tool"]
    act = trial["action_tool"]
    tools = ([{"name": ref["name"], "description": ref["description"], "schema": ref["schema"]}] if ref else []) + \
            [{"name": act["name"], "description": act["description"], "schema": act["schema"]}]

    action_calls = []
    ref_calls = []

    def _ref_handler(args):
        ref_calls.append(args)
        return ref["result"]

    def _act_handler(args):
        action_calls.append(args)
        return json.dumps({"status": "saved", "id": f"rec-{len(action_calls):03d}"})

    handlers = {act["name"]: _act_handler}
    if ref:
        handlers[ref["name"]] = _ref_handler

    messages = [{"role": "system", "content": trial["system"]},
                {"role": "user", "content": trial["turn1"]}]
    first_choice = ({"type": "function", "function": {"name": ref["name"]}}
                    if (ref and ref["force"]) else "auto")

    t0 = time.time()
    texts1, in1, out1, steps1 = run_turn(prov, messages, tools, first_choice, handlers, [],
                                         max_tokens=max_tokens, temperature=temperature)
    ref_calls_t1 = len(ref_calls)
    action_calls_t1 = len(action_calls)
    messages.append({"role": "user", "content": trial["turn2"]})
    texts2, in2, out2, steps2 = run_turn(prov, messages, tools, "auto", handlers, [],
                                         max_tokens=max_tokens, temperature=temperature)
    return {
        "texts_turn1": texts1, "texts_turn2": texts2,
        "ref_calls": ref_calls, "ref_calls_turn1": ref_calls_t1,
        "action_calls": action_calls, "action_calls_turn1": action_calls_t1,
        "steps": [steps1, steps2],
        "input_tokens": in1 + in2, "output_tokens": out1 + out2,
        "seconds": round(time.time() - t0, 1),
        "messages": messages,
    }
