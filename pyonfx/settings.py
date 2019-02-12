# -*- coding: utf-8 -*-

class Settings:
	"""
	Class Settings with the following fields:
	"""

	aegisub = False
	"""
	If **True**, PyonFX will automatically open the output with Aegisub at the end of the generation.
	"""

	mpv = True
	"""
	If **True**, PyonFX will automatically open the output with mpv, playing in softsub.
	"""

	mpv_options = {
		"video_file": "",
		"video_start": "",
		"full_screen": False
	}
	"""
	| A dictionary containing some easy to set parameters for mpv player.
	| You can specify **video file path**, **video start** (https://mpv.io/manual/master/#options-start)
	  and if you want to use **full screen** or not.
	| If you don't specify anything, it will automatically assume as video file **meta.video**,
	| as video start **"0"** and it will **not play in full screen**
	"""