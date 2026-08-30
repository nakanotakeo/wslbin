# wslbin
A collection of small tools for WSL

## For C programming class

* ProCcompile.sh : Compiles C source files in the specified directory using the Visual Studio compiler.
* ProCexec.sh : Executes compiled binaries and outputs the results to a single log file.
* ProCexecStdin.sh : Executes compiled binaries by feeding the contents of a specified file to stdin.
*  ProCcatsrc.sh : Concatenates C source files in a directory into a single PDF file.
* identity_check.sh : Checks the identity of C source files in a specified directory.
* Cstrip.py : Strips spaces and CR/LF from C source files. Used by identity_check.sh.
* vscc.sh : Compiles a single C source file using the Visual Studio compiler.

## For CoursePower

* mkCPupload : Organizes the names of PDF files in the current directory and generates a CSV file for grading.
* mkCPuploadDate : Extends mkCPupload by adding submission dates to the CSV file.
* mkCPhist : Reads a CSV file and generates a grade histogram as a PDF.

## Misc
* EEexpAddTopPagePDF.py : Add ChkPage to students submitted pdf
* getRSSzip.sh : get RSS zip file from surf

