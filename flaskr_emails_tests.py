import unittest
import json
import datetime

from flaskr_tests import FlaskrWithMongoTest, assert_mailgun
from unittest.mock import patch
from flaskr_users_tests import TEST_CONFIRMED_USER_IN_DB as CONFIRMED_USER_IN_DB, \
    TEST_NOT_CONFIRMED_USER_IN_DB as NOT_CONFIRMED_USER_IN_DB, EMAIL_ADDRESS as USER_EMAIL_ADDRESS

FIRST_MAIL_SUBJECT = "Introduction to test workshop"
SECOND_MAIL_SUBJECT = "Link to repository"

WORKSHOP_ID = "test_workshop"

CURRENT_DATE = datetime.datetime(2007, 12, 6, 16, 29, 43, 79043)

WORKSHOP_IN_DB = {
    "workshopId": WORKSHOP_ID,
    "mentors": [
        "jan@kowalski.pl",
        "adam@nowak.pl"
    ],
    "users": [
        "user@example.com"
    ],
    "emails": [
        {"emailId": 1, "subject": FIRST_MAIL_SUBJECT, "text": "text", "date": CURRENT_DATE}
    ]
}

EMAILS = {"emails": [{"subject": FIRST_MAIL_SUBJECT, "text": "text", "date": "Thu, 06 Dec 2007 16:29:43 GMT"}]}

REGISTER_EMAIL_REQUEST = """{
            "subject": "%s",
            "text": "text"
        }""" % SECOND_MAIL_SUBJECT


class EmailsEndpointTest(FlaskrWithMongoTest, unittest.TestCase):

    @patch('mailgunresource.requests')
    def test_should_get_list_of_emails_for_specified_workshops(self, requests_mock):
        # Given a database with one workshop
        self.db.workshops.insert(WORKSHOP_IN_DB)

        # When request
        rv = self.get_one_workshop()

        # Correct response should be returned
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(rv.data.decode('UTF-8')), EMAILS)

    @patch('mailgunresource.requests')
    def test_should_return_404_if_workshop_not_found(self, requests_mock):
        # Given an empty database

        # When request
        rv = self.get_one_workshop()

        # Correct response should be returned
        self.assertEqual(rv.status_code, 404)

    @patch('mailgunresource.requests')
    def test_should_save_user_registration_in_database_when_user_selects_workshop(self, requests_mock):
        # Given:
        self.user_and_workshop_exists()

        # When:
        self.user_selects_workshop()

        # Then
        workshop = self.db.workshops.find_one()
        self.assertIn(USER_EMAIL_ADDRESS, workshop['users'])

    @patch('mailgunresource.requests')
    def test_should_fail_to_save_user_registration_when_not_confirmed_user_selects_workshop(self, requests_mock):
        # Given:
        self.user_and_workshop_exists(user=NOT_CONFIRMED_USER_IN_DB)

        # When:
        response = self.user_selects_workshop()

        # Then
        self.assertEqual(response.status_code, 412)

    @patch('mailgunresource.requests')
    def test_should_save_user_registration_once_if_when_user_selected_workshop_multipe_times(self, requests_mock):
        # Given:
        self.user_and_workshop_exists(user=CONFIRMED_USER_IN_DB)
        self.user_selects_workshop()

        # When:
        self.user_selects_workshop()

        # Then
        self.assertEqual(2, len(self.db.workshops.find_one()['users']))

    @patch('mailgunresource.requests')
    def test_should_send_emails_for_workshop_when_user_selects_workshop(self, requests_mock):
        # Given:
        self.user_and_workshop_exists()

        # When:
        self.user_selects_workshop()

        # Then
        assert_mailgun(requests_mock, subject=FIRST_MAIL_SUBJECT)

    @patch('mailgunresource.requests')
    def test_should_not_send_emails_already_sent_to_this_user(self, requests_mock):
        # Given:
        self.user_and_workshop_exists()
        self.user_selects_workshop()
        self.user_deselects_workshop()
        self.new_workshop_email_is_registered()

        # When:
        self.user_selects_workshop()

        # Then
        self.assertEqual(2, requests_mock.post.call_count)
        assert_mailgun(requests_mock, subject=SECOND_MAIL_SUBJECT)

    @patch('mailgunresource.requests')
    def test_should_save_new_email_in_workshop(self, requests_mock):
        # Given:
        self.user_and_workshop_exists()

        # When:
        self.new_workshop_email_is_registered()

        # Then
        workshop = self.db.workshops.find_one()
        self.assertEqual(2, len(workshop['emails']))
        self.assertEqual(SECOND_MAIL_SUBJECT, workshop['emails'][1]['subject'])
        self.assertIsNotNone(workshop['emails'][1]['emailId'])
        self.assertIsNotNone(workshop['emails'][1]['date'])


    @patch('mailgunresource.requests')
    def test_should_unregister_user_from_workshop(self, requests_mock):
        # Given:
        self.user_and_workshop_exists()
        self.user_selects_workshop()

        # When:
        self.user_deselects_workshop()

        # Then
        workshop = self.db.workshops.find_one()
        self.assertNotIn(USER_EMAIL_ADDRESS, workshop['users'])

    def user_and_workshop_exists(self, user=CONFIRMED_USER_IN_DB, workshop=WORKSHOP_IN_DB):
        self.db.users.insert(user)
        self.db.workshops.insert(workshop)

    def user_selects_workshop(self):
        return self.app.put('/emails/%s/%s' % (WORKSHOP_ID, USER_EMAIL_ADDRESS))

    def user_deselects_workshop(self):
        return self.app.delete('/emails/%s/%s' % (WORKSHOP_ID, USER_EMAIL_ADDRESS))

    def new_workshop_email_is_registered(self):
        return self.app.post('/emails/%s' % WORKSHOP_ID, data=REGISTER_EMAIL_REQUEST, content_type="application/json")

    def get_one_workshop(self):
        rv = self.app.get('/emails/%s' % WORKSHOP_ID, content_type="application/json")
        return rv


if __name__ == '__main__':
    unittest.main()
