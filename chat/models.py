from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from bookings.models import Booking
from providers.models import ProviderProfile


class Conversation(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="conversation",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_conversations",
    )

    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name="conversations",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["customer", "-updated_at"],
            ),
            models.Index(
                fields=["provider", "-updated_at"],
            ),
        ]

    def clean(self):
        if self.booking_id:
            if self.customer_id != self.booking.customer_id:
                raise ValidationError(
                    {
                        "customer": (
                            "Conversation customer must match the booking customer."
                        )
                    }
                )

            if self.provider_id != self.booking.provider_id:
                raise ValidationError(
                    {
                        "provider": (
                            "Conversation provider must match the booking provider."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Conversation #{self.pk} - " f"Booking #{self.booking_id}"

class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )

    content = models.TextField()

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at"],
            ),
            models.Index(
                fields=["conversation", "is_read"],
            ),
        ]

    def clean(self):
        if not self.conversation_id or not self.sender_id:
            return

        if self.sender_id not in {
            self.conversation.customer_id,
            self.conversation.provider.user_id,
        }:
            raise ValidationError(
                {
                    "sender": (
                        "Message sender must be a participant "
                        "in the conversation."
                    )
                }
            )

        if not self.content.strip():
            raise ValidationError(
                {
                    "content": "Message content cannot be empty."
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Message #{self.pk} - "
            f"Conversation #{self.conversation_id}"
        )
