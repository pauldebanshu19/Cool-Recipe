import os
import time

import pymongo
import voyageai
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:12404/?directConnection=true")
MONGO_DB = os.getenv("MONGO_DB", "cookbook")


# MongoDB connection
try:
    # Connect to MongoDB
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db["recipes"]

    # Initialize Voyage AI client
    # This automatically uses the VOYAGE_API_KEY environment variable
    vo = voyageai.Client()

    # Find documents without voyage_embedding
    query = {"voyage_embedding": {"$exists": False}}
    documents_without_embeddings = list(collection.find(query))

    print(
        f"Found {len(documents_without_embeddings)} documents without Voyage embeddings"
    )

    # Add embeddings to documents that don't have them
    for doc in tqdm(documents_without_embeddings, desc="Adding embeddings"):
        # Prepare content for embedding - just the title and the ingredients
        content_to_embed = (
            f"{doc['title']}. Ingredients: {doc['embedding_ingredients']}"
        )

        # Get embedding from Voyage AI
        try:
            embedding_result = vo.embed(
                [content_to_embed],
                model="voyage-lite-01-instruct",
                input_type="document",
            )
            embedding = embedding_result.embeddings[0]

            # Update document with embedding
            collection.update_one(
                {"_id": doc["_id"]}, {"$set": {"voyage_embedding": embedding}}
            )

            # Add a small delay to avoid hitting rate limits
            time.sleep(25)

        except Exception as e:
            print(f"Error generating embedding for recipe '{doc['title']}': {e}")

    print(
        f"Successfully added embeddings to {len(documents_without_embeddings)} documents"
    )

except pymongo.errors.ConnectionFailure as e:
    print(f"Error connecting to MongoDB: {e}")
except Exception as e:
    print(f"Error processing documents: {e}")
