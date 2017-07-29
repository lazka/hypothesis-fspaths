#!/bin/bash
# ./run_wine.sh 2.7.12 python
# ./run_wine.sh 2.7.12 cmd
# ./run_wine.sh 3.4.4 python
# ./run_wine.sh 3.4.4 cmd
# ./run_wine.sh 3.5.2 cmd

SCRIPTDIR="$( cd "$( dirname "$0" )" && pwd )"
DIR=$(mktemp -d)
export WINEPREFIX="$DIR/_wine_env"
export WINEDLLOVERRIDES="mscoree,mshtml="
export WINEDEBUG="-all"
mkdir -p "$WINEPREFIX"

VERSION="$1"
TEMP=${VERSION//./}
PYVER=${TEMP:0:2}
DIRNAME="Python"${PYVER}
DESTDIR="$WINEPREFIX/drive_c/$DIRNAME"

if [ "${PYVER}" = "35" ] ; then
    wget -P "$DIR" "https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks"
    chmod a+x "$DIR/winetricks"
    "$DIR/winetricks" -q vcrun2015
    wget -P "$SCRIPTDIR/.cache" -c "https://www.python.org/ftp/python/${VERSION}/python-${VERSION}-embed-win32.zip"
    unzip "$SCRIPTDIR/.cache/python-${VERSION}-embed-win32.zip" -d "$DESTDIR"
    unzip "$DESTDIR/python$PYVER.zip" -d "$DESTDIR/Lib"
    rm -Rf "$DESTDIR/python$PYVER.zip"
    wine reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v Path /t REG_SZ /d "%path%;$(winepath $DESTDIR);$(winepath $DESTDIR/Scripts)"
else
    wget -P "$SCRIPTDIR/.cache" -c "https://www.python.org/ftp/python/$VERSION/python-$VERSION.msi"
    wine msiexec /a "$SCRIPTDIR/.cache/python-$VERSION.msi" /qb
fi

PYTHONEXE="$DESTDIR/python.exe"
PIPEXE="$DESTDIR/Scripts/pip.exe"
wget "https://bootstrap.pypa.io/get-pip.py"
wine "$PYTHONEXE" get-pip.py
rm get-pip.py
wine "$PIPEXE" install pytest coverage hypothesis

if [ "$2" == "cmd" ]; then
    wineconsole --backend=curses
elif [ "$2" == "python" ]; then
    wine "$PYTHONEXE" ${@:3}
else
    wine ${@:2}
fi

exit_code=$?
wineserver --wait
rm -Rf "$DIR"
exit $exit_code
