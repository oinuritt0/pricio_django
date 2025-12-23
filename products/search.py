"""
Smart search module with Cyrillic support and product similarity scoring.
"""
import re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from django.db.models import Q
from .models import Product


# ============================================================================
# PRODUCT ATTRIBUTES
# ============================================================================

@dataclass
class ProductAttributes:
    """Structured product attributes extracted from name."""
    product_type: Optional[str] = None   # молоко, сыр, колбаса
    brand: Optional[str] = None          # Простоквашино, Mucho Mas
    volume_ml: Optional[float] = None    # объём в мл
    weight_g: Optional[float] = None     # вес в граммах
    fat_percent: Optional[float] = None  # жирность
    quantity: Optional[int] = None       # количество в упаковке


# Product type keywords for normalization
PRODUCT_TYPES = {
    'молоко': ['молоко', 'молочко'],
    'кефир': ['кефир'],
    'йогурт': ['йогурт', 'йогу|рт'],
    'творог': ['творог', 'творожок', 'творожный', 'творожная', 'творожное'],
    'сметана': ['сметана'],
    'сливки': ['сливки'],
    'сыр': ['сыр', 'сырок', 'сырный', 'сырная'],
    'масло': ['масло'],
    'колбаса': ['колбаса', 'колбасный', 'колбасная', 'колбаски'],
    'сосиски': ['сосиски', 'сосиска', 'сардельки', 'сарделька'],
    'ветчина': ['ветчина'],
    'бекон': ['бекон'],
    'курица': ['курица', 'куриный', 'куриная', 'куриное', 'цыплёнок', 'цыпленок'],
    'индейка': ['индейка', 'индюшиный', 'индюшиная'],
    'свинина': ['свинина', 'свиной', 'свиная', 'свиное'],
    'говядина': ['говядина', 'говяжий', 'говяжья', 'говяжье'],
    'фарш': ['фарш'],
    'рыба': ['рыба', 'рыбный', 'рыбная', 'рыбное'],
    'лосось': ['лосось', 'сёмга', 'семга', 'форель'],
    'креветки': ['креветки', 'креветка'],
    'хлеб': ['хлеб', 'хлебец', 'хлебцы'],
    'батон': ['батон', 'багет'],
    'булка': ['булка', 'булочка', 'булочки'],
    'вино': ['вино'],
    'пиво': ['пиво'],
    'водка': ['водка'],
    'виски': ['виски'],
    'коньяк': ['коньяк'],
    'сок': ['сок', 'нектар'],
    'вода': ['вода', 'минералка', 'минеральная'],
    'лимонад': ['лимонад', 'газировка'],
    'чай': ['чай'],
    'кофе': ['кофе'],
    'шоколад': ['шоколад', 'шоколадка', 'шоколадный', 'шоколадная'],
    'конфеты': ['конфеты', 'конфета'],
    'печенье': ['печенье'],
    'торт': ['торт'],
    'мороженое': ['мороженое', 'пломбир', 'эскимо'],
    'чипсы': ['чипсы'],
    'яблоко': ['яблоко', 'яблоки', 'яблочный', 'яблочная'],
    'банан': ['банан', 'бананы'],
    'апельсин': ['апельсин', 'апельсины', 'апельсиновый'],
    'лимон': ['лимон', 'лимоны'],
    'помидор': ['помидор', 'помидоры', 'томат', 'томаты'],
    'огурец': ['огурец', 'огурцы'],
    'картофель': ['картофель', 'картошка'],
    'морковь': ['морковь', 'морковка'],
    'лук': ['лук', 'луковый'],
    'капуста': ['капуста'],
    'рис': ['рис', 'рисовый', 'рисовая'],
    'гречка': ['гречка', 'гречневый', 'гречневая', 'греча'],
    'макароны': ['макароны', 'паста', 'спагетти', 'пенне', 'фузилли'],
    'курага': ['курага'],
    'изюм': ['изюм'],
    'чернослив': ['чернослив'],
    'орехи': ['орехи', 'орех', 'миндаль', 'фундук', 'грецкий', 'кешью'],
}

