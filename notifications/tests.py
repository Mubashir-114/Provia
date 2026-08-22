from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import time

from notifications.models import Notification
from notifications.services import (
    create_notification,
    get_unread_notification_count,
    mark_notification_as_read,
)

User = get_user_model()


class NotificationListViewTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="testuser1",
            email="user1@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.user2 = User.objects.create_user(
            username="testuser2",
            email="user2@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

    def test_authenticated_user_can_access_notification_list(self):
        self.client.force_login(self.user1)
        url = reverse("notifications:list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "notifications/list.html")
        self.assertIn("page_obj", response.context)

    def test_unauthenticated_user_is_redirected_to_login(self):
        url = reverse("notifications:list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_user_sees_only_own_notifications(self):
        n1 = create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.BOOKING_CREATED,
            title="User 1 Notification",
            message="Message for User 1",
        )

        n2 = create_notification(
            recipient=self.user2,
            notification_type=Notification.NotificationType.PAYMENT_SUCCESS,
            title="User 2 Notification",
            message="Message for User 2",
        )

        self.client.force_login(self.user1)
        url = reverse("notifications:list")
        response = self.client.get(url)

        notifications_in_context = list(response.context["page_obj"])
        self.assertIn(n1, notifications_in_context)
        self.assertNotIn(n2, notifications_in_context)

    def test_notifications_are_ordered_newest_first(self):
        n1 = create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.BOOKING_CREATED,
            title="First Notification",
            message="Older notification message",
        )

        # Ensure created_at diff
        Notification.objects.filter(pk=n1.pk).update(
            created_at=timezone.now() - timezone.timedelta(hours=2)
        )

        n2 = create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.BOOKING_CONFIRMED,
            title="Second Notification",
            message="Newer notification message",
        )

        self.client.force_login(self.user1)
        url = reverse("notifications:list")
        response = self.client.get(url)

        page_items = list(response.context["page_obj"])
        self.assertEqual(page_items[0], n2)
        self.assertEqual(page_items[1], n1)

    def test_pagination_works(self):
        for i in range(15):
            create_notification(
                recipient=self.user1,
                notification_type=Notification.NotificationType.BOOKING_CREATED,
                title=f"Notification #{i + 1}",
                message=f"Message #{i + 1}",
            )

        self.client.force_login(self.user1)
        url = reverse("notifications:list")

        # Page 1 (10 items)
        response_p1 = self.client.get(url)
        self.assertEqual(response_p1.status_code, 200)
        page1_obj = response_p1.context["page_obj"]
        self.assertEqual(len(page1_obj), 10)
        self.assertTrue(page1_obj.has_next())

        # Page 2 (5 items)
        response_p2 = self.client.get(url + "?page=2")
        self.assertEqual(response_p2.status_code, 200)
        page2_obj = response_p2.context["page_obj"]
        self.assertEqual(len(page2_obj), 5)
        self.assertTrue(page2_obj.has_previous())

    def test_empty_notification_list_renders_successfully(self):
        self.client.force_login(self.user1)
        url = reverse("notifications:list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 0)
        self.assertContains(response, "No Notifications")

    def test_another_user_notification_never_appears(self):
        create_notification(
            recipient=self.user2,
            notification_type=Notification.NotificationType.REVIEW_RECEIVED,
            title="Private User 2 Notification",
            message="Secret message for user 2",
        )

        self.client.force_login(self.user1)
        url = reverse("notifications:list")
        response = self.client.get(url)

        self.assertEqual(len(response.context["page_obj"]), 0)
        self.assertNotContains(response, "Private User 2 Notification")


class NotificationUnreadCountTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="countuser1",
            email="countuser1@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )
        self.user2 = User.objects.create_user(
            username="countuser2",
            email="countuser2@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

    def test_returns_zero_when_no_unread_notifications(self):
        self.assertEqual(get_unread_notification_count(user=self.user1), 0)

    def test_counts_only_unread_notifications_for_user(self):
        read_notification = create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.BOOKING_CREATED,
            title="Read notification",
            message="Already read",
        )
        read_notification.is_read = True
        read_notification.save(update_fields=["is_read"])

        create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.BOOKING_CONFIRMED,
            title="Unread notification 1",
            message="Unread 1",
        )
        create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.PAYMENT_SUCCESS,
            title="Unread notification 2",
            message="Unread 2",
        )
        create_notification(
            recipient=self.user2,
            notification_type=Notification.NotificationType.REVIEW_RECEIVED,
            title="Other user's unread",
            message="Hidden",
        )

        self.assertEqual(get_unread_notification_count(user=self.user1), 2)

    def test_count_decreases_after_marking_notification_as_read(self):
        notification = create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.BOOKING_CREATED,
            title="Counts down",
            message="Before read",
        )

        self.assertEqual(get_unread_notification_count(user=self.user1), 1)

        mark_notification_as_read(notification=notification, user=self.user1)
        self.assertEqual(get_unread_notification_count(user=self.user1), 0)


class NotificationContextProcessorTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="contextuser",
            email="context@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

    def test_authenticated_user_has_unread_count_in_context(self):
        create_notification(
            recipient=self.user,
            notification_type=Notification.NotificationType.BOOKING_CREATED,
            title="Context count",
            message="Still unread",
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("notifications:list"))

        self.assertEqual(response.context["unread_notification_count"], 1)

    def test_anonymous_user_gets_zero_count_without_accessing_db(self):
        from notifications.context_processors import unread_notification_count
        request = type(
            "RequestStub",
            (),
            {"user": type("AnonymousStub", (), {"is_authenticated": False})()},
        )()

        self.assertEqual(unread_notification_count(request)["unread_notification_count"], 0)


class NotificationMarkAsReadTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.notification = create_notification(
            recipient=self.user1,
            notification_type=Notification.NotificationType.BOOKING_CREATED,
            title="Test Notification",
            message="Test Notification Message",
        )

    def test_authenticated_user_can_mark_own_unread_notification_as_read(self):
        self.client.force_login(self.user1)
        url = reverse("notifications:mark_as_read", args=[self.notification.pk])
        response = self.client.post(url)

        self.assertRedirects(response, reverse("notifications:list"))

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)

    def test_already_read_notification(self):
        # First mark as read
        mark_notification_as_read(notification=self.notification, user=self.user1)
        self.notification.refresh_from_db()
        initial_read_at = self.notification.read_at

        # Call service again
        result = mark_notification_as_read(notification=self.notification, user=self.user1)
        self.notification.refresh_from_db()

        self.assertTrue(self.notification.is_read)
        self.assertEqual(self.notification.read_at, initial_read_at)
        self.assertEqual(result.pk, self.notification.pk)

    def test_user_cannot_mark_another_user_notification_as_read(self):
        n2 = create_notification(
            recipient=self.user2,
            notification_type=Notification.NotificationType.PAYMENT_SUCCESS,
            title="User 2 Notification",
            message="Secret message",
        )

        self.client.force_login(self.user1)
        url = reverse("notifications:mark_as_read", args=[n2.pk])
        response = self.client.post(url)

        # Expected 404 because queryset is recipient-scoped
        self.assertEqual(response.status_code, 404)

        n2.refresh_from_db()
        self.assertFalse(n2.is_read)
        self.assertIsNone(n2.read_at)

        # Direct service permission check
        with self.assertRaises(ValidationError):
            mark_notification_as_read(notification=n2, user=self.user1)

    def test_get_request_cannot_mark_notification_as_read(self):
        self.client.force_login(self.user1)
        url = reverse("notifications:mark_as_read", args=[self.notification.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)
        self.assertIsNone(self.notification.read_at)

    def test_unauthenticated_user_cannot_mark_notification_as_read(self):
        url = reverse("notifications:mark_as_read", args=[self.notification.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)
        self.assertIsNone(self.notification.read_at)

    def test_successful_mark_as_read_redirects_to_notifications_list(self):
        self.client.force_login(self.user1)
        url = reverse("notifications:mark_as_read", args=[self.notification.pk])
        response = self.client.post(url)

        self.assertRedirects(response, reverse("notifications:list"))

