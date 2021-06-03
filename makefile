RM			=	rm -rf
TARGET		=	jetbrains-installer

all:		$(TARGET)

$(TARGET): 
		pyinstaller jetbrains-install.py --onefile

clean:
		$(RM) build/
		$(RM) dist/
		$(RM) jetbrains-install.spec

re:		clean all

.PHONY: all run clean re