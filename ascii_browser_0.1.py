from html.parser import HTMLParser

class Renderer(HTMLParser):

    def __init__(self):
        super().__init__()
        self.output = ""

    def clean_text(self, text):
        return " ".join(text.split())
    
    def handle_starttag(self, tag, attrs):
        # print("START:", tag)
        if tag == "p":
            self.output += "\n"

        if tag == "hr":
            self.output += "\n"
            self.output += "-" * 40
            self.output += "\n"
        

    def handle_endtag(self, tag):
        # print("END:", tag)
        if tag == "p":
            self.output += "\n"

    def handle_data(self, data):
        data = self.clean_text(data)

        if not data:
            return
        self.output += data




html = """
<html>
<h1>Bigger 

text</h1>
<hr>
<p>Paragraphed text</p>
</html>
"""

parser = Renderer()
parser.feed(html)

print(parser.output)