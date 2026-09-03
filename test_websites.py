#!/usr/bin/env python3
"""Test NATO Browser with real websites."""
import sys
import io

# Set UTF-8 output
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from nato_browser.network.http import fetch
from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom

def run_website(url):
    """Fetch and render a website."""
    print(f"\n{'='*60}")
    print(f"Fetching: {url}")
    print(f"{'='*60}\n")
    
    try:
        final_url, html, headers, status = fetch(url)
        print(f"Status: {status}")
        print(f"Final URL: {final_url}")
        print(f"Content Length: {len(html)} bytes\n")
        
        # Parse HTML
        parser = DOMBuilder()
        parser.feed(html)
        root = parser.root
        
        # Render to ASCII
        rendered, links, controls = render_dom(root, width=80)
        
        # Show output (first 50 lines)
        lines = rendered.split('\n')
        for i, line in enumerate(lines[:50]):
            print(line)
        
        if len(lines) > 50:
            print(f"\n... ({len(lines) - 50} more lines)")
        
        print(f"\nFound {len(links)} links")
        if links[:5]:
            print("Sample links:")
            for num, href, text in links[:5]:
                print(f"  [{num}] {text[:40]} -> {href[:50]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test with some interesting websites
    sites = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    for site in sites:
        run_website(site)
