import csv
import random

from StringIO import StringIO

import colander
from deform import Form
from deform.exception import ValidationFailure
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.url import resource_url
from pyramid.renderers import render
from pyramid.response import Response
from betahaus.pyracont.factories import createContent
from betahaus.pyracont.factories import createSchema

from voteit.core import security
from voteit.core.views.base_view import BaseView
from voteit.core.models.interfaces import IMeeting
from voteit.core.models.schemas import add_csrf_token
from voteit.core.models.schemas import button_add
from voteit.core.models.schemas import button_cancel
from voteit.core.helpers import generate_slug

from voteit.importparticipants import VoteITImportParticipants as _


_PW_CHARS = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'


class AddParticipantsView(BaseView):
    
    def _generate_password(self):
        return ''.join(random.choice(_PW_CHARS) for x in range(10))
    
    def _import_participants(self, input, roles):
        # the value shoud be in unicode from colander and csv wants ascii or utf-8
        input = input.encode('UTF-8')
        participants = csv.reader(StringIO(input), delimiter=';', quotechar='"')
        output = []
        for row in participants:
            appstruct = {}
            userid = unicode(row[0])
            if len(row) > 1 and row[1]:
                appstruct['password'] = unicode(row[1])
            else:
                appstruct['password'] = self._generate_password()
            if len(row) > 2 and row[2]:
                appstruct['email'] = unicode(row[2])
            else:
                appstruct['email'] = u""
            if len(row) > 3 and row[3]:
                appstruct['first_name'] = row[3].decode('UTF-8')
            else:
                appstruct['first_name'] = u""
            if len(row) > 4 and row[4]:
                appstruct['last_name'] = row[4].decode('UTF-8')
            else:
                appstruct['last_name'] = u""
            
            # add user to root
            from betahaus.pyracont import generate_slug
            userid = generate_slug(self.api.root.users, userid)
            user = createContent('User', creators=[userid], **appstruct)
            self.api.root.users[userid] = user
            
            # add user to meeting
            self.context.add_groups(userid, roles, event = True)
            
            appstruct['userid'] = userid
            output.append(appstruct)
            
        return output
    
    @view_config(name="add_participants", context=IMeeting, renderer="voteit.core.views:templates/base_edit.pt", permission=security.MANAGE_GROUPS)
    def add_participants(self):
        """ Add participants to this meeting.
            Renders a form where you can paste a csv with the users and select which roles they
            should have once they register. When the form is submitted, a list of userids and 
            passwords is displayed 
        """
        self.response['title'] = _(u"Add meeting participants")

        post = self.request.POST
        if 'cancel' in post:
            self.api.flash_messages.add(_(u"Canceled"))
            url = resource_url(self.context, self.request)
            return HTTPFound(location=url)

        schema = createSchema('AddParticipantsSchema').bind(context=self.context, request=self.request, api=self.api)
        add_csrf_token(self.context, self.request, schema)

        form = Form(schema, buttons=(button_add, button_cancel))
        self.api.register_form_resources(form)

        if 'add' in post:
            controls = post.items()
            try:
                appstruct = form.validate(controls)
            except ValidationFailure, e:
                self.response['form'] = e.render()
                return self.response
            
            roles = appstruct['roles']

            output = self._import_participants(appstruct['csv'], roles)
                          
            msg = _('added_participants_text', default=u"Successfully added ${participant_count} participants", mapping={'participant_count':len(output)} )
            self.api.flash_messages.add(msg)
            
            self.response['heading'] = "%s %s" % (len(output), self.api.pluralize(self.api.translate(_("participant added")), self.api.translate(_("participants added")), len(output)))
            self.response['participants'] = output
            return Response(render("add_participants.pt", self.response, request = self.request))


        #No action - Render add form
        self.response['form'] = form.render()
        return self.response