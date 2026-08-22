from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render

from .models import Conversation
from .services import (
    get_conversation_for_user,
    get_conversation_messages,
    mark_messages_as_read,
)


@login_required
def conversation_list(request):
    conversations = list(
        Conversation.objects.select_related(
            "booking",
            "booking__service",
            "booking__service__category",
            "customer",
            "provider",
            "provider__user",
        )
        .prefetch_related("messages")
        .filter(
            Q(customer=request.user) | Q(provider__user=request.user),
        )
        .order_by("-updated_at")
    )

    for c in conversations:
        c.latest_message = c.messages.order_by("-created_at").first()
        c.unread_count = (
            c.messages.filter(is_read=False).exclude(sender=request.user).count()
        )
        c.other_party_name = (
            c.provider.business_name
            if c.customer_id == request.user.id
            else (c.customer.get_full_name() or c.customer.username)
        )

    return render(
        request,
        "chat/conversations.html",
        {
            "conversations": conversations,
        },
    )


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_conversation_for_user(
        conversation_id=conversation_id,
        user=request.user,
    )

    if conversation is None:
        raise Http404

    messages = list(
        get_conversation_messages(
            conversation=conversation,
            user=request.user,
            limit=100,
        )
    )

    messages.reverse()

    mark_messages_as_read(
        conversation=conversation,
        user=request.user,
    )

    all_conversations = list(
        Conversation.objects.select_related(
            "booking",
            "booking__service",
            "booking__service__category",
            "customer",
            "provider",
            "provider__user",
        )
        .prefetch_related("messages")
        .filter(
            Q(customer=request.user) | Q(provider__user=request.user),
        )
        .order_by("-updated_at")
    )

    for c in all_conversations:
        c.latest_message = c.messages.order_by("-created_at").first()
        c.unread_count = (
            0
            if c.id == conversation.id
            else c.messages.filter(is_read=False).exclude(sender=request.user).count()
        )
        c.other_party_name = (
            c.provider.business_name
            if c.customer_id == request.user.id
            else (c.customer.get_full_name() or c.customer.username)
        )

    is_customer = conversation.customer_id == request.user.id
    other_party_name = (
        conversation.provider.business_name
        if is_customer
        else (conversation.customer.get_full_name() or conversation.customer.username)
    )

    return render(
        request,
        "chat/conversation.html",
        {
            "conversation": conversation,
            "chat_messages": messages,
            "conversations": all_conversations,
            "other_party_name": other_party_name,
            "is_customer": is_customer,
        },
    )


