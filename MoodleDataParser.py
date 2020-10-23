#!/usr/bin/env python3
import json
import csv
import argparse
import statistics
import mimetypes
import sys
import os

# Set up a dictionary to hold the assessment data. This will be a nested dictionary, with the outer level being a pair of Student Fullanme and a dictionary which itself contains all the data from the moodle gradebook.
datadict = {}

# Testing Functions

def countProgress():
    in_progress=0
    for stu in datadict:
        if datadict[stu]["Status"]=="In progress":
            in_progress+=1
    return(in_progress)
    
def countNevSub():
    count_nev_sub=0
    for stu in datadict:
        if datadict[stu]["Status"]=="Never submitted":
            count_nev_sub+=1
    return(count_nev_sub)
    
def stuNum(n):
    return list(datadict.values())[n]
    
def stuName(name):
    return datadict[name]
    
def findName(partName):
    lst=[]
    for key in datadict.keys():
        if partName.lower() in key.lower():
            lst.append(datadict[key])
    return lst
    
def countTotalAttempts():
    return len(datadict)
    
def totalAverage():
    lst=[]
    for val in datadict.values():
        mark = val['Grade']
        if mark != '-':
            lst.append(float(mark))
    return statistics.mean(lst)
    
def writeOutput(outputfile):
    with open(outputfile,'w') as outputCSV:
        csvWriter = csv.writer(outputCSV, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvWriter.writerow(['Name','Email','Grade'])
        for stu in datadict:
            stuEntry = datadict[stu]
            row = [stuEntry["First Name"]+' '+stuEntry["Surname"],stuEntry["Email"]]
            if stuEntry["Grade"] == '-':
                row.append('')
            else:
                markPercent = float(stuEntry["Grade"])*100/quizTotal
                if markPercent >= 80:
                    row.append('A')
                elif markPercent >= 60:
                    row.append('B')
                elif markPercent >= 40:
                    row.append('C')
                elif markPercent >= 20:
                    row.append('D')
                else:
                    row.append('E')
            csvWriter.writerow(row)
        outputCSV.close()
    
# Set up the basic command line arguments
parser = argparse.ArgumentParser(description='Process Moodle results, from either JSON or CSV.')
parser.add_argument('assessmentResults', metavar='input_file', help='The data file name containing the results data. Must be CSV or JSON')
parser.add_argument('-b', type=int, default=0, metavar='No. Qns', help='The number of questions to breakout separately')
parser.add_argument('-qt','--quiztotal', type=int, default=10, metavar='Quiz Total', help='The maximum possible mark for the quiz. Used to calculate letter grades based on percentages of the quiz total.')
parser.add_argument('--debug', action='store_true',help='log some additional info for debugging purposes')
# Create of group of mutually exclusive option flags. This means that only one piece of analysis can be done at once.
exgroup = parser.add_mutually_exclusive_group()
exgroup.add_argument('--num', dest='num', type=int,
                   help='print the nth object in the data dictionary')
exgroup.add_argument('--name',dest='name',metavar='Name',help='print the data for a student with a given name')
exgroup.add_argument('--findname', '-f',dest='partname',metavar='Name',help='prints the data for all students whose name contains a given string')
exgroup.add_argument('--inprogress','-ip',action='store_true',help='print the number of attempts with status \'In Progress\'')
exgroup.add_argument('--neversubmitted','-ns',action='store_true',help='print the number of attempts with status \'Never Submitted\'')
exgroup.add_argument('-t', '--total',action='store_true',help='print the total number of attempts')
exgroup.add_argument('-a', '--average','--avg',action='store_true',help='print the average of all finished attempts')
exgroup.add_argument('-o', '--out', '--output', metavar='output_file [out.csv]', nargs='?', const='out.csv', help='Output a CSV file of letter grades for uploading to records. If no filename is given, then a default value of \'out.csv\' is used.')
                   
args = parser.parse_args()
debug = args.debug
if debug:
    print(args)
assessmentResults = args.assessmentResults
breakoutQns = args.b
name = args.name
num = args.num
partname = args.partname
inprog = args.inprogress
nevsub = args.neversubmitted
total = args.total
avg = args.average
outfile = args.out
if outfile and os.path.splitext(outfile)[1] != '.csv':
    outfile += '.csv'
quizTotal = args.quiztotal

def processData(data):
    # The overall average data is exported by moodle. I don't want this as part of my dictionary, but I might as well keep it. I'm hoping for the time being that it's always the last item, but this is currently in an 'if' to be safe.
    if data[-1][0] == "Overall average":
        averages = data.pop()
    # Name the key fields. The list comprehension which is concatenated allows for a quick way to use this on quizzes with different numbers of questions using the above variable.
    questionkeys = []
    if breakoutQns>0:
        questionkeys=["Q. "+str(i) for i in range(1,breakoutQns + 1)]
    dictkeys=["Surname","First Name","Email","Status","Started On","Completed On","Time Taken","Grade"]+questionkeys
    # Go through the list and turn it into the data structure mentioned before. An item of the dictionary looks like {'First_name Surname':{'Surname':surname,'First Name':first_name,...,"Q. 1":q1_grade,...} }
    for i in range(len(data)):
        stuname = data[i][1]+' '+data[i][0]
        # One record is exported containing the averages. This information is potentiall relevant so is stored separately, but is excluded from the dictionary. If it was the last item in the imported data, then it will have already been popped above, if not, exclude it anyway. Also, we want to keep the best grade for students that were allowed multiple attempts (for whatever reason).
        if data[i][3] != 'Never submitted' and (stuname not in datadict or int(float(datadict[stuname]["Grade"]))<int(float(data[i][7]))) and stuname != " Overall average":
            # Append the actual data to the dictionary. Create the actual inner data dictionary using a dictionary comprehension.
            datadict[stuname]={dictkeys[j]:data[i][j] for j in range(len(dictkeys))}
        # Handle non-submitted attempts
        if data[i][3] == 'Never submitted':
            marksAwarded = 0
            graded = False
            breakoutStart = 8
            if len(data[i])>breakoutStart+breakoutQns:
                breakoutStart += len(data[i])-breakoutStart-breakoutQns
            for j in range(breakoutStart,breakoutStart+breakoutQns):
                mark = data[i][j]
                if mark != '-':
                    marksAwarded += int(float(mark))
                    graded = True
            if (stuname not in datadict or int(float(datadict[stuname]["Grade"]))<int(float(marksAwarded))) and stuname != " Overall average":
                datadict[stuname] = {dictkeys[j]:data[i][j] for j in range(len(dictkeys))}
                if graded:
                    datadict[stuname]["Grade"] = float(marksAwarded)
    return datadict

mime=mimetypes.guess_type(assessmentResults)

if mime[0] == 'application/json':
    # Load the JSON file from the given file input parameter
    with open(assessmentResults, "r") as read_file:
        data = json.load(read_file)
        # For some reason, this data object is stored as a singleton list, which itself stores all the actual data. This seems to just be how moodle is exporting it. I don't need the extra depth, so just pick out the actual list of data
        data=data[0]
        datadict = processData(data)
elif mime[0] == 'text/csv':
    # Load the CSV file from the given file input parameter
    with open(assessmentResults,'r') as csvfile:
        data = list(csv.reader(csvfile, delimiter=','))
        # The Moodle CSV data seems to contain headings as a first row of the data. For consistency with the JSON -- which doesn't -- we'll pop this out of data and into a separate list
        headers=data.pop(0)
        datadict = processData(data)
else:
    sys.exit('This file doesn\'t appear to be either a CSV or JSON file. Giving up.')

# Based on the given option flags, print the output from the appropriate testing function.

if name:
    print(stuName(name))
elif num:
    print(stuNum(num))
elif partname:
    records = findName(partname)
    print('{0:d} matching records:'.format(len(records)))
    for i in records:
        print('\t',i)
elif inprog:
    print('There were {} attempts with status \'In Progress\''.format(countProgress()))
elif nevsub:
    print('There were {} attempts with status \'Never Submitted\''.format(countNevSub()))
elif avg:
    print('The average grade of all* completed attempts was {:.3f}'.format(totalAverage()))
    print('*This includes \'Never Submitted\' grades which have at least some marked data, but ignores those with no data at all.')
elif outfile:
    writeOutput(outfile)
else:
    print('This data file contains grading data for {} total attempts.'.format(countTotalAttempts()))