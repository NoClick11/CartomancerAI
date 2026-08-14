class ComfyUIError(Exception):
    """Base class for errors talking to the ComfyUI API."""


class ComfyUIConnectionError(ComfyUIError):
    """Could not reach the ComfyUI API at all."""


class ComfyUIRequestError(ComfyUIError):
    """The ComfyUI API returned an error response, or rejected the workflow."""


class ComfyUITimeoutError(ComfyUIError):
    """A queued prompt did not finish within the configured timeout."""


class ComfyUIExecutionError(ComfyUIError):
    """ComfyUI reported an execution error for a queued prompt."""
