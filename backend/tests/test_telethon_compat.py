import struct
import unittest
from telethon.extensions import BinaryReader
import telethon.tl.alltlobjects as alltlobjects
import telethon.tl.types as types

from app.services.telethon_compat import UserCompatB1B8CC83, register_telethon_compat


class TestTelethonCompat(unittest.TestCase):
    def test_registration_idempotence(self):
        # Registration was already run on import
        self.assertIn(0xB1B8CC83, alltlobjects.tlobjects)
        self.assertIs(alltlobjects.tlobjects[0xB1B8CC83], UserCompatB1B8CC83)

        # Calling again should be idempotent and return False (no modification)
        result = register_telethon_compat()
        self.assertFalse(result)
        self.assertIs(alltlobjects.tlobjects[0xB1B8CC83], UserCompatB1B8CC83)

    def test_deserialize_captured_live_bot_payload(self):
        """Deserializes the exact byte structure captured from the live @Spoty_xbot error."""
        cid = struct.pack("<I", 0xB1B8CC83)
        # flags: 0x0200c02b (access_hash, first_name, username, photo, bot, bot_chat_history, apply_min_photo)
        flags = struct.pack("<I", 0x0200C02B)
        # flags2: 0x00001010 (stories_unavailable, bot_active_users)
        flags2 = struct.pack("<I", 0x00001010)
        uid = struct.pack("<q", 8264214434)
        access_hash = struct.pack("<q", -6917282464152500750)
        first_name = b"\tSpoty Bot\x00\x00"
        username = b"\nSpoty_xbot\x00"
        photo = struct.pack("<I", types.UserProfilePhotoEmpty.CONSTRUCTOR_ID)
        bot_info_version = struct.pack("<i", 1)
        bot_active_users = struct.pack("<i", 15000)

        full_payload = (
            cid
            + flags
            + flags2
            + uid
            + access_hash
            + first_name
            + username
            + photo
            + bot_info_version
            + bot_active_users
        )

        reader = BinaryReader(full_payload)
        user = reader.tgread_object()

        self.assertIsInstance(user, UserCompatB1B8CC83)
        self.assertIsInstance(user, types.User)
        self.assertEqual(user.id, 8264214434)
        self.assertEqual(user.first_name, "Spoty Bot")
        self.assertEqual(user.username, "Spoty_xbot")
        self.assertTrue(user.bot)
        self.assertTrue(user.bot_chat_history)
        self.assertTrue(user.stories_unavailable)
        self.assertEqual(user.bot_info_version, 1)
        self.assertEqual(user.bot_active_users, 15000)
        self.assertIsNone(user.linked_community_id)

    def test_deserialize_with_linked_community_id(self):
        """Tests that when flags2 bit 21 is set, linked_community_id is deserialized properly."""
        cid = struct.pack("<I", 0xB1B8CC83)
        flags = struct.pack("<I", 0x0200C02B)
        # Set bit 21 (1 << 21 = 2097152 = 0x200000)
        flags2 = struct.pack("<I", 0x00001010 | (1 << 21))
        uid = struct.pack("<q", 8264214434)
        access_hash = struct.pack("<q", -6917282464152500750)
        first_name = b"\tSpoty Bot\x00\x00"
        username = b"\nSpoty_xbot\x00"
        photo = struct.pack("<I", types.UserProfilePhotoEmpty.CONSTRUCTOR_ID)
        bot_info_version = struct.pack("<i", 1)
        bot_active_users = struct.pack("<i", 15000)
        linked_community_id = struct.pack("<q", 998877665544)

        full_payload = (
            cid
            + flags
            + flags2
            + uid
            + access_hash
            + first_name
            + username
            + photo
            + bot_info_version
            + bot_active_users
            + linked_community_id
        )

        reader = BinaryReader(full_payload)
        user = reader.tgread_object()

        self.assertEqual(user.id, 8264214434)
        self.assertEqual(user.linked_community_id, 998877665544)
        d = user.to_dict()
        self.assertEqual(d["linked_community_id"], 998877665544)

    def test_bytes_roundtrip(self):
        """Verifies that serialization matches deserialization."""
        user = UserCompatB1B8CC83(
            id=123456789,
            first_name="Test User",
            username="test_user",
            bot=True,
            bot_info_version=1,
            linked_community_id=555666777,
        )
        serialized = user._bytes()
        reader = BinaryReader(serialized)
        deserialized = reader.tgread_object()

        self.assertEqual(deserialized.id, user.id)
        self.assertEqual(deserialized.first_name, user.first_name)
        self.assertEqual(deserialized.username, user.username)
        self.assertEqual(deserialized.bot, user.bot)
        self.assertEqual(deserialized.linked_community_id, user.linked_community_id)


if __name__ == "__main__":
    unittest.main()
