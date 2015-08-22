def findLongestString (table):
	width = 0
	for line in table:
		for item in line:
			if len(item) > width:
				width = len(item)
	return width
def findLongestLine(table):
	length = 0
	for line in table:
		if len(line) > length:
			length = len(line)
	return length

#--------------------------------------------------------------------##
#		Main program 
#--------------------------------------------------------------------##

def MakeLatexTable(datalines,   outfile):
	 
	
	 
 
	#--------------------------------------------------------------------##
	#		input
	#--------------------------------------------------------------------##
 
	table 		= list()	
	tablelines 	= list()
	columnWidth 	= dict()	 
	data 		= list()
	size 		= 5
	longestitem 	= 1
	numberofcolumns = 0

	for line in datalines:	 
		dataline = list()
		items = line.split()
		for item in items:
			dataline.append(item)	
		data.append(dataline)
	 
	
	for line in data:
		tableline = list()
		for item in line:			 
			tableline.append(item)
		tableline.append (" \\\\ ")
		table.append(tableline)
	
	columnwidth = findLongestString(table)
	numberofcolumns = findLongestLine(table)			

	#--------------------------------------------------------------------##
	#		output
	#--------------------------------------------------------------------##
	start1 		= """\\documentclass{article}\n"""
	start3 		= """\\begin{document}\n"""
	start2 		= """\\usepackage{booktabs}\n"""
	
	tablestart 	= "\\begin{tabular}" + "{" + 'l' * numberofcolumns + "}" 
	tableend 	= "\\end{tabular}" 
	footer3 	= "\\end{document}\n"

	print(start1, start2, start3, file=outfile)
	print(tablestart, file=outfile)
	for i in range (len (table)):
		for j  in range(len(table[i])):
			item = table[i][j]
			packing = columnwidth - len(item)
			print(' ' * packing + item, end=" ", file=outfile)
			if j < len(table[i]) - 1:
				print("&", end=" ", file=outfile)
		if i == 0:
			print("\\toprule", end=" ", file=outfile)
		if i == 1:
			print("\\midrule", end=" ", file=outfile)
		if i == len(table) - 1:
			print("\\bottomrule", end=" ", file=outfile)
		print(file=outfile)
		
	print(tableend, file=outfile)
	print(footer3, file=outfile)

	#outfile.close()

