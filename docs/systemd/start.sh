
# Change to application dir, activate venv and start application
cd "$(realpath "$(dirname $(realpath $0))/../..")"

# Start window manager
openbox-session &

# Disable energy features to avoid black screens
[ `which xset` ] && ( xset -dpms ; xset s off )

# Set startup background
feh --bg-scale ./common/static/common/background.png
rm -f ./data/background.txt

# Background listener
(
  while [ "1" = "1" ] ; do
    if [ -f ./data/background.txt ] ; then
      if [ -s ./data/background.txt ] ; then
        convert -font helvetica -fill white -gravity South -pointsize 25 -annotate +0+100 "$(cat ./data/background.txt)" ./common/static/common/background.png ./data/background.png
      else
        rm -f ./data/background.png
      fi
      if [ -s ./data/background.png ] ; then
        feh --bg-scale ./data/background.png
      else
        feh --bg-scale ./common/static/common/background.png
      fi
      rm -f ./data/background.txt
    fi
    sleep 1
  done
) &

# Activate env and install requirements
. ../venv/bin/activate
if [ ! -f ./data/framarama-init.json ] ; then
  echo "Updating ..." > ./data/background.txt
  [ "$FRAMARAMA_APP_UPDATE_PRECMD" = "" ] || eval "$FRAMARAMA_UPDATE_PRECMD"
  pip install -r requirements/default.txt
  [ "$FRAMARAMA_APP_UPDATE_POSTCMD" = "" ] || eval "$FRAMARAMA_UPDATE_POSTCMD"
fi

# Start main loop
while [ "1" = "1" ] ; do
  echo "Starting ..." > ./data/background.txt

  # Start application
  gunicorn --capture-output -b 0.0.0.0:8000 framarama.wsgi

  sleep 5

done

