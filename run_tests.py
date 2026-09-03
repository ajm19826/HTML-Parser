"""Run quick smoke tests for Phase 1 and Phase 2."""
from __future__ import annotations

import sys
import io

# Set UTF-8 output to handle Unicode box drawing chars
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom
from nato_browser.network.http import fetch

def test_render():
    html = '''<html><head><style>p { color: red; } h1 { font-weight: bold; }</style><title>Test</title></head>
    <body>
      <h1>Big Heading</h1>
      <p style="color:blue">Hello <a href="/about">About</a></p>
      <pre>  line1\n  line2</pre>
      <table><tr><th>Name</th><th>Score</th></tr><tr><td>Alex</td><td>100</td></tr></table>
    </body></html>'''

    b = DOMBuilder()
    b.feed(html)
    root = b.root
    rendered, links, controls = render_dom(root, width=60)
    print('--- Rendered Output ---')
    print(rendered)
    print('--- Links ---')
    print(links)
    print('--- Controls ---')
    print(controls)

    # additional table with colspan/rowspan
    html2 = '''<html><body>
    <table>
      <tr><th>R\C</th><th>Col1</th><th>Col2</th></tr>
      <tr><td rowspan="2">A</td><td colspan="2">Span across</td></tr>
      <tr><td>Below1</td><td>Below2</td></tr>
    </table>
    </body></html>'''
    b2 = DOMBuilder()
    b2.feed(html2)
    r2 = b2.root
    rendered2, links2, controls2 = render_dom(r2, width=60)
    print('--- Table Colspan/Rowspan ---')
    print(rendered2)

def test_audio_video():
    """Test Phase 5: audio/video rendering."""
    html = '''<html><body>
    <audio src="test.mp3" controls></audio>
    <video src="test.mp4">
      <source src="test.webm" type="video/webm">
      <source src="test.mp4" type="video/mp4">
    </video>
    </body></html>'''
    b = DOMBuilder()
    b.feed(html)
    rendered, _, _ = render_dom(b.root, width=60)
    print('--- Audio/Video Rendering (Phase 5) ---')
    print(rendered)

def test_image_cache():
    """Test Phase 4.5: image disk cache."""
    from nato_browser.rendering.images import _get_disk_cache_path, _cache_key_from_url
    import os
    
    cache_dir = _get_disk_cache_path()
    print(f'--- Image Cache Directory ---')
    print(f'Cache dir: {cache_dir}')
    print(f'Cache exists: {os.path.exists(cache_dir)}')
    
    # test cache key generation
    key = _cache_key_from_url('https://example.com/image.jpg', 40)
    print(f'Cache key for image: {key[:16]}...')

def test_fetch():
    print('Fetching https://example.com...')
    final, html, headers, status = fetch('https://example.com')
    print('status=', status, 'final=', final)
    print('html len=', len(html))

def test_ui_import():
    try:
        import nato_browser.ui.app as app
        print('UI import ok')
    except Exception as e:
        print('UI import failed:', e)

def test_tkinter_import():
    """Test Tkinter UI import."""
    try:
        from nato_browser.ui.tkinter_app import NatoTkinterApp
        print('Tkinter UI import ok')
    except Exception as e:
        print('Tkinter UI import failed:', e)

if __name__ == '__main__':
    test_render()
    test_audio_video()
    test_image_cache()
    test_fetch()
    test_ui_import()
    test_tkinter_import()
    print('\nAll tests completed')
    sys.exit(0)