# Known Russian brands
RUSSIAN_BRANDS = {
    'простоквашино', 'домик в деревне', 'вкуснотеево', 'савушкин', 'брест-литовск',
    'черкизово', 'мираторг', 'останкино', 'велком', 'папа может',
    'добрый', 'любимый', 'фруктовый сад', 'моя семья', 'j7', 'rich',
    'макфа', 'барилла', 'щебекинские',
    'lay\'s', 'lays', 'pringles', 'cheetos',
    'аленка', 'бабаевский', 'красный октябрь', 'коркунов', 'merci',
    'bonduelle', 'heinz', 'calve', 'mixbar', 'greenfield', 'ahmad',
    'lipton', 'nescafe', 'jacobs', 'jardin', 'tchibo',
}

# Stop words to ignore in search
STOP_WORDS = {
    'магнит', 'пятёрочка', 'пятерочка', 'для', 'без', 'или', 'the', 'штук', 'шт',
    'упаковка', 'пакет', 'бзмж', 'premium', 'extra', 'new', 'global', 'village',
    'напиток', 'продукт', 'изделие', 'товар', 'набор', 'ассорти', 'микс',
    'добавлением', 'натуральный', 'свежий', 'вкусный', 'домашний', 'классический',
    'молочный', 'молочная', 'молочное', 'детский', 'детская', 'взрослый',
    'гавайский', 'тропический', 'летняя', 'летний', 'садовая', 'садовый',
    'лесная', 'лесной', 'красное', 'красный', 'белое', 'белый', 'зеленый', 'зелёный',
    'фасованное', 'фасованный', 'отборные', 'отборный', 'сокосодержащий',
    'восстановленный', 'протеиновый', 'протеиновое', 'высокобелковый',
    'энергетический', 'газированный', 'негазированный', 'безалкогольный',
    'с', 'и', 'в', 'на', 'из', 'по', 'со', 'к', 'у', 'о', 'от',
    'уп', 'упак', 'and', 'for', 'with'
}


# ============================================================================
# TEXT NORMALIZATION
# ============================================================================

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


# ============================================================================
# PRODUCT ATTRIBUTE PARSING
# ============================================================================

def parse_product_attributes(name: str) -> ProductAttributes:
    """Extract structured attributes from product name."""
    name_lower = name.lower()
    attrs = ProductAttributes()
    
    # Extract volume: 750мл, 1л, 1.5л, 0.5 л
    volume_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:мл|ml)\b', name_lower)
    if volume_match:
        attrs.volume_ml = float(volume_match.group(1).replace(',', '.'))
    else:
        volume_match = re.search(r'(\d+(?:[.,]\d+)?)\s*л(?:итр|\b)', name_lower)
        if volume_match:
            attrs.volume_ml = float(volume_match.group(1).replace(',', '.')) * 1000
    
    # Extract weight: 500г, 1кг, 1.2кг
    weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:г|гр|грамм)(?!\w)', name_lower)
    if weight_match:
        attrs.weight_g = float(weight_match.group(1).replace(',', '.'))
    else:
        weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*кг\b', name_lower)
        if weight_match:
            attrs.weight_g = float(weight_match.group(1).replace(',', '.')) * 1000
    
    # Extract fat percentage: 3.2%, 2,5%
    fat_match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', name_lower)
    if fat_match:
        attrs.fat_percent = float(fat_match.group(1).replace(',', '.'))
    
    # Extract quantity: 6шт, x12
    qty_match = re.search(r'(\d+)\s*(?:шт|штук)|x(\d+)', name_lower)
    if qty_match:
        attrs.quantity = int(qty_match.group(1) or qty_match.group(2))
    
    # Extract brand (Latin - priority)
    latin_brands = re.findall(r'\b([A-Z][a-zA-Z\']+(?:\s+[A-Z][a-zA-Z\']+)?)\b', name)
    if latin_brands:
        attrs.brand = max(latin_brands, key=len)
    
    # Check known Russian brands
    if not attrs.brand:
        for brand in RUSSIAN_BRANDS:
            if brand in name_lower:
                attrs.brand = brand.title()
                break
    
    # Determine product type
    for product_type, keywords in PRODUCT_TYPES.items():
        for keyword in keywords:
            if keyword in name_lower:
                attrs.product_type = product_type
                break
        if attrs.product_type:
            break
    
    return attrs


# ============================================================================
# SIMILARITY SCORING
# ============================================================================

