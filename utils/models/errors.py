class LabyrinthianException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class ExternalImportError(LabyrinthianException):
    def __init__(self, msg):
        super().__init__(msg)


class FormTimeoutError(LabyrinthianException):
    def __init__(self):
        super().__init__(
            "It seems your form timed out, if you see this message, it is most likely because you took too long to fill out a form."
        )


class FormInvalidInputError(LabyrinthianException):
    def __init__(self, msg):
        super().__init__(msg)


class IntegerConversionError(LabyrinthianException):
    def __init__(self, msg):
        super().__init__(msg)


class PriceTooLowError(LabyrinthianException):
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


class MissingCharacterDataError(LabyrinthianException):
    """Raised when a database call for character data returns nothing."""

    def __init__(self):
        super().__init__("It seems that characters data is missing, or lost.")
