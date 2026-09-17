"""Isolated compatibility module for unmapped Telegram MTProto constructors.

Currently handles user#b1b8cc83 introduced in Telegram Layer 195+ which adds
conditional `linked_community_id` on flags2 bit 21.

This module registers the compatibility constructor idempotently into
Telethon's type registry without modifying the installed Telethon package.
"""

import logging
import struct
from typing import Any, List, Optional

import telethon.tl.alltlobjects as alltlobjects
import telethon.tl.types as types
from telethon.tl.tlobject import TLObject

logger = logging.getLogger("cineforge.telethon_compat")


class UserCompatB1B8CC83(types.User):
    """Compatibility implementation for Telegram constructor user#b1b8cc83 (Layer 195+).

    Wire schema:
    user#b1b8cc83 flags:# self:flags.10?true contact:flags.11?true mutual_contact:flags.12?true
        deleted:flags.13?true bot:flags.14?true bot_chat_history:flags.15?true bot_nochats:flags.16?true
        verified:flags.17?true restricted:flags.18?true min:flags.20?true bot_inline_geo:flags.21?true
        support:flags.23?true scam:flags.24?true apply_min_photo:flags.25?true fake:flags.26?true
        bot_attach_menu:flags.27?true premium:flags.28?true attach_menu_enabled:flags.29?true
        flags2:# bot_can_edit:flags2.1?true close_friend:flags2.2?true stories_hidden:flags2.3?true
        stories_unavailable:flags2.4?true contact_require_premium:flags2.10?true bot_business:flags2.11?true
        bot_has_main_app:flags2.13?true bot_forum_view:flags2.16?true bot_forum_can_manage_topics:flags2.17?true
        bot_can_manage_bots:flags2.18?true bot_guestchat:flags2.19?true bot_guard:flags2.20?true
        id:long access_hash:flags.0?long first_name:flags.1?string last_name:flags.2?string
        username:flags.3?string phone:flags.4?string photo:flags.5?UserProfilePhoto
        status:flags.6?UserStatus bot_info_version:flags.14?int
        restriction_reason:flags.18?Vector<RestrictionReason> bot_inline_placeholder:flags.19?string
        lang_code:flags.22?string emoji_status:flags.30?EmojiStatus
        usernames:flags2.0?Vector<Username> stories_max_id:flags2.5?RecentStory
        color:flags2.8?PeerColor profile_color:flags2.9?PeerColor bot_active_users:flags2.12?int
        bot_verification_icon:flags2.14?long send_paid_messages_stars:flags2.15?long
        linked_community_id:flags2.21?long = User;
    """

    CONSTRUCTOR_ID = 0xB1B8CC83
    SUBCLASS_OF_ID = 0x2DA17977

    def __init__(
        self,
        id: int,
        *,
        is_self: bool = False,
        contact: bool = False,
        mutual_contact: bool = False,
        deleted: bool = False,
        bot: bool = False,
        bot_chat_history: bool = False,
        bot_nochats: bool = False,
        verified: bool = False,
        restricted: bool = False,
        min: bool = False,
        bot_inline_geo: bool = False,
        support: bool = False,
        scam: bool = False,
        apply_min_photo: bool = False,
        fake: bool = False,
        bot_attach_menu: bool = False,
        premium: bool = False,
        attach_menu_enabled: bool = False,
        bot_can_edit: bool = False,
        close_friend: bool = False,
        stories_hidden: bool = False,
        stories_unavailable: bool = False,
        contact_require_premium: bool = False,
        bot_business: bool = False,
        bot_has_main_app: bool = False,
        bot_forum_view: bool = False,
        bot_forum_can_manage_topics: bool = False,
        bot_can_manage_bots: bool = False,
        bot_guestchat: bool = False,
        bot_guard: bool = False,
        access_hash: Optional[int] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        phone: Optional[str] = None,
        photo: Optional[Any] = None,
        status: Optional[Any] = None,
        bot_info_version: Optional[int] = None,
        restriction_reason: Optional[List[Any]] = None,
        bot_inline_placeholder: Optional[str] = None,
        lang_code: Optional[str] = None,
        emoji_status: Optional[Any] = None,
        usernames: Optional[List[Any]] = None,
        stories_max_id: Optional[Any] = None,
        color: Optional[Any] = None,
        profile_color: Optional[Any] = None,
        bot_active_users: Optional[int] = None,
        bot_verification_icon: Optional[int] = None,
        send_paid_messages_stars: Optional[int] = None,
        linked_community_id: Optional[int] = None,
    ):
        super().__init__(
            id=id,
            is_self=is_self,
            contact=contact,
            mutual_contact=mutual_contact,
            deleted=deleted,
            bot=bot,
            bot_chat_history=bot_chat_history,
            bot_nochats=bot_nochats,
            verified=verified,
            restricted=restricted,
            min=min,
            bot_inline_geo=bot_inline_geo,
            support=support,
            scam=scam,
            apply_min_photo=apply_min_photo,
            fake=fake,
            bot_attach_menu=bot_attach_menu,
            premium=premium,
            attach_menu_enabled=attach_menu_enabled,
            bot_can_edit=bot_can_edit,
            close_friend=close_friend,
            stories_hidden=stories_hidden,
            stories_unavailable=stories_unavailable,
            contact_require_premium=contact_require_premium,
            bot_business=bot_business,
            bot_has_main_app=bot_has_main_app,
            bot_forum_view=bot_forum_view,
            bot_forum_can_manage_topics=bot_forum_can_manage_topics,
            bot_can_manage_bots=bot_can_manage_bots,
            bot_guestchat=bot_guestchat,
            bot_guard=bot_guard,
            access_hash=access_hash,
            first_name=first_name,
            last_name=last_name,
            username=username,
            phone=phone,
            photo=photo,
            status=status,
            bot_info_version=bot_info_version,
            restriction_reason=restriction_reason,
            bot_inline_placeholder=bot_inline_placeholder,
            lang_code=lang_code,
            emoji_status=emoji_status,
            usernames=usernames,
            stories_max_id=stories_max_id,
            color=color,
            profile_color=profile_color,
            bot_active_users=bot_active_users,
            bot_verification_icon=bot_verification_icon,
            send_paid_messages_stars=send_paid_messages_stars,
        )
        self.linked_community_id = linked_community_id

    @classmethod
    def from_reader(cls, reader):
        flags = reader.read_int()

        _is_self = bool(flags & 1024)
        _contact = bool(flags & 2048)
        _mutual_contact = bool(flags & 4096)
        _deleted = bool(flags & 8192)
        _bot = bool(flags & 16384)
        _bot_chat_history = bool(flags & 32768)
        _bot_nochats = bool(flags & 65536)
        _verified = bool(flags & 131072)
        _restricted = bool(flags & 262144)
        _min = bool(flags & 1048576)
        _bot_inline_geo = bool(flags & 2097152)
        _support = bool(flags & 8388608)
        _scam = bool(flags & 16777216)
        _apply_min_photo = bool(flags & 33554432)
        _fake = bool(flags & 67108864)
        _bot_attach_menu = bool(flags & 134217728)
        _premium = bool(flags & 268435456)
        _attach_menu_enabled = bool(flags & 536870912)

        flags2 = reader.read_int()

        _bot_can_edit = bool(flags2 & 2)
        _close_friend = bool(flags2 & 4)
        _stories_hidden = bool(flags2 & 8)
        _stories_unavailable = bool(flags2 & 16)
        _contact_require_premium = bool(flags2 & 1024)
        _bot_business = bool(flags2 & 2048)
        _bot_has_main_app = bool(flags2 & 8192)
        _bot_forum_view = bool(flags2 & 65536)
        _bot_forum_can_manage_topics = bool(flags2 & 131072)
        _bot_can_manage_bots = bool(flags2 & 262144)
        _bot_guestchat = bool(flags2 & 524288)
        _bot_guard = bool(flags2 & 1048576)

        _id = reader.read_long()

        if flags & 1:
            _access_hash = reader.read_long()
        else:
            _access_hash = None

        if flags & 2:
            _first_name = reader.tgread_string()
        else:
            _first_name = None

        if flags & 4:
            _last_name = reader.tgread_string()
        else:
            _last_name = None

        if flags & 8:
            _username = reader.tgread_string()
        else:
            _username = None

        if flags & 16:
            _phone = reader.tgread_string()
        else:
            _phone = None

        if flags & 32:
            _photo = reader.tgread_object()
        else:
            _photo = None

        if flags & 64:
            _status = reader.tgread_object()
        else:
            _status = None

        if flags & 16384:
            _bot_info_version = reader.read_int()
        else:
            _bot_info_version = None

        if flags & 262144:
            reader.read_int()
            _restriction_reason = []
            for _ in range(reader.read_int()):
                _x = reader.tgread_object()
                _restriction_reason.append(_x)
        else:
            _restriction_reason = None

        if flags & 524288:
            _bot_inline_placeholder = reader.tgread_string()
        else:
            _bot_inline_placeholder = None

        if flags & 4194304:
            _lang_code = reader.tgread_string()
        else:
            _lang_code = None

        if flags & 1073741824:
            _emoji_status = reader.tgread_object()
        else:
            _emoji_status = None

        if flags2 & 1:
            reader.read_int()
            _usernames = []
            for _ in range(reader.read_int()):
                _x = reader.tgread_object()
                _usernames.append(_x)
        else:
            _usernames = None

        if flags2 & 32:
            _stories_max_id = reader.tgread_object()
        else:
            _stories_max_id = None

        if flags2 & 256:
            _color = reader.tgread_object()
        else:
            _color = None

        if flags2 & 512:
            _profile_color = reader.tgread_object()
        else:
            _profile_color = None

        if flags2 & 4096:
            _bot_active_users = reader.read_int()
        else:
            _bot_active_users = None

        if flags2 & 16384:
            _bot_verification_icon = reader.read_long()
        else:
            _bot_verification_icon = None

        if flags2 & 32768:
            _send_paid_messages_stars = reader.read_long()
        else:
            _send_paid_messages_stars = None

        # Layer 195+ addition: flags2 bit 21 (1 << 21 = 2097152)
        if flags2 & 2097152:
            _linked_community_id = reader.read_long()
        else:
            _linked_community_id = None

        return cls(
            id=_id,
            is_self=_is_self,
            contact=_contact,
            mutual_contact=_mutual_contact,
            deleted=_deleted,
            bot=_bot,
            bot_chat_history=_bot_chat_history,
            bot_nochats=_bot_nochats,
            verified=_verified,
            restricted=_restricted,
            min=_min,
            bot_inline_geo=_bot_inline_geo,
            support=_support,
            scam=_scam,
            apply_min_photo=_apply_min_photo,
            fake=_fake,
            bot_attach_menu=_bot_attach_menu,
            premium=_premium,
            attach_menu_enabled=_attach_menu_enabled,
            bot_can_edit=_bot_can_edit,
            close_friend=_close_friend,
            stories_hidden=_stories_hidden,
            stories_unavailable=_stories_unavailable,
            contact_require_premium=_contact_require_premium,
            bot_business=_bot_business,
            bot_has_main_app=_bot_has_main_app,
            bot_forum_view=_bot_forum_view,
            bot_forum_can_manage_topics=_bot_forum_can_manage_topics,
            bot_can_manage_bots=_bot_can_manage_bots,
            bot_guestchat=_bot_guestchat,
            bot_guard=_bot_guard,
            access_hash=_access_hash,
            first_name=_first_name,
            last_name=_last_name,
            username=_username,
            phone=_phone,
            photo=_photo,
            status=_status,
            bot_info_version=_bot_info_version,
            restriction_reason=_restriction_reason,
            bot_inline_placeholder=_bot_inline_placeholder,
            lang_code=_lang_code,
            emoji_status=_emoji_status,
            usernames=_usernames,
            stories_max_id=_stories_max_id,
            color=_color,
            profile_color=_profile_color,
            bot_active_users=_bot_active_users,
            bot_verification_icon=_bot_verification_icon,
            send_paid_messages_stars=_send_paid_messages_stars,
            linked_community_id=_linked_community_id,
        )

    def _bytes(self):
        assert ((self.bot or self.bot is not None) and (self.bot_info_version or self.bot_info_version is not None)) or ((self.bot is None or self.bot is False) and (self.bot_info_version is None or self.bot_info_version is False)), 'bot, bot_info_version parameters must all be False-y (like None) or all be True-y'
        assert ((self.restricted or self.restricted is not None) and (self.restriction_reason or self.restriction_reason is not None)) or ((self.restricted is None or self.restricted is False) and (self.restriction_reason is None or self.restriction_reason is False)), 'restricted, restriction_reason parameters must all be False-y (like None) or all be True-y'
        return b"".join((
            b"\x83\xcc\xb8\xb1",
            struct.pack(
                "<I",
                (0 if self.is_self is None or self.is_self is False else 1024)
                | (0 if self.contact is None or self.contact is False else 2048)
                | (0 if self.mutual_contact is None or self.mutual_contact is False else 4096)
                | (0 if self.deleted is None or self.deleted is False else 8192)
                | (0 if self.bot is None or self.bot is False else 16384)
                | (0 if self.bot_chat_history is None or self.bot_chat_history is False else 32768)
                | (0 if self.bot_nochats is None or self.bot_nochats is False else 65536)
                | (0 if self.verified is None or self.verified is False else 131072)
                | (0 if self.restricted is None or self.restricted is False else 262144)
                | (0 if self.min is None or self.min is False else 1048576)
                | (0 if self.bot_inline_geo is None or self.bot_inline_geo is False else 2097152)
                | (0 if self.support is None or self.support is False else 8388608)
                | (0 if self.scam is None or self.scam is False else 16777216)
                | (0 if self.apply_min_photo is None or self.apply_min_photo is False else 33554432)
                | (0 if self.fake is None or self.fake is False else 67108864)
                | (0 if self.bot_attach_menu is None or self.bot_attach_menu is False else 134217728)
                | (0 if self.premium is None or self.premium is False else 268435456)
                | (0 if self.attach_menu_enabled is None or self.attach_menu_enabled is False else 536870912)
                | (0 if self.access_hash is None or self.access_hash is False else 1)
                | (0 if self.first_name is None or self.first_name is False else 2)
                | (0 if self.last_name is None or self.last_name is False else 4)
                | (0 if self.username is None or self.username is False else 8)
                | (0 if self.phone is None or self.phone is False else 16)
                | (0 if self.photo is None or self.photo is False else 32)
                | (0 if self.status is None or self.status is False else 64)
                | (0 if self.bot_info_version is None or self.bot_info_version is False else 16384)
                | (0 if self.restriction_reason is None or self.restriction_reason is False else 262144)
                | (0 if self.bot_inline_placeholder is None or self.bot_inline_placeholder is False else 524288)
                | (0 if self.lang_code is None or self.lang_code is False else 4194304)
                | (0 if self.emoji_status is None or self.emoji_status is False else 1073741824),
            ),
            struct.pack(
                "<I",
                (0 if self.bot_can_edit is None or self.bot_can_edit is False else 2)
                | (0 if self.close_friend is None or self.close_friend is False else 4)
                | (0 if self.stories_hidden is None or self.stories_hidden is False else 8)
                | (0 if self.stories_unavailable is None or self.stories_unavailable is False else 16)
                | (0 if self.contact_require_premium is None or self.contact_require_premium is False else 1024)
                | (0 if self.bot_business is None or self.bot_business is False else 2048)
                | (0 if self.bot_has_main_app is None or self.bot_has_main_app is False else 8192)
                | (0 if self.bot_forum_view is None or self.bot_forum_view is False else 65536)
                | (0 if self.bot_forum_can_manage_topics is None or self.bot_forum_can_manage_topics is False else 131072)
                | (0 if self.bot_can_manage_bots is None or self.bot_can_manage_bots is False else 262144)
                | (0 if self.bot_guestchat is None or self.bot_guestchat is False else 524288)
                | (0 if self.bot_guard is None or self.bot_guard is False else 1048576)
                | (0 if self.usernames is None or self.usernames is False else 1)
                | (0 if self.stories_max_id is None or self.stories_max_id is False else 32)
                | (0 if self.color is None or self.color is False else 256)
                | (0 if self.profile_color is None or self.profile_color is False else 512)
                | (0 if self.bot_active_users is None or self.bot_active_users is False else 4096)
                | (0 if self.bot_verification_icon is None or self.bot_verification_icon is False else 16384)
                | (0 if self.send_paid_messages_stars is None or self.send_paid_messages_stars is False else 32768)
                | (0 if self.linked_community_id is None or self.linked_community_id is False else 2097152),
            ),
            struct.pack("<q", self.id),
            b"" if self.access_hash is None or self.access_hash is False else struct.pack("<q", self.access_hash),
            b"" if self.first_name is None or self.first_name is False else self.serialize_bytes(self.first_name),
            b"" if self.last_name is None or self.last_name is False else self.serialize_bytes(self.last_name),
            b"" if self.username is None or self.username is False else self.serialize_bytes(self.username),
            b"" if self.phone is None or self.phone is False else self.serialize_bytes(self.phone),
            b"" if self.photo is None or self.photo is False else self.photo._bytes(),
            b"" if self.status is None or self.status is False else self.status._bytes(),
            b"" if self.bot_info_version is None or self.bot_info_version is False else struct.pack("<i", self.bot_info_version),
            b""
            if self.restriction_reason is None or self.restriction_reason is False
            else b"".join((
                b"\x15\xc4\xb5\x1c",
                struct.pack("<i", len(self.restriction_reason)),
                b"".join(x._bytes() for x in self.restriction_reason),
            )),
            b""
            if self.bot_inline_placeholder is None or self.bot_inline_placeholder is False
            else self.serialize_bytes(self.bot_inline_placeholder),
            b"" if self.lang_code is None or self.lang_code is False else self.serialize_bytes(self.lang_code),
            b"" if self.emoji_status is None or self.emoji_status is False else self.emoji_status._bytes(),
            b""
            if self.usernames is None or self.usernames is False
            else b"".join((
                b"\x15\xc4\xb5\x1c",
                struct.pack("<i", len(self.usernames)),
                b"".join(x._bytes() for x in self.usernames),
            )),
            b"" if self.stories_max_id is None or self.stories_max_id is False else self.stories_max_id._bytes(),
            b"" if self.color is None or self.color is False else self.color._bytes(),
            b"" if self.profile_color is None or self.profile_color is False else self.profile_color._bytes(),
            b"" if self.bot_active_users is None or self.bot_active_users is False else struct.pack("<i", self.bot_active_users),
            b""
            if self.bot_verification_icon is None or self.bot_verification_icon is False
            else struct.pack("<q", self.bot_verification_icon),
            b""
            if self.send_paid_messages_stars is None or self.send_paid_messages_stars is False
            else struct.pack("<q", self.send_paid_messages_stars),
            b""
            if self.linked_community_id is None or self.linked_community_id is False
            else struct.pack("<q", self.linked_community_id),
        ))

    def to_dict(self):
        d = super().to_dict()
        d["linked_community_id"] = self.linked_community_id
        return d


def register_telethon_compat() -> bool:
    """Idempotently registers constructor 0xb1b8cc83 into Telethon's type registry."""
    if (
        0xB1B8CC83 in alltlobjects.tlobjects
        and alltlobjects.tlobjects[0xB1B8CC83] is UserCompatB1B8CC83
    ):
        return False

    alltlobjects.tlobjects[0xB1B8CC83] = UserCompatB1B8CC83
    logger.info("Registered compatibility constructor for Telegram User (0xb1b8cc83)")
    return True


# Automatically run idempotent registration on import
register_telethon_compat()
