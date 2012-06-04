import colander
import deform
from betahaus.pyracont.decorators import schema_factory

from voteit.core import security

from voteit.importparticipants.validators import csv_participant_validator
from voteit.importparticipants import VoteITImportParticipants as _


@schema_factory('AddParticipantsSchema',
                title = _(u"Add meeting participants"),
                description = _(u"add_participants_schema_main_description",
                                default = u"""Import participants from CSV. If different participants should 
                                have different rights you should import one level of rights at a time. 
                                Normally users have discuss, propose and vote."""))
class AddParticipantsSchema(colander.Schema):
    roles = colander.SchemaNode(
        deform.Set(),
        title = _(u"Roles"),
        default = (security.ROLE_DISCUSS, security.ROLE_PROPOSE, security.ROLE_VOTER),
        description = _(u"add_participants_roles_description",
                        default = u"""A user can have more than one role. Note that to be able to propose,
                        discuss and vote you need respective role. This is selected by default. If you want
                        to add a user that can only view, select View and uncheck everything else."""),
        widget = deform.widget.CheckboxChoiceWidget(values=security.MEETING_ROLES,),
    )
    csv = colander.SchemaNode(colander.String(),
                                 title = _(u"add_participants_csv_title",
                                           default=u"CSV list of participants"),
                                 description = _(u"add_participants_csv_description",
                                                 default=u"""A semicolon separated csv, with the following columns 
                                                 prefered userid (mandatory); password (if left empty a random 
                                                 password will be generated); email (not mandatory, but recommended); 
                                                 firstname; lastname"""),
                                 widget = deform.widget.TextAreaWidget(rows=25, cols=75),
                                 validator = csv_participant_validator,
    )