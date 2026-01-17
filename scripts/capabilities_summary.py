#!/usr/bin/env python3
"""
Summary of model capabilities detected
"""
from chat import ChatWindow, ModelCapabilities, MODELS_DIR
from pathlib import Path

models = ChatWindow._discover_models_static()

print("\n" + "="*90)
print("MODEL CAPABILITY DETECTION SUMMARY")
print("="*90)

vision_models = []
text_only_models = []
tool_capable = []

for model_name in models:
    model_dir = MODELS_DIR / model_name
    caps = ModelCapabilities.get_capabilities(model_dir)
    
    if caps["has_vision"]:
        vision_models.append(model_name)
    else:
        text_only_models.append(model_name)
    
    if caps["has_tools"]:
        tool_capable.append(model_name)

print(f"\nVision-Capable Models ({len(vision_models)}):")
for model in vision_models:
    print(f"  * {model} [Vision]")

print(f"\nText-Only Models ({len(text_only_models)}):")
for model in text_only_models:
    print(f"  • {model}")

if tool_capable:
    print(f"\nTool-Capable Models ({len(tool_capable)}):")
    for model in tool_capable:
        print(f"  # {model}")
else:
    print(f"\nNo explicit tool-calling metadata found (most models still require prompting for tool use)")

print("\n" + "="*90)
print("KEY FINDINGS")
print("="*90)

# Analyze Qwen3 models
qwen3_models = [m for m in models if "Qwen3" in m]
print(f"\nQwen3 Models ({len(qwen3_models)}):")
for model in qwen3_models:
    model_dir = MODELS_DIR / model
    caps = ModelCapabilities.get_capabilities(model_dir)
    vision = " [Vision]" if caps["has_vision"] else ""
    print(f"  {model}{vision}")

# Analyze Huihui models
huihui_models = [m for m in models if "Huihui" in m]
print(f"\nHuihui Models ({len(huihui_models)}):")
for model in huihui_models:
    model_dir = MODELS_DIR / model
    caps = ModelCapabilities.get_capabilities(model_dir)
    vision = " [Vision]" if caps["has_vision"] else " [Text-Only]"
    print(f"  {model}{vision}")

print("\n" + "="*90)
print("USAGE IN UI")
print("="*90)
print("\nThe model list in ChatLlama now displays capability badges:")
print("  [Vision] - Model supports vision/image input")
print("  [Tools]  - Model has explicit tool-calling support")
print("\nThis helps users quickly identify model capabilities at a glance.")
print("\n" + "="*90 + "\n")
