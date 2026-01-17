"""Fashion Curator Server MCP - Stateful HTTP Server Style

A modern stateful MCP server that runs in its own console.
Maintains user preferences and provides personalized fashion recommendations.
Uses fastmcp with proper MCP protocol for tool introspection.
"""

import random
import json
from datetime import datetime
from typing import Optional
from fastmcp.server import FastMCP

# Initialize the stateful MCP server
server = FastMCP("fashion-curator")

# Fashion looks for 2026
FASHION_LOOKS_2026 = [
    {
        "id": 1,
        "name": "Neo-Minimalist Edge",
        "description": "Clean tailored pieces with unexpected cutouts and asymmetrical details.",
        "key_items": ["oversized blazer with side cutout", "high-waisted black trousers", "sleek leather loafers", "minimalist jewelry"],
        "color_palette": ["black", "cream", "caramel"],
        "vibe": "Modern, sophisticated, rebellious"
    },
    {
        "id": 2,
        "name": "Cyberpunk Glam",
        "description": "Holographic and metallic accents paired with sleek silhouettes.",
        "key_items": ["metallic bodysuit", "oversized translucent trench coat", "chrome platform boots", "geometric sunglasses"],
        "color_palette": ["silver", "holographic", "neon accents"],
        "vibe": "Futuristic, bold, confident"
    },
    {
        "id": 3,
        "name": "Quiet Luxury Revived",
        "description": "Premium basics elevated with understated luxury and perfect tailoring.",
        "key_items": ["cashmere sweater", "tailored midi skirt", "ballet flats", "subtle luxury handbag"],
        "color_palette": ["beige", "cream", "soft brown", "white"],
        "vibe": "Effortless, refined, timeless"
    },
    {
        "id": 4,
        "name": "Cottagecore Meets City",
        "description": "Romantic prairie-inspired pieces styled with modern accessories.",
        "key_items": ["maxi floral dress", "leather moto jacket", "vintage-inspired boots", "minimalist crossbody bag"],
        "color_palette": ["sage green", "cream", "burnt orange"],
        "vibe": "Romantic, adventurous, nostalgic"
    },
    {
        "id": 5,
        "name": "Street Maximalist",
        "description": "Bold patterns, clashing prints, and vibrant colors mixed fearlessly.",
        "key_items": ["patterned cargo pants", "oversized graphic tee", "colorful puffer jacket", "chunky sneakers"],
        "color_palette": ["multi-color", "neon", "rich jewel tones"],
        "vibe": "Playful, expressive, joyful"
    },
    {
        "id": 6,
        "name": "Tech-Chic Nomad",
        "description": "Performance fabrics and functional pieces styled for modern mobility.",
        "key_items": ["moisture-wicking jacket", "sleek leggings", "hiking-inspired boots", "crossbody tech bag"],
        "color_palette": ["black", "slate gray", "forest green"],
        "vibe": "Practical, modern, adventurous"
    },
    {
        "id": 7,
        "name": "Romantic 70s Redux",
        "description": "Soft silhouettes, vintage textures, and groovy accessories.",
        "key_items": ["flared denim", "bohemian blouse", "suede platform boots", "vintage sunglasses"],
        "color_palette": ["olive", "terracotta", "dusty pink"],
        "vibe": "Groovy, feminine, retro"
    },
    {
        "id": 8,
        "name": "Power Androgyne",
        "description": "Gender-neutral tailoring with sharp lines and unexpected textures.",
        "key_items": ["oversized button-up shirt", "wide-leg trousers", "pointed-toe shoes", "bold accessories"],
        "color_palette": ["black", "white", "deep navy"],
        "vibe": "Confident, commanding, modern"
    }
]

