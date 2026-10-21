# À exécuter dans une NOUVELLE cellule de la session Colab déjà utilisée pour SDXL.
# Réutilise les poids chargés. N'écrase ni output.png, ni le résultat déjà importé.
import time
from pathlib import Path
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
from IPython.display import display
from PIL.PngImagePlugin import PngInfo
import json

if not isinstance(globals().get('pipe'), StableDiffusionXLPipeline):
    raise RuntimeError('Le pipeline SDXL doit être chargé dans cette session avant cet essai.')
if not torch.cuda.is_available():
    raise RuntimeError('Le GPU doit être disponible. Aucun téléchargement ou remplacement de modèle ne sera lancé ici.')

photo_prompt = ('Professional landscape photograph of a real botanical garden at sunrise, '
                'natural irregular shrubs and trees, distinct individual leaves, delicate translucent foliage, '
                'weathered stone path, subtle golden morning light, realistic shadows, '
                'natural green colors, believable botanical details, optical depth, no people, no text')
photo_negative = ('illustration, painting, drawing, cartoon, CGI, 3d render, plastic, wool, felt, '
                  'knitted texture, fuzzy spheres, repeated geometric bushes, oversaturated, blurry, text, watermark')
if getattr(pipe, 'hf_device_map', None) or getattr(pipe, '_all_hooks', []):
    raise RuntimeError('Ce pipeline utilise un offload. Chargez d’abord le profil GPU FP16 par tuiles dans une session propre.')
if str(pipe.device) != 'cuda:0' and str(pipe.device) != 'cuda':
    raise RuntimeError('Le pipeline doit être placé sur le GPU avec le chargeur T4 corrigé avant l’essai 1024.')
pipe.enable_vae_tiling()
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, algorithm_type='dpmsolver++', use_karras_sigmas=True)
torch.cuda.synchronize()
photo_started = time.perf_counter()
photo_image = pipe(prompt=photo_prompt, negative_prompt=photo_negative, width=1024, height=1024,
                   num_inference_steps=35, guidance_scale=5.5,
                   generator=torch.Generator(device='cuda').manual_seed(42)).images[0]
torch.cuda.synchronize()
photo_seconds = time.perf_counter() - photo_started
photo_metadata = PngInfo()
photo_metadata.add_text('studio_parameters', json.dumps({'model_id':'stabilityai/stable-diffusion-xl-base-1.0',
    'model_revision':globals().get('revision'), 'prompt':photo_prompt,'negative_prompt':photo_negative,
    'width':1024,'height':1024,'steps':35,'seed':42,'guidance_scale':5.5,'scheduler':'DPM++ / Karras',
    'generation_sec':round(photo_seconds,3)},ensure_ascii=False))
photo_path = Path('essai-photo-1024.png')
photo_image.save(photo_path, pnginfo=photo_metadata)
print(f'Essai natif 1024 × 1024 : {photo_seconds:.2f} secondes. Qualité à juger à 100 %, pas garantie.')
display(photo_image)
# Pour télécharger après examen : from google.colab import files; files.download(str(photo_path))
