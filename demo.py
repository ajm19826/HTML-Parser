#!/usr/bin/env python3
"""Quick visual demo of NATO Browser with colors."""
import sys
import io

# Set UTF-8 output
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom

def demo():
    """Show a visual demo of the NATO Browser."""
    html = '''
    <html>
    <head>
        <style>
            h1 { font-weight: bold; color: cyan; }
            h2 { color: blue; }
            a { color: blue; text-decoration: underline; }
            code { color: magenta; }
        </style>
    </head>
    <body>
        <h1>NATO ASCII Browser</h1>
        
        <h2>Features</h2>
        <ul>
            <li>View any website in ASCII art</li>
            <li>Click links with your keyboard or mouse</li>
            <li>Submit forms and view results</li>
            <li>Beautiful terminal UI with colors</li>
        </ul>
        
        <h2>Navigation</h2>
        <p>Try clicking on <a href="https://example.com">example.com</a> to get started!</p>
        
        <h2>Example Code</h2>
        <pre><code>python -m nato_browser https://example.com</code></pre>
        
        <blockquote>
            The NATO ASCII Browser brings web browsing to the terminal.
            Simple, fast, and lightweight.
        </blockquote>
        
        <h2>Links</h2>
        <p>
            <a href="https://github.com">GitHub</a>
            <a href="https://wikipedia.org">Wikipedia</a>
            <a href="https://news.ycombinator.com">Hacker News</a>
        </p>
    </body>
    </html>
    '''
    
    parser = DOMBuilder()
    parser.feed(html)
    root = parser.root
    
    rendered, links, controls = render_dom(root, width=80)
    
    print("\n" + "="*80)
    print("NATO ASCII BROWSER - VISUAL DEMO")
    print("="*80 + "\n")
    
    print(rendered)
    
    print("\n" + "="*80)
    print(f"Found {len(links)} links:")
    for num, href, text in links:
        print(f"  [{num}] {text} → {href}")
    print("="*80)

if __name__ == "__main__":
    demo()