# Stateful storage for user preferences and history
class FashionCurator:
    def __init__(self):
        self.user_preferences = {}  # user_id -> {favorite_vibes, favorite_looks, etc}
        self.recommendation_history = {}  # user_id -> list of recommendations
        self.saved_looks = {}  # user_id -> list of saved look_ids
        
    def create_user(self, user_id: str, favorite_vibes: list[str]) -> dict:
        """Create a new user profile with preferences."""
        if user_id in self.user_preferences:
            return {"success": False, "message": f"User {user_id} already exists"}
        
        self.user_preferences[user_id] = {
            "favorite_vibes": favorite_vibes,
            "created_at": datetime.now().isoformat(),
            "recommendations_count": 0
        }
        self.recommendation_history[user_id] = []
        self.saved_looks[user_id] = []
        
        return {
            "success": True,
            "message": f"User {user_id} created with vibes: {favorite_vibes}",
            "user_id": user_id
        }
    
    def get_personalized_look(self, user_id: str) -> dict:
        """Get a personalized fashion look based on user preferences."""
        if user_id not in self.user_preferences:
            return {"success": False, "message": f"User {user_id} not found"}
        
        user_prefs = self.user_preferences[user_id]
        favorite_vibes = user_prefs["favorite_vibes"]
        
        # Find looks matching user's favorite vibes
        matching_looks = []
        for look in FASHION_LOOKS_2026:
            for vibe in favorite_vibes:
                if vibe.lower() in look["vibe"].lower():
                    matching_looks.append(look)
                    break
        
        # If no matches, return random
        if not matching_looks:
            matching_looks = FASHION_LOOKS_2026
        
        look = random.choice(matching_looks)
        
        # Track in history
        self.recommendation_history[user_id].append({
            "look_id": look["id"],
            "look_name": look["name"],
            "timestamp": datetime.now().isoformat()
        })
        user_prefs["recommendations_count"] += 1
        
        return {
            "success": True,
            "user_id": user_id,
            "look": look,
            "personalized": len(matching_looks) > 0,
            "total_recommendations_for_user": user_prefs["recommendations_count"]
        }
    
    def save_look(self, user_id: str, look_id: int) -> dict:
        """Save a look to user's favorites."""
        if user_id not in self.user_preferences:
            return {"success": False, "message": f"User {user_id} not found"}
        
        if look_id not in self.saved_looks[user_id]:
            self.saved_looks[user_id].append(look_id)
        
        look = next((l for l in FASHION_LOOKS_2026 if l["id"] == look_id), None)
        
        return {
            "success": True,
            "message": f"Look '{look['name'] if look else 'Unknown'}' saved",
            "user_id": user_id,
            "total_saved": len(self.saved_looks[user_id])
        }
    
    def get_saved_looks(self, user_id: str) -> dict:
        """Get user's saved looks."""
        if user_id not in self.user_preferences:
            return {"success": False, "message": f"User {user_id} not found"}
        
        saved_ids = self.saved_looks[user_id]
        saved_looks = [l for l in FASHION_LOOKS_2026 if l["id"] in saved_ids]
        
        return {
            "success": True,
            "user_id": user_id,
            "saved_looks": saved_looks,
            "total_saved": len(saved_looks)
        }
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get user statistics."""
        if user_id not in self.user_preferences:
            return {"success": False, "message": f"User {user_id} not found"}
        
        user_prefs = self.user_preferences[user_id]
        
        return {
            "success": True,
            "user_id": user_id,
            "favorite_vibes": user_prefs["favorite_vibes"],
            "total_recommendations": user_prefs["recommendations_count"],
            "total_saved_looks": len(self.saved_looks[user_id]),
            "created_at": user_prefs["created_at"],
            "recent_recommendations": self.recommendation_history[user_id][-5:]  # Last 5
        }

# Create curator instance
curator = FashionCurator()

# MCP Tools
@server.tool()
def create_user_profile(user_id: str, favorite_vibes: list[str]) -> dict:
    """Create a new user profile with favorite style vibes.
    
    Args:
        user_id: Unique identifier for the user
        favorite_vibes: List of favorite vibes (e.g., ['bold', 'modern', 'romantic'])
    
    Returns:
        Confirmation of user creation with stored preferences.
    """
    return curator.create_user(user_id, favorite_vibes)


@server.tool()
def get_personalized_recommendation(user_id: str) -> dict:
    """Get a personalized fashion look based on user preferences.
    
    Args:
        user_id: The user to get a recommendation for
    
    Returns:
        A personalized fashion look matching user's vibes.
    """
    return curator.get_personalized_look(user_id)


@server.tool()
def save_favorite_look(user_id: str, look_id: int) -> dict:
    """Save a fashion look to user's favorites.
    
    Args:
        user_id: The user saving the look
        look_id: The ID of the look to save
    
    Returns:
        Confirmation of save with updated count.
    """
    return curator.save_look(user_id, look_id)


@server.tool()
def get_user_saved_looks(user_id: str) -> dict:
    """Get all saved looks for a user.
    
    Args:
        user_id: The user to retrieve looks for
    
    Returns:
        List of all saved fashion looks.
    """
    return curator.get_saved_looks(user_id)


@server.tool()
def get_user_statistics(user_id: str) -> dict:
    """Get user statistics and profile information.
    
    Args:
        user_id: The user to get stats for
    
    Returns:
        User preferences, recommendation count, and recent history.
    """
    return curator.get_user_stats(user_id)


@server.tool()
def list_all_looks() -> dict:
    """List all available fashion looks for 2026.
    
    Returns:
        Complete catalog of fashion looks with all details.
    """
    return {
        "success": True,
        "total_looks": len(FASHION_LOOKS_2026),
        "looks": FASHION_LOOKS_2026
    }


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Fashion Curator Server - MCP Server")
    print("=" * 60)
    print(f"Server starting at {datetime.now().isoformat()}")
    print("MCP Tools Available:")
    print("  - create_user_profile")
    print("  - get_personalized_recommendation")
    print("  - save_favorite_look")
    print("  - get_user_saved_looks")
    print("  - get_user_statistics")
    print("  - list_all_looks")
    print("=" * 60)
    print("\nServer running with stateful storage...")
    print("Listening for MCP protocol connections...\n")
    
    # Run the server with MCP protocol (stdin/stdout)
    server.run()
