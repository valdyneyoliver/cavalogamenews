#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radar de Games: agrega manchetes e resumos curtos, sem copiar matérias.
Gera radar.json separado de posts.json e sempre aponta para a fonte original.
"""
import html, json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

OUT = Path('radar.json')
MAX_ITEMS = 40
MAX_AGE_HOURS = 72
UA = 'Mozilla/5.0 (compatible; CavaloGameNewsRadar/1.0)'
FEEDS = [
 'https://news.google.com/rss/search?q=video+games+OR+gaming+OR+videogames&hl=pt-BR&gl=BR&ceid=BR:pt-419',
 'https://news.google.com/rss/search?q=Xbox+OR+PlayStation+OR+Nintendo+OR+PC+games&hl=pt-BR&gl=BR&ceid=BR:pt-419',
 'https://news.google.com/rss/search?q=games+Brasil+OR+games+lançamento+OR+Game+Pass+OR+Steam&hl=pt-BR&gl=BR&ceid=BR:pt-419',
]

def get(url, timeout=20):
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read(), r.geturl()

def plain(s):
    s=html.unescape(s or '')
    s=re.sub(r'(?is)<(script|style).*?>.*?</\1>', ' ', s)
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).strip()

def translate(text):
    text=plain(text)
    if not text: return ''
    # Google Translate endpoint público; se falhar, mantém o texto recebido pelo feed pt-BR.
    try:
        url='https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=pt&dt=t&q='+urllib.parse.quote(text[:1800])
        data,_=get(url,15)
        obj=json.loads(data.decode('utf-8'))
        return ''.join(part[0] for part in obj[0] if part and part[0]).strip() or text
    except Exception:
        return text

def original_url(url):
    try:
        data, final=get(url)
        if 'news.google.com' not in urllib.parse.urlparse(final).netloc: return final
        # Tenta URL original codificada no HTML de redirecionamento.
        page=data.decode('utf-8','ignore')
        m=re.search(r'https?://[^\s"<>]+', page)
        if m and 'google.com' not in urllib.parse.urlparse(m.group(0)).netloc: return html.unescape(m.group(0))
    except Exception:
        pass
    # Não publica URL intermediária do Google como se fosse fonte original.
    return ''

def date_of(item):
    raw=item.findtext('pubDate') or ''
    try:
        d=parsedate_to_datetime(raw)
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception: return datetime.now(timezone.utc)

def source_from_title(title):
    # Google News normalmente entrega "Manchete - Nome da publicação".
    parts=title.rsplit(' - ',1)
    return (parts[1].strip(), parts[0].strip()) if len(parts)==2 else ('Fonte original',title.strip())

def main():
    now=datetime.now(timezone.utc); cutoff=now-timedelta(hours=MAX_AGE_HOURS)
    old=[]
    if OUT.exists():
        try: old=json.loads(OUT.read_text(encoding='utf-8'))
        except Exception: old=[]
    seen={x.get('link') for x in old if x.get('link')}
    found=[]
    for feed in FEEDS:
        try:
            raw,_=get(feed)
            root=ET.fromstring(raw)
            for item in root.findall('.//item'):
                pub=date_of(item)
                if pub < cutoff: continue
                raw_title=plain(item.findtext('title') or '')
                raw_desc=plain(item.findtext('description') or '')
                link=(item.findtext('link') or '').strip()
                if not raw_title or not link: continue
                source, headline=source_from_title(raw_title)
                found.append((pub,headline,raw_desc,link,source))
        except Exception as e: print('[AVISO] Feed indisponível:',e)
    found.sort(key=lambda x:x[0], reverse=True)
    result=[]
    for pub,title,desc,link,source in found:
        if len(result)>=MAX_ITEMS: break
        final=original_url(link)
        if not final or final in seen: continue
        # Traduz título e resumo; o resumo é um trecho editorial curto do feed, não o artigo.
        title_pt=translate(title)
        summary=translate(desc) if desc else f'Confira as informações e os detalhes desta notícia diretamente na fonte: {source}.'
        summary=summary[:360].rsplit(' ',1)[0] if len(summary)>360 else summary
        result.append({'titulo':title_pt,'resumo':summary,'fonte':source,'link':final,'data':pub.astimezone().strftime('%d/%m/%Y %H:%M')})
        seen.add(final)
    # Preserva notícias anteriores ainda dentro do limite para evitar sumiço entre execuções.
    merged=result + [x for x in old if x.get('link') not in {n['link'] for n in result}]
    merged=merged[:MAX_ITEMS]
    OUT.write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'[OK] radar.json atualizado: {len(result)} novas; {len(merged)} no total.')

if __name__=='__main__': main()
