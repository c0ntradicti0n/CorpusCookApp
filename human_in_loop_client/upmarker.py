class UpMarker:
    def __init__(self):
        pass

    # [{'kind': 'CONTRAST'}, {'kind':'SUBJECT'},  {'kind':'ASPECT'},  {'kind':'CONTRAST_MARKER'},
    # {'kind':'SUBJECT_EXCEPT'}, {'kind':'COMPARISON_MARKER'}]
    #
    annotation_dict = {
        'SUBJECT': ('b','24316C'),
        'CONTRAST': ('b', 'A84138'),
        'ASPECT': ('b', '712660'),
        'CONTRAST_MARKER': ('b', '4A4A19'),
        'SUBJECT_EXCEPT': ('b', '287079'),
        'COMPARISON_MARKER': ('b', '16413A')
    }

    def markup_word(self, word, anno_tag):
        for kind, (mark_tag, color) in self.annotation_dict.items():
            if kind in anno_tag:
                return "[{tag}][color=#{color}]{word}[/color][/{tag}]".format(tag=mark_tag, word=word, color=color)
        else:
           return word

    def markup(self, annotation):
        return " ".join([self.markup_word(*anno) for anno in annotation])

