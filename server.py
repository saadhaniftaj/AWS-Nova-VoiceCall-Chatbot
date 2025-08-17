import os
import contextlib
import asyncio
import base64
import json
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.models import (
    InvokeModelWithBidirectionalStreamInputChunk,
    BidirectionalInputPayloadPart,
)
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver
from dotenv import load_dotenv


# Load local env file for credentials/region if present
load_dotenv("nova_sonic.env")

AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
MODEL_ID = os.environ.get("MODEL_ID", "amazon.nova-sonic-v1:0")


class NovaSession:
    """Manages a single Nova Sonic bidirectional streaming session."""

    def __init__(self, model_id: str, region: str):
        self.model_id = model_id
        self.region = region
        self.client: BedrockRuntimeClient | None = None
        self.stream = None
        self.is_active: bool = False
        self.prompt_name: str = f"prompt-{uuid.uuid4()}"
        self.text_content_name: str = f"text-{uuid.uuid4()}"
        self.audio_content_name: str | None = None

    def _client(self) -> BedrockRuntimeClient:
        if not self.client:
            config = Config(
                endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
                region=self.region,
                aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
                http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
                http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()},
            )
            self.client = BedrockRuntimeClient(config=config)
        return self.client

    async def start(self, system_prompt: str):
        self.stream = await self._client().invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True

        # sessionStart
        await self._send_event(
            {
                "event": {
                    "sessionStart": {
                        "inferenceConfiguration": {
                            "maxTokens": 1024,
                            "topP": 0.9,
                            "temperature": 0.7,
                        }
                    }
                }
            }
        )

        # promptStart (configure audio/text output)
        await self._send_event(
            {
                "event": {
                    "promptStart": {
                        "promptName": self.prompt_name,
                        "textOutputConfiguration": {"mediaType": "text/plain"},
                        "audioOutputConfiguration": {
                            "mediaType": "audio/lpcm",
                            "sampleRateHertz": 24000,
                            "sampleSizeBits": 16,
                            "channelCount": 1,
                            "voiceId": "sarah",
                            "encoding": "base64",
                            "audioType": "SPEECH",
                        },
                    }
                }
            }
        )

        # SYSTEM text with persona (single SYSTEM block only!)
        await self._send_event(
            {
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": self.text_content_name,
                        "type": "TEXT",
                        "interactive": True,
                        "role": "SYSTEM",
                        "textInputConfiguration": {"mediaType": "text/plain"},
                    }
                }
            }
        )

        await self._send_event(
            {
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": self.text_content_name,
                        "content": system_prompt,
                    }
                }
            }
        )

        await self._send_event(
            {
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": self.text_content_name,
                    }
                }
            }
        )

    async def begin_audio_turn(self):
        # Open a new audio content for this user turn
        self.audio_content_name = f"audio-{uuid.uuid4()}"
        await self._send_event(
            {
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": self.audio_content_name,
                        "type": "AUDIO",
                        "interactive": True,
                        "role": "USER",
                        "audioInputConfiguration": {
                            "mediaType": "audio/lpcm",
                            "sampleRateHertz": 16000,
                            "sampleSizeBits": 16,
                            "channelCount": 1,
                            "audioType": "SPEECH",
                            "encoding": "base64",
                        },
                    }
                }
            }
        )

    async def send_audio_chunk(self, pcm_bytes: bytes):
        if not self.audio_content_name:
            # In case client forgot to call begin_audio_turn
            await self.begin_audio_turn()
        audio_b64 = base64.b64encode(pcm_bytes).decode("utf-8")
        await self._send_event(
            {
                "event": {
                    "audioInput": {
                        "promptName": self.prompt_name,
                        "contentName": self.audio_content_name,
                        "content": audio_b64,
                    }
                }
            }
        )

    async def end_audio_turn(self):
        if not self.audio_content_name:
            return
        await self._send_event(
            {
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": self.audio_content_name,
                    }
                }
            }
        )
        self.audio_content_name = None

    async def _send_event(self, payload: dict):
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps(payload).encode("utf-8"))
        )
        await self.stream.input_stream.send(event)

    async def close(self):
        if not self.is_active:
            return
        try:
            await self._send_event({"event": {"promptEnd": {"promptName": self.prompt_name}}})
            await self._send_event({"event": {"sessionEnd": {}}})
        except Exception:
            pass
        try:
            await self.stream.input_stream.close()
        except Exception:
            pass
        self.is_active = False


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    # Serve inline minimal page if index.html missing
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("""
<!doctype html>
<html><head><meta charset=\"utf-8\"><title>Nova Voice</title></head>
<body>
  <h3>Nova Voice App</h3>
  <p>Please add index.html to the project root.</p>
  </body></html>
""")


