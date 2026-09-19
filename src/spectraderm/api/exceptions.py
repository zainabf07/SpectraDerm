class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code, self.message, self.status_code = code, message, status_code
        super().__init__(message)

class ServiceUnavailable(APIError):
    def __init__(self, message: str = "Requested service is unavailable."):
        super().__init__("SERVICE_UNAVAILABLE", message, 503)

class ArtifactUnavailable(APIError):
    """A scan reference exists but cannot be resolved to a usable local artifact."""
    def __init__(self, message: str = "The image artifact for this scan is unavailable."):
        super().__init__("IMAGE_ARTIFACT_UNAVAILABLE", message, 422)
