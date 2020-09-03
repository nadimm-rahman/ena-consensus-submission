#!/usr/bin/bash

# AUTHOR=Zahra Waheed
# Minor adaptations made by Nadim Rahman

INPUTFILE=$1

#read the headers file line by line and append to an array
while read sequence
do 
	sequences+=($sequence)
done < $INPUTFILE

declare -a sequences #make the array of strings above into an indexed array
printf "indexed array of consensus sequences is:\n" 
declare -p sequences #displays the attributes and values of each name ##should -p or -a come first?
echo
printf "full array of consensus sequences is:\n" 
echo ${sequences[@]} #prints the entire array 'think of @ as all'

#creating the tab separated chromosome list file
for i in ${sequences[@]}
do 
	printf "%s\t" "${i}" "1" "Monopartite" > ${i}_chromosomelist.txt  
done

gzip *_chromosomelist.txt
ls *chromosomelist.txt.gz > chromosome_list_files.txt

printf "number of chromosome list files generated: " 
ls ./*chromosomelist.txt.gz | wc -l
