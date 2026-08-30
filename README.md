# wslbin
A collection of small tools for WSL

## Tools for C programming Classes

* ProCcompile.sh : Compiles C source files in the specified directory using the Visual Studio compiler.
* ProCexec.sh : Executes compiled binaries and outputs the results to a single log file.
* ProCexecStdin.sh : Executes compiled binaries by feeding the contents of a specified file to stdin.
* ProCcatsrc.sh : Concatenates C source files in a directory into a single PDF file.
* identity_check.sh : Detects C sourse files for identical content from a directory.
* Cstrip.py : Removes white spaces and line breaks from C source files. Used by identity_check.sh.
* vscc.sh : Compiles a single C source file using the Visual Studio compiler.

## For CoursePower

* mkCPupload : Organizes the names of PDF files in the current directory and generates a CSV file for grading.
* mkCPuploadDate : Extends mkCPupload by adding submission dates to the CSV file.
* mkCPhist : Reads a CSV file and generates a grade histogram as a PDF.

## Misc
* EEexpAddTopPagePDF.py : Add a ChkPage to PDFs submitted by students
* getRSSzip.sh : Get RSS ZIP file from the surf server

