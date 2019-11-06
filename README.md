# App and scripts for using the CorpusCook-server

## App
To run the app call 

```python main.py``` 

It's a python kivy desktop app, that allows to:

* look at predictions of your text with colorful annotations and correct them:

![Annotation correction with sliders](https://github.com/c0ntradicti0n/CorpusCookApp/raw/master/images/sample_annotation.png)
* load full pdfs (and other formats, that Apache Tika reads) and make predictions on this:

![Annotate paper](https://github.com/c0ntradicti0n/CorpusCookApp/raw/master/images/sample_pdfs_reader.png)

* take the counterexamples from them to make the corpus better (click on the text displayed and select the thing you want to reannotate)

## Script

Run

```buildoutcfg
python human_in_loop_client/paper_reader.py your.pdf
```

Output formatted HTML, that marks the annotations. See e.g. [Annotated Adolph-Gruenbaum-paper](https://raw.githubusercontent.com/c0ntradicti0n/CorpusCookApp/master/pdfs/Adolph%20Gruenbaum%20-%20Physics%2C%20Philosophy%20and%20Psychoanalysis.pdf.html) like this:

![Marked html](https://github.com/c0ntradicti0n/CorpusCookApp/raw/master/images/sample_pdf2html.png)

