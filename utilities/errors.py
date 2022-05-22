class LabyrinthianException(Exception):
	def __init__(self, msg):
		super().__init__(msg)

class noValidTemplate(LabyrinthianException):
	def __init__(self):
		super().__init__("This is not a valid template")

class ExternalImportError(LabyrinthianException):
	def __init__(self, msg):
		super().__init__(msg)


class SelectionException(LabyrinthianException):
    """A base exception for message awaiting exceptions to stem from."""

    pass


class NoSelectionElements(SelectionException):
    """Raised when get_selection() is called with no choices."""

    def __init__(self, msg=None):
        super().__init__(msg or "There are no choices to select from.")


class SelectionCancelled(SelectionException):
    """Raised when get_selection() is cancelled or times out."""

    def __init__(self):
        super().__init__("Selection timed out or was cancelled.")