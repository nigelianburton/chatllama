from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

from fastmcp import Client


def _load_image_data_uri(image_path: Path) -> str:
        data = image_path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"


def build_svg(portrait_uri: str, landscape_uri: str) -> str:
        return f"""<svg width=\"480\" height=\"640\" viewBox=\"0 0 480 640\" xmlns=\"http://www.w3.org/2000/svg\">
    <image href=\"{portrait_uri}\" x=\"0\" y=\"0\" width=\"480\" height=\"640\" preserveAspectRatio=\"xMidYMid slice\"/>
    <rect width=\"480\" height=\"640\" fill=\"none\" stroke=\"#d4a373\" stroke-width=\"8\"/>
    <text x=\"240\" y=\"80\" font-family=\"Georgia\" font-size=\"36\" font-weight=\"bold\" text-anchor=\"middle\" fill=\"#ffd60a\">Urban Light</text>
    <text x=\"240\" y=\"110\" font-family=\"Arial\" font-size=\"14\" text-anchor=\"middle\" fill=\"#ff6fb7\">January 2026 • Special Design Issue</text>
    <text x=\"240\" y=\"420\" font-family=\"Arial\" font-size=\"22\" font-weight=\"bold\" text-anchor=\"middle\" fill=\"#ffd60a\">Inside the New Studio Wave</text>
    <text x=\"240\" y=\"450\" font-family=\"Arial\" font-size=\"14\" text-anchor=\"middle\" fill=\"#ff6fb7\">Profiles • Trends • Tools</text>
    <rect x=\"320\" y=\"500\" width=\"120\" height=\"100\" fill=\"#f2f2f2\" stroke=\"#cfcfcf\"/>
    <image href=\"{landscape_uri}\" x=\"320\" y=\"500\" width=\"120\" height=\"100\" preserveAspectRatio=\"xMidYMid slice\"/>
</svg>"""


def _dump_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


async def main() -> None:
    url = "http://127.0.0.1:6821/mcp"
    resources_dir = Path("D:/_GITN/chatllama/SIMPLE/resources")
    portrait_path = resources_dir / "pic1-portrait.jpg"
    landscape_path = resources_dir / "pic2-landscape.jpg"
    svg_payload = build_svg(
        _load_image_data_uri(portrait_path),
        _load_image_data_uri(landscape_path),
    )
    async with Client(url) as client:
        create_result = await client.call_tool("CreateCard", {"isPortrait": True})
        print("CreateCard:", create_result)

        guid = None
        if hasattr(create_result, "data"):
            guid = getattr(create_result, "data")
        if not guid and hasattr(create_result, "structured_content"):
            structured = getattr(create_result, "structured_content") or {}
            guid = structured.get("result")
        if not guid and hasattr(create_result, "content"):
            content = getattr(create_result, "content") or []
            if content:
                guid = getattr(content[0], "text", None)
        if not guid:
            raise RuntimeError("CreateCard did not return GUID")

        draw_result = await client.call_tool("DrawCard", {"GUID": guid, "svg_instructions": svg_payload})
        print("DrawCard:", _dump_result(draw_result))

        print("Card created and drawn. Leaving it open.")


if __name__ == "__main__":
    asyncio.run(main())
