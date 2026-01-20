"""Fashion Advisor MCP - HTTP Server for LM Studio

Returns a cool women's fashion look for the 1960s (randomly selected).
Runs as HTTP server compatible with LM Studio's MCP configuration.

To use with LM Studio, add to C:\\Users\\{username}\\.lmstudio\\mcp-config.json:
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

# Fashion looks for the 1960s
FASHION_LOOKS_1960S = [
    {
        "name": "Mod Minis",
        "description": "Crisp A-line mini dresses with geometric shapes and bold color blocking.",
        "key_items": ["A-line mini dress", "opaque tights", "go-go boots", "graphic shift dress"],
        "color_palette": ["white", "black", "red", "primary colors"],
        "vibe": "Youthful, graphic, modern"
    },
    {
        "name": "Space Age Chic",
        "description": "Futuristic metallics and sleek silhouettes inspired by the space race.",
        "key_items": ["metallic shift dress", "white vinyl jacket", "helmet-style hat", "block-heel shoes"],
        "color_palette": ["silver", "white", "midnight blue"],
        "vibe": "Futuristic, bold, clean"
    },
    {
        "name": "Beatnik Black",
        "description": "Slim black turtlenecks and cigarette pants with minimalist lines.",
        "key_items": ["black turtleneck", "cigarette pants", "ballet flats", "beret"],
        "color_palette": ["black", "charcoal"],
        "vibe": "Intellectual, understated, cool"
    },
    {
        "name": "Swinging London",
        "description": "Playful prints, bold patterns, and youthful silhouettes.",
        "key_items": ["patterned mini dress", "knee-high boots", "statement earrings", "colorful tights"],
        "color_palette": ["yellow", "turquoise", "pink"],
        "vibe": "Playful, energetic, iconic"
    },
    {
        "name": "Psychedelic Pop",
        "description": "Vivid prints, swirling motifs, and statement accessories.",
        "key_items": ["psychedelic print blouse", "high-waisted skirt", "bold sunglasses", "chunky bangles"],
        "color_palette": ["orange", "purple", "lime"],
        "vibe": "Artistic, bold, expressive"
    },
    {
        "name": "Bouclé Elegance",
        "description": "Tailored bouclé suits with refined, ladylike polish.",
        "key_items": ["bouclé jacket", "matching skirt", "pearls", "low heels"],
        "color_palette": ["cream", "navy", "pastel pink"],
        "vibe": "Polished, elegant, timeless"
    },
    {
        "name": "Shift Dress Classic",
        "description": "Simple, structured shift dresses with a neat neckline.",
        "key_items": ["shift dress", "simple pumps", "headband", "structured handbag"],
        "color_palette": ["navy", "white", "mustard"],
        "vibe": "Clean, classic, refined"
    },
    {
        "name": "Color-Blocked Coats",
        "description": "Structured coats in bold, contrasting blocks of color.",
        "key_items": ["color-block coat", "sleek dress", "leather gloves", "block heel"],
        "color_palette": ["red", "white", "black"],
        "vibe": "Structured, bold, confident"
    }
]


@server.tool()
def get_fashion_look() -> dict:
    """Get a random cool women's fashion look for the 1960s.
    
    Returns a complete fashion look with description, key items, colors, and vibe.
    Perfect for style inspiration or fashion recommendations.
    """
    look = random.choice(FASHION_LOOKS_1960S)
    return {
        "look_name": look["name"],
        "description": look["description"],
        "key_items": ", ".join(look["key_items"]),
        "color_palette": ", ".join(look["color_palette"]),
        "vibe": look["vibe"],
        "year": "1960s"
    }


@server.tool()
def get_all_looks() -> list[dict]:
    """Get all available fashion looks for the 1960s.
    
    Returns the complete collection of 8 curated fashion looks.
    Use this to browse all options before making a recommendation.
    """
    return [
        {
            "name": look["name"],
            "vibe": look["vibe"],
            "description": look["description"]
        }
        for look in FASHION_LOOKS_1960S
    ]


@server.tool()
def get_look_by_vibe(vibe: str) -> dict:
    """Find a 1960s fashion look matching a specific vibe or mood.
    
    Args:
        vibe: The desired vibe/mood (e.g., "modern", "romantic", "bold", "playful")
    
    Returns a fashion look that matches the requested vibe.
    """
    vibe_lower = vibe.lower()
    
    # Find matching look
    for look in FASHION_LOOKS_1960S:
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
    fallback = random.choice(FASHION_LOOKS_1960S)
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
    print("LM Studio config (C:\\\\Users\\\\{username}\\\\.lmstudio\\\\mcp-config.json):")
    print('{')
    print('  "mcpServers": {')
    print('    "fashion-advisor": {')
    print('      "url": "http://127.0.0.1:6820/mcp"')
    print('    }')
    print('  }')
    print('}')
    print("\nServer starting on http://127.0.0.1:6820...")
    
    # Run with HTTP transport on port 6820
    server.run(transport="http", host="127.0.0.1", port=6820)
