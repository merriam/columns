from markdown.extensions import Extension

class Columns(Extension):
    def extendMarkdown(self, md, md_globals):
        # Insert code here to change markdown's behavior.
        print("Hello from my extension")
