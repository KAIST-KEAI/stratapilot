from .bash import *

# file operation
mkdir = Bash("mkdir")
touch = Bash("touch")
cp = Bash("cp")
mv = Bash("mv")
rm = Bash("rm")
ls = Bash("ls")
tree = Bash("tree")

# tools
grep = Bash("grep")
cut = Bash("cut")
wget = Bash("wget")
gedit = Bash("gedit")
Pkexec_gedit = Pkexec_GUI("gedit")

# system & setting
apt = Bash("apt")
Pkexec_apt = Pkexec("apt")
pip = Bash("pip")
gsettings = Bash("gsettings")
xrandr = Bash("xrandr")

# development
python = Bash("python")
code = Bash("code")

# application
evince = Bash("evince")
<<<<<<< HEAD
rhythmbox_client = Bash("rhythmbox-client")
totem = Bash("totem")
=======
gedit = Bash("gedit")
rhythmbox_client = Bash("rhythmbox-client")
totem = Bash("totem")
libreoffice = Bash("libreoffice")
>>>>>>> aaa5bdd (add multi-parameter open_document function)
