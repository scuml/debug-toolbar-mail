import io
import pickle
import sys
import unittest

import debug_toolbar
from debug_toolbar.toolbar import DebugToolbar
from django.core import mail
from django.test.client import RequestFactory
from mail_panel.backend import MailToolbarBackend, MailToolbarBackendEmail
from mail_panel.panels import MailToolbarPanel
from mail_panel.utils import clear_outbox

rf = RequestFactory()
get_request = rf.get("/hello/")
post_request = rf.post("/submit/", {"foo": "bar"})


class ToolbarSuite(unittest.TestCase):
    def setUp(self):
        debug_toolbar_version = debug_toolbar.VERSION

        self.request = rf.post("/submit/", {"foo": "bar"})

        # django-debug-toolbar 1.x take 1 argument, 2.x take 2 arguments
        if debug_toolbar_version < "2.0":
            self.toolbar = DebugToolbar(self.request)
            self.panel_args = (self.toolbar,)
        else:
            self.toolbar = DebugToolbar(self.request, None)
            self.panel_args = (self.toolbar, None)

    @staticmethod
    def get_fake_message(
        subject=None,
        to=None,
        cc=None,
        bcc=None,
        reply_to=None,
        from_email=None,
        body=None,
        alternatives=None,
        headers=None,
    ):
        # TODO Use Faker (https://github.com/joke2k/faker)
        return mail.EmailMultiAlternatives(
            subject=subject or "fake subject",
            to=to or ["to@fake.com"],
            cc=cc or ["cc@fake.com"],
            bcc=bcc or ["bcc@fake.com"],
            reply_to=reply_to or ["reply_to@fake.com"],
            from_email=from_email or "from_email@fake.com",
            body=body or "body",
            alternatives=alternatives or [("<b>HTML</b> body", "text/html")],
            headers=headers or {"X-MyHeader": "myheader"},
        )

    def test_panel(self):
        """
        General 'does it run' test.
        """
        p = MailToolbarPanel(*self.panel_args)
        self.assertEqual(p.toolbar, self.toolbar)

    def test_generate_stats(self):

        clear_outbox()

        p = MailToolbarPanel(*self.panel_args)

        # Test empty indox
        p.generate_stats(None, None)
        self.assertEqual(len(p.mail_list), 0)

        # Test inbox with one message
        fake_message = self.get_fake_message()
        backend = MailToolbarBackend()
        backend.send_messages([fake_message])

        p.generate_stats(None, None)
        self.assertEqual(len(p.mail_list), 1)

    def test_process_response(self):
        p = MailToolbarPanel(*self.panel_args)
        p.process_response(None, None)

    def test_backend_email(self):
        fake_message = self.get_fake_message()

        # Create MailToolbarBackendEmail from fake EmailMultiAlternatives
        message = MailToolbarBackendEmail(fake_message)

        # Check email fields
        self.assertEqual(message.subject, fake_message.subject)
        self.assertEqual(message.to, fake_message.to)
        self.assertEqual(message.cc, fake_message.cc)
        self.assertEqual(message.bcc, fake_message.bcc)
        self.assertEqual(message.reply_to, fake_message.reply_to)
        self.assertEqual(message.from_email, fake_message.from_email)
        self.assertEqual(message.body, fake_message.body)
        self.assertEqual(message.alternatives, fake_message.alternatives)
        self.assertEqual(message.extra_headers, fake_message.extra_headers)

        # Check extra fields
        self.assertIsNotNone(message.id)
        self.assertIsNotNone(message.date_sent)
        self.assertFalse(message.read)

    def test_backend(self):
        # Test with simple message
        fake_message = self.get_fake_message()

        backend = MailToolbarBackend()
        backend.send_messages([fake_message])

        # Test with not serializable message
        fake_message = self.get_fake_message()
        fake_message.not_serializable_field = io.BufferedReader(
            io.StringIO(u"initial text data")
        )

        # BufferedReader is serializable in Python2
        if sys.version_info[0] >= 3:
            with self.assertRaises(TypeError):
                pickle.dumps(fake_message, pickle.HIGHEST_PROTOCOL)

        backend = MailToolbarBackend()
        backend.send_messages([fake_message])
