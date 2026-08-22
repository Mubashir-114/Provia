from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from bookings.models import Booking
from providers.models import ProviderProfile

from .models import Conversation, Message


def _get_provider_for_user(*, user):
    try:
        return ProviderProfile.objects.get(
            user=user,
        )
    except ProviderProfile.DoesNotExist:
        return None


def is_conversation_participant(*, conversation, user):
    if conversation.customer_id == user.id:
        return True

    return conversation.provider.user_id == user.id


def get_conversation_for_user(*, conversation_id, user):
    return (
        Conversation.objects
        .select_related(
            "booking",
            "customer",
            "provider",
            "provider__user",
            "booking__service",
        )
        .filter(
            pk=conversation_id,
        )
        .filter(
            Q(customer=user)
            | Q(provider__user=user),
        )
        .first()
    )


@transaction.atomic
def create_conversation(*, booking, customer, provider):
    if booking.customer_id != customer.id:
        raise ValidationError("Customer must own the booking.")

    if booking.provider_id != provider.id:
        raise ValidationError("Provider must own the booking.")

    conversation, _ = Conversation.objects.get_or_create(
        booking=booking,
        defaults={
            "customer": customer,
            "provider": provider,
        },
    )

    if (
        conversation.customer_id != customer.id
        or conversation.provider_id != provider.id
    ):
        raise ValidationError("Conversation participants do not match the booking.")

    return conversation


@transaction.atomic
def get_or_create_conversation_for_booking(
    *,
    booking,
    user,
):
    if booking.customer_id == user.id:
        customer = user
        provider = booking.provider

    elif booking.provider.user_id == user.id:
        customer = booking.customer
        provider = booking.provider

    else:
        raise ValidationError(
            "You do not have permission to access this booking conversation."
        )

    return create_conversation(
        booking=booking,
        customer=customer,
        provider=provider,
    )


@transaction.atomic
def create_message(
    *,
    conversation,
    sender,
    content,
):
    if not is_conversation_participant(
        conversation=conversation,
        user=sender,
    ):
        raise ValidationError("You are not a participant in this conversation.")

    if not content or not content.strip():
        raise ValidationError("Message content cannot be empty.")

    message = Message(
        conversation=conversation,
        sender=sender,
        content=content.strip(),
    )

    message.full_clean()
    message.save()

    Conversation.objects.filter(
        pk=conversation.pk,
    ).update(
        updated_at=message.created_at,
    )

    return message


def get_conversation_messages(
    *,
    conversation,
    user,
    limit=50,
):
    if not is_conversation_participant(
        conversation=conversation,
        user=user,
    ):
        raise ValidationError("You do not have permission to access this conversation.")

    return (
        Message.objects.filter(
            conversation=conversation,
        )
        .select_related(
            "sender",
        )
        .order_by(
            "-created_at",
        )[:limit]
    )


@transaction.atomic
def mark_messages_as_read(
    *,
    conversation,
    user,
):
    if not is_conversation_participant(
        conversation=conversation,
        user=user,
    ):
        raise ValidationError("You do not have permission to modify this conversation.")

    return (
        Message.objects.filter(
            conversation=conversation,
            is_read=False,
        )
        .exclude(
            sender=user,
        )
        .update(
            is_read=True,
        )
    )


def get_unread_message_count(*, user):
    return (
        Message.objects.filter(
            conversation__customer=user,
            is_read=False,
        )
        .exclude(
            sender=user,
        )
        .count()
        + Message.objects.filter(
            conversation__provider__user=user,
            is_read=False,
        )
        .exclude(
            sender=user,
        )
        .count()
    )


SYSTEM_COMPLETION_CONTENT = (
    "[SYSTEM] SERVICE_COMPLETED\n"
    "Your service request has been marked as completed."
)


@transaction.atomic
def create_system_message_for_booking_completion(*, booking):
    """
    Idempotently creates a system message in the conversation for a completed booking.
    Broadcasts the event over the channels group if available.
    """
    conversation, _ = Conversation.objects.get_or_create(
        booking=booking,
        defaults={
            "customer": booking.customer,
            "provider": booking.provider,
        },
    )

    existing = Message.objects.filter(
        conversation=conversation,
        content=SYSTEM_COMPLETION_CONTENT,
    ).exists()

    if existing:
        return None

    # Sender must be a participant per model clean rule: use provider.user
    message = Message(
        conversation=conversation,
        sender=booking.provider.user,
        content=SYSTEM_COMPLETION_CONTENT,
    )
    message.full_clean()
    message.save()

    Conversation.objects.filter(
        pk=conversation.pk,
    ).update(
        updated_at=message.created_at,
    )

    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"chat_conversation_{conversation.id}",
                {
                    "type": "chat.message",
                    "message_id": message.id,
                    "sender_id": message.sender_id,
                    "sender_username": "System",
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                },
            )
    except Exception:
        pass

    return message

