import itertools
from collections import OrderedDict
from typing import Dict
import logging
import pprint
import difflib

from more_itertools import flatten, pairwise

import config
from client import bio_annotation

simple_html = """
<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>

<style>

span.subject1      {color: red;}
span.contrast1     {color: blue;}

span.subject2      {
    margin: 0.05em;
    padding:0.05em;
    line-height:1.2;
    display:inline-block;
    border-radius:.55em;
    border:2px solid;
    border-color: black;
}
span.contrast2     {
    margin: 0.05em;
    padding:0.05em;
    line-height:1.2;
    display:inline-block;
    border-radius:.025em;
    border:2px solid;
    border-color: black;
}

span.subject3      { text-decoration: underline; 
}
span.contrast3     { font-style: oblique; 
}

/*
span.privative     {    opacity: 0.99;
		                mix-blend-mode: difference;
                       	filter: invert(0.9); 
                       	}
  */                     	
span.threshold     {}  

.indentation     {display:inline-block; 
                  width: 50px;
}
</style>
</head>
<body>
%s
</body>
</html>
"""

class Bwalp:
    level = 0
    paragraph = None
    def __init__(self, _word:str, _id, _level:int=0, _paragraph=None, _before = None, _after = None):
        if not _before:
            self.before = []
            self.after = []
        else:
            self.before = _before
            self.after = _after

        self.word = _word
        self.id = _id
        self.level = _level
        self.paragraph = _paragraph

    def update(self, _tag, _before=[], _after=[], _level=None, _paragraph=None):
        for b, a in zip(_before, _after):
            if not b in self.before:
                self.before.append(b)
                self.after.append(a)
                if _level:
                    self.level = _level
                if _paragraph:
                    self.paragraph = _paragraph
            else:
                _=0
                logging.info('annotating {self} multiple times'.format(self=self))
        return self


    def __str__(self):
        return  "{0} {1} {2}".format(
            "".join(sorted(self.before)),
            self.word,
            "".join(sorted(self.after)[::-1]))

    def delete_beginning(self, tag):
        try:
            self.before.remove(tag)
        except Exception:
            logging.info("Trying to delete beginning, that is not there")

    def delete_everything(self, tag):
        self.delete_beginning(tag)
        self.delete_ending(tag)

    def delete_ending(self, tag):
        try:
            self.after.remove(tag)
        except Exception:
            logging.info("Trying to delete ending, that is not there")


def threewise(iterable):
    "s -> (s0,s1,s2), (s1,s2, s3), (s2, s3, s4), ..."
    iterable = list(iterable)
    l = len(iterable)
    for i in range(1,l-1):
        yield iterable[i-1], iterable[i], iterable[i+1]

css_dict = {
    0: {
    "subject" : """{color: red!important; }""",
    "contrast": """{color: blue!important;}"""},
    1: {
        "subject":"""{
    margin: 0.05em!important;
    padding:0.05em!important;
    line-height:1.2!important;
    display:inline-block!important;
    border-radius:.55em!important;
    border:2px solid!important;
    border-color: black!important;}""",
    "contrast": """{
    margin: 0.05em !important;
    padding:0.05em !important;
    line-height:1.2 !important;
    display:inline-block !important;
    border-radius:.025em !important;
    border:2px solid !important;
    border-color: black; !important}"""},
    2:{
        "subject":"""{ text-decoration: underline !important;}""",
        "contrast": """{ font-style: oblique !important;}"""
    }
}
class CSS_word:
    word = "not set"
    id = 0

    level = 0
    def __init__(self, _word, _id):
        self.annotation = []
        self.word = _word
        self.id = _id

    def update(self, _tag, _before=[], _after=[], _level=None, _paragraph=None):
        self.annotation.append(_tag)
        return self

    def collect_css (indexed_csswords, _indexed_words):
        #indexed_csswords = CSS_word.align_with_real (indexed_csswords, _indexed_words)
        css_collection = {level: {annotation_tag: [] for annotation_tag in annotation.keys()} for level, annotation in css_dict.items()}
        for i, indexed_cssword in indexed_csswords.items():
            if indexed_cssword.annotation:
                for level, annotation in enumerate(indexed_cssword.annotation):
                    css_collection[0][annotation.lower()].append(indexed_cssword.id)
                    # TODO make level variant again

        css_markup_lists = []
        for level, css_tags in css_dict.items():
            for annotation, format in css_tags.items():
                ids = css_collection[level][annotation.lower()]
                if ids:
                    ids_str = ", ".join(["#"+config.INDEX_WRAP_TAG_NAME+str(id) for id in ids])
                    css_markup_lists.append(f"""{ids_str} {format}""")
        css_markup_lists.append("z {background:rgba(1,1,1,0.09) !important;}")
        css = "\n\n".join(css_markup_lists)
        return css

    def align_with_real(indexed_csswords, _indexed_words):
        s = difflib.SequenceMatcher(None,
                                    [icw.word for icw in indexed_csswords.values()],
                                    list(_indexed_words.values()))

        result = {}
        for block in s.get_matching_blocks():
            print (
            "exact match of length", block.size, "starting at indices", block.a, "and", block.b)
            for i in range(0,block.size):
                result[block.b + i] = indexed_csswords[block.a + i]
        return result

    def __repr__(self):
        return f"css {self.word}"


