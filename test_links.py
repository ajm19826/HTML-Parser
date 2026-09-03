#!/usr/bin/env python3
"""Debug link parsing."""
import sys
import io

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom

# Simple test with links
html = '''
<html>
<body>
<p>Check out these links:</p>
<a href="https://example.com">Example</a>
<a href="https://google.com">Google</a>
<p><a href="https://github.com">GitHub inside paragraph</a></p>
</body>
</html>
'''

parser = DOMBuilder()
parser.feed(html)
root = parser.root

rendered, links, controls = render_dom(root, width=80)

print("Rendered:")
print(rendered)
print("\nLinks found:")
for num, href, text in links:
    print(f"  [{num}] {text} → {href}")
