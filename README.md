# AToP (Automated Testing of Pipelines)
## Installation
To install the required packages of AToP, simply type:\
`pip install pipeline-tester` from the base directory\
Make sure also that the Python version currently used is >= 3.0 as it is the Python version used for this project.
## Lauching
To launch the application, you should type in the following command (from directory `pipeline-tester`):\
`python atop/manage.py runserver`
## Testing
To test this web application, you may do it by typing (from directory `pipeline-tester`):\
`python atop/manage.py test atop`

(NOTE: you may need administrative rights to perform the testing correctly)

## Resetting the database
To reset the database (and apply the possible new changes to the database), you will have to type in the following commands (from directory `pipeline-tester`):\
`rm atop/db.sqlite3`\
`rm -r atop/atop/migrations`\
`python atop/manage.py makemigrations atop`\
`python atop/manage.py migrate`
