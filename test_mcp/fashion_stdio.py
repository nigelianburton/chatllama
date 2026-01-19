"""Fashion Advisor MCP - Stdio Style

Returns a cool woman's fashion look for 2026 (randomly selected).
Uses fastmcp with stdio transport for integration with other tools.
"""

import random
from fastmcp.server import FastMCP

# Initialize the MCP server
server = FastMCP("fashion-advisor")

# Fashion looks for 2026
FASHION_LOOKS_2026 = [
    {
        "name": "Neo-Minimalist Edge",
        "description": "Clean tailored pieces with unexpected cutouts and asymmetrical details.",
        "key_items": ["oversized blazer with side cutout", "high-waisted black trousers", "sleek leather loafers", "minimalist jewelry"],
        "color_palette": ["black", "cream", "caramel"],
        "vibe": "Modern, sophisticated, rebellious"
    },
    {
        "name": "Cyberpunk Glam",
        "description": "Holographic and metallic accents paired with sleek silhouettes.",
        "key_items": ["metallic bodysuit", "oversized translucent trench coat", "chrome platform boots", "geometric sunglasses"],
        "color_palette": ["silver", "holographic", "neon accents"],
        "vibe": "Futuristic, bold, confident"
    },
    {
        "name": "Quiet Luxury Revived",
        "description": "Premium basics elevated with understated luxury and perfect tailoring.",
        "key_items": ["cashmere sweater", "tailored midi skirt", "ballet flats", "subtle luxury handbag"],
        "color_palette": ["beige", "cream", "soft brown", "white"],
        "vibe": "Effortless, refined, timeless"
    },
    {
        "name": "Cottagecore Meets City",
        "description": "Romantic prairie-inspired pieces styled with modern accessories.",
        "key_items": ["maxi floral dress", "leather moto jacket", "vintage-inspired boots", "minimalist crossbody bag"],
        "color_palette": ["sage green", "cream", "burnt orange"],
        "vibe": "Romantic, adventurous, nostalgic"
    },
    {
        "name": "Street Maximalist",
        "description": "Bold patterns, clashing prints, and vibrant colors mixed fearlessly.",
        "key_items": ["patterned cargo pants", "oversized graphic tee", "colorful puffer jacket", "chunky sneakers"],
        "color_palette": ["multi-color", "neon", "rich jewel tones"],
        "vibe": "Playful, expressive, joyful"
    },
    {
        "name": "Tech-Chic Nomad",
        "description": "Performance fabrics and functional pieces styled for modern mobility.",
        "key_items": ["moisture-wicking jacket", "sleek leggings", "hiking-inspired boots", "crossbody tech bag"],
        "color_palette": ["black", "slate gray", "forest green"],
        "vibe": "Practical, modern, adventurous"
    },
    {
        "name": "Romantic 70s Redux",
        "description": "Soft silhouettes, vintage textures, and groovy accessories.",
        "key_items": ["flared denim", "bohemian blouse", "suede platform boots", "vintage sunglasses"],
        "color_palette": ["olive", "terracotta", "dusty pink"],
        "vibe": "Groovy, feminine, retro"
    },
    {
        "name": "Power Androgyne",
        "description": "Gender-neutral tailoring with sharp lines and unexpected textures.",
        "key_items": ["oversized button-up shirt", "wide-leg trousers", "pointed-toe shoes", "bold accessories"],
        "color_palette": ["black", "white", "deep navy"],
        "vibe": "Confident, commanding, modern"
    }
]


@server.tool()
def get_fashion_look() -> dict:
    """Get a hot woman's fashion trend for 2026, randomly selected.
    
    These are the most anticipated fashion trends that will be hot in 2026.
    Returns a complete outfit inspiration with name, description, key items, colors, and vibe.
    """
    look = random.choice(FASHION_LOOKS_2026)
    return {
        "success": True,
        "look": look,
        "styling_tip": f"{look['name']} is trending big in 2026! Pair these items with confidence and your personal flair!",
        "total_looks_available": len(FASHION_LOOKS_2026)
    }


@server.tool()
def get_all_looks() -> dict:
    """Get all hot fashion trends for 2026.
    
    Returns a complete list of the hottest anticipated fashion looks for 2026.
    These are the trends expected to dominate the fashion scene.
    """
    return {
        "success": True,
        "total_looks": len(FASHION_LOOKS_2026),
        "looks": FASHION_LOOKS_2026,
        "note": "These are the hottest fashion trends predicted for 2026"
    }


@server.tool()
def get_fashion_look() -> dict:
    """Get a hot woman's fashion trend for 2026 (randomly selected).
    
    Use this instead of get_look_by_vibe if you need any trending look.
    These are the most anticipated fashion trends that will be hot in 2026.
    Returns a complete outfit inspiration with name, description, key items, colors, and vibe.
    """
    look = random.choice(FASHION_LOOKS_2026)
    return {
        "success": True,
        "look": look,
        "styling_tip": f"{look['name']} is trending big in 2026! Pair these items with confidence and your personal flair!",
        "total_looks_available": len(FASHION_LOOKS_2026)
    }


@server.tool()
def get_look_by_vibe(vibe: str = None) -> dict:
    """Get a hot 2026 fashion trend that matches a specific vibe/mood.
    
    Optional parameter: vibe (string)
    If provided, the tool will try to find a trend matching that vibe.
    If not provided, returns a random trend.
    
    Args:
        vibe: Optional vibe/mood string (e.g., 'bold', 'sophisticated', 'romantic', 'modern')
              If omitted, a random trend is returned.
    
    Returns:
        A hot 2026 fashion trend matching or similar to the requested vibe (or random if no vibe provided).
    """
    if not vibe:
        # No vibe provided, return random
        look = random.choice(FASHION_LOOKS_2026)
        return {
            "success": True,
            "requested_vibe": None,
            "look": look,
            "found_match": True
        }
    
    vibe_lower = vibe.lower()
    matching_looks = [
        look for look in FASHION_LOOKS_2026 
        if vibe_lower in look['vibe'].lower()
    ]
    
    if not matching_looks:
        # If no exact match, return random
        matching_looks = FASHION_LOOKS_2026
    
    look = random.choice(matching_looks)
    return {
        "success": True,
        "requested_vibe": vibe,
        "look": look,
        "found_match": vibe_lower in look['vibe'].lower()
    }


if __name__ == "__main__":
    # Run the server with stdio transport
    server.run()
