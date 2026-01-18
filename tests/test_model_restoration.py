#!/usr/bin/env python3
"""
Test script to verify model restoration when switching modes.
Simulates the combo box behavior without running the full GUI.
"""

class MockComboBox:
    """Mock QComboBox for testing."""
    def __init__(self):
        self.items = []
        self.current_index = 0
    
    def addItem(self, text, userData=None):
        self.items.append((text, userData))
    
    def clear(self):
        self.items = []
        self.current_index = 0
    
    def count(self):
        return len(self.items)
    
    def currentData(self):
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index][1]
        return None
    
    def currentText(self):
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index][0]
        return None
    
    def setCurrentIndex(self, index):
        if 0 <= index < len(self.items):
            self.current_index = index
    
    def itemData(self, index):
        if 0 <= index < len(self.items):
            return self.items[index][1]
        return None
    
    def __repr__(self):
        return f"MockComboBox(items={self.items}, current={self.current_index})"


def simulate_mode_switching():
    """Simulate the mode switching behavior."""
    print("=" * 60)
    print("Testing Model Restoration on Mode Switch")
    print("=" * 60)
    
    # Simulate combo box
    combo = MockComboBox()
    last_local_model = None
    
    # Step 1: Load local models (initial state)
    print("\n[1] Initial Local Mode - Loading local models...")
    local_models = [
        ("👁️ 🔧 Qwen3-VL-8B", "mradermacher/Qwen3-VL-8B-Instruct-abliterated-v2.0"),
        ("🔧 Huihui-LFM2-2.6B", "mradermacher/Huihui-LFM2-2.6B-Exp-abliterated"),
        ("🔧 Ministral-3-8B", "mradermacher/Huihui-Ministral-3-8B-Reasoning"),
    ]
    
    for display_text, model_path in local_models:
        combo.addItem(display_text, userData=model_path)
    
    # Select the second model
    combo.setCurrentIndex(1)
    selected_local = combo.currentData()
    print(f"  Current model: {combo.currentText()}")
    print(f"  Model path (userData): {selected_local}")
    
    # Step 2: Switch to LM Studio mode
    print("\n[2] Switching to LM Studio Mode...")
    print("  Storing current local model...")
    if combo and combo.count() > 0:
        last_local_model = combo.currentData() or combo.currentText()
        print(f"  ✓ Stored: {last_local_model}")
    
    print("  Loading LM Studio models...")
    combo.clear()
    lm_studio_models = [
        ("qwen3-vl-8b (loaded)", "qwen3-vl-8b-instruct"),
        ("huihui-lfm2-2.6b (not-loaded)", "huihui-lfm2-2.6b"),
        ("ministral-3-8b (loaded)", "ministral-3-8b"),
    ]
    
    for display_text, model_id in lm_studio_models:
        combo.addItem(display_text, userData=model_id)
    
    combo.setCurrentIndex(0)
    print(f"  Current LM Studio model: {combo.currentText()}")
    
    # Step 3: Switch back to Local mode
    print("\n[3] Switching back to Local Mode...")
    print("  Repopulating local models...")
    combo.clear()
    for display_text, model_path in local_models:
        combo.addItem(display_text, userData=model_path)
    
    print("  Restoring previously selected local model...")
    if last_local_model and combo:
        found = False
        for i in range(combo.count()):
            if combo.itemData(i) == last_local_model:
                combo.setCurrentIndex(i)
                print(f"  ✓ Restored: {combo.currentText()}")
                print(f"  ✓ Model path: {combo.currentData()}")
                found = True
                break
        
        if not found:
            print(f"  ✗ Model not found: {last_local_model}")
    
    # Verify restoration
    print("\n[4] Verification")
    current_path = combo.currentData()
    if current_path == selected_local:
        print("  ✓ SUCCESS: Model correctly restored!")
        print(f"    Original: {selected_local}")
        print(f"    Current:  {current_path}")
        return True
    else:
        print("  ✗ FAILED: Model not restored correctly")
        print(f"    Expected: {selected_local}")
        print(f"    Got:      {current_path}")
        return False


if __name__ == "__main__":
    success = simulate_mode_switching()
    print("\n" + "=" * 60)
    if success:
        print("TEST PASSED ✓")
    else:
        print("TEST FAILED ✗")
    print("=" * 60)
