import os

import voyageai
from anthropic import Anthropic
from bson import ObjectId
from bson.errors import InvalidId
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from dotenv import load_dotenv
from pymongo import MongoClient
import json

from .models import Recipe

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def index(request):
    return render(request, "index.html", {"message": "Recipes App"})


def top_recipes(request):
    recipes = Recipe.objects.all().order_by("title")[:20]

    return render(request, "top_recipes.html", {"recipes": recipes})


def recipe_detail(request, recipe_id):
    """
    Display a recipe by its MongoDB ObjectId

    Args:
        request: Django request object
        recipe_id: String representation of the MongoDB ObjectId
    """
    # Convert string ID to MongoDB ObjectId
    try:
        object_id = ObjectId(recipe_id)
    except InvalidId:
        raise Http404(f"Invalid recipe ID format: {recipe_id}")

    # Get the recipe or return 404
    recipe = get_object_or_404(Recipe, id=object_id)

    # Create context with all needed data
    context = {"recipe": recipe}

    return render(request, "recipe_detail.html", context)


def recipe_statistics(request):
    # Define the aggregation pipeline
    pipeline = [
        # Stage 1: Extract cuisine from the features subdocument
        {"$project": {"_id": 1, "cuisine": "$features.cuisine"}},
        # Stage 2: Group by cuisine and count occurrences
        {"$group": {"_id": "$cuisine", "count": {"$sum": 1}}},
        # Stage 3: Sort by count in descending order
        {"$sort": {"count": -1}},
        # Stage 4: Reshape the output for better readability
        {
            "$project": {
                "_id": 1,
                "cuisine": {"$ifNull": ["$_id", "Unspecified"]},
                "count": 1,
            }
        },
    ]

    stats = Recipe.objects.raw_aggregate(pipeline)
    result = list(stats)

    return render(
        request,
        "statistics.html",
        {"cuisine_stats": result},
    )


def perform_vector_search(query_text, limit=10, num_candidates=None):
    if num_candidates is None:
        num_candidates = limit * 3

    try:
        # Generate embedding for the search query
        vo = voyageai.Client()  # Uses VOYAGE_API_KEY from environment
        query_embedding = vo.embed(
            [query_text], model="voyage-lite-01-instruct", input_type="query"
        ).embeddings[0]

        # Use Django's raw_aggregate to perform vector search
        results = Recipe.objects.raw_aggregate(
            [
                {
                    "$vectorSearch": {
                        "index": "recipe_vector_index",
                        "path": "voyage_embedding",
                        "queryVector": query_embedding,
                        "numCandidates": num_candidates,
                        "limit": limit,
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "ingredients": 1,
                        "instructions": 1,
                        "features": 1,
                        "score": {"$meta": "vectorSearchScore"},
                    }
                },
            ]
        )

        # Format the results - accessing attributes directly
        recipes = []
        for recipe in results:
            try:
                # Try direct attribute access first
                recipe_dict = {
                    "id": str(recipe.id),
                    "title": recipe.title,
                    "ingredients": recipe.ingredients,
                    "instructions": getattr(recipe, "instructions", ""),
                    "features": getattr(recipe, "features", {}),
                    "similarity_score": getattr(recipe, "score", 0),
                }
                recipes.append(recipe_dict)
            except Exception as e:
                print(f"Error formatting recipe: {str(e)}")
        return recipes

    except Exception as e:
        print(f"Error in vector search: {str(e)}")
        return []


def ingredient_vector_search(request):
    """
    View for searching recipes by ingredients using vector search
    """
    query = request.GET.get("query", "")
    results = []

    if query:
        ingredient_query = f"Ingredients: {query}"
        results = perform_vector_search(ingredient_query, limit=10)

    context = {"query": query, "results": results}
    return render(request, "vector_search.html", context)


