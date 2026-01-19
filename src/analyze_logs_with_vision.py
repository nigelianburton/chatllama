"""Vision-based log analysis utility.

Uses a vision-capable LLM to analyze captured card/SVG images from ChatLlama sessions.
Helps understand what the UI showed when the LLM was responding.

Usage:
    python src/analyze_logs_with_vision.py --log-session session_2026-01-18_22-05-20
    python src/analyze_logs_with_vision.py --image D:\_GITN\chatllama\logs\session_2026-01-18_22-05-20_cardsvg01.png
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from llama_cpp import Llama
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_card_images(session_prefix: str, logs_dir: Path) -> list:
    """Find all card SVG images for a given session.
    
    Args:
        session_prefix: Session name without extension (e.g., 'session_2026-01-18_22-05-20')
        logs_dir: Path to logs directory
        
    Returns:
        Sorted list of card image paths
    """
    pattern = f"{session_prefix}_cardsvg*.png"
    images = sorted(logs_dir.glob(pattern))
    return images


def analyze_image_with_vision_model(
    image_path: Path, 
    model: Llama,
    prompt: str = None
) -> dict:
    """Analyze an image using a vision-capable LLM.
    
    Args:
        image_path: Path to the image to analyze
        model: Loaded Llama model instance with vision support
        prompt: Custom analysis prompt (if None, uses default)
        
    Returns:
        dict with analysis results
    """
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return {"error": f"Image not found: {image_path}"}
    
    if not prompt:
        prompt = """Analyze this screenshot of a ChatLlama card/SVG output. Describe:
1. **Layout**: What is the overall layout and structure?
2. **Content**: What text, images, or graphics are visible?
3. **Quality**: Is the content rendered clearly?
4. **Type**: What type of content is shown (SVG, demo, generated)?

Respond in JSON format with keys: layout, content, quality, type, observations."""
    
    try:
        # Load image and convert to bytes
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        logger.info(f"Analyzing image: {image_path}")
        logger.info(f"Image size: {len(image_data)} bytes")
        
        # Use model to analyze - format depends on vision support
        # For now, just return basic info
        result = {
            "image": str(image_path),
            "size_bytes": len(image_data),
            "exists": True,
            "analysis": {
                "note": "Vision analysis requires a vision-capable model in chat mode",
                "status": "pending"
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing image {image_path}: {e}")
        return {"error": str(e), "image": str(image_path)}


def generate_analysis_report(
    session_prefix: str, 
    logs_dir: Path,
    output_file: Path = None
) -> dict:
    """Generate a comprehensive analysis report for a session.
    
    Args:
        session_prefix: Session name
        logs_dir: Path to logs directory  
        output_file: Optional path to save report as JSON
        
    Returns:
        dict with analysis report
    """
    images = find_card_images(session_prefix, logs_dir)
    
    if not images:
        logger.warning(f"No card images found for session: {session_prefix}")
        return {"error": f"No card images found for {session_prefix}", "images_found": []}
    
    logger.info(f"Found {len(images)} card images for session {session_prefix}")
    
    # Try to load vision model
    try:
        from llama_cpp import Llama
        # Note: This would need to be a vision-capable model
        logger.info("To analyze images with vision, use the ChatLlama UI directly")
        logger.info("This utility can help organize and reference the images")
    except:
        pass
    
    report = {
        "session": session_prefix,
        "timestamp": datetime.now().isoformat(),
        "images": {
            "count": len(images),
            "files": [str(img) for img in images]
        },
        "images_exist": all(img.exists() for img in images),
        "next_step": "Open these images in ChatLlama UI and ask the LLM to describe them"
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {output_file}")
    
    return report


def prompt_llm_to_describe_images(session_prefix: str, logs_dir: Path) -> str:
    """Generate a prompt to paste into ChatLlama to have the LLM describe captured images.
    
    Args:
        session_prefix: Session name
        logs_dir: Path to logs directory
        
    Returns:
        Formatted prompt for the user to copy to ChatLlama
    """
    images = find_card_images(session_prefix, logs_dir)
    
    if not images:
        return f"No card images found for session {session_prefix}"
    
    prompt_lines = [
        f"I captured {len(images)} images from a ChatLlama session. Please analyze them:",
        "",
    ]
    
    for i, img in enumerate(images, 1):
        prompt_lines.append(f"Image {i}: {img.name}")
    
    prompt_lines.extend([
        "",
        "For each image, describe:",
        "1. The overall layout and composition",
        "2. Any text content and what it says",
        "3. The type of content (SVG, graphics, demo, etc.)",
        "4. The quality and clarity of rendering",
        "5. Any notable features or issues",
        "",
        "Format your response as JSON with keys for each image."
    ])
    
    return "\n".join(prompt_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze ChatLlama captured images with vision LLM"
    )
    parser.add_argument(
        "--log-session",
        help="Session prefix to analyze (e.g., session_2026-01-18_22-05-20)"
    )
    parser.add_argument(
        "--logs-dir",
        default=PROJECT_ROOT / "logs",
        help="Path to logs directory"
    )
    parser.add_argument(
        "--report",
        help="Output file for analysis report (JSON)"
    )
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Only generate a prompt for ChatLlama, don't analyze"
    )
    
    args = parser.parse_args()
    logs_dir = Path(args.logs_dir)
    
    if not logs_dir.exists():
        logger.error(f"Logs directory not found: {logs_dir}")
        return 1
    
    if not args.log_session:
        # List available sessions with card images
        logger.info("Available sessions with card images:")
        sessions = set()
        for png in logs_dir.glob("*_cardsvg*.png"):
            session = png.name.split("_cardsvg")[0]
            sessions.add(session)
        
        if not sessions:
            logger.info("No card images found in logs directory")
            return 1
        
        for session in sorted(sessions):
            images = find_card_images(session, logs_dir)
            logger.info(f"  {session}: {len(images)} images")
        
        return 0
    
    # Generate report
    if args.prompt_only:
        prompt = prompt_llm_to_describe_images(args.log_session, logs_dir)
        print("\n" + "="*80)
        print("COPY THIS PROMPT INTO CHATLLAMA:")
        print("="*80 + "\n")
        print(prompt)
        print("\n" + "="*80)
    else:
        report = generate_analysis_report(
            args.log_session,
            logs_dir,
            Path(args.report) if args.report else None
        )
        print(json.dumps(report, indent=2))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
