# %%
# CHECK 1 - MOOSE
import subprocess
result = subprocess.run(["moosez", "--help"], capture_output=True, text=True)
print("MOOSE:", "OK" if result.returncode == 0 else result.stderr[:200])

# %%
# CHECK 2 - TotalSegmentator
result = subprocess.run(["TotalSegmentator", "--help"], capture_output=True, text=True)
print("TotalSegmentator:", "OK" if result.returncode == 0 else result.stderr[:200])

# %%
# CHECK 3 - VoxTell
result = subprocess.run(["voxtell-predict", "--help"], capture_output=True, text=True)
print("VoxTell:", "OK" if result.returncode == 0 else result.stderr[:200])

# %%
# CHECK 4 - GPU
import torch
print("CUDA available:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")
print("Torch version:", torch.__version__)
