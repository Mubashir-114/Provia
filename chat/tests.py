from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from accounts.models import User
from bookings.models import Booking
from chat.models import Conversation, Message
from providers.models import ProviderProfile
from services.models import Service, ServiceCategory
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from config.asgi import application
import json


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    },
)
class WebSocketRoutingTests(TestCase):
    def test_chat_consumer_rejects_anonymous_connection(self):
        communicator = WebsocketCommunicator(
            application,
            "/ws/chat/1/",
        )

        connected, _ = async_to_sync(
            communicator.connect,
        )()

        self.assertFalse(connected)


class ChatModelTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="chat_customer",
            email="chat_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider_user = User.objects.create_user(
            username="chat_provider",
            email="chat_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Chat Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Chat Category",
            slug="chat-category",
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Chat Service",
            description="Service used for chat tests.",
            price="100.00",
            duration_minutes=60,
            is_published=True,
        )

        self.booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date="2099-01-01",
            start_time="10:00",
            end_time="11:00",
            total_amount="100.00",
            status=Booking.Status.CONFIRMED,
        )

        self.conversation = Conversation.objects.create(
            booking=self.booking,
            customer=self.customer,
            provider=self.provider,
        )

    def test_valid_message_can_be_created(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            content="Hello, I have a question.",
        )

        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.sender, self.customer)
        self.assertEqual(message.content, "Hello, I have a question.")
        self.assertFalse(message.is_read)

    def test_provider_can_send_message(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.provider_user,
            content="Sure, how can I help?",
        )

        self.assertEqual(message.sender, self.provider_user)

    def test_non_participant_cannot_send_message(self):
        other_user = User.objects.create_user(
            username="other_customer",
            email="other_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        message = Message(
            conversation=self.conversation,
            sender=other_user,
            content="Unauthorized message.",
        )

        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_empty_message_is_rejected(self):
        message = Message(
            conversation=self.conversation,
            sender=self.customer,
            content="   ",
        )

        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_messages_are_ordered_oldest_first(self):
        first = Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            content="First message",
        )

        second = Message.objects.create(
            conversation=self.conversation,
            sender=self.provider_user,
            content="Second message",
        )

        messages = list(self.conversation.messages.all())

        self.assertEqual(
            messages,
            [first, second],
        )


class ChatServiceTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="service_customer",
            email="service_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider_user = User.objects.create_user(
            username="service_provider",
            email="service_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="other_service_customer",
            email="other_service_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Service Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="Service Category",
            slug="service-category",
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Service",
            description="Service description.",
            price="100.00",
            duration_minutes=60,
            is_published=True,
        )

        self.booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date="2099-01-01",
            start_time="10:00",
            end_time="11:00",
            total_amount="100.00",
            status=Booking.Status.CONFIRMED,
        )

    def test_create_conversation_for_booking(self):
        from chat.services import (
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        self.assertEqual(
            conversation.customer,
            self.customer,
        )
        self.assertEqual(
            conversation.provider,
            self.provider,
        )
        self.assertEqual(
            conversation.booking,
            self.booking,
        )

    def test_get_or_create_conversation_is_idempotent(self):
        from chat.services import (
            get_or_create_conversation_for_booking,
        )

        first = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        second = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        self.assertEqual(first.pk, second.pk)

        self.assertEqual(
            Conversation.objects.count(),
            1,
        )

    def test_provider_can_access_booking_conversation(self):
        from chat.services import (
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.provider_user,
        )

        self.assertEqual(
            conversation.provider,
            self.provider,
        )

    def test_unrelated_user_cannot_access_conversation(self):
        from django.core.exceptions import ValidationError

        from chat.services import (
            get_or_create_conversation_for_booking,
        )

        with self.assertRaises(ValidationError):
            get_or_create_conversation_for_booking(
                booking=self.booking,
                user=self.other_customer,
            )

    def test_create_message_for_participant(self):
        from chat.services import (
            create_message,
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        message = create_message(
            conversation=conversation,
            sender=self.customer,
            content="Hello provider",
        )

        self.assertEqual(
            message.conversation,
            conversation,
        )
        self.assertEqual(
            message.sender,
            self.customer,
        )
        self.assertEqual(
            message.content,
            "Hello provider",
        )

    def test_non_participant_cannot_create_message(self):
        from django.core.exceptions import ValidationError

        from chat.services import (
            create_message,
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        with self.assertRaises(ValidationError):
            create_message(
                conversation=conversation,
                sender=self.other_customer,
                content="Unauthorized message",
            )

    def test_empty_message_is_rejected(self):
        from django.core.exceptions import ValidationError

        from chat.services import (
            create_message,
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        with self.assertRaises(ValidationError):
            create_message(
                conversation=conversation,
                sender=self.customer,
                content="   ",
            )

    def test_conversation_messages_are_scoped(self):
        from chat.services import (
            create_message,
            get_conversation_messages,
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        create_message(
            conversation=conversation,
            sender=self.customer,
            content="First",
        )

        create_message(
            conversation=conversation,
            sender=self.provider_user,
            content="Second",
        )

        messages = list(
            get_conversation_messages(
                conversation=conversation,
                user=self.customer,
            )
        )

        self.assertEqual(
            len(messages),
            2,
        )

    def test_mark_messages_as_read(self):
        from chat.services import (
            create_message,
            get_or_create_conversation_for_booking,
            mark_messages_as_read,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        message = create_message(
            conversation=conversation,
            sender=self.provider_user,
            content="Hello customer",
        )

        self.assertFalse(message.is_read)

        updated = mark_messages_as_read(
            conversation=conversation,
            user=self.customer,
        )

        self.assertEqual(updated, 1)

        message.refresh_from_db()

        self.assertTrue(message.is_read)

    def test_unread_message_count_excludes_own_messages(self):
        from chat.services import (
            create_message,
            get_or_create_conversation_for_booking,
            get_unread_message_count,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        create_message(
            conversation=conversation,
            sender=self.customer,
            content="Customer message",
        )

        create_message(
            conversation=conversation,
            sender=self.provider_user,
            content="Provider message",
        )

        self.assertEqual(
            get_unread_message_count(
                user=self.customer,
            ),
            1,
        )

        self.assertEqual(
            get_unread_message_count(
                user=self.provider_user,
            ),
            1,
        )

    def test_customer_can_get_own_conversation(self):
        from chat.services import (
            get_conversation_for_user,
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        result = get_conversation_for_user(
            conversation_id=conversation.pk,
            user=self.customer,
        )

        self.assertEqual(result, conversation)

    def test_provider_can_get_own_conversation(self):
        from chat.services import (
            get_conversation_for_user,
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.provider_user,
        )

        result = get_conversation_for_user(
            conversation_id=conversation.pk,
            user=self.provider_user,
        )

        self.assertEqual(result, conversation)

    def test_other_customer_cannot_get_conversation(self):
        from chat.services import (
            get_conversation_for_user,
            get_or_create_conversation_for_booking,
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        result = get_conversation_for_user(
            conversation_id=conversation.pk,
            user=self.other_customer,
        )

        self.assertIsNone(result)

    def test_other_provider_cannot_get_conversation(self):
        from chat.services import (
            get_conversation_for_user,
            get_or_create_conversation_for_booking,
        )

        other_provider_user = User.objects.create_user(
            username="other_provider",
            email="other_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        result_provider = ProviderProfile.objects.create(
            user=other_provider_user,
            business_name="Other Provider",
        )

        conversation = get_or_create_conversation_for_booking(
            booking=self.booking,
            user=self.customer,
        )

        result = get_conversation_for_user(
            conversation_id=conversation.pk,
            user=other_provider_user,
        )

        self.assertIsNone(result)

    def test_nonexistent_conversation_returns_none(self):
        from chat.services import get_conversation_for_user

        result = get_conversation_for_user(
            conversation_id=999999,
            user=self.customer,
        )

        self.assertIsNone(result)

    def test_provider_cannot_create_conversation_for_another_provider_booking(
        self,
    ):
        from django.core.exceptions import ValidationError

        from chat.services import (
            get_or_create_conversation_for_booking,
        )

        other_provider_user = User.objects.create_user(
            username="another_provider",
            email="another_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        other_provider = ProviderProfile.objects.create(
            user=other_provider_user,
            business_name="Another Provider",
        )

        with self.assertRaises(ValidationError):
            get_or_create_conversation_for_booking(
                booking=self.booking,
                user=other_provider_user,
            )


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    },
)
class ChatConsumerTests(TransactionTestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="consumer_customer",
            email="consumer_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider_user = User.objects.create_user(
            username="consumer_provider",
            email="consumer_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="consumer_other_customer",
            email="consumer_other_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Consumer Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="Consumer Category",
            slug="consumer-category",
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Consumer Service",
            description="Service for consumer tests.",
            price="100.00",
            duration_minutes=60,
            is_published=True,
        )

        self.booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date="2099-01-01",
            start_time="10:00",
            end_time="11:00",
            total_amount="100.00",
            status=Booking.Status.CONFIRMED,
        )

        self.conversation = Conversation.objects.create(
            booking=self.booking,
            customer=self.customer,
            provider=self.provider,
        )

    def test_unauthenticated_user_is_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.conversation.pk}/",
        )

        connected, _ = async_to_sync(
            communicator.connect,
        )()

        self.assertFalse(connected)

    def test_authorized_customer_can_connect(self):
        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )

            communicator.scope["user"] = self.customer

            connected, _ = await communicator.connect()

            self.assertTrue(connected)

            await communicator.disconnect()

        async_to_sync(test)()

    def test_authorized_provider_can_connect(self):
        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )

            communicator.scope["user"] = self.provider_user

            connected, _ = await communicator.connect()

            self.assertTrue(connected)

            await communicator.disconnect()

        async_to_sync(test)()

    def test_unrelated_user_is_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.conversation.pk}/",
        )

        communicator.scope["user"] = self.other_customer

        connected, _ = async_to_sync(
            communicator.connect,
        )()

        self.assertFalse(connected)

    def test_customer_can_send_message(self):
        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )

            communicator.scope["user"] = self.customer

            connected, _ = await communicator.connect()

            self.assertTrue(connected)

            await communicator.send_json_to(
                {
                    "content": "Hello provider",
                }
            )

            response = await communicator.receive_json_from()

            self.assertEqual(
                response["type"],
                "message",
            )

            self.assertEqual(
                response["content"],
                "Hello provider",
            )

            self.assertEqual(
                response["sender_id"],
                self.customer.id,
            )

            message_exists = await sync_to_async(
                Message.objects.filter(
                    conversation=self.conversation,
                    sender=self.customer,
                    content="Hello provider",
                ).exists
            )()

            self.assertTrue(message_exists)

            await communicator.disconnect()

        async_to_sync(test)()

    def test_empty_message_returns_error(self):
        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )

            communicator.scope["user"] = self.customer

            connected, _ = await communicator.connect()

            self.assertTrue(connected)

            await communicator.send_json_to(
                {
                    "content": "   ",
                }
            )

            response = await communicator.receive_json_from()

            self.assertEqual(
                response["type"],
                "error",
            )

            await communicator.disconnect()

        async_to_sync(test)()

    def test_invalid_json_returns_error(self):
        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )

            communicator.scope["user"] = self.customer

            connected, _ = await communicator.connect()

            self.assertTrue(connected)

            await communicator.send_to(
                text_data="not valid json",
            )

            response = await communicator.receive_json_from()

            self.assertEqual(
                response["type"],
                "error",
            )

            await communicator.disconnect()

        async_to_sync(test)()

    def test_multiple_messages_on_same_websocket_connection(self):
        async def test():
            comm_customer = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )
            comm_customer.scope["user"] = self.customer
            connected_cust, _ = await comm_customer.connect()
            self.assertTrue(connected_cust)

            comm_provider = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )
            comm_provider.scope["user"] = self.provider_user
            connected_prov, _ = await comm_provider.connect()
            self.assertTrue(connected_prov)

            # Send Message 1 from customer
            await comm_customer.send_json_to({"content": "Customer message 1"})
            msg1_cust = await comm_customer.receive_json_from()
            msg1_prov = await comm_provider.receive_json_from()
            self.assertEqual(msg1_cust["content"], "Customer message 1")
            self.assertEqual(msg1_prov["content"], "Customer message 1")

            # Send Message 2 from customer over the SAME connection
            await comm_customer.send_json_to({"content": "Customer message 2"})
            msg2_cust = await comm_customer.receive_json_from()
            msg2_prov = await comm_provider.receive_json_from()
            self.assertEqual(msg2_cust["content"], "Customer message 2")
            self.assertEqual(msg2_prov["content"], "Customer message 2")

            # Send Reply 1 from provider over the SAME connection
            await comm_provider.send_json_to({"content": "Provider reply 1"})
            reply1_cust = await comm_customer.receive_json_from()
            reply1_prov = await comm_provider.receive_json_from()
            self.assertEqual(reply1_cust["content"], "Provider reply 1")
            self.assertEqual(reply1_prov["content"], "Provider reply 1")

            # Send Reply 2 from provider over the SAME connection
            await comm_provider.send_json_to({"content": "Provider reply 2"})
            reply2_cust = await comm_customer.receive_json_from()
            reply2_prov = await comm_provider.receive_json_from()
            self.assertEqual(reply2_cust["content"], "Provider reply 2")
            self.assertEqual(reply2_prov["content"], "Provider reply 2")

            await comm_customer.disconnect()
            await comm_provider.disconnect()

        async_to_sync(test)()

    def test_four_sequential_messages_on_single_websocket_connection(self):
        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )
            communicator.scope["user"] = self.customer
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            for i in range(1, 5):
                content = f"Sequential message #{i}"
                await communicator.send_json_to({"content": content})
                response = await communicator.receive_json_from()
                self.assertEqual(response["type"], "message")
                self.assertEqual(response["content"], content)

            await communicator.disconnect()

        async_to_sync(test)()

    def test_consumer_resilient_to_group_send_failure(self):
        from unittest.mock import patch

        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )
            communicator.scope["user"] = self.customer
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            with patch(
                "channels.layers.InMemoryChannelLayer.group_send",
                side_effect=Exception("Redis connection error"),
            ):
                # Send message 1 when group_send fails
                await communicator.send_json_to({"content": "Resilient message 1"})

                # Assert NO fallback message returned (broadcast failed)
                self.assertTrue(await communicator.receive_nothing())

                # Verify message 1 is persisted
                msg1_exists = await sync_to_async(
                    Message.objects.filter(
                        conversation=self.conversation,
                        content="Resilient message 1",
                    ).exists
                )()
                self.assertTrue(msg1_exists)

            # Send message 2 on the SAME connection after group_send recovers
            await communicator.send_json_to({"content": "Resilient message 2"})
            res2 = await communicator.receive_json_from()
            self.assertEqual(res2["type"], "message")
            self.assertEqual(res2["content"], "Resilient message 2")

            # Verify message 2 is persisted
            msg2_exists = await sync_to_async(
                Message.objects.filter(
                    conversation=self.conversation,
                    content="Resilient message 2",
                ).exists
            )()
            self.assertTrue(msg2_exists)

            await communicator.disconnect()

        async_to_sync(test)()

    def test_consumer_rejects_connection_on_group_add_failure(self):
        from unittest.mock import patch

        async def test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversation.pk}/",
            )
            communicator.scope["user"] = self.customer

            with patch(
                "channels.layers.InMemoryChannelLayer.group_add",
                side_effect=Exception("Redis join error"),
            ):
                connected, _ = await communicator.connect()
                self.assertFalse(connected)

        async_to_sync(test)()



class ChatViewTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="view_customer",
            email="view_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider_user = User.objects.create_user(
            username="view_provider",
            email="view_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="view_other_customer",
            email="view_other_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.other_provider_user = User.objects.create_user(
            username="view_other_provider",
            email="view_other_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="View Provider",
        )

        self.other_provider = ProviderProfile.objects.create(
            user=self.other_provider_user,
            business_name="Other View Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="View Category",
            slug="view-category",
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="View Service",
            description="Service used for chat view tests.",
            price="100.00",
            duration_minutes=60,
            is_published=True,
        )

        self.other_service = Service.objects.create(
            provider=self.other_provider,
            category=self.category,
            title="Other View Service",
            description="Other service used for isolation tests.",
            price="200.00",
            duration_minutes=60,
            is_published=True,
        )

        self.booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date="2099-01-01",
            start_time="10:00",
            end_time="11:00",
            total_amount="100.00",
            status=Booking.Status.CONFIRMED,
        )

        self.other_booking = Booking.objects.create(
            customer=self.other_customer,
            service=self.other_service,
            provider=self.other_provider,
            booking_date="2099-01-02",
            start_time="12:00",
            end_time="13:00",
            total_amount="200.00",
            status=Booking.Status.CONFIRMED,
        )

        self.conversation = Conversation.objects.create(
            booking=self.booking,
            customer=self.customer,
            provider=self.provider,
        )

        self.other_conversation = Conversation.objects.create(
            booking=self.other_booking,
            customer=self.other_customer,
            provider=self.other_provider,
        )

    def test_conversation_list_requires_authentication(self):
        response = self.client.get(
            reverse("chat:list"),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_customer_can_access_conversation_list(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("chat:list"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            self.conversation.pk,
        )

    def test_provider_can_access_conversation_list(self):
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("chat:list"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            self.conversation.pk,
        )

    def test_customer_only_sees_own_conversations(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("chat:list"),
        )

        conversations = response.context["conversations"]

        self.assertEqual(
            list(conversations),
            [self.conversation],
        )

        self.assertNotIn(
            self.other_conversation,
            conversations,
        )

    def test_provider_only_sees_own_conversations(self):
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("chat:list"),
        )

        conversations = response.context["conversations"]

        self.assertEqual(
            list(conversations),
            [self.conversation],
        )

        self.assertNotIn(
            self.other_conversation,
            conversations,
        )

    def test_other_customer_does_not_see_conversation(self):
        self.client.force_login(self.other_customer)

        response = self.client.get(
            reverse("chat:list"),
        )

        conversations = response.context["conversations"]

        self.assertEqual(
            list(conversations),
            [self.other_conversation],
        )

        self.assertNotIn(
            self.conversation,
            conversations,
        )

    def test_conversation_detail_requires_authentication(self):
        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_customer_can_access_own_conversation(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["conversation"],
            self.conversation,
        )

    def test_provider_can_access_own_conversation(self):
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["conversation"],
            self.conversation,
        )

    def test_unrelated_customer_cannot_access_conversation(self):
        self.client.force_login(self.other_customer)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_unrelated_provider_cannot_access_conversation(self):
        self.client.force_login(self.other_provider_user)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_conversation_detail_loads_messages(self):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            content="Hello provider",
        )

        Message.objects.create(
            conversation=self.conversation,
            sender=self.provider_user,
            content="Hello customer",
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        messages = list(
            response.context["messages"],
        )

        self.assertEqual(
            len(messages),
            2,
        )

        self.assertEqual(
            messages[0].content,
            "Hello provider",
        )

        self.assertEqual(
            messages[1].content,
            "Hello customer",
        )

    def test_conversation_detail_marks_incoming_messages_as_read(self):
        incoming_message = Message.objects.create(
            conversation=self.conversation,
            sender=self.provider_user,
            content="Hello customer",
        )

        self.assertFalse(
            incoming_message.is_read,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        incoming_message.refresh_from_db()

        self.assertTrue(
            incoming_message.is_read,
        )

    def test_conversation_detail_does_not_mark_own_messages_as_read(self):
        own_message = Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            content="My message",
        )

        self.assertFalse(
            own_message.is_read,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        own_message.refresh_from_db()

        self.assertFalse(
            own_message.is_read,
        )

    def test_nonexistent_conversation_returns_404(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": 999999,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_conversation_detail_renders_websocket_elements(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "chat:conversation",
                kwargs={
                    "conversation_id": self.conversation.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'data-chat-root',
        )
        self.assertContains(
            response,
            f'data-conversation-id="{self.conversation.id}"',
        )
        self.assertContains(
            response,
            f'data-user-id="{self.customer.id}"',
        )
        self.assertContains(
            response,
            'id="chat-connection-status"',
        )
        self.assertContains(
            response,
            'id="chat-form"',
        )
        self.assertContains(
            response,
            'id="chat-message-input"',
        )
        self.assertContains(
            response,
            'js/chat.js',
        )

