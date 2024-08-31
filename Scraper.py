import sys
import subprocess
import re
import time
import datetime
from bs4 import BeautifulSoup

###NOTE: to run this script, you need to do the following steps:
#1) create working_files directory next to script
#2) log in to connectcarolina on Chromium (or use an existing session)
#3) go to course search, and press F12 to open developer tools. Click on network tab
#4) select the current term on the term dropdown at the top of the search.
#5) right click on the resulting POST request and select copy as curl. 
#6) paste contents into COMP_search_curl.sh in SAME DIRECTORY as script
### you can also call the repeat.sh script to have this script run in a loop

#fails if there are too many results
    
def getColoredTD(enrollmentFractionString):
    nums = enrollmentFractionString.split('/')
    tdString = "<td>"
    if enrollmentFractionString == "Seats filled":
        tdString = "<td style='color:red'>"
    if len(nums) < 2:
        return tdString
    if int(nums[1]) > 0 and float(nums[0]) / float(nums[1]) > .85:
        tdString = "<td style='color:orange'>"
    if int(nums[1]) > 0 and int(nums[0]) >= int(nums[1]):
        tdString = "<td style='color:red'>"
    return tdString

#SET UP CHROMIUM OR IT WILL GIVE SO MANY BUGS 
def correctEnrollment(enrollmentString):
    nums = enrollmentString.split('/')
    if len(nums) < 2:
        return enrollmentString
    return str(int(nums[1])-int(nums[0]))+"/"+nums[1]

def getContentById(targetId, data):
    relevantData = ""
    lines = data.splitlines();
    count = 0;
    while count < len(lines):
        line = lines[count]
        if targetId in line:
            relevantData = relevantData + line + "\n"
            while not ("/span" in line):
                count = count + 1
                line = lines[count]
                relevantData = relevantData + line + "\n"
        count = count + 1
    if not relevantData:
        #don't want a crash if there is no description or notes
        if targetId == "DERIVED_CLSRCH_DESCRLONG" or targetId == "SSR_CLS_DTL_WRK_CLASS_NBR" or targetId == "DERIVED_CLSRCH_SSR_CLASSNOTE_LONG":
            return ""
        print("couldn't find match for id "+targetId+"!\n")
    
    soup = BeautifulSoup(relevantData, 'html.parser')
    if targetId == "DERIVED_CSLRCH":
        retString = str(soup.find(id=targetId).get_text()).replace(",", ",<br />")
    elif targetId == "DERIVED_CLSRCH_SSR_CLASSNOTE_LONG":
        #print(relevantData+"\n")
        retString = soup.find(id=targetId).get_text(separator='\n')+"\n"
    else:
        retString = str(soup.find(id=targetId).string).replace(u'\xa0', u'&nbsp;')
    
    return retString

#extract class list(s)
def createSearchCommand(term, state, dept, splitSearch, ICSID, cutoff = 500):
    stateNum = state + 1

    if not splitSearch:
        command = open("COMP_search_curl.sh", "r").read().splitlines()
        command[-1] = makeDeptQuery(term, stateNum, ICSID, dept, 0)
        dept_search_file = "working_files/"+dept+"_search_curl.sh"
        new_command_file = open(dept_search_file, "w")
        for line in command:
            new_command_file.write(line+"\n")
        new_command_file.close()
    else:
        command = open("COMP_search_curl.sh", "r").read().splitlines()
        command[-1] = makeDeptQuery(term, stateNum, ICSID, dept, 2, cutoff)
        dept_search_file = "working_files/second_"+dept+"_search_curl.sh"
        new_command_file = open(dept_search_file, "w")
        for line in command:
            new_command_file.write(line+"\n")
        new_command_file.close()

        command = open("COMP_search_curl.sh", "r").read().splitlines()
        command[-1] = makeDeptQuery(term, stateNum, ICSID, dept, 1, cutoff)
        dept_search_file = "working_files/"+dept+"_search_curl.sh"
        new_command_file = open(dept_search_file, "w")
        for line in command:
            new_command_file.write(line+"\n")
        new_command_file.close()

    return dept_search_file
    
def logResponse(fileName, data):
    log_file = open(fileName, "w")
    log_file.write(data)
    log_file.close()

def startClassList(dept_search_file):
    #use curl to get class list
    count = 0
    numClasses = 0
    classListData = ""
    while (classListData == "" or numClasses == 0) and count < 3:
        classListData = subprocess.run(["bash", dept_search_file], capture_output=True).stdout.decode("utf-8")
        if classListData == "":
            time.sleep(1)
            print("couldn't get classListData, trying again\n")
            count += 1
            continue
        #extract number of classes
        for line in classListData.splitlines():
            if "class section(s) found" in line:
                numClasses = int(re.sub("[^0-9]", "", line))
                break
        print("number of classes: " + str(numClasses))
        if numClasses == 0:
            time.sleep(1)
            print("no classes, trying again\n")
            count += 1
            
            

    logResponse("working_files/dept_response.txt", classListData)

 
    if numClasses == 0:
        print("wasn't able to find any classes")
        return -1

    return numClasses

