# mw2pdf
Convert Mediawiki to PDF via pandoc and latex, including UML conversion 

## Purpose

Given a mediawiki where multiple documents (each spread across
multiple pages) are developed. Provide an
easy way to translate that into a separate PDF per document. Use
pandoc/latex to do so. 

Specific requirement: supported embedded plantUML in the pages, use
plantUML to produce the figures. 

## Usage

### On the wiki

* Provide a page in the wiki where you list all the documents you want
to have translated.
* In that page, put a bullet list with names of wiki pages, one line
per document
* These pages again contain a bullet list of wiki pages. These pages
  will be contained in the final document, in the order in which they
  are listed on this page
* Feel free  to use plantuml in your pages.  

### Translation process

* Put configuration data in config.py: user name, password, etc.
* run build.py
* it will download wiki pages, figures, etc.
* extracts uml, translates it via plantuml
* uses pandocs to translate into latex
* runs pdflatex
* uploads the pdfs and results page 

### Results

* For each document mentioned in the documentlist, there will be a
  file .pdf uploaded and a page with the name of documnet and
  BuildReport added. 
* BuildReports contains error messages as well as a link to the
  PDF. They are also added to a category BuildReport 
* They also have a link to the generated and uploaded PDF. 

## TODOs

* Better handling of figures: captions, size, ...

## Installation

* plantuml jar file is included here, but look for a more up-to-date
version
* python modules needed: mwclient and pypandoc
* installation: python, java, pandoc
