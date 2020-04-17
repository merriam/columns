import markdown


if __name__ == '__main__':
        txt = """
This is __ins__ text
This is --strike-- or --del-- text
This is **bold** text
This is //italics//, versus *old italics* text
This is *old italics*, **old bold** and ***old confusing*** text
        """
        print(markdown.markdown(txt, extensions=['columns']))

        print(markdown.markdown(txt,
                                extensions=['columns'],
                                extension_configs={
                                        'columns': {'ins_del': True}
                                }))