def addClassEntry(state, dept_search_file, ICSID, i):

    class_search = open(dept_search_file, "r").read().splitlines()
    StateNum = state + 2
    class_search[-1] = "  --data-raw 'ICAJAX=1&ICNAVTYPEDROPDOWN=1&ICType=Panel&ICElementNum=0&ICStateNum="+str(StateNum)+"&ICAction=MTG_CLASS_NBR%24"+str(i)+"&ICModelCancel=0&ICXPos=0&ICYPos=0&ResponsetoDiffFrame=-1&TargetFrameName=None&FacetPath=None&ICFocus=&ICSaveWarningFilter=0&ICChanged=-1&ICSkipPending=0&ICAutoSave=0&ICResubmit=0&ICSID="+ICSID+"&ICActionPrompt=false&ICBcDomData=&ICPanelName=&ICFind=&ICAddCount=&ICAppClsData=' \\"


    class_file_name = "working_files/class_search_curl.sh"
    class_file = open(class_file_name, "w")
    for line in class_search:
        class_file.write(line+"\n")
    class_file.close()

 
    count = 0
    classRawData = ""
    while classRawData == "" and count < 5:
        classRawData = subprocess.run(["bash", class_file_name], capture_output=True).stdout.decode("utf-8")
      
        logResponse("working_files/class_response.txt", classRawData)
        if classRawData == "":
            time.sleep(1)
            print("couldn't get classRawData, trying again\n")
            count += 1
        else:
            classNum = getContentById("SSR_CLS_DTL_WRK_CLASS_NBR", classRawData)
            if classNum == "":
                time.sleep(1)
                print("couldn't get classNum, trying again\n")
                classRawData = ""
                count += 1

    
    className = getContentById("DERIVED_CLSRCH_DESCR200", classRawData)
    classTime = getContentById("MTG_SCHED$0", classRawData)
    instructor = getContentById("MTG_INSTR$0", classRawData)
    room = getContentById("MTG_LOC$0", classRawData)
    unresEnrollmentString = correctEnrollment(getContentById("NC_RC_OPEX_WRK_DESCR1$0", classRawData))
    resEnrollmentString = correctEnrollment(getContentById("NC_RC_OPEX_WRK_DESCR1$1", classRawData))
    waitlistString = correctEnrollment(getContentById("NC_RC_OPEX_WRK_DESCR1$311$$0", classRawData))
    totalSeatsString = getContentById("NC_RC_OPEX_WRK_DESCR1$2", classRawData)
    description = getContentById("DERIVED_CLSRCH_DESCRLONG", classRawData)
    units = getContentById("SSR_CLS_DTL_WRK_UNITS_RANGE", classRawData)
    

    if "COMP" in className and ("89 -" in className or "590 -" in className or "790 -" in className):
        notes = getContentById("DERIVED_CLSRCH_SSR_CLASSNOTE_LONG", classRawData)

        specialTitleStart = notes.find("TITLE:") + 7
        specialTitleEnd = notes.find('\n')
        if specialTitleStart != 6:
        	genericTitleStart = className.find("Topics in Computer Science")
        


    # changed this but might not work on your machine 
    waitlistTD = getColoredTD(waitlistString)

    tableLines = "<tr><td>"+classNum+"</td><td>"+className+"</td><td>"+classTime+"</td><td>"+instructor+"</td><td>"+room+"</td><td>"+unresEnrollmentString+"</td><td>"+resEnrollmentString+"</td>"+totalEnrollmentTD+totalEnrollmentString+"</td>"+waitlistTD+waitlistString+"</td></tr>\n<tr class='expandable'><td colspan=7><strong>Description: </strong>"+description+" "+units+"."

    tableLines = tableLines + "</td></tr>\n"

    return tableLines

term_list = ["fall 2023"]
term_folder_list = ["fall2024"]
term_query_string_list = ["2249"]
numTerms = len(term_list)
termCounter = 0

dept_search_file = "COMP_search_curl.sh"

#extract ICSID from the curl used for the search
dept_search_data = dept_search[-1]
start_ICSID = dept_search_data.find("ICSID=")
end_ICSID = dept_search_data.find("&", start_ICSID)
ICSID = dept_search_data[start_ICSID+6: end_ICSID]
print("retrieved ICSID "+ICSID+"\n")
#extract state number from the curl used for the search
start_state = dept_search_data.find("ICStateNum=")
end_state = dept_search_data.find("&", end_ICSID)
stateNum = int(dept_search_data[start_state+11:end_state])
print("retrieved ICStateNum "+str(stateNum)+"\n")

