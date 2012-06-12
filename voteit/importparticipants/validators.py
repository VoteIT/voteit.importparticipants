import re
import colander
import csv

from StringIO import StringIO
from pyramid.traversal import find_root

from voteit.core.validators import html_string_validator
from voteit.core.validators import password_validation
from voteit.core.validators import UniqueEmail
from voteit.core.validators import NEW_USERID_PATTERN

from voteit.importparticipants import VoteITImportParticipants as _


@colander.deferred
def csv_participant_validator(node, kw):
    context = kw['context']
    api = kw['api']
    return CSVParticipantValidator(context, api)
    
class CSVParticipantValidator(object):
    """
        validates that input is a valid csv file
    """
    def __init__(self, context, api):
        self.context = context
        self.api = api
    
    def __call__(self, node, value):
        html_string_validator(node, value)
        
        users = find_root(self.context).users
        
        nouserid = set()
        invalid = set()
        notunique = set()
        email = set()
        password = set()
        row_count = 0
        # the value shoud be in unicode from colander and csv wants ascii or utf-8 
        value = value.encode('UTF-8')
        data = csv.reader(StringIO(value), delimiter=';', quotechar='"')
        try:
            for row in data:
                row_count = row_count + 1
                if not row[0]:
                    nouserid.add("%s" % row_count) 
                if row[0] and not NEW_USERID_PATTERN.match(row[0]):
                    invalid.add(row[0])
                if row[0] in users:
                    notunique.add(row[0])
                # only validate email if there is an email
                if len(row) > 2 and row[2]:
                    try:
                        UniqueEmail(self.context)(node, row[2])
                    except colander.Invalid:
                        email.add("%s" % row[2])
                # only validate password if there is a password
                if len(row) > 1 and row[1]:
                    try:
                        password_validation(node, row[1])
                    except colander.Invalid:
                        password.add("%s" % row_count)
        except IndexError:
            raise colander.Invalid(node, _('add_participants_invalid_csv',
                                           default=u"""CSV file is not valid, make sure at least userid is specified on 
                                           each row and field delimiter is ; and text delimiter is " """))

        msgs = []
        if nouserid: 
            msgs.append(self.api.translate(_('add_participants_no_userid_error',
                           default=u"The following rows had no userid specified: ${nouserid}.",
                           mapping={'nouserid': nouserid})))
        if invalid: 
            invalid = ", ".join(invalid)
            msgs.append(self.api.translate(_('add_participants_userid_char_error',
                         default=u"The following userids is invalid: ${invalid}. UserID must be 3-30 chars, start with lowercase a-z and only contain lowercase a-z, numbers, minus and underscore.",
                         mapping={'invalid': invalid})))
        if notunique: 
            notunique = ", ".join(notunique)
            msgs.append(self.api.translate(_('add_participants_notunique_error',
                    default=u"The following userids is already registered: ${notunique}.",
                    mapping={'notunique': notunique})))
        if email: 
            email = ", ".join(email)
            msgs.append(self.api.translate(_('add_participants_email_error',
                    default=u"The following email addresses is invalid or already registered: ${email}.",
                    mapping={'email': email})))
        if password: 
            password = ", ".join(password)
            msgs.append(self.api.translate(_('add_participants_password_error',
                    default=u"The following rows has invalid password: ${password}. Password must be between 6 and 100 characters",
                    mapping={'password': password})))
            
        if msgs:
            msg = "\n".join(msgs)
            raise colander.Invalid(node, msg)
