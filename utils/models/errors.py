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


class IntegerConversionError(LabyrinthianException):
    def __init__(self, msg):
        super().__init__(msg)
        
        
class PriceTooLowError(LabyrinthianException):
    def __init__(self, msg):
        super().__init__(msg)
