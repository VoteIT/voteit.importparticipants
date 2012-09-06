from pyramid.url import resource_url
from betahaus.viewcomponent import view_action

from voteit.core.security import MANAGE_GROUPS

from voteit.importparticipants import VoteITImportParticipants as _


@view_action('participants_menu', 'add_participants', title = _(u"Import participants"), link = "add_participants", permission = MANAGE_GROUPS)
def generic_menu_link(context, request, va, **kw):
    """ This is for simple menu items for the meeting root """
    api = kw['api']
    url = "%s%s" % (api.meeting_url, va.kwargs['link'])
    return """<li><a href="%s">%s</a></li>""" % (url, api.translate(va.title))