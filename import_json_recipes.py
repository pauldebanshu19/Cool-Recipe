import os
import pymongo
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection URI and database name from environment variables
# Falls back to default values if not set
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:12404/?directConnection=true")
MONGO_DB = os.getenv("MONGO_DB", "cookbook")

try:
    # Establish connection to MongoDB
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    print(db)
    
    # Open and load the JSON file containing recipe data
    with open("bigger_sample.json", "r") as f:
        recipes_data = json.load(f)
    
    # Iterate through each recipe in the loaded data
    for recipe in recipes_data:
        try:
            # Create a document with selected fields from the recipe
            recipe_doc = {
                "title": recipe["title"],
                "ingredients": recipe["ingredients"],
                "instructions": recipe["instructions"],
                "embedding_ingredients": recipe["embedding_ingredients"],
                "features": recipe["features"],
            }
            print(recipe_doc)
            
            # Insert the recipe document into the 'recipes' collection
            db.recipes.insert_one(recipe_doc)
        except Exception as e:
            # Handle errors for individual recipe insertion
            print(f"Error inserting recipe: {e}")
    
    # Print success message with count of inserted recipes
    print(f"Inserted {len(recipes_data)} recipes into MongoDB")

except pymongo.errors.ConnectionFailure as e:
    # Handle MongoDB connection failures
    print(f"Error connecting to MongoDB: {e}")
except Exception as e:
    # Handle any other exceptions during the import process
    print(f"Error inserting recipes: {e}")