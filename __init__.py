"""
ComfyUI PyTorch 2.10 Compatibility Patcher
Automatically fixes WanVideoModel for PyTorch 2.10.0+ compatibility
"""

import sys
import torch

class PyTorch210CompatibilityPatcher:
    """
    Node that patches WanVideoModel for PyTorch 2.10+ compatibility.
    
    PyTorch 2.10.0 introduced stricter attribute checking in nn.Module.__getattr__
    which causes AttributeError when BaseModel.__init__() tries to access 
    self.diffusion_model before it's created.
    
    This node monkey-patches the WanVideoModel class to add a placeholder
    nn.Identity() before calling parent __init__(), which satisfies PyTorch 2.10's
    stricter checking.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "force_patch": ("BOOLEAN", {"default": True, "tooltip": "Force patch even if PyTorch < 2.10"}),
                "fix_string_to_seed": ("BOOLEAN", {"default": True, "tooltip": "Fix string_to_seed deprecation warning"}),
                "verbose": ("BOOLEAN", {"default": True, "tooltip": "Print patch status"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "patch_model"
    CATEGORY = "WanVideoWrapper/Utils"
    OUTPUT_NODE = True

    def patch_model(self, force_patch=True, fix_string_to_seed=True, verbose=True):
        """Apply PyTorch 2.10 compatibility patch to WanVideoModel"""
        
        status_messages = []
        
        # Get PyTorch version
        torch_version = torch.__version__
        major, minor = map(int, torch_version.split('.')[:2])
        
        # Check if patch is needed
        needs_patch = (major > 2 or (major == 2 and minor >= 10)) or force_patch
        
        if not needs_patch:
            status = f"✅ PyTorch {torch_version} - No patch needed"
            if verbose:
                print(status)
            return (status,)
        
        try:
            # Try to find WanVideoModel in sys.modules (already loaded by ComfyUI)
            wanvideo_module = None
            for module_name in sys.modules:
                if 'WanVideoWrapper' in module_name and 'nodes_model_loading' in module_name:
                    wanvideo_module = sys.modules[module_name]
                    break
            
            if wanvideo_module is None:
                # Try direct import (different possible paths)
                try:
                    from nodes_model_loading import WanVideoModel
                except:
                    # Last resort - search in custom_nodes
                    import importlib.util
                    import os
                    custom_nodes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
                    wrapper_path = os.path.join(custom_nodes_dir, 'ComfyUI-WanVideoWrapper', 'nodes_model_loading.py')
                    
                    spec = importlib.util.spec_from_file_location("nodes_model_loading", wrapper_path)
                    wanvideo_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(wanvideo_module)
            
            # Get WanVideoModel class
            if hasattr(wanvideo_module, 'WanVideoModel'):
                WanVideoModel = wanvideo_module.WanVideoModel
            else:
                WanVideoModel = getattr(wanvideo_module, 'WanVideoModel')
            
            import torch.nn as nn
            
            # Store original __init__
            original_init = WanVideoModel.__init__
            
            # Create patched __init__
            def patched_init(self, *args, **kwargs):
                """PyTorch 2.10+ compatible __init__"""
                # Create placeholder diffusion_model BEFORE super().__init__()
                # This satisfies PyTorch 2.10's stricter attribute checking
                self.diffusion_model = nn.Identity()
                
                # Call original init (which calls super().__init__())
                # The placeholder will be replaced with actual model later
                original_init(self, *args, **kwargs)
            
            # Apply monkey patch
            WanVideoModel.__init__ = patched_init
            
            status_messages.append(f"✅ WanVideoModel patched for PyTorch {torch_version} compatibility")
            if verbose:
                print(f"✅ WanVideoModel patched for PyTorch {torch_version} compatibility")
                print("   → diffusion_model placeholder added")
                print("   → Compatible with PyTorch 2.9.0 and 2.10.0+")
            
        except ImportError as e:
            msg = f"❌ Failed to import WanVideoModel: {e}"
            status_messages.append(msg)
            if verbose:
                print(msg)
        except Exception as e:
            msg = f"❌ WanVideoModel patch failed: {e}"
            status_messages.append(msg)
            if verbose:
                print(msg)
        
        # Fix string_to_seed deprecation warning
        if fix_string_to_seed:
            try:
                # Find utils module
                utils_module = None
                for module_name in sys.modules:
                    if 'WanVideoWrapper' in module_name and 'utils' in module_name:
                        utils_module = sys.modules[module_name]
                        break
                
                if utils_module is None:
                    # Try importing directly
                    import importlib.util
                    import os
                    custom_nodes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
                    utils_path = os.path.join(custom_nodes_dir, 'ComfyUI-WanVideoWrapper', 'utils.py')
                    
                    if os.path.exists(utils_path):
                        spec = importlib.util.spec_from_file_location("wanvideo_utils", utils_path)
                        utils_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(utils_module)
                
                if utils_module:
                    # Patch string_to_seed import in utils module
                    # Replace the import to use comfy.utils instead of comfy.model_patcher
                    try:
                        from comfy.utils import string_to_seed as new_string_to_seed
                        utils_module.string_to_seed = new_string_to_seed
                        
                        msg = "✅ string_to_seed deprecation fixed"
                        status_messages.append(msg)
                        if verbose:
                            print(msg)
                            print("   → Updated import from comfy.model_patcher to comfy.utils")
                    except ImportError:
                        # comfy.utils doesn't have it, keep old import
                        if verbose:
                            print("   ℹ️  string_to_seed patch skipped (ComfyUI version doesn't need it)")
                else:
                    if verbose:
                        print("   ℹ️  WanVideoWrapper utils not found, string_to_seed patch skipped")
                        
            except Exception as e:
                msg = f"⚠️  string_to_seed patch failed: {e}"
                status_messages.append(msg)
                if verbose:
                    print(msg)
        
        # Return combined status
        final_status = "\n".join(status_messages) if status_messages else "✅ All patches applied"
        return (final_status,)


class PyTorchVersionChecker:
    """Utility node to check PyTorch version and compatibility"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}
    
    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("pytorch_version", "cuda_version", "needs_patch")
    FUNCTION = "check_version"
    CATEGORY = "WanVideoWrapper/Utils"
    OUTPUT_NODE = True

    def check_version(self):
        """Check PyTorch and CUDA versions"""
        
        torch_version = torch.__version__
        cuda_version = torch.version.cuda if torch.cuda.is_available() else "N/A"
        
        # Check if PyTorch 2.10+
        major, minor = map(int, torch_version.split('.')[:2])
        needs_patch = (major > 2 or (major == 2 and minor >= 10))
        
        print("=" * 60)
        print(f"PyTorch Version: {torch_version}")
        print(f"CUDA Version: {cuda_version}")
        print(f"PyTorch 2.10+ Patch Needed: {needs_patch}")
        print("=" * 60)
        
        return (torch_version, cuda_version, needs_patch)


# ComfyUI Node Registration
NODE_CLASS_MAPPINGS = {
    "PyTorch210CompatibilityPatcher": PyTorch210CompatibilityPatcher,
    "PyTorchVersionChecker": PyTorchVersionChecker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PyTorch210CompatibilityPatcher": "PyTorch 2.10 Compatibility Patcher",
    "PyTorchVersionChecker": "PyTorch Version Checker",
}