class UpMarker:
    def __init__(self, _generator='bbcode'):
        """

        :param _generator:
         - html
         - tml body content of html
         - bbcode (kivy formatting)
        """
        self.generator = _generator

        if _generator == 'tml':  # html torso
            self.generator = 'html'
            self.body['html'] = "%s"


    nl = {
        'bbcode': Bwalp(_word="\n", _id=0),
        'html': Bwalp(_word="<br />\n", _id=0)
    }
    indent = {
        'bbcode': Bwalp(_word="~~~", _id=0),
        'html': Bwalp(_word="<span class='indentation'>  </span>", _id=0)
    }
    sincere = {
        'bbcode': [],
        'html': [('',''),('<span class="privative">','</span>')]
    }
    threshold = {
        'bbcode':[],
        'html': [("<hr class='threshold'>",''),("<hr class='threshold'>",''),("<hr class='threshold'>",''),("<hr class='threshold'>",'')]
    }
    body = {
        'bbcode': "%s",
        'html': simple_html
    }
    _generator_tags = {
        'bbcode': (('[', ']'), ('[/',']'), ('[/',']'),  ('[/',']')),
        'html': (('<', '>'), ('</','>'),  ('</','>'),  ('</','>'))
    }
    annotation_dicts = {
        'bbcode' :
        [{
            'SUBJECT': ('b','color=#24316C'),
            'CONTRAST': ('b', 'color=#A84138'),
            'ASPECT': ('b', 'color=#712660'),
            'CONTRAST_MARKER': ('b', 'color=#4A4A19'),
            'SUBJECT_EXCEPT': ('b', 'color=#287079'),
            'COMPARISON_MARKER': ('b', 'color=#16413A')
        }, {
        'SUBJECT': ('i'),
        'CONTRAST': ('u'),
        'ASPECT': ('b', 'color=#F1FF1F'),
        'CONTRAST_MARKER': ('b', 'color=#F1FF1F'),
        'SUBJECT_EXCEPT': ('b', 'color=#F1FF1F'),
        'COMPARISON_MARKER': ('b', 'color=#F1FF1F')
        },
        {
        'SUBJECT': ('i'),
        'CONTRAST': ('u'),
        'ASPECT': ('b', 'color=#F1FF1F'),
        'CONTRAST_MARKER': ('b', 'color=#F1FF1F'),
        'SUBJECT_EXCEPT': ('b', 'color=#F1FF1F'),
        'COMPARISON_MARKER': ('b', 'color=#F1FF1F')
        },
        {
        'SUBJECT': ('i'),
        'CONTRAST': ('u'),
        'ASPECT': ('b', 'color=#F1FF1F'),
        'CONTRAST_MARKER': ('b', 'color=#F1FF1F'),
        'SUBJECT_EXCEPT': ('b', 'color=#F1FF1F'),
        'COMPARISON_MARKER': ('b', 'color=#F1FF1F')
        }
    ]
    ,
    'html':
    [{
            'SUBJECT':  ('span class="subject level1 subject1"',),
            'CONTRAST': ('span class="contrast level1 contrast1"',),
            'ASPECT': ('b', 'color=#712660'),
            'CONTRAST_MARKER': ('b', 'color=#4A4A19'),
            'SUBJECT_EXCEPT': ('b', 'color=#287079'),
            'COMPARISON_MARKER': ('b', 'color=#16413A')
        }, {
            'SUBJECT':  ('span class="subject level2 subject2"',),
            'CONTRAST': ('span class="contrast level2 contrast2"',),
            'ASPECT': ('b', 'color=#F1FF1F'),
            'CONTRAST_MARKER': ('b', 'color=#F1FF1F'),
            'SUBJECT_EXCEPT': ('b', 'color=#F1FF1F'),
            'COMPARISON_MARKER': ('b', 'color=#F1FF1F'),
        }, {
            'SUBJECT':  ('span class="subject level3 subject3"',),
            'CONTRAST': ('span class="contrast level3 contrast3"',),
            'ASPECT': ('b', 'color=#F1FF1F'),
            'CONTRAST_MARKER': ('b', 'color=#F1FF1F'),
            'SUBJECT_EXCEPT': ('b', 'color=#F1FF1F'),
            'COMPARISON_MARKER': ('b', 'color=#F1FF1F'),
        }, {
            'SUBJECT':  ('span class="subject level4 subject4"',),
            'CONTRAST': ('span class="contrast level4 contrast4"',),
            'ASPECT': ('b', 'color=#F1FF1F'),
            'CONTRAST_MARKER': ('b', 'color=#F1FF1F'),
            'SUBJECT_EXCEPT': ('b', 'color=#F1FF1F'),
            'COMPARISON_MARKER': ('b', 'color=#F1FF1F'),
        }]
    }

    def new_start_dict(self, indexed_words, data_model):
        """ Creating a dict, that contains a bwalp for each possible index, filling up missing ones"""
        max_index = max(list(indexed_words.keys()))+1
        min_index = min(list(indexed_words.keys()))

        which_not_indexed = [i for i in range(min_index, max_index) if i not in indexed_words ]
        if which_not_indexed:
            logging.error(f"some words could not be indexed again. queer alignment. {which_not_indexed}")
        return  OrderedDict(
            (i, data_model(_word=indexed_words[i], _id=i)) if i in indexed_words else (i, data_model(' [missing index]'))
            for i in range(min_index, max_index))

    def gen_before_tag(self, tag):
        gcs = self._generator_tags[self.generator][0]
        return gcs[0] + tag + gcs[1]

    def gen_after_tag(self, tag):
        gce = self._generator_tags[self.generator][1]
        return gce[0] + tag.partition(' ')[0].partition('=')[0] + gce[1]

    before_to_after_map = {}

    def markup_word(self, tag, paragraph, new_level, sincerity):
        before = []
        after = []
        level = None
        if self.generator == "css":
            return {
                 '_tag': tag,
                 '_before': [],
                 '_after':  [],
                 '_level':  new_level,
                 '_paragraph': paragraph
            }

        else:
            if len(tag)>2:
                non_bio_tag = tag

                # beginning and closing output tag
                gc_beg = self.annotation_dicts[self.generator][new_level][non_bio_tag]
                gc_end = self.annotation_dicts[self.generator][new_level][non_bio_tag]

                before.extend(self.gen_before_tag(code_tag) for code_tag in gc_beg)
                after.extend (self.gen_after_tag(code_tag) for code_tag in gc_end)
                self.before_to_after_map.update(
                       {
                        self.gen_before_tag(start_tag):self.gen_after_tag(end_tag)
                        for start_tag, end_tag in zip (gc_beg, gc_end)
                       })
                level = new_level

                if sincerity:
                    before.append(self.sincere[self.generator][sincerity][0])
                    after.append( self.sincere[self.generator][sincerity][1])
                    self.before_to_after_map.update(
                        {
                            self.sincere[self.generator][sincerity][0]: self.sincere[self.generator][sincerity][1]
                        })

            return {
                 '_tag': tag,
                 '_before': before,
                 '_after': after,
                 '_level': level,
                 '_paragraph': paragraph
            }

    def wrap_indent_paragraph(self, highlighted_dict: Dict[int, Bwalp],  wrap:int=80, fill:str= " ", dont=False) -> str:
        if dont:
            return highlighted_dict
        width = 0

        def break_line(i):
            yet_written.append(self.nl[self.generator])
            if i:
                yet_written.extend([fill] * i)
            return len ([fill]) * i

        first = next(iter(highlighted_dict.values()))

        yet_written = []
        yet_indented = first.level
        yet_paragraph = first.paragraph

        for index, bwalp in highlighted_dict.items():
            additional_width = len(bwalp.word)

            # wrap, when line full
            if width + additional_width > wrap:
                additional_width += break_line(bwalp.level)
                width = 0

            # wrap, when new indentation level
            elif bwalp.level != yet_indented:
                additional_width += break_line(bwalp.level)
                width = 0

            # on new paragraph also
            elif bwalp.paragraph != yet_paragraph:
                additional_width += break_line(bwalp.level)
                additional_width += break_line(bwalp.level)
                width = 0

            yet_written.append(bwalp)
            width += additional_width
            yet_indented = bwalp.level
            yet_paragraph = bwalp.paragraph

        self.conspan(yet_written, spans=list(itertools.groupby(yet_written, key=lambda x: x.before)))
        result = " ". join([str(xyz) for xyz in yet_written])
        return result

    def markup_annotation(self, annotation, start_level=0):
        if not annotation:
            raise ValueError("annotation must not be empty")

        spans = list(bio_annotation.BIO_Annotation.annotation2nested_spans(annotation))
        highlighted = self.new_start_dict(dict(enumerate(word for word, tag in annotation)), data_model=Bwalp)

        for an_set in spans:
            for tag, span_range, span_annotation in an_set:
                for index in range(*span_range):
                    highlighted[index].update(**self.markup_word(tag, paragraph=0, new_level=start_level, sincerity=True))

        return self.body[self.generator] % "".join(  # insert at format mark in body
            self.wrap_indent_paragraph(
                highlighted,
                fill=self.indent[self.generator],
                wrap=130)
        )

    def reasonable(self, annotation):
        return len(annotation) >= 2 and all (len(span)==2 for span in annotation)

    def markup_proposal_list(self, proposals, _indexed_words=None):
        self._indexed_words = _indexed_words
        self.indices = _indexed_words

        proposals = sorted(proposals, key=lambda d: d['indices'][0])
        #if text:
        #    self.indices = dict(enumerate(text.split()))
        #else:
        #    self.indices = {index: word for annotation in proposals for (word, tag), index in
        #                     zip(annotation['annotation'], annotation['indices'])}
        if self.generator == "css":
            data_model = CSS_word
        else:
            data_model = Bwalp

        highlighted = self.new_start_dict(self.indices, data_model)

        def update_dict_from_annotation(indices, annotation, paragraph, start_level, sincerity, mark_end, yes_no):
            res = {}
            spans = list(bio_annotation.BIO_Annotation.annotation2nested_spans(annotation))

            try:
                logging.info(f"using {pprint.pformat(list(zip(indices, annotation)))}")
            except TypeError:
                raise
            if self.reasonable(spans ):
                highlighted = self.new_start_dict(dict((index, word) for index, (word, tag) in zip(indices, annotation)), data_model)
                start = min(indices)
                for an_set in spans:
                    for tag, span_range, span_annotation in an_set:
                        for local_index in range(*span_range):
                            res[start + local_index] = \
                                    highlighted[start + local_index].update(
                                        **self.markup_word(
                                            tag,
                                            paragraph=0,
                                            new_level=start_level,
                                            sincerity=True))

            return res

        def subdate(highlighted, subs):
            for sub_paragraph, sub_annotation in enumerate(subs):
                highlighted.update(
                    update_dict_from_annotation(
                        sub_annotation['indices'], 
                        sub_annotation['annotation'], 
                        paragraph,
                        start_level=sub_annotation['depth'],
                        sincerity=annotation['privative'],
                        mark_end=annotation['mark_end'],
                        yes_no=annotation['difference']
                        )                    
                    )
            #for sub_paragraph, sub_annotation in enumerate(subs):
            #    subdate(highlighted, sub_annotation['subs'])

        for paragraph, annotation in enumerate(proposals):
            highlighted.update(
                        update_dict_from_annotation(annotation['indices'], 
                            annotation['annotation'], 
                            paragraph, 
                            start_level=0,
                            sincerity=annotation['privative'],
                            mark_end=annotation['mark_end'],
                            yes_no=annotation['difference']
                            )
            )


            # Overwrite higher-level annotations with lower level for indenting them
            #subdate(highlighted=highlighted, subs=annotation["subs"])

        if self.generator=="css":
            return CSS_word.collect_css(highlighted, _indexed_words=self._indexed_words)
        return self.body[self.generator] % "".join (self.wrap_indent_paragraph(
                highlighted,
                fill=self.indent[self.generator],
                wrap=130 ))

    def conspan(self, yet_written,  spans=[]):
        # don't want to use set, want to use for

        unique = set([tag for tags, span_group in spans for tag in tags])
        to_call = []
        for u in unique:

            for bwalp1, bwalp2 in pairwise(yet_written):
                if u in set(bwalp1.before) and u in set(bwalp2.before):
                    try:
                        to_call.append((bwalp1.delete_ending, self.before_to_after_map[u]))
                        to_call.append((bwalp2.delete_beginning, u ))
                    except KeyError:
                        raise

        for procedure, arg in to_call:
            procedure(arg)