while termCounter < numTerms:

    term = term_list[termCounter]
    term_folder = term_folder_list[termCounter]
    term_query_string = term_query_string_list[termCounter]


    dept_list = ["COMP", "AAAD", "AMST", "ANTH", "APPL", "ASTR", "BCB", "BIOL", "BIOS", "BMME", "BUSI", "CHEM", "CLAR", "CMPL", "COMM", "DATA", "DRAM", "ECON", "EDUC", "ENEC", "ENGL", "ENVR", "EPID", "EXSS", "GEOG", "HBEH", "HIST", "INLS", "LING", "MATH", "MEJO", "PHIL", "PHYS", "PLAN", "PLCY", "POLI", "PSYC", "ROML", "SOCI", "STOR", "WGST"]

    large_dept_list = ["BIOL","CHEM","ENGL", "HIST", "MATH"]
    large_dept_cutoffs = [500, 250, 150, 250, 500]

    if "summer" in term:
        dept_list = ["COMP","AMST", "COMM", "MATH", "STOR"]
        large_dept_list = []

    print("Starting term "+term)
    
    skipDeptCounter = 0

    for dept in dept_list:

        bigDept = False
        bigCutoff = 500
        if dept in large_dept_list:
            bigDept = True
            bigCutoff = large_dept_cutoffs[large_dept_list.index(dept)]

        print("starting to get data for "+dept)

        dept_search_file = createSearchCommand(term_query_string, stateNum, dept, bigDept, ICSID, bigCutoff)

        numClasses = startClassList(dept_search_file)
        if numClasses == -1 and skipDeptCounter < 4:
            skipDeptCounter += 1
            print("skipping to next department\n")
            continue
        elif numClasses == -1:
            print("something is wrong, giving up\n")
            sys.exit(1)


        html = open("page_template.html", "r").read()



        html = html + "<h1>"+dept+" Courses</h1>\n\n"

        html = html + "<p>Here is information about "+dept+" class enrollment for <strong>"+term+"</strong>. Classes with no meeting time listed are not shown. Feel free to <a href='https://cs.unc.edu/~saba'>contact me</a> with any questions/comments/issues. I am happy to add any departments that are missing from these listings, just reach out to ask!</p>\n\n"

        html = html + "<p><strong>Click <a id='show'>here</a> to show class descriptions</strong>. Click <a id='hide'>here</a> to hide them.</p>\n\n"

        html = html + "<script src='../choose_term.js'></script>\n"

        html = html + "<p> Data also available for: <a href='index.html'>COMP</a>"

        for item in dept_list:
            if item == "COMP":
                continue
            html = html + ", <a href='"+item+"_classes.html'>"+item+"</a>"

        html = html + "</p>\n"

        #get timestamp for start of search
        timestamp = datetime.datetime.now()
        html = html + "<p>Data last updated: "+str(timestamp)+"</p>\n"

        #beginning of table
        html = html + "<table>\n<tr>\n<th>Class Number</th>\n<th>Class</th>\n<th>Meeting Time</th>\n<th>Instructor</th>\n<th>Room</th>\n<th>Unreserved Enrollment</th>\n<th>Reserved Enrollment</th>\n<th>Total Enrollment</th>\n<th>Wait List</th>\n</tr>\n"

      
        for i in range(numClasses):
            time.sleep(1) #avoid too many queries in a rush
            html = html + addClassEntry(stateNum, dept_search_file, ICSID, i)

        #if this is a big dept, we need to repeat some of this work for the second file
        if bigDept:
         
            dept_search_file = "working_files/second_"+dept+"_search_curl.sh"
            numClasses = startClassList(dept_search_file)
            if numClasses == -1 and skipDeptCounter < 4:
                skipDeptCounter += 1
                print("skipping to next department\n")
                continue
            elif numClasses == -1:
                print("something is wrong, giving up\n")
                sys.exit(1)
     
            for i in range(numClasses):
                html = html + addClassEntry(stateNum, dept_search_file, ICSID, i)

       

        html = html + "\n</table>\n</body>\n</html>"
        outFileName = "index.html"
        if dept != "COMP":
            outFileName = dept+"_classes.html"
        outFile = open("working_files/"+term_folder+"/"+outFileName, "w")
        outFile.write(html)
        outFile.close()

        print("done with "+dept+"!")
    
    def start_class_list2(dept_search_file):
    logging.basicConfig(level=logging.INFO)
    max_retries = 3
    retry_count = 0
    num_classes = 0
    class_list_data = ""

    while retry_count < max_retries:
        try:
            # Run the bash script and capture output THIS IS WHAT I ADDED 
            result = subprocess.run(["bash", dept_search_file], capture_output=True, text=True, check=True)
            class_list_data = result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing script: {e}")
            time.sleep(1)
            retry_count += 1
            continue
        
        # Extract number of classes
        match = re.search(r"(\d+)\s+class section\(s\) found", class_list_data)
        if match:
            num_classes = int(match.group(1))
            logging.info(f"Number of classes: {num_classes}")
            if num_classes > 0:
                return num_classes
        
        # If no classes or data issue, retry
        logging.info("No classes found or data issue, retrying...")
        time.sleep(1)
        retry_count += 1
    
    logging.error("Failed to retrieve class list after several attempts.")
    return num_classes

    termCounter += 1
    print("done with term "+term+"!\n")
    

print("done!")