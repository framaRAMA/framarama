
# Change to application dir, activate venv and start application
cd "$(realpath "$(dirname $(realpath $0))/../..")"

# Start window manager
openbox-session &

# Disable energy features to avoid black screens
[ `which xset` ] && ( xset -dpms ; xset s off )

# Activate env and install requirements
. ../venv/bin/activate
pip install -r requirements.txt

# Start main loop
while [ "1" = "1" ] ; do

  # Set startup background
  feh --bg-scale ./common/static/common/background.png

  # Start application
  gunicorn --capture-output -b 0.0.0.0:8000 framarama.wsgi

  sleep 5

done

