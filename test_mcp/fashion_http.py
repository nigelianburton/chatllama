"""Fashion Advisor MCP - HTTP Server for LM Studio

Returns a cool woman's fashion look for 2026 (randomly selected).
Runs as HTTP server compatible with LM Studio's MCP configuration.

To use with LM Studio, add to C:\Users\{username}\.lmstudio\mcp-config.json:
{
  "mcpServers": {
    "fashion-advisor": {
      "url": "http://127.0.0.1:6820/sse"
    }
  }
}
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
        "description": "Functional tech fabrics in sleek, travel-ready silhouettes.",
        "key_items": ["water-resistant blazer", "convertible pants", "ergonomic sneakers", "smart backpack"],
        "color_palette": ["charcoal", "olive", "black"],
        "vibe": "Practical, modern, adventurous"
    },
    {
        "name": "Romantic 70s Redux",
        "description": "Flowing fabrics, bohemian prints, and retro-inspired silhouettes.",
        "key_items": ["flared jeans", "crochet top", "platform sandals", "fringe bag"],
        "color_palette": ["rust", "mustard", "cream", "terracotta"],
        "vibe": "Groovy, feminine, retro"
    },
    {
        "name": "Power Androgyne",
        "description": "Sharp tailoring with gender-neutral silhouettes and bold confidence.",
        "key_items": ["oversized suit", "crisp white shirt", "oxford shoes", "structured handbag"],
        "color_palette": ["black", "white", "navy"],
        "vibe": "Confident, commanding, modern"
    }
]


@server.tool()
def get_fashion_look() -> dict:
    """Get a random cool woman's fashion look for 2026.
    
    Returns a complete fashion look with description, key items, colors, and vibe.
    Perfect for style inspiration or fashion recommendations.
    """
    look = random.choice(FASHION_LOOKS_2026)
    return {
        "look_name": look["name"],
        "description": look["description"],
        "key_items": ", ".join(look["key_items"]),
        "color_palette": ", ".join(look["color_palette"]),
        "vibe": look["vibe"],
        "year": "2026"
    }


@server.tool()
def get_all_looks() -> list[dict]:
    """Get all available fashion looks for 2026.
    
    Returns the complete collection of 8 curated fashion looks.
    Use this to browse all options before making a recommendation.
    """
    return [
        {
            "name": look["name"],
            "vibe": look["vibe"],
            "description": look["description"]
        }
        for look in FASHION_LOOKS_2026
    ]


@server.tool()
def get_look_by_vibe(vibe: str) -> dict:
    """Find a fashion look matching a specific vibe or mood.
    
    Args:
        vibe: The desired vibe/mood (e.g., "modern", "romantic", "bold", "playful")
    
    Returns a fashion look that matches the requested vibe.
    """
    vibe_lower = vibe.lower()
    
    # Find matching look
    for look in FASHION_LOOKS_2026:
        if vibe_lower in look["vibe"].lower():
            return {
                "look_name": look["name"],
                "description": look["description"],
                "key_items": ", ".join(look["key_items"]),
                "color_palette": ", ".join(look["color_palette"]),
                "vibe": look["vibe"],
                "matched_vibe": vibe
            }
    
    # If no match, return a random one
    fallback = random.choice(FASHION_LOOKS_2026)
    return {
        "look_name": fallback["name"],
        "description": fallback["description"],
        "key_items": ", ".join(fallback["key_items"]),
        "color_palette": ", ".join(fallback["color_palette"]),
        "vibe": fallback["vibe"],
        "note": f"No exact match for '{vibe}', here's an alternative!"
    }


if __name__ == "__main__":
    # Run as HTTP server for LM Studio integration
    # Access at: http://127.0.0.1:6820/mcp
    print("Starting Fashion Advisor MCP HTTP Server...")
    print("LM Studio config (C:\\Users\\{username}\\.lmstudio\\mcp-config.json):")
    print('{')
    print('  "mcpServers": {')
    print('    "fashion-advisor": {')
    print('      "url": "http://127.0.0.1:6820/sse"')
    print('    }')
    print('  }')
    print('}')
    print("\nServer starting on http://127.0.0.1:6820...")
    
    # Run with HTTP transport on port 6820
    server.run(transport="sse", host="127.0.0.1", port=6820)
