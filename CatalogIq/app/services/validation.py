ALLOWED_CATEGORIES = {
    "Groceries",
    "Beverages",
    "Personal Care",
    "Household",
    "Electronics",
    "Fashion",
    "Home & Kitchen",
    "Other",
}


def validate_llm_result(result):
    #result must be a dictionary
    if not isinstance(result, dict):
        raise ValueError("LLM response must be a JSON object")

    clean_title = result.get("clean_title")

    if not isinstance(clean_title, str) or not clean_title.strip():
        raise ValueError("clean_title must be a non-empty string")

    category = result.get("category")

    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Invalid category: {category}"
        )

    # Brand must be string or null
    brand = result.get("brand")

    if brand is not None and not isinstance(brand, str):
        raise ValueError("brand must be a string or null")

    tags = result.get("tags")

    if not isinstance(tags, list):
        raise ValueError("tags must be a list")

    #maximum 5 tags
    if len(tags) > 5:
        raise ValueError("Maximum 5 tags are allowed")

    #every tag must be lowercase string
    for tag in tags:
        if not isinstance(tag, str):
            raise ValueError("Every tag must be a string")

        if tag != tag.lower():
            raise ValueError("Tags must be lowercase")

    return {
        "clean_title": clean_title.strip(),
        "category": category,
        "brand": brand,
        "tags": tags,
    }