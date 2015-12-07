# move to this script's path
cd "${0%/*}"
lessc cosinnus.less > ../css/cosinnus.css
echo cosinnus.css created.
echo Now watching Cosinnus LESS files...
while inotifywait -e close_write,moved_to,create .; do lessc cosinnus.less > ../css/cosinnus.css; done
