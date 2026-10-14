"""Local PDF plan previews using Poppler; original files remain in persistent data."""
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import threading
import uuid

MAX_PDF=10*1024*1024
MAX_PAGES=100
RENDER_LOCK=threading.BoundedSemaphore(1)


def run(command, timeout=30):
    try:
        result=subprocess.run(command, capture_output=True, timeout=timeout,
                              env=dict(os.environ, LC_ALL='C'), check=False)
    except FileNotFoundError:
        raise ValueError('Il supporto PDF non è installato: aggiorna e ricostruisci l’add-on')
    except subprocess.TimeoutExpired:
        raise ValueError('PDF troppo complesso: esporta la sola pagina della planimetria')
    if result.returncode:
        raise ValueError('PDF non leggibile o protetto da password: esporta una copia non protetta')
    return result.stdout


def directory(root, document_id):
    if not isinstance(document_id,str) or not re.fullmatch('[a-f0-9]{32}',document_id):
        raise ValueError('Identificativo planimetria non valido')
    folder=pathlib.Path(root)/document_id
    if not (folder/'originale.pdf').is_file():
        raise FileNotFoundError('PDF originale non trovato')
    return folder


def jpeg_size(data):
    if not data.startswith(b'\xff\xd8'):
        raise ValueError('Anteprima PDF non valida')
    i=2
    while i<len(data):
        if data[i]!=0xff:
            i+=1;continue
        while i<len(data) and data[i]==0xff:i+=1
        marker=data[i];i+=1
        if marker in (0xd8,0xd9):continue
        size=int.from_bytes(data[i:i+2],'big')
        if marker in (0xc0,0xc1,0xc2,0xc3):
            return int.from_bytes(data[i+5:i+7],'big'),int.from_bytes(data[i+3:i+5],'big')
        if size<2:break
        i+=size
    raise ValueError('Dimensioni della planimetria non disponibili')


def preview(root, document_id, page=1):
    folder=directory(root,document_id)
    info=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    if isinstance(page,bool) or not isinstance(page,int) or not 1<=page<=info['pagine']:
        raise ValueError('Pagina PDF non valida')
    target=folder/('pagina-%d.jpg'%page)
    if not target.exists():
        if not RENDER_LOCK.acquire(blocking=False):
            raise ValueError('Un’altra pagina è in elaborazione: riprova tra poco')
        try:
            if not target.exists():
                with tempfile.TemporaryDirectory(dir=folder) as temp:
                    dest=pathlib.Path(temp)/'pagina'
                    run(['pdftoppm','-f',str(page),'-l',str(page),'-singlefile',
                         '-scale-to','2200','-jpeg','-jpegopt','quality=90',
                         str(folder/'originale.pdf'),str(dest)])
                    image=dest.with_suffix('.jpg')
                    if not image.exists() or image.stat().st_size>8*1024*1024:
                        raise ValueError('Anteprima PDF troppo grande')
                    jpeg_size(image.read_bytes())
                    image.replace(target)
        finally:
            RENDER_LOCK.release()
    width,height=jpeg_size(target.read_bytes())
    return dict(info,id=document_id,pagina=page,width=width,height=height,
                url='api/planimetrie/'+document_id+'/pagina/'+str(page))


def import_pdf(root, name, encoded):
    if not isinstance(name,str) or not name.lower().endswith('.pdf'):
        raise ValueError('Seleziona un file PDF')
    if not isinstance(encoded,str) or len(encoded)>((MAX_PDF+2)//3)*4:
        raise ValueError('PDF massimo 10 MB')
    try:
        content=base64.b64decode(encoded,validate=True)
    except ValueError:
        raise ValueError('File PDF non valido')
    if not content or len(content)>MAX_PDF:
        raise ValueError('PDF massimo 10 MB')
    if b'%PDF-' not in content[:1024]:
        raise ValueError('Il file non contiene un PDF valido')
    identifier=uuid.uuid4().hex
    folder=pathlib.Path(root)/identifier
    folder.mkdir(parents=True)
    try:
        (folder/'originale.pdf').write_bytes(content)
        details=run(['pdfinfo',str(folder/'originale.pdf')]).decode('utf-8',errors='replace')
        match=re.search(r'^Pages:\s+(\d+)\s*$',details,re.M)
        if not match or not 1<=int(match[1])<=MAX_PAGES:
            raise ValueError('PDF senza pagine o con più di 100 pagine: esporta la sola planimetria')
        info={'nome':pathlib.Path(name.replace('\\','/')).name[:200],'pagine':int(match[1])}
        (folder/'metadata.json').write_text(json.dumps(info,ensure_ascii=False),encoding='utf-8')
        return preview(root,identifier,1)
    except Exception:
        shutil.rmtree(folder)
        raise
