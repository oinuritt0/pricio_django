"""
Smart search module with Cyrillic support.
"""
import re
from typing import List, Tuple
from django.db.models import Q
from .models import Product


# Stop words to ignore in search
STOP_WORDS = {
    'и', 'в', 'на', 'с', 'для', 'от', 'по', 'из', 'к', 'у', 'о',
    'бзмж', 'шт', 'уп', 'упак', 'the', 'and', 'for', 'with'
}


def normalize_text(text: str) -> str:
    """Normalize text for search (lowercase, replace ё with е)."""
    if not text:
        return ""
    text = text.lower()
    text = text.replace('ё', 'е')
    text = ' '.join(text.split())
    return text


def tokenize_query(query: str) -> List[str]:
    """Split query into tokens."""
    query = normalize_text(query)
    tokens = re.split(r'[\s,.\-_/\\()]+', query)
    tokens = [t for t in tokens if len(t) >= 2 and t not in STOP_WORDS]
    return tokens


def stem_russian(word: str) -> str:
    """Simple Russian stemming - remove common endings."""
    if len(word) < 4:
        return word
    endings = ['ами', 'ями', 'ах', 'ях', 'ов', 'ев', 'ей', 'ий', 'ый', 'ая', 'яя', 'ое', 'ее',
               'ы', 'и', 'а', 'я', 'у', 'ю', 'е', 'о']
    for ending in endings:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


def smart_search(store_id: str, query: str, category: str = None, limit: int = 50) -> List[Tuple[Product, int]]:
    """
    Smart product search with relevance scoring.
    Returns list of (product, score) tuples.
    """
    if not query or len(query) < 2:
        return []
    
    query_normalized = normalize_text(query)
    tokens = tokenize_query(query)
    
    if not tokens:
        return []
    
    # Get all products for this store (we filter in Python for Cyrillic support)
    products = Product.objects.filter(store_id=store_id)
    if category:
        products = products.filter(category_name=category)
    
    results = []
    
    for product in products:
        name_normalized = normalize_text(product.name)
        score = 0
        
        # Exact phrase match - highest priority
        if query_normalized in name_normalized:
            score += 100
            # Bonus if name starts with query
            if name_normalized.startswith(query_normalized):
                score += 20
        
        # Token matching
        matched_tokens = 0
        for token in tokens:
            if token in name_normalized:
                score += 30
                matched_tokens += 1
            else:
                # Try stemmed version
                stemmed = stem_russian(token)
                if len(stemmed) >= 3 and stemmed in name_normalized:
                    score += 20
                    matched_tokens += 1
        
        # Bonus for matching all tokens
        if matched_tokens == len(tokens) and len(tokens) > 1:
            score += 25
        
        # Category match
        if product.category_name:
            cat_normalized = normalize_text(product.category_name)
            if query_normalized in cat_normalized:
                score += 15
        
        if score > 0:
            results.append((product, score))
    
    # Sort by score (descending), then by name
    results.sort(key=lambda x: (-x[1], x[0].name))
    
    return results[:limit]


def get_similar_products(product: Product, limit: int = 6) -> List[Product]:
    """Find similar products in the same store."""
    name_normalized = normalize_text(product.name)
    words = [w for w in name_normalized.split() if len(w) >= 3 and w not in STOP_WORDS]
    
    if not words:
        return []
    
    # Get products from same category
    similar = Product.objects.filter(
        store=product.store,
        category_name=product.category_name
    ).exclude(pk=product.pk)
    
    results = []
    for p in similar:
        p_name = normalize_text(p.name)
        # Count matching words
        matches = sum(1 for w in words if w in p_name or stem_russian(w) in p_name)
        if matches > 0:
            results.append((p, matches))
    
    results.sort(key=lambda x: -x[1])
    return [p for p, _ in results[:limit]]

