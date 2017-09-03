class AccountLinkingButton(object):

    button_type = 'account_link'

    def __init__(self, url):
        self.url = url

    def to_dict(self):
        serialised = {
            'type': self.button_type,
            'url': self.url
        }
        return serialised
