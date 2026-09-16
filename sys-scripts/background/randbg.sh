#!/bin/sh

bg_path="$HOME/.background"

if [ ! -f "$1" ]; then 
  echo "Provide a valid file path"
  exit 1;
fi 


printf "%s\n" $1 > "${bg_path}.md"
cp $1 "${bg_path}"

awww img --transition-type wipe --transition-angle 30 --transition-step 90 $1

