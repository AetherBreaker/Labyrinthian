import disnake
import os
from disnake.ext import commands
from dotenv import load_dotenv
import pymongo

load_dotenv()

class dbClient:
	def __init__(self, database, collection):
		c = pymongo.MongoClient(f"mongodb+srv://labyrinthadmin:{os.getenv('DBPSS')}@labyrinthdb.ng3ca.mongodb.net/helveticaDB?retryWrites=true&w=majority")
		self.client = c
		if database in c.list_database_names():
			self.db = self.client[database]
		else:
			raise FileNotFoundError(f"'{database}' does not exist!")
		if collection in self.db.list_collection_names():
			self.collection = self.db[collection]
		else:
			raise FileNotFoundError(f"'{collection}' does not exist in the database!")

	def insertDoc(self, collectionName, document, isMany):
		if isMany:
			self.collection.insert_many([document])
		else:
			self.collection.insert_one(document)
	
	def entExists(self, key, value):
		if self.collection.find({key: value}) != None:
			return True
		else:
			return False