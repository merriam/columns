from markdown import util, preprocessors, postprocessors
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.postprocessors import Postprocessor

import xml.etree.ElementTree as etree


class ColumnsPreprocessor(Preprocessor):
    def __init__(self, config):
        self.config = config
        super().__init__()

    def run(self, lines):
        return lines


class ColumnsPostprocessor(Postprocessor):
    def __init__(self, config):
        self.config = config
        super().__init__()

    def run(self, lines):
        return lines


class ColumnsExtension(Extension):
    def __init__(self, **kwargs):
        self.config = {
            'verbose': [False, 'print extra information to stdout'],
            'style': [None, 'style type: default, bare, or stylesheet filename']}
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        md.preprocessors.register(
            ColumnsPreprocessor(self.config), 'columns', 35)  # at end
        md.postprocessors.register(ColumnsPostprocessor(self.config), 'columns', 35)  # at end


def makeExtension(**kwargs):
    return ColumnsExtension(**kwargs)