def fuzzy_search(request):
    """
    Simple function-based view for fuzzy search using MongoDB Atlas Search
    """
    query = request.GET.get("q", "")
    recipes = []

    if query:
        # Get MongoDB connection details from environment variables
        MONGO_URI = os.getenv(
            "MONGO_URI", "mongodb://localhost:12404/?directConnection=true"
        )
        MONGO_DB = os.getenv("MONGO_DB", "cookbook")

        # Connect to MongoDB directly for Atlas Search
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db["recipes"]

        # Build the fuzzy search pipeline
        pipeline = [
            {
                "$search": {
                    "index": "default",  # Use the default index
                    "compound": {
                        "should": [
                            {
                                "text": {
                                    "query": query,
                                    "path": "title",
                                    "fuzzy": {"maxEdits": 2, "prefixLength": 2},
                                    "score": {"boost": {"value": 5}},
                                }
                            },
                            {
                                "text": {
                                    "query": query,
                                    "path": "ingredients",
                                    "fuzzy": {"maxEdits": 2, "prefixLength": 1},
                                    "score": {"boost": {"value": 3}},
                                }
                            },
                            {
                                "text": {
                                    "query": query,
                                    "path": "instructions",
                                    "fuzzy": {"maxEdits": 2, "prefixLength": 1},
                                }
                            },
                        ]
                    },
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "ingredients": 1,
                    "instructions": 1,
                    "features": 1,
                    "score": {"$meta": "searchScore"},
                }
            },
            {"$sort": {"score": -1}},
            {"$limit": 50},  # Limit results
        ]

        # Execute the search
        search_results = list(collection.aggregate(pipeline))

        # Extract IDs from search results
        recipe_ids = [result["_id"] for result in search_results]

        # Get Django model instances and preserve ordering
        id_to_position = {str(id): idx for idx, id in enumerate(recipe_ids)}
        recipes_unordered = Recipe.objects.filter(id__in=recipe_ids)

        # Convert to list and sort by search score order
        recipes = list(recipes_unordered)
        recipes.sort(key=lambda r: id_to_position.get(str(r.id), 999))

    # Render the template with results
    return render(request, "vector_search.html", {"recipes": recipes, "query": query})


def get_claude_suggestions(user_ingredients, similar_recipes, max_suggestions=4):
    """
    Get meal suggestions from Claude based on available ingredients and similar recipes

    Args:
        user_ingredients (list): List of ingredients provided by the user
        similar_recipes (list): List of similar recipes found by vector search
        max_suggestions (int): Maximum number of suggestions to return

    Returns:
        list: List of meal suggestions from Claude
    """
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Prepare the prompt for Claude
    prompt = f"""I have these ingredients: {", ".join(user_ingredients)}


Based on these ingredients, I need `{max_suggestions}` meal suggestions. 
Here are some similar recipes from my database that might help you:

    {json.dumps(similar_recipes, indent=2)}

For each suggestion, please:
1. Provide a recipe name
2. List the ingredients I have that can be used
3. Suggest substitutions for any missing ingredients
4. Give a brief description of how to prepare it
5. Mention difficulty level (easy, medium, hard)

Be friendly, practical, and focus on using what I have available with minimal extra ingredients. 
Keep your answer concise and focused on the meal suggestions.
"""

    # Call Claude API
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1500,
        temperature=0.7,
        system="You are a helpful cooking assistant that provides meal suggestions based on available ingredients.",
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract and parse suggestions
    suggestions_text = response.content[0].text

    # Split the suggestions - we'll assume each suggestion starts with a recipe name and number
    raw_suggestions = []
    current_suggestion = ""

    for line in suggestions_text.split("\n"):
        # Check if this line starts a new suggestion
        if line.strip() and (
            line.strip()[0].isdigit() and line.strip()[1:3] in [". ", ") "]
        ):
            if current_suggestion:
                raw_suggestions.append(current_suggestion.strip())
            current_suggestion = line
        else:
            current_suggestion += "\n" + line

    # Add the last suggestion
    if current_suggestion:
        raw_suggestions.append(current_suggestion.strip())

    # Limit to max_suggestions
    return raw_suggestions[:max_suggestions]


def ai_meal_suggestions(request):
    """
    View that combines vector search with Claude AI to suggest meals
    based on user-provided ingredients
    """
    query = request.GET.get("ingredients", "")
    suggestions = []
    error_message = None

    if query:
        try:
            # Clean up the input - split by commas and strip whitespace
            ingredients_list = [ing.strip() for ing in query.split(",") if ing.strip()]
            ingredients_text = ", ".join(ingredients_list)

            # Perform vector search to find similar recipes
            search_query = f"Ingredients: {ingredients_text}"
            similar_recipes = perform_vector_search(search_query, limit=10)

            if similar_recipes:
                # Format recipe data for Claude
                recipes_data = []
                for recipe in similar_recipes:
                    recipes_data.append(
                        {
                            "title": recipe.get("title", ""),
                            "ingredients": recipe.get("ingredients", []),
                            "score": recipe.get("similarity_score", 0),
                            "id": recipe.get("id", ""),
                        }
                    )

                # Call Claude API for meal suggestions
                suggestions = get_claude_suggestions(ingredients_list, recipes_data)
            else:
                error_message = "No similar recipes found for the provided ingredients."

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"

    context = {
        "ingredients": query,
        "suggestions": suggestions,
        "error_message": error_message,
    }

    return render(request, "ai_suggestions.html", context)