def calculate_similarity_score(attrs1: ProductAttributes, attrs2: ProductAttributes,
                               name1: str, name2: str) -> int:
    """
    Calculate similarity score between two products (0-100).
    Higher score = more similar products.
    """
    score = 0
    
    # Normalize names
    name1_norm = normalize_text(name1)
    name2_norm = normalize_text(name2)
    
    # Extract words (minimum 3 characters)
    words1 = set(re.findall(r'[а-яёa-z]{3,}', name1_norm))
    words2 = set(re.findall(r'[а-яёa-z]{3,}', name2_norm))
    words1 -= STOP_WORDS
    words2 -= STOP_WORDS
    
    # Get first significant word (usually product type)
    first_word1 = name1_norm.split()[0] if name1_norm else ""
    first_word2 = name2_norm.split()[0] if name2_norm else ""
    
    # 1. First word (product type) - most important criterion
    first_word_match = False
    if first_word1 and first_word2:
        if first_word1 == first_word2:
            score += 35
            first_word_match = True
        elif stem_russian(first_word1) == stem_russian(first_word2):
            score += 30
            first_word_match = True
        elif first_word1 in first_word2 or first_word2 in first_word1:
            score += 25
            first_word_match = True
    
    # If first words don't match, check product_type
    if not first_word_match and attrs1.product_type and attrs2.product_type:
        if attrs1.product_type == attrs2.product_type:
            score += 30
            first_word_match = True
        elif stem_russian(attrs1.product_type) == stem_russian(attrs2.product_type):
            score += 25
            first_word_match = True
    
    # No type match - products are not similar (unless many common words)
    if not first_word_match:
        common_words = words1 & words2
        if len(common_words) >= 2:
            score += 20
        else:
            return 0
    
    # 2. Brand (very important for price comparison!)
    if attrs1.brand and attrs2.brand:
        if attrs1.brand.lower() == attrs2.brand.lower():
            score += 35  # Same brand - big bonus
        else:
            score += 5   # Different brands - minimal bonus
    elif attrs1.brand or attrs2.brand:
        score += 3  # One has brand, other doesn't
    else:
        score += 10  # Both without brand - possibly generic products
    
    # 3. Volume/weight (important for correct comparison)
    if attrs1.volume_ml and attrs2.volume_ml:
        ratio = min(attrs1.volume_ml, attrs2.volume_ml) / max(attrs1.volume_ml, attrs2.volume_ml)
        if ratio > 0.95:
            score += 12
        elif ratio > 0.8:
            score += 8
        elif ratio > 0.5:
            score += 4
    elif attrs1.weight_g and attrs2.weight_g:
        ratio = min(attrs1.weight_g, attrs2.weight_g) / max(attrs1.weight_g, attrs2.weight_g)
        if ratio > 0.95:
            score += 12
        elif ratio > 0.8:
            score += 8
        elif ratio > 0.5:
            score += 4
    
    # 4. Fat percentage (for dairy)
    if attrs1.fat_percent and attrs2.fat_percent:
        if abs(attrs1.fat_percent - attrs2.fat_percent) < 0.5:
            score += 8
        elif abs(attrs1.fat_percent - attrs2.fat_percent) < 1.5:
            score += 4
    
    # 5. Word intersection (fuzzy matching)
    if words1 and words2:
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        if union > 0:
            jaccard = intersection / union
            score += int(jaccard * 15)
    
    return min(score, 100)


def calculate_price_per_unit(product) -> Optional[Dict]:
    """Calculate price per unit (liter or kg)."""
    attrs = parse_product_attributes(product.name if hasattr(product, 'name') else product.get('name', ''))
    price = float(product.current_price) if hasattr(product, 'current_price') else float(product.get('current_price', 0) or 0)
    
    if not price:
        return None
    
    if attrs.volume_ml and attrs.volume_ml > 0:
        price_per_liter = price / attrs.volume_ml * 1000
        return {'value': price_per_liter, 'unit': 'л', 'display': f"{price_per_liter:.2f} ₽/л"}
    
    if attrs.weight_g and attrs.weight_g > 0:
        price_per_kg = price / attrs.weight_g * 1000
        return {'value': price_per_kg, 'unit': 'кг', 'display': f"{price_per_kg:.2f} ₽/кг"}
    
    return None


# ============================================================================
# SMART SEARCH
# ============================================================================

