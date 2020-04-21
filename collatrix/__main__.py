#---------------------------------------------------------------
#__main__.py
#this script collates measurements from individual csv outputs of
#the morphometriX GUI
#the csvs can be saved either all in one folder or within each individual
#animals folder.
#this version includes a safety net that recalculates the measurement using
#accurate altitude and focal lengths that the user must provie in csvs.
# this version uses PyQt5 instead of easygui (used in v2.0)
#created by: Clara Bird (clara.birdferrer#gmail.com), March 2020
#----------------------------------------------------------------

#import modules
import pandas as pd
import numpy as np
import os, sys
import math
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog, QMessageBox
from PyQt5.QtGui import QIcon

class App(QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'close box to end script'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.show()

        #ask how csvs are saved
        items = ('Individual Folders', 'One Folder', 'DateFlightInd')
        option, okPressed = QInputDialog.getItem(self, "Option","Saved Where", items, 0, False)
        if okPressed and option:
            print("option selected: {0}".format(option))

        #ask if they want safey net
        items = ('yes', 'no')
        safety, okPressed = QInputDialog.getItem(self,"Safety?", "Yes or No?",items,0,False)
        if okPressed and safety:
            print("{0} safety".format(safety))
        #if safety yes, ask for file
        if safety == 'yes':
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            safe_csv, _ = QFileDialog.getOpenFileName(self,"img list w/ altitudes and focal lengths", "","All Files (*);;csv files (*.csv)", options=options)
            print("safety csv = {0}".format(safe_csv))
        elif safety == 'no':
            pass

        #animal id list?
        items = ('no','yes')
        idchoice, okPressed = QInputDialog.getItem(self, "do you want output to only contain certain individuals?",'use animal id list?',items,0,False)
        if idchoice and okPressed:
            print("{0} subset list".format(idchoice))
        if idchoice == 'yes':
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            idsCSV, _ = QFileDialog.getOpenFileName(self,"file containing ID list", "","All Files (*);;csv files (*.csv)", options=options)
            if idsCSV:
                print("ID list file = {0}".format(idsCSV))
        elif idchoice == 'no':
            pass

        #ask for name of output
        outname, okPressed = QInputDialog.getText(self, "output name",'name',QLineEdit.Normal,"")

        #set up list of constants
        constants = ['Image ID', 'Image Path', 'Focal Length', 'Altitude', 'Pixel Dimension']

        #import safety csv if safety selected
        if safety == 'yes':
            dfList = pd.read_csv(safe_csv, sep = ",")
            df_L = dfList.groupby('Image').first().reset_index()
            df_L['Image'] = [x.strip() for x in df_L['Image']]
        elif safety == 'no':
            df_L = "no safety"

        #define functions
        ##duplicate check function
        def anydup(l): #we'll use this function later to check for duplicates
            seen = set()
            for x in l:
                if x in seen: return True
                seen.add(x)
            return False
        ##this is the function that does the collating
        def collate(csvs,measurements,nonPercMeas,df_L,safety):
            for f in csvs: #first loop through all the csvs pulls the measurement names
                print(f)
                temp=pd.read_csv(f,sep='^',header=None,prefix='X',engine = 'python') #read in csv as one column
                df00=temp.X0.str.split(',',expand=True) #split rows into columns by delimeter
                df00 = df00.replace("",np.nan)
                df0 = df00.dropna(how='all',axis = 'rows')
                df0 = df0.fillna('') #replace nans by blank space
                idx = df0.loc[df0[0] == 'Object'].index #find index (row) values of 'Object'
                df = df0.truncate(before=idx[0]) #take subset of df starting at first row containing Object
                head = df.iloc[0] #make list out of names in first row
                df = df[1:] #take the data less the header row
                df.columns = head #set the header row as the df header

                wlist = df.iloc[0] #make list of all the width types
                widths = []
                for ww in wlist: #loop through widths row to make sure only widths are in list
                    if "Width" in str(ww):
                        widths += [str(ww)]

                l = df['Object'].tolist() #make list of Object columns aka. names of measurements made
                l = [x for x in l if pd.isna(x) == False] #eliminate all empty cells
                l = [x for x in l if x not in constants and x != 'Object'] #elimate all other instances of Object
                l = [x for x in l if x] #make sure no blank elements in list

                measurements = measurements + l #add the measurement names to the master list
                nonPercMeas = nonPercMeas + l #copy of the master list that does not include widths

                new_header = df.columns[0:2].values.tolist() + df.iloc[0,2:].values.tolist() #merge header with width names
                df = df[1:] #cut header row off
                df.columns = new_header #make the updated list the new header

                df = df.set_index('Object') #set Object column as the index
                df = df.replace(r'^\s*$', np.nan, regex=True) #replace blank space with nan

                if anydup(l) == True: #check for any duplicate measurement names, if exists, exit code, print error msg
                    print("please check file {0} for duplicate Objects and remove duplicates".format(f))
                    sys.exit("remove duplicate and run script again")
                elif anydup(l) == False:
                    for i in l: #loop through list of measurement types
                        for w in (w for w in widths if w[0].isdigit()): #loop through the widths
                            x = df.loc[i,w] #extract cell value of width of measurement type
                            if pd.isna(x) == False: #if the cell isn't empty
                                ww = i + "-" + w #combine the names
                                measurements += [ww] #add this combined name to the master list

            #now we're going to set up a dictionary to fill in with all the measurements
            #that we will eventually turn into a dataframe where the keys are the columns
            rawM = measurements
            measurements += ['Image','Animal_ID','Altitude','Focal Length','PixD','Notes']
            names = ['Image','Animal_ID','Altitude','Focal Length','PixD','Notes']
            mDict = dict.fromkeys(measurements)
            keys = list(mDict.keys())

            df_all = pd.DataFrame(columns = keys) #make an empty dataframe with the headers being the measurement types/info to pull

            rawMM = set(rawM) #get unique list of measurements

            for f in csvs: #this second loop now goes back through the csvs and pulls the measurement values
                print(f)
                #pull the initial values i.e image, ID, alt, focal length
                temp=pd.read_csv(f,sep='^',header=None,prefix='X',engine = 'python') #import as one column
                df1=temp.X0.str.split(',',expand=True) #split on comma delimeter
                df00 = df1.replace("",np.nan)
                df0 = df00.dropna(how='all',axis = 'rows')
                df0 = df0.fillna('') #replace nans by blank space
                idx = df0.loc[df0[0]=='Object'].index #set object column to index
                df = df0.truncate(after=idx[0]) #subset df to be only top info section

                if option == 'Individual Folders':
                    aID = os.path.split(os.path.split(f)[0])[1] #extract animal ID
                elif option == 'One Folder':
                    aID = df[df[0] == 'Image ID'].loc[:,[1]].values[0] #pull animal id
                    aID = aID[0]
                elif option == 'DateFlightInd':
                    aID = os.path.split(os.path.split(f)[0])[1] #extract animal ID
                mDict['Animal_ID'] = aID

                image = os.path.split(df[df[0] == 'Image Path'].loc[:,1].values[0])[1] #extract image
                print(image)
                mDict['Image'] = image

                alt = float((df[df[0] == 'Altitude'].loc[:,[1]].values[0])[0]) #extract entered altitude
                mDict['Altitude'] = alt

                focl = float((df[df[0] == 'Focal Length'].loc[:,[1]].values[0])[0]) #extract entered focal length
                mDict['Focal Length'] = focl

                pixd = float((df[df[0] == 'Pixel Dimension'].loc[:,[1]].values[0])[0]) #extract entered pixel dimension
                mDict['PixD'] = pixd

                notes = df[df[0] == 'Notes'].loc[:,[1]].values[0] #extract entered notes
                mDict['Notes'] = notes[0]

                #go into the cvs to look for the measurement values
                dfGUI = df0.truncate(before=idx[0]) #now subset the df so we're just looking at the measurements
                head = dfGUI.iloc[0] #isolate the current header row
                dfGUI = dfGUI[1:] #chop off the top 2 rows
                dfGUI.columns = head #make the header the original header
                new_headerG = dfGUI.columns[0:2].values.tolist() + dfGUI.iloc[0,2:].values.tolist() #merge header with width names
                dfGUI = dfGUI[1:] #take the data minus the header row
                dfGUI.columns = new_headerG #reset the headers to this created version
                dfGUI = dfGUI.set_index('Object') #make index column the one named Object

                if safety == 'yes': #pull the altitude, focal length, and pix d from the safety csv by image name
                    alt_act = float(df_L[df_L.Image == image].loc[:,'Altitude'].values[0]) #this says: find row where image = image and pull altitude
                    foc_act = float(df_L[df_L.Image == image].loc[:,'Focal_Length'].values[0])
                    pixd_act = float(df_L[df_L.Image == image].loc[:,'Pixel_Dimension'].values[0])
                else:
                    pass

                for key in keys: #loop through the keys aka future column headers
                    if key in nonPercMeas: #if that key is in the list of measurement types (not widths)
                        if key in dfGUI.index: #if that key (measurement) is in this csv
                            x = float(dfGUI.loc[key,'Length (m)']) #extract the measurement value using location
                            if safety == 'yes': # now is the time to do the back calculations
                                pixc = (x/pixd)*(focl/alt) #back calculate the pixel count
                                xx = ((alt_act/foc_act)*pixd_act)*pixc #recalculate using the accurate focal length and altitude
                            elif safety == 'no':
                                xx = x
                        else: #if this key is not in the csv
                            xx = np.nan
                        mDict[key] = xx #add the value to the respective key
                    elif "%" in key and key.split("-")[0] in dfGUI.index: #if the key is a width
                        row = key.split("-")[0] #split the name of the measurement
                        col = key.split("-")[1] #to get the row and column indices
                        y = float(dfGUI.loc[row,col]) #to extract the measurement value
                        if safety == 'yes': #back calculate and recalculate
                            pixc = (y/pixd)*(focl/alt) #back calculate the pixel count
                            yy = ((alt_act/foc_act)*pixd_act)*pixc #recalculate using the accurate focal length and altitude
                        elif safety == 'no':
                            yy = y
                        mDict[key] = yy
                    elif key not in dfGUI.index and key not in names: #if measurement not in this csv
                        mDict[key] = np.nan


                df_op = pd.DataFrame(data = mDict,index=[1]) #make dictionary (now filled with the measurements from this one csv) into dataframe
                df_all = pd.concat([df_all,df_op],sort = True) # add this dataframe to the empty one with all the measurements as headers

            df_allx = df_all.drop(columns = ['Altitude','Focal Length','PixD']).replace(np.nan,0) #drop non-measurement cols
            return df_allx

        if option == 'Individual Folders':
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            INDfold = QFileDialog.getExistingDirectory(None, "folder containing individual folders",options=options)
            saveFold = QFileDialog.getExistingDirectory(None,"folder where output should be saved",options = options)
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog

            #make lists
            measurements = []
            nonPercMeas = []
            csvs = []

            #loop through individual folders and make list of GUI output csvs
            files = os.listdir(INDfold) #list all folders
            for i in files:
                fii = os.path.join(INDfold,i) #set up full path of folder
                f = os.path.isdir(fii) #check if it's a folder
                if f == True: #if it is a folder
                    clist = os.listdir(fii) #list the contents of the folder (this is the individual folder)
                    for ii in clist:
                        if ii.endswith('.csv'): #if its a csv
                            iii = os.path.join(fii,ii) #set up full file path
                            csvs += [iii] #add to list of csvs

            df_allx = collate(csvs,measurements,nonPercMeas,df_L,safety) #run collating function

        elif option == 'One Folder':
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            GUIfold = QFileDialog.getExistingDirectory(None, str("folder containing MorphoMetriX outputs"),options=options)
            saveFold = QFileDialog.getExistingDirectory(None,str("folder where output should be saved"),options=options)
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog

            #make empty lists
            measurements= []
            nonPercMeas = []

            #set up list of csvs to loop through
            files = os.listdir(GUIfold) #get list of files in the folder
            csvs = [os.path.join(GUIfold,x) for x in files if x.endswith('.csv')] #if it's a csv, make full file path

            df_allx = collate(csvs,measurements,nonPercMeas,df_L,safety) #run collating function

        elif option == "DateFlightInd":
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            GUIfold = QFileDialog.getExistingDirectory(None, str("folder containing MorphoMetriX outputs"),options=options)
            saveFold = QFileDialog.getExistingDirectory(None,str("folder where output should be saved"),options=options)
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog

            #make lists
            measurements = []
            nonPercMeas = []
            csvs = []

            #set up list of csvs to loop through
            files = os.listdir(GUIfold) #list all folders
            print(files)
            for i in files:
                fx = os.path.join(GUIfold,i) #set up full path of folder
                f = os.path.isdir(fx) #check if it's a folder
                if f == True: #if it is a folder
                    filesx = os.listdir(fx)
                    for j in filesx:
                        fy = os.path.join(fx,j)
                        f1 = os.path.isdir(fy)
                        if f1 == True:
                            clist = os.listdir(fy) #list the contents of the folder (this is the individual folder)
                            for ii in clist:
                                if ii.endswith('.csv'): #if its a csv
                                    iii = os.path.join(fy,ii) #set up full file path
                                    csvs += [iii] #add to list of csvs

            df_allx = collate(csvs,measurements,nonPercMeas,df_L,safety) #run collating function


        df_all_cols = df_allx.columns.tolist() #make list of column names
        gby = ['Animal_ID','Image','Notes'] #list of non-numeric columns
        togroup = [x for x in df_all_cols if x not in gby] #setting up list of columns to be grouped

        #now we group by ID and image just incase multiple images were measured for the same animal
        #this would combine those measurements (it's why I replaced nans with 0)
        df_all = df_allx.groupby(['Animal_ID','Image'])[togroup].apply(lambda x: x.astype(float).sum()).reset_index()
        df_notes = df_allx.groupby(['Animal_ID','Image'])['Notes'].first().reset_index()
        df_all =df_all.merge(df_notes,on=['Animal_ID','Image'])

        #calculate body volume
        df_all.columns = df_all.columns.str.replace(".00%", ".0%")

        #sort cols
        cols = list(df_all)
        a = "AaIiTtEeJjRrBbFfWwCcDdGgHhKkLlMmNnOoPpQqSsUuVvXxYyZz" #make your own ordered alphabet
        col = sorted(cols, key=lambda word:[a.index(c) for c in word[0]]) #sort headers based on this alphabet
        df_all1 = df_all1.loc[:,col] #sort columns based on sorted list of column header
        df_all1 = df_all1.replace(0,np.nan) #replace the 0s with nans

        outcsv = os.path.join(saveFold,"{0}_allIDs.csv".format(outname))
        df_all1.to_csv(outcsv,sep = ',')

        if idchoice == 'yes':
            df_ids = pd.read_csv(idsCSV,sep = ',') #read in id csv
            idList = df_ids['Animal_ID'].tolist() #make list of IDs
            df_allID = df_all1[df_all1['Animal_ID'].isin(idList)] #subset full dataframe to just those IDs

            outidcsv = os.path.join(saveFold,"{0}_IDS.csv".format(outname))
            df_allID.to_csv(outidcsv,sep = ',')
        elif idchoice == 'no':
            pass
        print("done, close GUI window to end script")
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
