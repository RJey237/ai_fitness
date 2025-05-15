# ai_model/templatetags/ai_model_tags.py

from django import template

register = template.Library()

@register.filter(name='get_at_index') # Register filter with the name 'get_at_index'
def get_at_index(list_obj, index):
    """
    Retrieves an item from a list/sequence at a specific zero-based index.
    Returns None if index is out of bounds, input is not indexable, or index is not valid.
    """
    try:
        # Ensure index is an integer before using it
        index = int(index)
        return list_obj[index]
    except (IndexError, TypeError, ValueError, AttributeError):
        # Handle potential errors: list index out of range, index not integer, list_obj not indexable
        return None # Or return an empty string '', or default value like 'Error'