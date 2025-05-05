# DMB Recipes: Django + MongoDB + Vector Search

A Django web application for searching recipes using natural language queries, powered by MongoDB's vector search capabilities.

## Features

- **Semantic Search**: Find recipes based on concepts and meanings, not just keywords
- **MongoDB Backend**: Leverages the official Django MongoDB Backend for schema flexibility
- **Vector Embeddings**: Converts recipe descriptions into mathematical vectors for intelligent searching
- **Import Tools**: Easily import recipes from JSON files
- **Fast Queries**: Optimized for speed even with large recipe collections

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/freethrow/dmb-recipes.git
   cd dmb-recipes
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up your MongoDB connection in the settings file

4. Run migrations:
   ```
   python manage.py migrate
   ```

5. Import sample recipes:
   ```
   python manage.py shell
   ```
   Then in the shell:
   ```python
   from scripts import import_json_recipes
   import_json_recipes.run()
   ```

6. Generate vector embeddings:
   ```
   python manage.py shell
   ```
   Then in the shell:
   ```python
   from scripts import generate_embeddings
   generate_embeddings.run()
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

## How It Works

DMB Recipes uses the Django MongoDB Backend to connect to a MongoDB database. Recipe descriptions and ingredients are processed into vector embeddings using machine learning. When you search, your query is also converted to a vector, and MongoDB's vector search finds recipes with similar vectors.

This means searching for "spicy dinner with chicken" will find recipes that match the concept, even if they don't contain those exact words!

## Project Structure

- `cookbook/` - Django app for the recipe functionality
- `cookbook/models.py` - Recipe and related models
- `cookbook/views.py` - Contains the search views
- `cookbook/search.py` - Vector search implementation
- `scripts/` - Contains import and embedding generation functionality
- `bigger_sample.json` - Sample recipe data

## Example Usage

After starting the development server, navigate to the homepage. Enter natural language queries like:

- "healthy breakfast with oats"
- "quick Italian dinner"
- "something spicy with vegetables"
- "dessert with chocolate that's easy to make"

The app will return recipes that match your query based on semantic similarity, not just keyword matching.

## License

MIT License. See LICENSE file for details.

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## Credits

Built with:
- Django
- MongoDB Django Backend 
- MongoDB Atlas Vector Search
