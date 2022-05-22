class LabyrinthianException(Exception):
	def __init__(self, msg):
		super().__init__(msg)

class noValidTemplate(LabyrinthianException):
	def __init__(self):
		super().__init__("This is not a valid template")

class ExternalImportError(LabyrinthianException):
	def __init__(self, msg):
		super().__init__(msg)