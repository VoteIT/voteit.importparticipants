import unittest

import colander
from pyramid import testing
from pyramid.response import Response
from webob.multidict import MultiDict
from voteit.core.testing_helpers import bootstrap_and_fixture
from voteit.core import security
from voteit.core.models.user import User
from voteit.core.models.meeting import Meeting



class AddParticipantsViewTests(unittest.TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
    
    @property
    def _cut(self):
        from voteit.importparticipants.views import AddParticipantsView
        return AddParticipantsView
        
    def test_add_participants_render_form(self):
        self.config.scan('voteit.importparticipants.schemas')
        self.config.testing_securitypolicy(userid='dummy',
                                           permissive=True)
        context = _meeting_fixture(self.config)
        request = testing.DummyRequest()
        obj = self._cut(context, request)
        response = obj.add_participants()
        self.assertIn('form', response)

    def test_add_participants_cancel(self):
        self.config.scan('voteit.importparticipants.schemas')
        self.config.include('voteit.core.models.flash_messages')
        self.config.testing_securitypolicy(userid='dummy',
                                           permissive=True)
        context = _meeting_fixture(self.config)
        request = testing.DummyRequest(post={'cancel': 'cancel'})
        obj = self._cut(context, request)
        response = obj.add_participants()
        self.assertEqual(response.location, 'http://example.com/m/')

    def test_add_participants_save(self):
        self.config.scan('voteit.importparticipants.schemas')
        self.config.testing_securitypolicy(userid='admin',
                                           permissive=True)
        _tz_vc_fixture(self.config)
        context = _meeting_fixture(self.config)
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
        self.config.testing_securitypolicy(userid='dummy',
                                           permissive=True)
        context = _meeting_fixture(self.config)
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
        obj(node, "user1;password1;user1@test.com;Dummy;User\n")
        
    def test_good_short(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        obj(node, "user1")
        
    def test_no_username(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, ";password1;user1@test.com;Dummy;User\n")

    def test_bad_username(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, "User1;password1;user1@test.com;Dummy;User\n")
        
    def test_not_unique(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, "tester;password1;user1@test.com;Dummy;User\n")

    def test_bad_password(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, "user1;pwd;user1@test.com;Dummy;User\n")
    
    def test_bad_csv_wrong_delimiter(self):
        context = self._fixture()
        api = self._api(context)
        obj = self._cut(context, api)
        node = None
        self.assertRaises(colander.Invalid, obj, node, "user1,pwd,user1@test.com,Dummy,User\n")


class FunctionalTests(unittest.TestCase):
    """ Important note about responses - if something goes wrong,
        the view will return a dict and not a Response-object.
        The dict won't have a body, so the test might return error instead of fail.
    """
    def setUp(self):
        self.config = testing.setUp()
        _tz_vc_fixture(self.config)
        self.config.scan('voteit.importparticipants.schemas')

    def tearDown(self):
        testing.tearDown()
    
    @property
    def _cut(self):
        from voteit.importparticipants.views import AddParticipantsView
        return AddParticipantsView

    def _make_request(self, csv, roles=('role:Viewer',), add = 'add', **kw):
        params = []
        params.append(('csv', csv))
        params.append(('__start__', 'roles:sequence'))
        for role in roles:
            params.append(('checkbox', role))
        params.append(('__end__', 'roles:sequence'))
        params.append(('add', add))
        return testing.DummyRequest(post = MultiDict(params), **kw)

    def test_no_pw(self):
        self.config.testing_securitypolicy(userid='admin',
                                           permissive=True)
        _tz_vc_fixture(self.config)
        context = _meeting_fixture(self.config)
        csv = "user1;;user1@test.com;Dummy;User\n"
        request = self._make_request(csv)
        obj = self._cut(context, request)
        response = obj.add_participants()
        self.assertIsInstance(response, Response)
        self.assertIn('1 participant added', response.body)


def _meeting_fixture(config):
    from voteit.core.models.meeting import Meeting
    root = bootstrap_and_fixture(config)
    root['m'] = meeting = Meeting()
    return meeting

def _tz_vc_fixture(config):
    config.registry.settings['default_timezone_name'] = "Europe/Stockholm"
    config.registry.settings['default_locale_name'] = 'sv'
    config.include('voteit.core.models.date_time_util')
    config.include('voteit.core.models.flash_messages')
    config.scan('voteit.core.views.components')
