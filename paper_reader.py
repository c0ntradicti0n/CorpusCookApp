import json
import logging
import os
import regex as re

import config
from client.annotation_protocol import MakeProposals, MakeProposalsIndexed
from client.annotation_client import AnnotationClient
from client.bio_annotation import BIO_Annotation
from client.upmarker import UpMarker
from helpers.os_tools import get_filename_from_path
from shell_commander import print_return_result
client = AnnotationClient()

def web_replace(path):
    return path.replace('.', '_').replace(' ', '_').replace('-', '_')


class paper_reader:
    """ multimedial extractor. it reads text from papers in pdfs, urls, html and other things.

        Formatting of text makes processing harder, text is cluttered up with remarks of the punlisher on every page,
        page and line numbers and other stuff, that must be ignored with the processing, especially, when joining the
        texts of different pages, where sentences continue.

        detecting text by comparing to the letter distribution of normal prose to parts of the text extracted.
    """
    def __init__(self, _threshold = 0.001, _length_limit = 20000):
        #with open('hamlet.txt', 'r+') as f:
        #    self.normal_data = list(f.read())

        self.length_limit = _length_limit
        self.threshold = _threshold

        self.normal_data = list(
                                    'used are variants of the predicate calculus. He  even says, Lately '
                                    'those who think  they ought to be so regarded seem to  be winning. '
                                    'Under these circumstances, it does seem odd for McDermott to devote '
                                    'much space to  complaining about the logical basis  of a book whose '
                                    'very title proclaims  it is about logical foundations. In any  '
                                    'case, given such a title, it wouldnt  seem necessary that readers '
                                    'should  be warned that the foundations being  explored are not '
                                    'In competition with this diversity  is the idea of a unified model '
                                    'of inference. The desire for such a model is  strong among those '
                                    'who study  declarative representations, and  Genesereth and Nilsson '
                                    'are no exception. As are most of their colleagues,  they are drawn '
                                    'to the model of inference as the derivation of conclusions  that '
                                    'are entailed by a set of beliefs.  They wander from this idea in a '
                                    'few  places but not for long. It is not hard  to see why: Deduction '
                                    'is one of the  fews kinds of inference for which we  have an '
                                    'interesting general theory. '.lower()
                                )

    def load_text(self, adress, preprocessor="tika"):
        if preprocessor == "tika":
            logging.info("tika reading text...")
            if not re.match(r"""((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*""",
                adress        ):
                self.raw_text = parser.from_file(adress)
            else:
                response = urllib.request.urlopen(adress)
                data = response.read()  # a `bytes` object
                self.raw_text = parser.from_buffer(data)
        if preprocessor == "pdf2htmlEX":
            with open(adress, adress + ".txt", "r", encoding="utf8") as f:
                self.raw_text = f.read()

    def analyse(self):
        """ Extracts prose text from  the loaded texts, that may contain line numbers somewhere, adresses, journal links etc.
        :return str:  prose text
        """
        logging.info("transferring text to nlp thing...")

        text = self.raw_text['content']
        paragraphs = text.split('\n\n')
        print ("mean length of splitted lines", (mean([len(p) for p in paragraphs])))

        # If TIKA resolved '\n'
        if (mean([len(p) for p in paragraphs])) > 80:
            paragraphs = [re.sub(r"- *\n", '', p) for p in paragraphs]
            paragraphs = [p.replace('\n', " ") for p in paragraphs]
            paragraphs = [p.replace(';', " ") for p in paragraphs]
            joiner = " "
        else:
            # If TIKA did not resolve '\n'
            joiner = " "

        processed_text = joiner.join([p
              for p in paragraphs
                   if
                        p and
                        ks_2samp(self.normal_data, list(p)).pvalue   >   self.threshold
                                      ]
                                     )

        return processed_text.strip() [:self.length_limit]
text_no = 0




def main():
    from twisted.internet import reactor
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Analyse txt, pdf etc. text files for utterances of differences.')
    parser.add_argument('file', type=str, help='file or directory to process')
    parser.add_argument("-p", "--preprocessor", help="if the file is preprocessed with pdf2htmlEX and indexed with true_format_html int hte html, it produces an {path}.html and a {path}.txt file; the processing here produces a css file {path}.css",
                        default="tika")
    args = parser.parse_args()

    def process_single_file(path):
        with open (path, 'r+') as f:
            data = json.load(f)
        indexed_words = {int(index): word for index, word in data['indexed_words'].items() }

        def collect_wrapper (islast, no, lend):
            collect_wrapper.last_index = 0
            def proceed(proposals=""):
                logging.info(f"appending result batch {no+1}/{lend} ")
                proposals, collect_wrapper.last_index = BIO_Annotation.push_indices(proposals, collect_wrapper.last_index)
                collect_wrapper.proposals.extend(proposals)
                if (islast):
                    logging.info(f"last one, tranforming to css")

                    if args.preprocessor =="tika":
                        upmarker_html = UpMarker(_generator='html')
                        html = upmarker_html.markup_proposal_list(proceed.proposals, _indexed_words=indexed_words)
                        result = html
                    elif args.preprocessor =="pdf2htmlEX":
                        upmarker_css = UpMarker(_generator="css")
                        css = upmarker_css.markup_proposal_list(collect_wrapper.proposals, _indexed_words=indexed_words)
                        filename = web_replace(get_filename_from_path(path))

                        css_path = config.apache_css_dir + filename + ".css"
                        with open(css_path, 'w', encoding="utf8") as f:
                            f.write(css)
                        result = f"file {css_path}"

                        reactor.stop()
                        print_return_result(result)
                        logging.info("PaperReader finished")
                    else:
                        logging.error("Preprocessor unknown!")
            return proceed


        logging.info ("Annotation command sent")
        splits = [list(indexed_words.values())[i:i+config.max_len_amp] for i in range(0, len(indexed_words), config.max_len_amp)]
        collect_wrapper.proposals = []
        for n, snippet in enumerate(splits):
            islast = True if (n == len(splits) - 1) else False
            logging.info (f"processing text snippet {n+1}/{len(splits)} with {len(snippet)} chars")
            client.commander(Command=MakeProposalsIndexed,
                             ProceedLocation=collect_wrapper(islast= islast, no= n, lend= len(splits)),
                             indexed=snippet,
                             text_name=path.replace("/", ""))

    process_single_file(path=args.file)
    reactor.run()


if __name__== "__main__":

    main()
