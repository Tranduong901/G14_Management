class AuditLogMiddleware:
    """Middleware to capture request object in context if needed."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

