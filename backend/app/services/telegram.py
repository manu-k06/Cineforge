import asyncio
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from telethon import TelegramClient, events
from telethon.tl.types import (
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    MessageMediaDocument,
    MessageMediaPhoto,
)

from app.config import settings
from app.models.delivery import (
    DeepLinkInfo,
    MediaMetadata,
    SelectedResultRequest,
    SelectedResultResponse,
    parse_telegram_deep_link,
)

logger = logging.getLogger("cineforge.telegram")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


class MediaWaiter:
    """Represents an isolated, asynchronous media waiter for a specific request."""

    def __init__(
        self,
        request_id: str,
        future: asyncio.Future,
        chat_id: Optional[int] = None,
    ):
        self.request_id = request_id
        self.future = future
        self.chat_id = chat_id
        self.created_at = time.time()


class TelegramService:
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._bot_lock = asyncio.Lock()
        self._waiters: Dict[str, MediaWaiter] = {}
        self._waiters_lock = asyncio.Lock()
        self._listener_registered = False

    def _get_client(self) -> Optional[TelegramClient]:
        if self.client is not None:
            return self.client

        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            logger.warning("Telegram API_ID or API_HASH is not configured.")
            return None

        self.client = TelegramClient(
            session=settings.TELEGRAM_SESSION_NAME,
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
        )
        return self.client

    def _register_event_handlers(self, client: TelegramClient):
        """Register global incoming message listeners on the Telethon client."""
        if self._listener_registered:
            return

        @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def on_private_message(event):
            await self._handle_incoming_private_message(event.message)

        self._listener_registered = True
        logger.info("Global incoming private message handler registered on Telegram client.")

    async def connect(self) -> bool:
        """Connect the Telegram client during application startup."""
        client = self._get_client()
        if client is None:
            return False

        try:
            if not client.is_connected():
                await client.connect()
                logger.info("Telethon user client connected successfully.")

            # Register event listener for incoming messages
            self._register_event_handlers(client)
            return True
        except Exception as e:
            logger.error("Failed to connect Telegram client: %s", str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect the Telegram client during application shutdown."""
        if self.client is not None and self.client.is_connected():
            try:
                await self.client.disconnect()
                logger.info("Telethon user client disconnected cleanly.")
            except Exception as e:
                logger.error("Error disconnecting Telegram client: %s", str(e))

    async def get_status(self) -> Dict[str, bool]:
        """Check connection and user authentication status."""
        client = self._get_client()
        if client is None:
            return {"connected": False, "authenticated": False}

        connected = client.is_connected()
        authenticated = False
        if connected:
            try:
                authenticated = await client.is_user_authorized()
            except Exception as e:
                logger.error("Error checking user authorization: %s", str(e))
                authenticated = False

        return {
            "connected": connected,
            "authenticated": authenticated,
        }

    def _extract_media_metadata(self, message) -> Optional[Dict[str, Any]]:
        """Extract detailed metadata from a Telegram media message without downloading."""
        if not getattr(message, "media", None):
            return None

        media = message.media
        media_type = "other"
        file_name: Optional[str] = None
        mime_type: Optional[str] = None
        size: Optional[int] = None
        duration: Optional[int] = None
        width: Optional[int] = None
        height: Optional[int] = None

        if isinstance(media, MessageMediaDocument) and media.document:
            doc = media.document
            mime_type = getattr(doc, "mime_type", None)
            size = getattr(doc, "size", None)
            media_type = "document"

            if mime_type:
                if mime_type.startswith("video/"):
                    media_type = "video"
                elif mime_type.startswith("audio/"):
                    media_type = "audio"
                elif mime_type.startswith("image/"):
                    media_type = "photo"

            for attr in getattr(doc, "attributes", []):
                if isinstance(attr, DocumentAttributeFilename):
                    file_name = attr.file_name
                elif isinstance(attr, DocumentAttributeVideo):
                    media_type = "video"
                    duration = getattr(attr, "duration", None)
                    width = getattr(attr, "w", None)
                    height = getattr(attr, "h", None)
                elif isinstance(attr, DocumentAttributeAudio):
                    media_type = "audio"
                    duration = getattr(attr, "duration", None)

        elif isinstance(media, MessageMediaPhoto):
            media_type = "photo"
            mime_type = "image/jpeg"

        return {
            "message_id": message.id,
            "chat_id": message.chat_id,
            "date": message.date.isoformat() if message.date else None,
            "media_type": media_type,
            "file_name": file_name,
            "mime_type": mime_type,
            "size": size,
            "duration": duration,
            "width": width,
            "height": height,
        }

    async def _handle_incoming_private_message(self, message):
        """Asynchronous callback when an incoming private message arrives."""
        logger.info(
            "Incoming Telegram message received (message_id=%s, chat_id=%s)",
            message.id,
            message.chat_id,
        )

        media_meta = self._extract_media_metadata(message)
        if media_meta is None:
            return

        logger.info(
            "Media detected (type=%s, file_name=%s, size=%s bytes)",
            media_meta.get("media_type"),
            media_meta.get("file_name"),
            media_meta.get("size"),
        )
        logger.info("Media metadata extracted successfully.")

        # Only notify MediaWaiter for actual media files (videos, documents, audio)
        if media_meta.get("media_type") in ("video", "document", "audio"):
            async with self._waiters_lock:
                for req_id, waiter in list(self._waiters.items()):
                    if waiter.chat_id is None or waiter.chat_id == message.chat_id:
                        if not waiter.future.done():
                            waiter.future.set_result(media_meta)
                            logger.info("Waiter matched with media file [request_id=%s]", req_id)

    async def wait_for_media(
        self,
        request_id: Optional[str] = None,
        from_chat_id: Optional[int] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Register an isolated waiter and await incoming media message with a timeout."""
        client = self._get_client()
        if client is None or not client.is_connected():
            raise RuntimeError("Telegram client is not connected.")

        req_id = request_id or str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        waiter = MediaWaiter(request_id=req_id, future=future, chat_id=from_chat_id)

        async with self._waiters_lock:
            self._waiters[req_id] = waiter

        logger.info(
            "Media waiter registered [request_id=%s, from_chat_id=%s, timeout=%.1fs]",
            req_id,
            from_chat_id,
            timeout,
        )

        start_time = time.perf_counter()
        try:
            media_data = await asyncio.wait_for(future, timeout=timeout)
            elapsed = time.perf_counter() - start_time
            return {
                "success": True,
                "request_id": req_id,
                "elapsed_seconds": round(elapsed, 3),
                "media": media_data,
            }
        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - start_time
            logger.warning("Waiter timed out [request_id=%s after %.1fs]", req_id, timeout)
            return {
                "success": False,
                "request_id": req_id,
                "elapsed_seconds": round(elapsed, 3),
                "error": f"Timeout: No media message received within {timeout}s.",
            }
        finally:
            async with self._waiters_lock:
                self._waiters.pop(req_id, None)
            logger.info("Waiter cleaned up [request_id=%s]", req_id)

    def select_result(self, request: SelectedResultRequest) -> SelectedResultResponse:
        """Validate and resolve a selected search result reference for delivery."""
        res_type = request.type.lower().strip()

        if res_type == "telegram_deep_link":
            raw_url = request.source_url or ""
            parsed_deep_link = parse_telegram_deep_link(raw_url)
            bot_username = (
                request.source_bot
                or (parsed_deep_link.bot_username if parsed_deep_link else None)
            )
            payload = (
                request.start_payload
                or (parsed_deep_link.start_payload if parsed_deep_link else None)
            )

            if not bot_username or not payload:
                raise ValueError(
                    f"Invalid Telegram deep link: unable to extract bot username or start payload from '{raw_url}'."
                )

            return SelectedResultResponse(
                status="resolved",
                resolved_type="telegram_deep_link",
                target_bot=bot_username,
                action_summary=f"Resolved Telegram deep link for delivery bot @{bot_username}",
                details={
                    "bot_username": bot_username,
                    "start_payload": payload,
                    "source_url": raw_url,
                    "command": f"/start {payload}",
                },
            )

        elif res_type == "callback":
            if not request.callback_data:
                raise ValueError("callback_data is required for callback selection type.")

            return SelectedResultResponse(
                status="resolved",
                resolved_type="callback",
                target_bot=request.source_bot or settings.TELEGRAM_BOT_USERNAME,
                action_summary="Resolved inline button callback action",
                details={
                    "message_id": request.message_id,
                    "callback_data": request.callback_data,
                    "source_bot": request.source_bot or settings.TELEGRAM_BOT_USERNAME,
                },
            )

        elif res_type == "url":
            if not request.source_url:
                raise ValueError("source_url is required for URL selection type.")

            return SelectedResultResponse(
                status="resolved",
                resolved_type="url",
                action_summary=f"External URL reference: {request.source_url}",
                details={"source_url": request.source_url},
            )

        else:
            raise ValueError(f"Unsupported selection type: '{request.type}'")

    async def join_channel_from_url(self, url: str) -> bool:
        """Automatically join a public channel or private invite link."""
        client = self._get_client()
        if client is None or not client.is_connected():
            return False

        clean_url = url.strip()
        from urllib.parse import urlparse
        parsed = urlparse(clean_url)
        path = parsed.path.strip("/")

        try:
            # Case 1: Private invite link with '+' or 'joinchat'
            invite_hash = None
            if path.startswith("+"):
                invite_hash = path[1:]
            elif path.startswith("joinchat/"):
                invite_hash = path.split("joinchat/")[1]

            if invite_hash:
                logger.info("Attempting to join private chat via invite hash: '%s'", invite_hash)
                from telethon.tl.functions.messages import ImportChatInviteRequest
                from telethon.errors import UserAlreadyParticipantError

                try:
                    await client(ImportChatInviteRequest(invite_hash))
                    logger.info("Successfully joined private channel via invite hash: %s", invite_hash)
                    return True
                except UserAlreadyParticipantError:
                    logger.info("Account is already a member of private channel: %s", invite_hash)
                    return True

            # Case 2: Public channel username (e.g. https://t.me/channel_username)
            elif path and not path.startswith("+") and not path.startswith("joinchat"):
                channel_username = path.split("/")[0].lstrip("@")
                if settings.TELEGRAM_BOT_USERNAME and channel_username.lower() == settings.TELEGRAM_BOT_USERNAME.lower():
                    return False

                logger.info("Attempting to join public channel: @%s", channel_username)
                from telethon.tl.functions.channels import JoinChannelRequest
                from telethon.errors import UserAlreadyParticipantError

                try:
                    await client(JoinChannelRequest(channel_username))
                    logger.info("Successfully joined public channel: @%s", channel_username)
                    return True
                except UserAlreadyParticipantError:
                    logger.info("Account is already a member of public channel: @%s", channel_username)
                    return True

        except Exception as e:
            logger.warning("Auto-join failed for '%s': %s", clean_url, str(e))
            return False

        return False

    async def test_delivery(self, source_url: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Execute a delivery test for a given Telegram deep link with automated FSub resolution."""
        deep_link = parse_telegram_deep_link(source_url)
        if not deep_link:
            raise ValueError(
                f"Invalid Telegram deep link: '{source_url}'. Expected format 'https://t.me/<bot_username>?start=<payload>'"
            )

        client = self._get_client()
        if client is None or not client.is_connected():
            raise RuntimeError("Telegram client is not connected.")

        if not await client.is_user_authorized():
            raise RuntimeError("Telegram user client is not authenticated.")

        bot_entity = await client.get_entity(deep_link.bot_username)
        bot_chat_id = bot_entity.id

        req_id = str(uuid.uuid4())
        logger.info(
            "Initiating test delivery [request_id=%s, bot=@%s, chat_id=%s, start_payload=%s]",
            req_id,
            deep_link.bot_username,
            bot_chat_id,
            deep_link.start_payload,
        )

        loop = asyncio.get_running_loop()
        media_future: asyncio.Future = loop.create_future()
        waiter = MediaWaiter(request_id=req_id, future=media_future, chat_id=bot_chat_id)

        async with self._waiters_lock:
            self._waiters[req_id] = waiter

        logger.info("Media waiter registered for delivery [request_id=%s, chat_id=%s]", req_id, bot_chat_id)

        start_time = time.perf_counter()

        async def _conversation_task():
            async with self._bot_lock:
                async with client.conversation(bot_entity, timeout=timeout) as conv:
                    command = f"/start {deep_link.start_payload}"
                    logger.info(
                        "Sending command '%s' to @%s [request_id=%s]",
                        command,
                        deep_link.bot_username,
                        req_id,
                    )
                    await conv.send_message(command)
                    resp = await conv.get_response()

                    # Check if response is already an actual media file
                    meta = self._extract_media_metadata(resp)
                    if meta and meta.get("media_type") in ("video", "document", "audio"):
                        return resp

                    # Check for Force-Subscription / Updates Channel gate
                    buttons = self._extract_buttons(resp)
                    channel_urls = []
                    try_again_button = None

                    for btn in buttons:
                        btn_url = btn.get("url")
                        if btn_url:
                            if ("t.me/+" in btn_url) or ("joinchat" in btn_url) or (
                                "t.me/" in btn_url and deep_link.bot_username.lower() not in btn_url.lower()
                            ):
                                channel_urls.append(btn_url)
                        elif btn.get("type") == "callback":
                            txt = (btn.get("text") or "").lower()
                            data = (btn.get("callback_data") or "").lower()
                            if any(k in txt or k in data for k in ("try", "again", "refresh", "check", "sub", "join")):
                                try_again_button = btn

                    # If channel links were detected in the gate message, auto-join them!
                    if channel_urls:
                        logger.info(
                            "FSub gatekeeper detected with %d channel link(s) [request_id=%s]",
                            len(channel_urls),
                            req_id,
                        )
                        for ch_url in channel_urls:
                            logger.info("Auto-joining channel: %s", ch_url)
                            await self.join_channel_from_url(ch_url)

                        # Propagation pause
                        await asyncio.sleep(1.2)

                        # Trigger verification
                        if try_again_button and try_again_button.get("callback_data"):
                            logger.info(
                                "Clicking verification callback button '%s' [request_id=%s]",
                                try_again_button.get("text"),
                                req_id,
                            )
                            try:
                                await resp.click(data=try_again_button.get("callback_data"))
                                retry_resp = await conv.get_response()
                                return retry_resp
                            except Exception as click_err:
                                logger.warning("Callback button click error, fallback to resending /start: %s", str(click_err))

                        # If no callback button or click failed, resend /start command
                        logger.info("Resending command '%s' after channel join [request_id=%s]", command, req_id)
                        await conv.send_message(command)
                        retry_resp = await conv.get_response()
                        return retry_resp

                    return resp

        conv_task = asyncio.create_task(_conversation_task())

        try:
            done, pending = await asyncio.wait(
                [media_future, conv_task],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            elapsed = round(time.perf_counter() - start_time, 3)

            # Case 1: MediaWaiter future completed with an incoming media document
            if media_future in done:
                conv_task.cancel()
                media_data = media_future.result()
                logger.info(
                    "Delivery succeeded: Media received [request_id=%s, elapsed=%.2fs]",
                    req_id,
                    elapsed,
                )
                return {
                    "success": True,
                    "request_id": req_id,
                    "status": "media_received",
                    "media": media_data,
                    "elapsed_seconds": elapsed,
                }

            # Case 2: Conversation task received a response message
            elif conv_task in done:
                try:
                    response_msg = conv_task.result()
                except Exception as e:
                    logger.error("Conversation task failed [request_id=%s]: %s", req_id, str(e))
                    return {
                        "success": False,
                        "request_id": req_id,
                        "status": "error",
                        "elapsed_seconds": elapsed,
                        "error": str(e),
                    }

                media_meta = self._extract_media_metadata(response_msg)
                buttons = self._extract_buttons(response_msg)

                if media_meta and media_meta.get("media_type") in ("video", "document", "audio"):
                    logger.info(
                        "Delivery succeeded: Direct media file response [request_id=%s, elapsed=%.2fs]",
                        req_id,
                        elapsed,
                    )
                    return {
                        "success": True,
                        "request_id": req_id,
                        "status": "media_received",
                        "media": media_meta,
                        "elapsed_seconds": elapsed,
                    }
                else:
                    logger.info(
                        "Delivery requires action/buttons: %d buttons detected [request_id=%s, elapsed=%.2fs]",
                        len(buttons),
                        req_id,
                        elapsed,
                    )
                    return {
                        "success": True,
                        "request_id": req_id,
                        "status": "action_required",
                        "message": response_msg.message or "",
                        "buttons": buttons,
                        "elapsed_seconds": elapsed,
                    }

            # Case 3: Timed out
            else:
                conv_task.cancel()
                logger.warning("Delivery timed out [request_id=%s after %.1fs]", req_id, timeout)
                return {
                    "success": False,
                    "request_id": req_id,
                    "status": "timeout",
                    "elapsed_seconds": elapsed,
                    "error": f"Timeout: No media or response received from @{deep_link.bot_username} within {timeout}s.",
                }

        except Exception as e:
            conv_task.cancel()
            elapsed = round(time.perf_counter() - start_time, 3)
            logger.error("Unexpected error during delivery test [request_id=%s]: %s", req_id, str(e))
            return {
                "success": False,
                "request_id": req_id,
                "status": "error",
                "elapsed_seconds": elapsed,
                "error": str(e),
            }
        finally:
            async with self._waiters_lock:
                self._waiters.pop(req_id, None)
            logger.info("Media waiter cleaned up for delivery [request_id=%s]", req_id)

    def _extract_buttons(self, message) -> List[Dict[str, Any]]:
        """Extract and normalize inline keyboard buttons from a Telegram message."""
        buttons_list: List[Dict[str, Any]] = []
        if not hasattr(message, "buttons") or not message.buttons:
            return buttons_list

        for row in message.buttons:
            for btn in row:
                button_text = getattr(btn, "text", "") or ""
                callback_data: Optional[str] = None
                url: Optional[str] = getattr(btn, "url", None)
                btn_type = "other"

                raw_data = getattr(btn, "data", None)
                if raw_data is not None:
                    btn_type = "callback"
                    if isinstance(raw_data, bytes):
                        try:
                            callback_data = raw_data.decode("utf-8")
                        except UnicodeDecodeError:
                            callback_data = raw_data.hex()
                    else:
                        callback_data = str(raw_data)
                elif url is not None:
                    btn_type = "url"
                elif hasattr(btn, "button") and hasattr(btn.button, "query"):
                    btn_type = "switch_inline"

                buttons_list.append({
                    "text": button_text,
                    "type": btn_type,
                    "callback_data": callback_data,
                    "url": url,
                })
        return buttons_list

    def _extract_button_rows(self, message) -> List[List[Dict[str, Any]]]:
        """Extract button layout preserving rows for detailed inspection."""
        rows_list: List[List[Dict[str, Any]]] = []
        if not hasattr(message, "buttons") or not message.buttons:
            return rows_list

        for row in message.buttons:
            current_row: List[Dict[str, Any]] = []
            for btn in row:
                button_text = getattr(btn, "text", "") or ""
                callback_data: Optional[str] = None
                url: Optional[str] = getattr(btn, "url", None)
                btn_type = "other"

                raw_data = getattr(btn, "data", None)
                if raw_data is not None:
                    btn_type = "callback"
                    if isinstance(raw_data, bytes):
                        try:
                            callback_data = raw_data.decode("utf-8")
                        except UnicodeDecodeError:
                            callback_data = raw_data.hex()
                    else:
                        callback_data = str(raw_data)
                elif url is not None:
                    btn_type = "url"
                elif hasattr(btn, "button") and hasattr(btn.button, "query"):
                    btn_type = "switch_inline"

                current_row.append({
                    "text": button_text,
                    "type": btn_type,
                    "callback_data": callback_data,
                    "url": url,
                })
            rows_list.append(current_row)
        return rows_list

    def _enrich_search_result(
        self,
        message_id: int,
        raw_text: str,
        buttons: List[Dict[str, Any]],
        has_media: bool,
        media_type: Optional[str],
        date_str: Optional[str],
    ) -> Dict[str, Any]:
        """Enrich search result item with extracted metadata hints and deep link detection."""
        title: Optional[str] = None
        size: Optional[str] = None
        quality: Optional[str] = None
        language: Optional[str] = None
        source_type: Optional[str] = None
        source_url: Optional[str] = None
        source_bot: Optional[str] = None
        start_payload: Optional[str] = None

        # Inspect buttons for deep links or callbacks
        for btn in buttons:
            btn_url = btn.get("url")
            if btn_url:
                deep_link = parse_telegram_deep_link(btn_url)
                if deep_link:
                    source_type = "telegram_deep_link"
                    source_url = btn_url
                    source_bot = deep_link.bot_username
                    start_payload = deep_link.start_payload
                    break
            elif btn.get("type") == "callback" and not source_type:
                source_type = "callback"

        # Regex hints for quality, size, and language
        combined_text = raw_text + " " + " ".join(b.get("text", "") for b in buttons)

        quality_match = re.search(
            r"\b(4k|2160p|1080p|720p|480p|hdrip|bluray|web-dl|webrip|dvdrip|camrip)\b",
            combined_text,
            re.IGNORECASE,
        )
        if quality_match:
            quality = quality_match.group(1).upper()

        size_match = re.search(
            r"(\b\d+(?:\.\d+)?\s*(?:GB|MB|GiB|MiB)\b)",
            combined_text,
            re.IGNORECASE,
        )
        if size_match:
            size = size_match.group(1)

        lang_match = re.search(
            r"\b(Dual Audio|Multi Audio|Hindi|English|Tamil|Telugu|Malayalam|Kannada)\b",
            combined_text,
            re.IGNORECASE,
        )
        if lang_match:
            language = lang_match.group(1)

        # Extract title from first line of message text
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if lines:
            title = lines[0]

        return {
            "message_id": message_id,
            "text": raw_text,
            "title": title,
            "size": size,
            "quality": quality,
            "language": language,
            "source_type": source_type,
            "source_url": source_url,
            "source_bot": source_bot,
            "start_payload": start_payload,
            "buttons": buttons,
            "has_media": has_media,
            "media_type": media_type,
            "date": date_str,
        }

    async def _resolve_bot_entity(self):
        """Helper to resolve the third-party bot entity."""
        if not settings.TELEGRAM_BOT_USERNAME:
            raise ValueError("TELEGRAM_BOT_USERNAME is not configured in .env")

        client = self._get_client()
        if client is None or not client.is_connected():
            raise RuntimeError("Telegram user client is not connected.")

        if not await client.is_user_authorized():
            raise RuntimeError("Telegram user client is not authenticated. Please complete login first.")

        return await client.get_entity(settings.TELEGRAM_BOT_USERNAME)

    async def search_bot(self, query: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Send a search query to the third-party bot in private chat and parse its response."""
        client = self._get_client()
        bot_entity = await self._resolve_bot_entity()
        effective_timeout = timeout or settings.TELEGRAM_BOT_RESPONSE_TIMEOUT

        # 1. Search request received
        logger.info("Search request received for query: '%s'", query)

        # 2. Query sent to Telegram bot in private chat
        logger.info("Query sent to Telegram bot: @%s (private chat)", settings.TELEGRAM_BOT_USERNAME)

        start_time = time.perf_counter()
        try:
            async with self._bot_lock:
                async with client.conversation(bot_entity, timeout=effective_timeout) as conv:
                    await conv.send_message(query)
                    response = await conv.get_response()
        except asyncio.TimeoutError:
            logger.error(
                "Timeout waiting for response from bot @%s after %.1f seconds",
                settings.TELEGRAM_BOT_USERNAME,
                effective_timeout,
            )
            raise TimeoutError(
                f"Telegram bot @{settings.TELEGRAM_BOT_USERNAME} did not respond within {effective_timeout}s."
            )

        elapsed = time.perf_counter() - start_time

        # 3. Bot response received
        logger.info(
            "Bot response received in private chat in %.2fs (message_id=%s)",
            elapsed,
            response.id,
        )

        # 4. Number of buttons detected
        buttons = self._extract_buttons(response)
        logger.info("Detected %d buttons in bot response", len(buttons))

        media_meta = self._extract_media_metadata(response)
        has_media = bool(media_meta)
        media_type = media_meta.get("media_type") if media_meta else None

        result_item = self._enrich_search_result(
            message_id=response.id,
            raw_text=response.message or "",
            buttons=buttons,
            has_media=has_media,
            media_type=media_type,
            date_str=response.date.isoformat() if response.date else None,
        )

        # 5. Structured result returned
        logger.info("Structured result returned for query '%s'", query)

        return {
            "query": query,
            "results": [result_item],
        }

    async def test_search_bot(self, query: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Development endpoint logic: Detailed search testing and button inspection in private chat."""
        client = self._get_client()
        bot_entity = await self._resolve_bot_entity()
        effective_timeout = timeout or settings.TELEGRAM_BOT_RESPONSE_TIMEOUT

        logger.info("[DEBUG] Test search request received for query: '%s'", query)
        logger.info("[DEBUG] Sending query to bot in private chat: @%s", settings.TELEGRAM_BOT_USERNAME)

        start_time = time.perf_counter()
        try:
            async with self._bot_lock:
                async with client.conversation(bot_entity, timeout=effective_timeout) as conv:
                    await conv.send_message(query)
                    response = await conv.get_response()
        except asyncio.TimeoutError:
            logger.error(
                "[DEBUG] Timeout waiting for response from bot @%s",
                settings.TELEGRAM_BOT_USERNAME,
            )
            raise TimeoutError(
                f"Telegram bot @{settings.TELEGRAM_BOT_USERNAME} did not respond within {effective_timeout}s."
            )

        elapsed = time.perf_counter() - start_time
        logger.info("[DEBUG] Bot response received in %.2fs (message_id=%s)", elapsed, response.id)

        buttons = self._extract_buttons(response)
        button_rows = self._extract_button_rows(response)
        logger.info("[DEBUG] Detected %d buttons across %d rows", len(buttons), len(button_rows))

        media_meta = self._extract_media_metadata(response)
        has_media = bool(media_meta)
        media_type = media_meta.get("media_type") if media_meta else None

        return {
            "query": query,
            "bot_username": settings.TELEGRAM_BOT_USERNAME,
            "elapsed_seconds": round(elapsed, 3),
            "response_message_id": response.id,
            "response_text": response.message or "",
            "has_media": has_media,
            "media_type": media_type,
            "buttons_count": len(buttons),
            "buttons": buttons,
            "raw_button_rows": button_rows,
        }


telegram_service = TelegramService()


async def interactive_login():
    """CLI utility for one-time interactive Telegram login."""
    print("=" * 65)
    print(" Cineforge — Interactive Telegram Authentication")
    print("=" * 65)

    if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
        print("ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        return

    client = TelegramClient(
        session=settings.TELEGRAM_SESSION_NAME,
        api_id=settings.TELEGRAM_API_ID,
        api_hash=settings.TELEGRAM_API_HASH,
    )

    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        name = f"{me.first_name or ''} {me.last_name or ''}".strip()
        print("\n" + "=" * 65)
        print("✅ ALREADY AUTHENTICATED!")
        print(f"Logged in as: {name} (User ID: {me.id})")
        print(f"Session saved to: {settings.TELEGRAM_SESSION_NAME}.session")
        print("You can launch the FastAPI server now!")
        print("=" * 65)
        await client.disconnect()
        return

    print("\nChoose authentication method:")
    print("  [1] Scan QR Code with Telegram App (Recommended - No SMS/code needed)")
    print("  [2] Phone Number + In-App Code")
    choice = input("\nEnter choice [1 or 2] (Default: 1): ").strip() or "1"

    if choice == "1":
        print("\nGenerating QR code for login...")
        try:
            import qrcode
            from telethon.errors import SessionPasswordNeededError

            qr_login = await client.qr_login()
            qr = qrcode.QRCode()
            qr.add_data(qr_login.url)
            print("\n" + "=" * 65)
            print("📲 Scan this QR Code with your Telegram App:")
            print("   👉 Open Telegram on your phone")
            print("   👉 Go to Settings > Devices > Link Desktop Device")
            print("   👉 Point camera at the QR code below")
            print("=" * 65 + "\n")
            qr.print_ascii(invert=True)
            print("\nWaiting for you to scan the QR code...")

            try:
                user = await qr_login.wait(timeout=120)
            except SessionPasswordNeededError:
                pwd = input("\n2FA Enabled. Please enter your 2FA Cloud Password: ")
                user = await client.sign_in(password=pwd)

            if user:
                name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                print("\n" + "=" * 65)
                print("✅ AUTHENTICATION SUCCESSFUL!")
                print(f"Logged in as: {name} (User ID: {user.id})")
                print(f"Session saved to: {settings.TELEGRAM_SESSION_NAME}.session")
                print("You can now launch the FastAPI server!")
                print("=" * 65)
        except Exception as e:
            print(f"\n❌ QR Login Error: {e}")
    else:
        print("\nℹ️  Phone Login:")
        print("1. Enter phone number with country code (e.g. +919876543210)")
        print("2. Check the official 'Telegram' chat in your app for the login code")
        print("-" * 65 + "\n")
        try:
            await client.start()
            if await client.is_user_authorized():
                me = await client.get_me()
                name = f"{me.first_name or ''} {me.last_name or ''}".strip()
                print("\n" + "=" * 65)
                print("✅ AUTHENTICATION SUCCESSFUL!")
                print(f"Logged in as: {name} (User ID: {me.id})")
                print(f"Session saved to: {settings.TELEGRAM_SESSION_NAME}.session")
                print("You can now launch the FastAPI server!")
                print("=" * 65)
        except Exception as e:
            print(f"\n❌ Login Error: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(interactive_login())
