import io
from telethon.extensions import BinaryReader
import telethon.tl.types as types

raw = b'\xc64\x9f\xd4\x00!D\x00\x08\x00\x00\x00W\xf8\x94m\x00\x00\x00\x00\x82D|\x864\xcf\xd1\x0f\x0cSpoty Series\x00\x00\x00\x11\x1cn\x1c\x02\x00\x00\x00"\xbb1\x1b^\xf7\x99V\x10\x01\x08\x08\xad\xfb\xbf+\xa7\xcfE\x14V\x07\xa6\x95\x8f\x00\x00\x00\x05\x00\x00\x00.\xd1\x0ef\x18\x04\x12\x9f\xfc\x05\xfe\r\xff\xff\xff\x7f'

reader = BinaryReader(raw)
cid = reader.read_int(signed=False)
print("Constructor ID:", hex(cid))
flags = reader.read_int()
print("flags:", bin(flags), flags)
flags2 = reader.read_int()
print("flags2:", bin(flags2), flags2)
_id = reader.read_long()
print("id:", _id)
if flags & 8192:
    _access_hash = reader.read_long()
    print("access_hash:", _access_hash)
_title = reader.tgread_string()
print("title:", _title)
if flags & 64:
    _username = reader.tgread_string()
    print("username:", _username)
_photo = reader.tgread_object()
print("photo:", _photo)
_date = reader.tgread_date()
print("date:", _date)
if flags & 512:
    reader.read_int()
    _restriction_reason = []
    for _ in range(reader.read_int()):
        _restriction_reason.append(reader.tgread_object())
    print("restriction_reason:", _restriction_reason)
if flags & 16384:
    _admin_rights = reader.tgread_object()
    print("admin_rights:", _admin_rights)
if flags & 32768:
    _banned_rights = reader.tgread_object()
    print("banned_rights:", _banned_rights)
if flags & 262144:
    _default_banned_rights = reader.tgread_object()
    print("default_banned_rights:", _default_banned_rights)
if flags & 131072:
    _participants_count = reader.read_int()
    print("participants_count:", _participants_count)

if flags2 & 1:
    reader.read_int()
    _usernames = []
    for _ in range(reader.read_int()):
        _usernames.append(reader.tgread_object())
    print("usernames:", _usernames)
if flags2 & 16:
    _stories_max_id = reader.tgread_object()
    print("stories_max_id:", _stories_max_id)
if flags2 & 128:
    _color = reader.tgread_object()
    print("color:", _color)
if flags2 & 256:
    _profile_color = reader.tgread_object()
    print("profile_color:", _profile_color)
if flags2 & 512:
    _emoji_status = reader.tgread_object()
    print("emoji_status:", _emoji_status)
if flags2 & 1024:
    _level = reader.read_int()
    print("level:", _level)
if flags2 & 2048:
    _subscription_until_date = reader.tgread_date()
    print("subscription_until_date:", _subscription_until_date)
if flags2 & 8192:
    _bot_verification_icon = reader.read_long()
    print("bot_verification_icon:", _bot_verification_icon)
if flags2 & 16384:
    _send_paid_messages_stars = reader.read_long()
    print("send_paid_messages_stars:", _send_paid_messages_stars)
if flags2 & 262144:
    _linked_monoforum_id = reader.read_long()
    print("linked_monoforum_id:", _linked_monoforum_id)
if flags2 & 1048576:
    _linked_community_id = reader.read_long()
    print("linked_community_id:", _linked_community_id)

print("Remaining bytes unread:", len(reader.get_bytes()) - reader.tell_position())
