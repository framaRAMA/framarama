
# Change to application dir, activate venv and start application
cd "$(realpath "$(dirname $(realpath $0))/../..")"

# Start window manager
openbox-session &

. ../venv/bin/activate
while [ "1" = "1" ] ; do

  # Set startup background
  feh --bg-scale ./common/static/common/background.png

  # Start application
  gunicorn --capture-output -b 0.0.0.0:8000 framarama.wsgi

  sleep 5

done

