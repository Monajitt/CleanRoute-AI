from rest_framework.negotiation import DefaultContentNegotiation


class IgnoreClientContentNegotiation(DefaultContentNegotiation):
    """
    Guarantees pure JSON responses even when client/browser sends Accept: text/html.
    Prevents 406 NotAcceptable and BrowsableAPIRenderer 500 crashes on production API services.
    """
    def select_renderer(self, request, renderers, format_suffix=None):
        return (renderers[0], renderers[0].media_type)
