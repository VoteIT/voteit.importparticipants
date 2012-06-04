from pyramid.i18n import TranslationStringFactory


VoteITImportParticipants = TranslationStringFactory('voteit.importparticipants')


def includeme(config):
    config.add_translation_dirs('voteit.importparticipants:locale/')
