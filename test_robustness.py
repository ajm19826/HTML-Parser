#!/usr/bin/env python3
"""Test robustness enhancements with edge case HTML."""
import sys
import io

# Set UTF-8 output
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom

def run_edge_case(title, html):
    """Test parsing and rendering edge case HTML."""
    print(f"\n{'='*60}")
    print(f"Test: {title}")
    print(f"{'='*60}")
    
    try:
        parser = DOMBuilder()
        parser.feed(html)
        root = parser.root
        
        rendered, links, controls = render_dom(root, width=80)
        
        # Show output
        lines = rendered.split('\n')
        for line in lines[:30]:
            if line:
                print(line)
        
        if len(lines) > 30:
            print(f"... ({len(lines) - 30} more lines)")
        
        print(f"\n✓ Success - Links: {len(links)}, Controls: {len(controls)}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test 1: Unbalanced tags
    run_edge_case("Unbalanced Tags", """
        <html>
        <body>
            <h1>Title
            <p>Paragraph without closing p
            <div>Div without closing
        </body>
        </html>
    """)
    
    # Test 2: Self-closing tags
    run_edge_case("Self-Closing Tags", """
        <html>
        <body>
            <h1>Gallery</h1>
            <img src="pic1.jpg" alt="Pic 1">
            <img src="pic2.jpg" alt="Pic 2">
            <br>
            <hr>
            <input type="text" placeholder="Enter text">
        </body>
        </html>
    """)
    
    # Test 3: Nested lists
    run_edge_case("Nested Lists", """
        <html>
        <body>
            <h1>Topics</h1>
            <ul>
                <li>First item
                <li>Second item
                    <ul>
                    <li>Nested 1
                    <li>Nested 2
                    </ul>
                <li>Third item
            </ul>
        </body>
        </html>
    """)
    
    # Test 4: Code with special chars
    run_edge_case("Code Blocks", """
        <html>
        <body>
            <h1>Code Example</h1>
            <pre><code>
def hello():
    print("Hello <world>")
    return True & False
            </code></pre>
        </body>
        </html>
    """)
    
    # Test 5: Complex table with colspan/rowspan
    run_edge_case("Tables", """
        <html>
        <body>
            <table>
            <tr><th>Header 1</th><th colspan="2">Merged Header</th></tr>
            <tr><td>A</td><td>B</td><td>C</td></tr>
            <tr><td rowspan="2">Tall</td><td>D</td><td>E</td></tr>
            <tr><td>F</td><td>G</td></tr>
            </table>
        </body>
        </html>
    """)
    
    # Test 6: Form elements
    run_edge_case("Forms", """
        <html>
        <body>
            <form action="/submit" method="POST">
                <input type="text" name="username" placeholder="Username">
                <input type="password" name="password" placeholder="Password">
                <input type="email" name="email" placeholder="Email">
                <button type="submit">Submit</button>
            </form>
        </body>
        </html>
    """)
    
    # Test 7: HTML5 semantic tags
    run_edge_case("HTML5 Semantic Tags", """
        <html>
        <body>
            <header>
                <h1>Website</h1>
                <nav>
                    <a href="/">Home</a>
                    <a href="/about">About</a>
                </nav>
            </header>
            <article>
                <h2>Article Title</h2>
                <p>Article content here</p>
            </article>
            <aside>
                <h3>Related</h3>
                <p>Related info</p>
            </aside>
            <footer>
                <p>Footer content</p>
            </footer>
        </body>
        </html>
    """)
    
    # Test 8: Blockquotes and colors
    run_edge_case("Blockquotes & Colors", """
        <html>
        <body>
            <h1>Famous Quote</h1>
            <blockquote style="color:blue">
                This is a famous quote that spans multiple lines
                and should be displayed with proper formatting.
            </blockquote>
            <p style="color:red">This is red text</p>
            <p style="font-weight:bold">This is bold text</p>
        </body>
        </html>
    """)
    
    # Test 9: Media tags
    run_edge_case("Media Tags", """
        <html>
        <body>
            <h1>Media</h1>
            <audio controls>
                <source src="sound.mp3" type="audio/mpeg">
                <source src="sound.ogg" type="audio/ogg">
            </audio>
            <video controls width="300" height="200">
                <source src="video.mp4" type="video/mp4">
                <source src="video.webm" type="video/webm">
            </video>
        </body>
        </html>
    """)
    
    # Test 10: Malformed attributes
    run_edge_case("Malformed Attributes", """
        <html>
        <body>
            <h1 class="title" id="main">Title</h1>
            <a href="/page" title="Link to page">Click here</a>
            <img src="image.jpg" alt='with single quotes' width=300 height=200>
            <input type=text name=username placeholder='user'>
        </body>
        </html>
    """)
    
    print("\n" + "="*60)
    print("All robustness tests completed!")
    print("="*60)