async def forward_bedrock_events(ws: WebSocket, session: NovaSession):
    # Track role/speculative flags and robust de-duplication per assistant turn
    current_role = None
    current_stage = None  # SPECULATIVE or FINAL
    # Remember emitted assistant lines within a single assistant turn
    emitted_assistant_lines: list[str] = []
    try:
        while session.is_active:
            output = await session.stream.await_output()
            result = await output[1].receive()
            if not result.value or not result.value.bytes_:
                continue
            msg = json.loads(result.value.bytes_.decode("utf-8"))
            ev = msg.get("event", {})

            if "contentStart" in ev:
                cs = ev["contentStart"]
                current_role = cs.get("role")
                # Reset per-turn de-dup when assistant starts speaking
                if current_role == "ASSISTANT":
                    emitted_assistant_lines = []
                # Track speculative/final stage if provided
                add_fields = cs.get("additionalModelFields")
                current_stage = None
                if add_fields:
                    try:
                        parsed = json.loads(add_fields)
                        current_stage = parsed.get("generationStage")  # SPECULATIVE / FINAL
                    except Exception:
                        current_stage = None
                await ws.send_json({"type": "contentStart", "role": current_role})

            elif "textOutput" in ev:
                text = ev["textOutput"].get("content", "")
                if current_role == "USER":
                    await ws.send_json({"type": "text", "role": "user", "content": text})
                elif current_role == "ASSISTANT":
                    # Strategy: only emit unique lines within a turn; ignore exact repeats
                    if text and text not in emitted_assistant_lines:
                        # If stages are present, prefer FINAL only: skip SPECULATIVE duplicates
                        if current_stage == "SPECULATIVE":
                            # Buffer speculative but do not emit duplicates
                            emitted_assistant_lines.append(text)
                        else:
                            await ws.send_json({"type": "text", "role": "assistant", "content": text})
                            emitted_assistant_lines.append(text)

            elif "audioOutput" in ev:
                await ws.send_json({
                    "type": "audio",
                    "sampleRate": 24000,
                    "content": ev["audioOutput"]["content"],  # base64 PCM16 24k
                })
            elif "contentEnd" in ev:
                # Signal end of current role's turn
                await ws.send_json({"type": "contentEnd", "role": current_role})
    except Exception:
        # Swallow to allow close
        pass


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    # Build persona/system prompt once per connection
    system_prompt = (
        "You are Saad, a professional and friendly male receptionist at TechCorp Solutions. "
        "You greet visitors warmly, answer questions about the company, schedule appointments, "
        "and direct calls appropriately. Always be polite, professional, and helpful. "
        "Keep responses concise and welcoming, like a real receptionist would speak. "
        "When the conversation starts, immediately introduce yourself by saying: "
        "'Hi! I'm Saad, the receptionist at TechCorp Solutions. How can I help you today?'"
    )

    session = NovaSession(MODEL_ID, AWS_REGION)
    forward_task = None
    try:
        await session.start(system_prompt)
        await ws.send_json({"type": "ready", "promptName": session.prompt_name})
        forward_task = asyncio.create_task(forward_bedrock_events(ws, session))

        # Client protocol:
        # - JSON {type: "beginAudio"}
        # - Binary frames: raw PCM16 mono 16k
        # - JSON {type: "endAudio"}
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("text")
            if data is not None:
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                mtype = obj.get("type")
                if mtype == "beginAudio":
                    await session.begin_audio_turn()
                elif mtype == "endAudio":
                    await session.end_audio_turn()
                else:
                    # no-op
                    pass
            else:
                # binary frame
                b: bytes | None = msg.get("bytes")
                if b:
                    await session.send_audio_chunk(b)

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await ws.send_json({"type": "error", "message": "Internal server error"})
        except Exception:
            pass
    finally:
        try:
            if forward_task:
                forward_task.cancel()
                with contextlib.suppress(Exception):
                    await forward_task
        except Exception:
            pass
        await session.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)


