RM			=	rm -rf
TARGET		=	ji

all:		$(TARGET)

$(TARGET): 
		pyinstaller $(TARGET).py --onefile

clean:
		$(RM) build/
		$(RM) dist/
		$(RM) *.spec
		$(RM) __pycache__/

re:		clean all

.PHONY: all run clean re