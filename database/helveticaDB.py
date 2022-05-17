import disnake
import os
from disnake.ext import commands
from dotenv import load_dotenv
import pymongo

load_dotenv()

class dbClient:
	def __init__(self, database):
		self.client = pymongo.MongoClient(f"mongodb+srv://labyrinthadmin:{os.getenv('DBPSS')}@labyrinthdb.ng3ca.mongodb.net/helveticaDB?retryWrites=true&w=majority")
		if database in self.client.list_database_names():
			self.db = self.client[database]
		else:
			raise FileNotFoundError(f"'{database}' does not exist!")

def insertDoc(collection, document, isMany):
	if isMany:
		collection.insert_many([document])
	else:
		collection.insert_one(document)
	
def entExists(collection, key, value):
	if collection.find({key: value}) != None:
		return True
	else:
		return False