 # -*- coding: UTF-8 -*-

import unittest

from pyramid import testing
from webob.multidict import MultiDict

import colander

from voteit.core.testing_helpers import bootstrap_and_fixture
from voteit.core import security
from voteit.core.models.user import User
from voteit.core.models.meeting import Meeting


class AddParticipantsViewViewTests(unittest.TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
    
    @property
    def _cut(self):
        from voteit.importparticipants.views import AddParticipantsView
        return AddParticipantsView
    
    def _fixture(self):
        """ Normal context for this view is an agenda item. """
        from voteit.core.models.meeting import Meeting
        root = bootstrap_and_fixture(self.config)
        root['m'] = meeting = Meeting()
        return meeting

    def _load_vcs(self):
        self.config.registry.settings['default_timezone_name'] = "Europe/Stockholm"
        self.config.registry.settings['default_locale_name'] = 'sv'
        self.config.include('voteit.core.models.date_time_util')
        self.config.scan('voteit.core.views.components.main')
        self.config.scan('voteit.core.views.components.meeting')
        self.config.scan('voteit.core.views.components.head')
        self.config.scan('voteit.core.views.components.global_actions')
        self.config.scan('voteit.core.views.components.meeting_actions')
        self.config.scan('voteit.core.views.components.navigation')
        self.config.scan('voteit.core.views.components.help_actions')
        
    def test_add_participants(self):
        self.config.scan('voteit.importparticipants.schemas')
        self.config.include('voteit.core.models.flash_messages')
        self.config.testing_securitypolicy(userid='dummy',
                                           permissive=True)
        context = self._fixture()
        request = testing.DummyRequest()
        obj = self._cut(context, request)
        response = obj.add_participants()
        self.assertIn('form', response)
        
    def test_add_participants_cancel(self):
        self.config.scan('voteit.importparticipants.schemas')
        self.config.include('voteit.core.models.flash_messages')
        self.config.testing_securitypolicy(userid='dummy',
                                           permissive=True)
        context = self._fixture()
        request = testing.DummyRequest(post={'cancel': 'cancel'})
        obj = self._cut(context, request)
        response = obj.add_participants()
        self.assertEqual(response.location, 'http://example.com/m/')
        
    def test_add_participants_save(self):
        self.config.scan('voteit.importparticipants.schemas')
        self.config.include('voteit.core.models.flash_messages')
        self.config.testing_securitypolicy(userid='admin',
                                           permissive=True)
        self._load_vcs()
        context = self._fixture()
        request = testing.DummyRequest(post = MultiDict([('csv', 'user1;;user1@test.com;Dummy;User\n'),
                                                         ('__start__', 'roles:sequence'),
                                                         ('checkbox', 'role:Admin'),
                                                         ('__end__', 'roles:sequence'),
                                                         ('add', 'add')]))
        obj = self._cut(context, request)
        response = obj.add_participants()
        self.assertIn('1 participant added', response.body)
        
    def test_add_participants_validation_error(self):
        self.config.scan('voteit.importparticipants.schemas')
        self.config.include('voteit.core.models.flash_messages')
        self.config.testing_securitypolicy(userid='dummy',
                                           permissive=True)
        context = self._fixture()
        request = testing.DummyRequest(post = MultiDict([('csv', ';password1;user1@test.com;Dummy;User\n'),
                                                         ('__start__', 'roles:sequence'),
                                                         ('checkbox', 'role:Admin'),
                                                         ('__end__', 'roles:sequence'),
                                                         ('add', 'add')]))
        obj = self._cut(context, request)
        response = obj.add_participants()
        self.assertIn('form', response)
 
        
class CSVParticipantValidatorTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def _fixture(self):
        root = bootstrap_and_fixture(self.config)
        tester = User(password = 'tester',
                      creators = ['tester'],
                      first_name = u'Tester',
                      email = "tester@voteit.se",)
        root.users['tester'] = tester
        moderator = User(password = 'moderator',
                         creators = ['moderator'],
                         first_name = u'Moderator',
                         email = "moderator@voteit.se",)
        root.users['moderator'] = moderator
    
        meeting = Meeting()
        meeting.add_groups('tester', [security.ROLE_DISCUSS, security.ROLE_PROPOSE, security.ROLE_VOTER])
        meeting.add_groups('moderator', [security.ROLE_MODERATOR])
        root['meeting'] = meeting
        return meeting

    def _cut(self, context, api):
        from voteit.importparticipants.validators import CSVParticipantValidator
        return CSVParticipantValidator(context, api)
    
    def _api(self, context=None, request=None):
        from voteit.core.views.api import APIView
        context = context and context or testing.DummyResource()
        request = request and request or testing.DummyRequest()
        return APIView(context, request)

    def test_good(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        obj(node, u"user1;password1;user1@test.com;Dummy;User\n")

    def test_good_nonascii(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        obj(node, u"user1;password1;user1@test.com;Dömmy;Üser\n")
        
    def test_good_short(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        obj(node, u"user1")
        
    def test_no_username(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, u";password1;user1@test.com;Dummy;User\n")

    def test_bad_username(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, u"User1;password1;user1@test.com;Dummy;User\n")
        
    def test_not_unique_username(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, u"tester;password1;user1@test.com;Dummy;User\n")
        
    def test_bad_email(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, u"user1;password1;user1@test;Dummy;User\n")
        
    def test_not_unique_email(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, u"user1;tester@voteit.se;Dummy;User\n")

    def test_bad_password(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, u"user1;pwd;user1@test.com;Dummy;User\n")
    
    def test_bad_csv_wrong_delimiter(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, u"user1,pwd,user1@test.com,Dummy,User\n")