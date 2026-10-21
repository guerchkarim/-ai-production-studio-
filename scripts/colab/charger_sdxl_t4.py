"""SDXL sur T4 : poids FP16 officiels, GPU et VAE par tuiles, sans offload CPU.
Ce chargeur ne garantit pas l'absence d'OOM. Une session propre est requise.
Copiable dans Colab ; aucune modification de budget ou location de machine.
"""
import gc
import time
import torch
import psutil
from diffusers import StableDiffusionXLPipeline
from huggingface_hub import model_info

if not torch.cuda.is_available():
    raise RuntimeError('GPU absent. Reconnectez la session T4 avant de continuer.')
GiB = 1024**3
torch.cuda.empty_cache()
free_gpu, total_gpu = torch.cuda.mem_get_info()
free_ram = psutil.virtual_memory().available
print(f'RAM système libre : {free_ram/GiB:.1f} Go ; GPU libre : {free_gpu/GiB:.1f}/{total_gpu/GiB:.1f} Go')
if total_gpu < 14*GiB or free_gpu < 10*GiB or free_ram < 8*GiB:
    raise RuntimeError('Mémoire libre insuffisante pour ce profil. Redémarrez une session GPU propre ; ne relancez pas en boucle et ne souscrivez pas une offre payante.')
model_id = 'stabilityai/stable-diffusion-xl-base-1.0'
revision = model_info(model_id, token=False).sha
load_started = time.perf_counter()
pipe = StableDiffusionXLPipeline.from_pretrained(
    model_id, revision=revision, variant='fp16', torch_dtype=torch.float16,
    use_safetensors=True, low_cpu_mem_usage=True, token=False
)
pipe.enable_vae_tiling()
pipe.to('cuda')
gc.collect()
torch.cuda.synchronize()
print(f'Chargement FP16 sur GPU terminé en {time.perf_counter()-load_started:.1f} s. VAE par tuiles activé. Aucun calcul image lancé.')
print('La qualité 1024 et le pic mémoire restent à vérifier avec un nouvel essai.')
