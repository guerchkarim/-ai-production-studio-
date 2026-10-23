const {spawn}=require('node:child_process');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
async function harness(){
 const root=path.resolve(__dirname,'..');
 const scratch=fs.mkdtempSync(path.join(os.tmpdir(),'studio-e2e-'));
 const output=path.join(root,'.studio-test-output');fs.mkdirSync(output,{recursive:true});
 const python=process.env.STUDIO_PYTHON||(fs.existsSync(path.join(root,'.venv','bin','python'))?path.join(root,'.venv','bin','python'):process.platform==='win32'&&fs.existsSync(path.join(root,'.venv','Scripts','python.exe'))?path.join(root,'.venv','Scripts','python.exe'):'python');
 const env={...process.env,STUDIO_DATA_DIR:scratch,STUDIO_TRUSTED_ORIGINS:'http://127.0.0.1:5175',STUDIO_API_URL:'http://127.0.0.1:8002'};
 const api=spawn(python,['-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8002'],{cwd:root,env,stdio:'pipe'});
 const web=spawn(process.execPath,[path.join(root,'node_modules','vite','bin','vite.js'),'--host','127.0.0.1','--port','5175'],{cwd:root,env,stdio:'pipe'});
 let logs='';for(const p of [api,web]){p.stdout.on('data',d=>logs+=d);p.stderr.on('data',d=>logs+=d);p.on('error',e=>logs+=e.message);}
 try {
  for(const url of ['http://127.0.0.1:8002/api/v1/health','http://127.0.0.1:5175']){
   let ready=false;
   for(let attempt=0;attempt<100;attempt++){
    if(api.exitCode!==null||web.exitCode!==null)throw new Error('Test server stopped: '+logs);
    try{const r=await fetch(url);if(r.ok){ready=true;break;}}catch{}
    await new Promise(r=>setTimeout(r,100));
   }
   if(!ready)throw new Error('Test server not ready: '+logs);
  }
  const exitCode=await new Promise((resolve,reject)=>{const test=spawn(process.execPath,[__filename],{cwd:root,env:{...env,STUDIO_E2E_URL:'http://127.0.0.1:5175/',STUDIO_E2E_OUTPUT:output},stdio:'inherit'});test.on('error',reject);test.on('exit',resolve);});
  if(exitCode!==0)throw new Error('Browser checks failed');
 } finally {
  await Promise.all([api,web].map(p=>new Promise(resolve=>{if(p.exitCode!==null){resolve();return;}p.once('exit',resolve);p.kill('SIGTERM');})));
  fs.rmSync(scratch,{recursive:true,force:true});
 }
}
if(!process.env.STUDIO_E2E_URL){harness().catch(e=>{console.error(e);process.exitCode=1;});}else{
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (require('node:fs').existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(process.env.STUDIO_E2E_URL);
await page.getByLabel('Mot de passe',{exact:true}).fill('test-local-studio-passphrase');
await page.getByRole('button',{name:'Créer mon accès'}).click();
await page.getByRole('heading',{name:'Chaque grande histoire commence ici.'}).waitFor();
await page.screenshot({path:process.env.STUDIO_E2E_OUTPUT+'/dashboard-desktop.png',fullPage:true});
await page.getByRole('button',{name:'Nouveau projet',exact:true}).click();
await page.getByLabel('Nom du projet').fill('Les jardins de demain');
await page.getByLabel('Langue').selectOption('FR / AR');
await page.getByLabel('Budget plafond (€)').fill('12');
await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
await page.getByRole('heading',{name:'Les jardins de demain',exact:true}).first().waitFor();
await page.getByRole('button',{name:'Modifier le projet',exact:true}).click();
await page.getByLabel('Budget plafond (€)').fill('14');
await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
await page.getByRole('button',{name:'Historique · v2',exact:true}).click();
await page.getByRole('dialog').locator('.history-item').nth(1).waitFor();
assert.equal(await page.getByRole('dialog').locator('.history-item').count(),2);
await page.keyboard.press('Escape');

await page.locator('nav').getByRole('button',{name:'Personnages',exact:true}).click();
await page.getByRole('button',{name:'Nouveau personnage',exact:true}).click();
await page.getByLabel('Nom',{exact:true}).fill('نور — Nour');
await page.getByLabel('Description et identité visuelle').fill('Personnage original, veste verte, carnet de croquis. شخصية أصلية');
await page.getByLabel('Intention de voix').fill('Arabe et français, voix douce');
await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
await page.getByRole('heading',{name:'نور — Nour'}).waitFor();
await page.locator('.character-card').getByRole('button',{name:'Modifier',exact:true}).click();
await page.getByLabel('Description et identité visuelle').fill('Personnage original, veste verte et carnet doré. شخصية أصلية');
await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
await page.locator('.character-card').getByRole('button',{name:'Historique',exact:true}).click();
await page.getByRole('dialog').locator('.history-item').nth(1).waitFor();
await page.getByRole('dialog').getByText('Personnage original, veste verte, carnet de croquis. شخصية أصلية',{exact:true}).waitFor();
await page.keyboard.press('Escape');

await page.locator('nav').getByRole('button',{name:'Bibliothèque',exact:true}).click();
await page.getByRole('button',{name:'Importer un média',exact:true}).first().click();
await page.locator('input[type=file]').setInputFiles({name:'reference.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAKklEQVR4nGNImRZFU8QwasGoBaMWjFowasGoBaMWjFowasGoBaMWDBULABdZUEzspj0IAAAAAElFTkSuQmCC','base64')});
await page.getByRole('button',{name:'Importer',exact:true}).click();
await page.getByRole('button',{name:/IMAGE reference.png/}).click();
await page.getByRole('dialog').getByRole('heading',{name:'reference.png'}).waitFor();
await page.keyboard.press('Escape');
await page.locator('nav').getByRole('button',{name:'Personnages',exact:true}).click();
await page.getByRole('button',{name:'Ajouter une référence',exact:true}).click();
await page.getByLabel('Image de référence').selectOption({label:'reference.png'});
await page.getByLabel('Vue ou usage').selectOption('face');
await page.getByLabel('J’approuve cette image comme référence maîtresse.').check();
await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
await page.getByText('Face · Approuvée',{exact:true}).waitFor();
await page.screenshot({path:process.env.STUDIO_E2E_OUTPUT+'/character-references.png',fullPage:true});
await page.locator('nav').getByRole('button',{name:'Tâches',exact:true}).click();
await page.getByRole('button',{name:'Préparer une demande',exact:true}).first().click();
await page.getByLabel('Votre demande').fill('Une serre lumineuse au lever du soleil');
await page.getByLabel('Plafond de la tâche (€)').fill('20');
await page.getByRole('button',{name:'Enregistrer la demande'}).click();
await page.getByRole('alert').filter({hasText:'dépasse le budget'}).waitFor();
await page.getByLabel('Plafond de la tâche (€)').fill('2');
await page.getByRole('button',{name:'Enregistrer la demande'}).click();
await page.getByText('Bloquée',{exact:true}).waitFor();
await page.reload();
await page.locator('nav').getByRole('button',{name:/Tâches/}).click();
await page.getByText('Bloquée',{exact:true}).waitFor();
const colabPacketDownload=page.waitForEvent('download');
await page.getByRole('button',{name:'Exporter pour Colab',exact:true}).click();
await (await colabPacketDownload).saveAs(process.env.STUDIO_E2E_OUTPUT+'/colab-request.json');
await page.getByText('À exécuter dans Colab',{exact:true}).waitFor();
const notebookDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Télécharger le notebook',exact:true}).click();
await (await notebookDownload).saveAs(process.env.STUDIO_E2E_OUTPUT+'/worker.ipynb');
await page.getByRole('button',{name:'Importer le résultat Colab',exact:true}).click();
await page.getByRole('dialog').getByLabel('Résultat Colab ZIP').waitFor();
await page.keyboard.press('Escape');
await page.getByRole('button',{name:'Annuler',exact:true}).click();
await page.getByText('Annulée',{exact:true}).waitFor();
await page.getByLabel('Filtrer par projet').selectOption({label:'Les jardins de demain'});
await page.locator('nav').getByRole('button',{name:'Storyboard',exact:true}).click();
await page.getByLabel('Scénario',{exact:true}).fill('Une serre au lever du soleil.\n\nLe jardin s’éveille.');
await page.getByRole('button',{name:'Enregistrer le scénario',exact:true}).click();
await page.getByRole('button',{name:'Découper le scénario',exact:true}).click();
await page.locator('.shot-card').nth(1).waitFor();
await page.locator('.shot-card').first().getByRole('button',{name:'Modifier le plan',exact:true}).click();
await page.getByLabel('Média du plan').selectOption({label:'reference.png'});
await page.getByLabel('Durée (secondes)').fill('0.5');
await page.getByLabel('J’approuve ce plan.').check();
await page.getByRole('button',{name:'Enregistrer le plan',exact:true}).click();
await page.locator('.shot-card').first().getByText('Approuvé',{exact:true}).waitFor();
await page.locator('nav').getByRole('button',{name:'Montage',exact:true}).click();
await page.getByRole('button',{name:'Depuis les plans approuvés',exact:true}).click();
await page.getByRole('button',{name:'Enregistrer le montage',exact:true}).click();
await page.getByRole('button',{name:'Exporter en MP4',exact:true}).click();
await page.getByRole('heading',{name:'Terminé',exact:true}).waitFor({timeout:30000});
const movie=page.waitForEvent('download');await page.getByRole('link',{name:'Télécharger le MP4',exact:true}).click();
await (await movie).saveAs(process.env.STUDIO_E2E_OUTPUT+'/production.mp4');
await page.screenshot({path:process.env.STUDIO_E2E_OUTPUT+'/montage-export.png',fullPage:true});

await page.locator('nav').getByRole('button',{name:'Projets',exact:true}).click();
await page.locator('.project-card').filter({hasText:'Les jardins de demain'}).click();
const download=page.waitForEvent('download');
await page.getByRole('link',{name:'Exporter le projet ZIP'}).click();
const file=await download;assert(file.suggestedFilename().endsWith('.zip'));await file.saveAs(process.env.STUDIO_E2E_OUTPUT+'/project-export.zip');
await page.getByRole('button',{name:'Restaurer un ZIP',exact:true}).click();
await page.locator('input[name=archive]').setInputFiles(process.env.STUDIO_E2E_OUTPUT+'/project-export.zip');
await page.getByRole('dialog').getByRole('button',{name:'Enregistrer',exact:true}).click();
await page.getByRole('heading',{name:'Les jardins de demain · restauré',exact:true}).first().waitFor();
// Real filesystem package -> background watcher -> casting UI, without manual upload.
await page.locator('nav').getByRole('button',{name:'Voix',exact:true}).click();
await page.getByRole('heading',{name:'Votre casting vocal',exact:true}).waitFor();
const voicePython=process.env.STUDIO_PYTHON||require('node:path').resolve('.venv/bin/python');
const voicePackage=require('node:child_process').execFileSync(voicePython,['-c',`
from pathlib import Path
import os,wave,json,hashlib,shutil
from scripts.colab.archiver_voix import save_voice
base=Path(os.environ['STUDIO_DATA_DIR'])
ref=base/'casting-fixture';ref.mkdir()
for name,duration,value in [('reference.wav',4,3),('replique.wav',1,5)]:
 with wave.open(str(ref/name),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(bytes([value,0])*24000*duration)
sha=hashlib.sha256((ref/'reference.wav').read_bytes()).hexdigest()
(ref/'voix.json').write_text(json.dumps({'profile_id':'M-petit','variant':2,'reference_sha256':sha,'reference_language':'fr'}))
audio=ref/'replique.wav'
audio.with_suffix('.json').write_text(json.dumps({'reference_sha256':sha,'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'language':'ar'}))
_,archive,_=save_voice(base/'Voix-a-importer',ref,audio)
print(archive)
`],{encoding:'utf8'}).trim();
await page.getByRole('heading',{name:'M-petit · variante 2',exact:true}).waitFor({timeout:25000});
await page.locator('.voice-library').getByText('Candidate',{exact:true}).waitFor();
assert.equal(await page.locator('.voice-library audio').count(),2);
const voiceAudioUrl=await page.locator('.voice-library audio').last().getAttribute('src');
assert.equal((await page.request.get(new URL(voiceAudioUrl,page.url()).href)).status(),200);
await page.getByRole('button',{name:'Retenir cette voix',exact:true}).click();
await page.getByRole('button',{name:'Remettre en candidate',exact:true}).waitFor();
await page.locator('.voice-library input[type=file]').setInputFiles(voicePackage);
await page.getByText('Paquet classé dans le casting.',{exact:true}).waitFor();
assert.equal(await page.locator('.voice-library .character-card').count(),1);
await page.getByRole('button',{name:'Utiliser dans le projet sélectionné',exact:true}).click();
await page.getByText('Réplique ajoutée au projet sélectionné.',{exact:true}).waitFor();
await page.screenshot({path:process.env.STUDIO_E2E_OUTPUT+'/casting-automatic.png',fullPage:true});
await page.setViewportSize({width:390,height:844});
await page.screenshot({path:process.env.STUDIO_E2E_OUTPUT+'/casting-mobile.png',fullPage:true});
assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Casting must fit mobile');
await page.setViewportSize({width:1440,height:1100});
// Verify the built PWA shell on the isolated API's production origin.
const productionPage=await browser.newPage();
await productionPage.goto('http://127.0.0.1:8002/');
await productionPage.getByLabel('Mot de passe',{exact:true}).waitFor();
await productionPage.evaluate(()=>navigator.serviceWorker.ready.then(()=>true));
const cachesSafe=await productionPage.evaluate(async()=>{for(const key of await caches.keys()){for(const req of await (await caches.open(key)).keys()){if(new URL(req.url).pathname.startsWith('/api/'))return false;}}return true;});
assert(cachesSafe,'Service worker must not cache private API responses');
await productionPage.close();

await page.locator('nav').getByRole('button',{name:'Vue d’ensemble',exact:true}).click();
await page.screenshot({path:process.env.STUDIO_E2E_OUTPUT+'/dashboard-populated.png',fullPage:true});
await page.setViewportSize({width:390,height:844});await page.waitForTimeout(300);
await page.screenshot({path:process.env.STUDIO_E2E_OUTPUT+'/dashboard-mobile.png',fullPage:true});
assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'No horizontal overflow on mobile');
await page.getByRole('button',{name:'Ouvrir la navigation'}).click();
await page.locator('nav').getByRole('button',{name:'Personnages',exact:true}).click();
await page.getByRole('heading',{name:'نور — Nour'}).waitFor();
assert.equal(errors.length,0,'No browser runtime errors: '+errors.join('; '));
console.log('E2E PASS: owner setup, project/character editing and histories, approved reference image, upload/preview, budget rejection, blocked task, refresh persistence, cancellation, storyboard, real MP4 export, ZIP restore, PWA privacy, Colab exchange controls, automatic casting folder import, voice selection and project use, mobile navigation; no page errors.');
await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});

}