def smart_search(store_id: str, query: str, category: str = None, limit: int = 500) -> List[Tuple[Product, int]]:
    """
    Smart product search with relevance scoring.
    Returns list of (product, score) tuples.
    """
    if not query or len(query) < 2:
        return []
    
    query_normalized = normalize_text(query)
    tokens = tokenize_query(query)
    
    if not tokens:
        # If all words are stop words, try searching anyway
        tokens = [t for t in query_normalized.split() if len(t) >= 2]
        if not tokens:
            return []
    
    # Get all products for this store (filter in Python for Cyrillic support)
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


# ============================================================================
# SIMILAR PRODUCTS SEARCH
# ============================================================================

def get_similar_products_v2(store_id: str, product_name: str, product_id: str,
                            current_price: float, category: str = None, limit: int = 6) -> List[Dict]:
    """
    Advanced similar products search with multi-level scoring.
    Returns list of products with additional fields:
    - similarity_score: similarity rating (0-100)
    - price_diff: price difference
    - is_cheaper: whether this product is cheaper
    - is_exact_match: high score = exact analog
    - price_per_unit: normalized price per unit
    """
    # Parse source product attributes
    source_attrs = parse_product_attributes(product_name)
    
    # Normalize name for search
    source_name_normalized = normalize_text(product_name)
    source_words = set(tokenize_query(product_name))
    
    # Build search terms
    search_terms = set()
    
    # 1. All words from name (minimum 3 chars)
    for word in source_words:
        if len(word) >= 3:
            search_terms.add(word)
            # Add stemmed version
            stemmed = stem_russian(word)
            if len(stemmed) >= 3:
                search_terms.add(stemmed)
    
    # 2. Product type
    if source_attrs.product_type:
        search_terms.add(source_attrs.product_type.lower())
        stemmed = stem_russian(source_attrs.product_type.lower())
        if len(stemmed) >= 3:
            search_terms.add(stemmed)
    
    # 3. Brand
    if source_attrs.brand:
        search_terms.add(source_attrs.brand.lower())
    
    # If no search terms, use first word
    if not search_terms:
        first_word = source_name_normalized.split()[0] if source_name_normalized else ""
        if len(first_word) >= 3:
            search_terms.add(first_word)
    
    # Get all products from this store
    all_products = Product.objects.filter(store_id=store_id)
    
    candidates = []
    seen_ids = {product_id}  # Exclude current product
    
    for product in all_products:
        if product.product_id in seen_ids:
            continue
        
        name_normalized = normalize_text(product.name)
        
        # Check match with any search term
        match_found = False
        for term in search_terms:
            if term in name_normalized:
                match_found = True
                break
        
        if match_found:
            seen_ids.add(product.product_id)
            candidates.append(product)
    
    # Score all candidates
    scored_candidates = []
    for candidate in candidates:
        cand_attrs = parse_product_attributes(candidate.name)
        score = calculate_similarity_score(source_attrs, cand_attrs, product_name, candidate.name)
        
        if score > 20:  # Minimum relevance threshold
            cand_price = float(candidate.current_price) if candidate.current_price else 0
            price_diff = cand_price - current_price if current_price else 0
            
            scored_candidates.append({
                'product': candidate,
                'similarity_score': score,
                'price_diff': price_diff,
                'is_cheaper': price_diff < -0.01,
                'is_exact_match': score >= 70,
                'price_per_unit': calculate_price_per_unit(candidate),
            })
    
    # Sort by score (descending), then by price
    scored_candidates.sort(key=lambda x: (-x['similarity_score'], float(x['product'].current_price or 0)))
    
    return scored_candidates[:limit]


def find_exact_match_cross_store(product_name: str, product_id: str,
                                  source_store: str, current_price: float) -> Optional[Dict]:
    """
    Find exact product analog in another store.
    Returns best match or None.
    """
    target_store = 'magnit' if source_store == '5ka' else '5ka'
    
    similar = get_similar_products_v2(
        target_store, product_name, product_id,
        current_price, limit=1
    )
    
    if similar and similar[0]['similarity_score'] >= 60:
        return similar[0]
    
    return None


def get_cross_store_comparison(product_name: str, product_id: str,
                                source_store: str, current_price: float, limit: int = 5) -> List[Dict]:
    """
    Find similar products in another store for price comparison.
    """
    target_store = 'magnit' if source_store == '5ka' else '5ka'
    
    return get_similar_products_v2(
        target_store, product_name, product_id,
        current_price, limit=limit
    )
